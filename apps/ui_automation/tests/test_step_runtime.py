import asyncio
import os
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse, quote

from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.ui_automation.models import TestCaseStep, LocalExecutionJob
from apps.ui_automation.playwright_engine import PlaywrightTestEngine
from apps.ui_automation.selenium_engine import SeleniumTestEngine
from local_playwright_agent import agent
from local_playwright_agent.step_runtime import (
    CAPABILITY, ACTIONS, ASSERTIONS, prepare_contract, validate_step, resolve_runtime, resolve_step_value,
    needs_runtime_v2, parse_keys, parse_selection, resolve_timeout_ms,
)


def step(action='assert', assertion='textEquals', expected='', value='', selector='#text', timeout=1500):
    return {'action_type': action, 'assert_type': assertion, 'assert_value': expected,
            'input_value': value, 'wait_time': timeout,
            'element': {'locator_strategy': 'css', 'locator_value': selector, 'wait_timeout': 0}}


class StepContractTests(SimpleTestCase):
    def test_model_and_runtime_choices_match(self):
        self.assertEqual(set(dict(TestCaseStep.ACTION_TYPE_CHOICES)), ACTIONS)
        self.assertEqual(set(dict(TestCaseStep.ASSERT_TYPE_CHOICES)), ASSERTIONS)

    def test_invalid_contracts_fail_closed(self):
        for data in [step(action='futureAction'), step(assertion='futureAssertion'),
                     step(assertion='hasAttribute'), step(assertion='countEquals', expected='-1'),
                     step(action='press', value='MadeUpKey'), step(action='selectOption', value='index:-1'),
                     step(action='getText', value='bad.name')]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_step(data)

    def test_missing_runtime_variable_and_literal_extraction(self):
        with self.assertRaisesRegex(ValueError, '未定义'):
            resolve_runtime('${runtime.orderId}', {})
        value = resolve_step_value('id=${runtime.orderId}/${factory()}',
                                   {'orderId': '${factory()}'},
                                   lambda text: text.replace('${factory()}', 'generated'))
        self.assertEqual(value, 'id=${factory()}/generated')
        self.assertEqual(resolve_runtime('${column}', {}), '${column}')

    def test_capability_recurses_into_rows_and_suites(self):
        self.assertFalse(needs_runtime_v2({'steps': [step(action='click')]}))
        self.assertTrue(needs_runtime_v2({'iterations': [{'steps': [step()]}]}))
        self.assertTrue(needs_runtime_v2({'suite_items': [{'payload': {'steps': [step(action='getText', value='id')]}}]}))

    def test_unused_editor_values_do_not_resolve_stale_variables(self):
        data = step(assertion='isVisible', expected='${runtime.oldValue}', value='${runtime.oldName}')
        self.assertEqual(prepare_contract(data, {})['assert_value'], '')

    def test_selection_and_key_contract(self):
        self.assertEqual(parse_selection('label:北京'), {'label': '北京'})
        self.assertEqual(parse_selection('index:0'), {'index': 0})
        self.assertEqual(parse_selection('value:a:b'), {'value': 'a:b'})
        self.assertEqual(parse_keys('ControlOrMeta+Shift+a'), ['ControlOrMeta', 'Shift', 'a'])

    def test_element_timeout_is_shared_by_actions_and_assertions(self):
        self.assertEqual(resolve_timeout_ms({'wait_timeout': 60}, 1000), 60_000)
        self.assertEqual(resolve_timeout_ms({'wait_timeout': 0}, 1500), 1500)
        self.assertEqual(resolve_timeout_ms(), 60_000)

    def test_server_assertions_use_element_timeout(self):
        data = SimpleNamespace(**step(assertion='isVisible', timeout=1000))
        element = {'locator_strategy': 'css', 'locator_value': '#text', 'wait_timeout': 60}

        playwright_engine = PlaywrightTestEngine()
        playwright_engine.page = object()
        with patch('apps.ui_automation.playwright_engine.playwright_locator', return_value=object()), \
                patch('apps.ui_automation.playwright_engine.execute_playwright_extension',
                      new_callable=AsyncMock, return_value='ok') as execute:
            result = asyncio.run(playwright_engine.execute_step(data, element))
            self.assertTrue(result[0])
            self.assertEqual(execute.call_args.args[4], 60_000)

        selenium_engine = SeleniumTestEngine()
        selenium_engine.driver = object()
        with patch('apps.ui_automation.selenium_engine.execute_selenium_extension',
                   return_value='ok') as execute:
            result = selenium_engine.execute_step(data, element)
            self.assertTrue(result[0])
            self.assertEqual(execute.call_args.args[5], 60_000)

    def test_server_engines_return_failure_for_unknown_operations(self):
        for engine in [PlaywrightTestEngine(), SeleniumTestEngine()]:
            data = step(action='newUnknownAction')
            if isinstance(engine, PlaywrightTestEngine):
                result = asyncio.run(engine.execute_step(SimpleNamespace(**data), {}))
            else:
                result = engine.execute_step(SimpleNamespace(**data), {})
            self.assertFalse(result[0])
            self.assertIn('不支持', result[1])

    def test_runtime_scopes_are_independent(self):
        for cls in [PlaywrightTestEngine, SeleniumTestEngine]:
            a, b = cls(), cls()
            a.runtime_variables['orderId'] = 'one'
            self.assertEqual(b.runtime_variables, {})


class StepApiTests(APITestCase):
    def setUp(self):
        from .test_local_runner import LocalRunnerApiTests
        LocalRunnerApiTests.setUp(self)

    def tearDown(self):
        from .test_local_runner import LocalRunnerApiTests
        LocalRunnerApiTests.tearDown(self)

    def test_invalid_update_rolls_back_existing_steps(self):
        original = list(self.test_case.steps.values_list('id', flat=True))
        response = self.client.patch(f'/api/ui-automation/test-cases/{self.test_case.id}/',
                                    {'steps': [step(action='unknown')]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.test_case.steps.values_list('id', flat=True)), original)

    def test_new_steps_roundtrip_and_old_runner_rejected_without_consuming_job(self):
        element_id = self.test_case.steps.first().element_id
        steps = [step(action='getText', value='orderId'),
                 step(action='fill', value='${runtime.orderId}'),
                 step(assertion='hasAttribute', value='title', expected='saved'),
                 step(assertion='urlContains', expected='example.test')]
        for item in steps:
            item.pop('element')
            item['element_id'] = element_id
        response = self.client.patch(f'/api/ui-automation/test-cases/{self.test_case.id}/',
                                    {'steps': steps}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['steps'][0]['input_value'], 'orderId')
        created = self.client.post(f'/api/ui-automation/test-cases/{self.test_case.id}/run-local/',
                                   {}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        code = parse_qs(urlparse(created.data['protocol_url']).query)['code'][0]
        old = self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                               {'launch_code': code, 'protocol_version': 3}, format='json')
        self.assertEqual(old.status_code, 400)
        self.assertIn('0.5', old.data['detail'])
        self.assertEqual(LocalExecutionJob.objects.get(pk=created.data['job_id']).status, 'waiting_runner')
        new = self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                               {'launch_code': code, 'protocol_version': 3, 'capabilities': [CAPABILITY]}, format='json')
        self.assertEqual(new.status_code, 200, new.data)
        self.assertEqual(new.data['payload']['steps'][1]['input_value'], '${runtime.orderId}')


HTML = '''<div id="text">处理中</div><input id="input"><input id="box" type="checkbox">
<select id="select"><option value="a">甲</option><option value="b">乙</option></select>
<button id="disabled" disabled>不能操作</button><div class="item">a</div><div class="item">b</div>
<div id="hidden" hidden>hidden</div><div id="remove">remove</div>
<script>document.querySelector('#input').addEventListener('keydown', e => {
if(e.key === 'Enter') document.querySelector('#input').setAttribute('data-enter', 'yes');
});</script>'''


def journey():
    return [
        step(expected='订单-42'),
        step(assertion='textContains', expected='42'),
        step(action='getText', value='orderId'),
        step(action='fill', value='${runtime.orderId}', selector='#input'),
        step(assertion='valueEquals', expected='订单-42', selector='#input'),
        step(action='press', value='ControlOrMeta+a', selector='#input'),
        step(action='press', value='x', selector='#input'),
        step(assertion='valueEquals', expected='x', selector='#input'),
        step(action='fill', value='${runtime.orderId}', selector='#input'),
        step(action='press', value='Enter', selector='#input'),
        step(assertion='hasAttribute', value='data-enter', expected='yes', selector='#input'),
        step(action='check', selector='#box'), step(action='check', selector='#box'),
        step(assertion='isChecked', selector='#box'), step(action='uncheck', selector='#box'),
        step(action='uncheck', selector='#box'), step(assertion='notChecked', selector='#box'),
        step(action='selectOption', value='label:乙', selector='#select'),
        step(assertion='valueEquals', expected='b', selector='#select'),
        step(action='selectOption', value='index:0', selector='#select'),
        step(assertion='valueEquals', expected='a', selector='#select'),
        step(action='selectOption', value='value:b', selector='#select'),
        step(assertion='countEquals', expected='2', selector='.item'),
        step(assertion='notExists', selector='#remove'),
        step(assertion='notVisible', selector='#hidden'), step(assertion='isVisible'),
        step(assertion='exists', selector='.item'),
        step(assertion='isDisabled', selector='#disabled'), step(assertion='isEnabled', selector='#input'),
        step(assertion='urlContains', expected='about:blank', selector=''),
        step(assertion='urlEquals', expected='about:blank', selector=''),
    ]


@skipUnless(os.environ.get('TESTHUB_BROWSER_TESTS') == '1', 'Set TESTHUB_BROWSER_TESTS=1 for real browser checks')
class BrowserStepTests(SimpleTestCase):
    def test_local_and_server_playwright_journeys(self):
        async def run():
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    for local in [True, False]:
                        context = await browser.new_context()
                        page = await context.new_page()
                        await page.set_content(HTML)
                        await page.evaluate("setTimeout(() => { document.querySelector('#text').innerText='订单-42'; document.querySelector('#remove').remove(); }, 250)")
                        engine = PlaywrightTestEngine()
                        engine.page, engine.context = page, context
                        variables = {}
                        for data in journey():
                            with self.subTest(local=local, action=data):
                                if local:
                                    await agent._execute_step(page, context, data, {}, variables)
                                else:
                                    result = await engine.execute_step(SimpleNamespace(**data), data['element'])
                                    self.assertTrue(result[0], result[1])
                        for data in [step(expected='never', timeout=100), step(action='unknown'),
                                     step(assertion='unknown'), step(action='fill', value='${runtime.missing}', selector='#input')]:
                            if local:
                                with self.assertRaises((ValueError, AssertionError)):
                                    await agent._execute_step(page, context, data, {}, variables)
                            else:
                                result = await engine.execute_step(SimpleNamespace(**data), data['element'])
                                self.assertFalse(result[0], result[1])
                        # An extraction in one run cannot satisfy a fresh local scope.
                        with self.assertRaisesRegex(ValueError, '未定义'):
                            await agent._execute_step(page, context, step(action='fill', value='${runtime.orderId}'), {}, {})
                        await context.close()
                finally:
                    await browser.close()
        asyncio.run(run())

    def test_selenium_journey(self):
        from selenium import webdriver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        driver = webdriver.Chrome(options=options)
        try:
            driver.get('data:text/html;charset=utf-8,' + quote(HTML))
            driver.execute_script("setTimeout(() => { document.querySelector('#text').innerText='订单-42'; document.querySelector('#remove').remove(); }, 250)")
            engine = SeleniumTestEngine()
            engine.driver = driver
            for data in journey():
                if data['assert_type'] == 'urlEquals':
                    data['assert_value'] = driver.current_url
                if data['assert_type'] == 'urlContains':
                    data['assert_value'] = 'data:text/html'
                with self.subTest(action=data):
                    result = engine.execute_step(SimpleNamespace(**data), data['element'])
                    self.assertTrue(result[0], result[1])
            for data in [step(expected='never', timeout=100), step(action='unknown'),
                         step(assertion='unknown'), step(action='fill', value='${runtime.missing}', selector='#input')]:
                result = engine.execute_step(SimpleNamespace(**data), data['element'])
                self.assertFalse(result[0], result[1])
        finally:
            driver.quit()
