import asyncio
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.ui_automation.data_driven import execute_rows, resolve_parameters
from apps.ui_automation.models import (
    TestCase, TestCaseExecution, TestCaseStep, TestSuite, TestSuiteTestCase, UiProject,
)
from apps.ui_automation.test_executor import TestExecutor


class FakeSelenium:
    instances = []

    def __init__(self, **kwargs):
        self.inputs = []
        self.stopped = False
        self.__class__.instances.append(self)

    def start(self):
        pass

    def navigate(self, url):
        return True, 'navigated'

    def stop(self):
        self.stopped = True

    def capture_screenshot(self):
        return None

    def execute_step(self, step, element):
        self.inputs.append((step.input_value, step.assert_value))
        return step.input_value != 'fail', 'fake step', None


class FakePlaywright(FakeSelenium):
    async def start(self):
        pass

    async def stop(self):
        self.stopped = True

    async def navigate(self, url):
        return True, 'navigated'

    async def capture_screenshot(self):
        return None

    async def execute_step(self, step, element):
        return super().execute_step(step, element)


class DataDrivenApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='data-owner', password='password')
        self.project = UiProject.objects.create(name='Data project', owner=self.user, base_url='https://example.test')
        self.case = TestCase.objects.create(
            name='Login', project=self.project, created_by=self.user, data_driven_enabled=True,
            data_rows=[{'username': 'first', 'expected': 'one'},
                       {'username': 'fail', 'expected': 'two'},
                       {'username': 'last', 'expected': 'three'}],
        )
        self.step = TestCaseStep.objects.create(
            test_case=self.case, step_number=1, action_type='fill',
            input_value='${username}', assert_value='${expected}',
        )
        self.client.force_authenticate(self.user)
        FakeSelenium.instances = []
        FakePlaywright.instances = []
        self.url = f'/api/ui-automation/test-cases/{self.case.id}/'

    def test_rows_run_in_isolated_sessions_and_failure_does_not_skip_next_row(self):
        with patch('apps.ui_automation.selenium_engine.SeleniumTestEngine', FakeSelenium):
            executions = execute_rows(self.case, self.user, engine='selenium')
        self.assertEqual([item.status for item in executions], ['passed', 'failed', 'passed'])
        self.assertEqual([item.data_index for item in executions], [1, 2, 3])
        self.assertEqual(len({item.batch_id for item in executions}), 1)
        self.assertEqual([engine.inputs for engine in FakeSelenium.instances],
                         [[('first', 'one')], [('fail', 'two')], [('last', 'three')]])
        self.assertTrue(all(engine.stopped for engine in FakeSelenium.instances))
        self.step.refresh_from_db()
        self.assertEqual(self.step.input_value, '${username}')

    def test_playwright_rows_receive_parameters_without_async_orm(self):
        with patch('apps.ui_automation.playwright_engine.PlaywrightTestEngine', FakePlaywright):
            executions = execute_rows(self.case, self.user)
        self.assertEqual([item.status for item in executions], ['passed', 'failed', 'passed'])
        self.assertEqual(len(FakePlaywright.instances), 3)
        self.assertTrue(all(engine.stopped for engine in FakePlaywright.instances))

    def test_retry_uses_the_original_row_snapshot(self):
        with patch('apps.ui_automation.selenium_engine.SeleniumTestEngine', FakeSelenium):
            previous = execute_rows(self.case, self.user, engine='selenium')[2]
            self.case.data_rows = [{'username': 'changed', 'expected': 'changed'}]
            self.case.save()
            retry = execute_rows(self.case, self.user, engine='selenium',
                                 request_data={'retry_execution_id': previous.id})
        self.assertEqual(len(retry), 1)
        self.assertEqual(retry[0].data_index, 3)
        self.assertEqual(FakeSelenium.instances[-1].inputs, [('last', 'three')])
        self.assertNotEqual(retry[0].batch_id, previous.batch_id)

    def test_invalid_config_and_missing_parameter_are_rejected_before_execution(self):
        for rows in ([{'bad-column': 'x'}], [{'a': 1}, {'b': 2}], [{'a': []}], []):
            response = self.client.patch(self.url, {'data_rows': rows}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        self.case.data_rows = [{'missing': 'x'}]
        self.case.save()
        response = self.client.post(self.url + 'run/', {'engine': 'selenium'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(TestCaseExecution.objects.count(), 0)

    def test_unbound_rows_are_rejected_instead_of_reusing_fixed_inputs(self):
        self.step.input_value = 'fixed-account@example.com'
        self.step.assert_value = 'fixed result'
        self.step.save(update_fields=['input_value', 'assert_value'])

        response = self.client.post(self.url + 'run/', {'engine': 'selenium'}, format='json')

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('尚未绑定任何数据列', str(response.data))
        self.assertEqual(TestCaseExecution.objects.count(), 0)

    def test_run_returns_pollable_batch_and_unauthorized_users_cannot_start_it(self):
        with self.captureOnCommitCallbacks(execute=False):
            response = self.client.post(self.url + 'run/', {'engine': 'selenium'}, format='json')
        self.assertEqual(response.status_code, 202, response.data)
        detail = self.client.get(f"/api/ui-automation/test-case-executions/{response.data['execution_id']}/")
        self.assertEqual(len(detail.data['data_results']), 3)
        self.assertEqual([item['status'] for item in detail.data['data_results']], ['pending'] * 3)
        other = get_user_model().objects.create_user(username='data-other', password='password')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(self.url + 'run/', {}, format='json').status_code, 404)
        self.assertEqual(self.client.get(f"/api/ui-automation/test-case-executions/{response.data['execution_id']}/").status_code, 404)

    def test_case_copy_keeps_rows_and_disabling_retains_data(self):
        response = self.client.post(self.url + 'copy_case/', {}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['data_rows'], self.case.data_rows)
        response = self.client.patch(self.url, {'data_driven_enabled': False}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data_rows'], self.case.data_rows)

    def test_suite_counts_row_runs_and_ordinary_cases(self):
        ordinary = TestCase.objects.create(name='Plain', project=self.project, created_by=self.user)
        TestCaseStep.objects.create(test_case=ordinary, step_number=1, action_type='wait')
        suite = TestSuite.objects.create(name='Suite', project=self.project)
        TestSuiteTestCase.objects.create(test_suite=suite, test_case=self.case, order=1)
        TestSuiteTestCase.objects.create(test_suite=suite, test_case=ordinary, order=2)
        executor = TestExecutor(suite, engine='selenium', executed_by=self.user)
        executor.create_execution_record()
        executor.get_test_cases()
        with patch('apps.ui_automation.selenium_engine.SeleniumTestEngine', FakeSelenium):
            executor.run_data_driven()
        self.assertEqual(executor.execution.total_cases, 4)
        self.assertEqual(executor.execution.passed_cases, 3)
        self.assertEqual(executor.execution.failed_cases, 1)
        self.assertEqual(len(executor.execution.result_data['test_cases']), 4)

    def test_mcp_batch_results_include_rows_without_image_payloads(self):
        import uuid
        from apps.mcp.tests.utils import ctx_with_jwt
        from apps.mcp.tools import get_ui_execution
        batch = uuid.uuid4()
        parent = TestCaseExecution.objects.create(test_case=self.case, project=self.project,
                                                 created_by=self.user, batch_id=batch, status='failed')
        TestCaseExecution.objects.create(test_case=self.case, project=self.project,
                                         created_by=self.user, batch_id=batch, data_index=1,
                                         data_row={'username': 'first'}, status='failed',
                                         screenshots=[{'url': 'data:image/png;base64,large', 'description': 'failure'}])
        ctx, _ = ctx_with_jwt(self.user)
        result = get_ui_execution(ctx, parent.id)
        self.assertEqual(result['data_results'][0]['data_label'], 'first')
        self.assertNotIn('url', result['data_results'][0]['screenshots'][0])

    def test_invalid_suite_case_does_not_skip_the_next_case(self):
        self.case.data_rows = [{'missing': 'value'}]
        self.case.save()
        plain = TestCase.objects.create(name='Next', project=self.project, created_by=self.user)
        TestCaseStep.objects.create(test_case=plain, step_number=1, action_type='wait')
        suite = TestSuite.objects.create(name='Validation suite', project=self.project)
        executor = TestExecutor(suite, engine='selenium', executed_by=self.user)
        executor.create_execution_record()
        executor.test_cases = [self.case, plain]
        with patch('apps.ui_automation.selenium_engine.SeleniumTestEngine', FakeSelenium):
            executor.run_data_driven()
        self.assertEqual(executor.execution.total_cases, 2)
        self.assertEqual([item['status'] for item in executor.results], ['error', 'passed'])

    def test_local_payload_is_parameterized_and_complete_requires_every_row(self):
        response = self.client.post(self.url + 'run-local/', {'browser': 'chrome'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        code = parse_qs(urlparse(response.data['protocol_url']).query)['code'][0]
        claim = self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                                 {'launch_code': code, 'protocol_version': 3}, format='json')
        payload = claim.data['payload']
        self.assertEqual(payload['protocol_version'], 2)
        self.assertEqual([item['steps'][0]['input_value'] for item in payload['iterations']], ['first', 'fail', 'last'])
        authorization = f"Bearer {claim.data['upload_token']}"
        complete_url = f"/api/ui-automation/local-runner/jobs/{claim.data['job_id']}/complete/"
        rows = [{'data_index': i, 'success': i != 2, 'duration': 1, 'step_results': []} for i in (1, 2, 3)]
        complete = self.client.post(complete_url, {'success': True, 'row_results': rows}, format='json', HTTP_AUTHORIZATION=authorization)
        self.assertEqual(complete.status_code, 200, complete.data)
        self.assertEqual(complete.data['status'], 'failed')
        detail = self.client.get(f"/api/ui-automation/test-case-executions/{response.data['execution_id']}/")
        self.assertEqual([item['status'] for item in detail.data['data_results']], ['passed', 'failed', 'passed'])

    def test_local_retry_uses_only_the_original_data_row_snapshot(self):
        previous = TestCaseExecution.objects.create(
            test_case=self.case, project=self.project, created_by=self.user,
            status='failed', engine='playwright', browser='chrome',
            data_index=2, data_row={'username': 'original', 'expected': 'snapshot'},
        )
        self.case.data_rows = [{'username': 'changed', 'expected': 'changed'}]
        self.case.save(update_fields=['data_rows'])

        response = self.client.post(
            self.url + 'run-local/',
            {'browser': 'chrome', 'retry_execution_id': previous.id},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        code = parse_qs(urlparse(response.data['protocol_url']).query)['code'][0]
        claim = self.client.post(
            '/api/ui-automation/local-runner/jobs/claim/',
            {'launch_code': code, 'protocol_version': 3},
            format='json',
        )

        self.assertEqual(claim.status_code, 200, claim.data)
        self.assertEqual(len(claim.data['payload']['iterations']), 1)
        iteration = claim.data['payload']['iterations'][0]
        self.assertEqual(iteration['data_index'], 2)
        self.assertEqual(iteration['steps'][0]['input_value'], 'original')
        self.assertEqual(iteration['steps'][0]['assert_value'], 'snapshot')

    def test_old_local_runner_is_rejected_before_claim_and_finishes_all_rows(self):
        response = self.client.post(self.url + 'run-local/', {}, format='json')
        code = parse_qs(urlparse(response.data['protocol_url']).query)['code'][0]
        claim = self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                                 {'launch_code': code}, format='json',
                                 HTTP_USER_AGENT='TestHub-Local-Runner/0.2')
        self.assertEqual(claim.status_code, 400)
        self.assertIn('需要更新', str(claim.data))
        self.assertEqual(list(TestCaseExecution.objects.values_list('status', flat=True)), ['failed'] * 4)
        parent = TestCaseExecution.objects.get(pk=response.data['execution_id'])
        self.assertIsNotNone(parent.finished_at)
        self.assertIsNone(parent.local_job.claimed_at)

    def test_incomplete_local_results_finish_failed_instead_of_polling_forever(self):
        response = self.client.post(self.url + 'run-local/', {}, format='json')
        code = parse_qs(urlparse(response.data['protocol_url']).query)['code'][0]
        claim = self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                                 {'launch_code': code}, format='json',
                                 HTTP_USER_AGENT='TestHub-Local-Runner/0.3')
        self.assertEqual(claim.status_code, 200)
        complete = self.client.post(
            f"/api/ui-automation/local-runner/jobs/{claim.data['job_id']}/complete/",
            {'success': True}, format='json',
            HTTP_AUTHORIZATION=f"Bearer {claim.data['upload_token']}",
        )
        self.assertEqual(complete.status_code, 400)
        parent = TestCaseExecution.objects.get(pk=response.data['execution_id'])
        self.assertEqual(parent.local_job.status, 'failed')
        self.assertEqual(parent.status, 'failed')
        self.assertIn('完整数据行', parent.error_message)
        self.assertEqual(list(TestCaseExecution.objects.values_list('status', flat=True)), ['failed'] * 4)


class ParameterTests(SimpleTestCase):
    def test_parameters_preserve_function_syntax_and_false_and_empty_values(self):
        self.assertEqual(resolve_parameters('${a}/${b}/${c}/${timestamp()}', {'a': False, 'b': 0, 'c': None}),
                         'False/0//${timestamp()}')

    def test_local_agent_runs_all_rows_after_a_failure(self):
        spec = importlib.util.spec_from_file_location('local_data_agent', Path(__file__).resolve().parents[3] / 'local_playwright_agent/agent.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        iterations = [{'data_index': i, 'steps': [{'step_number': 1, 'action_type': 'fill', 'input_value': str(i)}]} for i in (1, 2, 3)]
        class Client:
            job = {'job_id': 'test', 'payload': {'iterations': iterations, 'assets': [], 'case': {}, 'headless': True}}
            def complete(self, *args, **kwargs):
                self.results = kwargs['row_results']
            def event(self, *args, **kwargs):
                pass
        async def row_runner(client, work_dir):
            index = client.index
            client.complete(index != 2, 1, [], '' if index != 2 else 'failed')
            return index != 2
        original = module._run_job
        client = Client()
        with tempfile.TemporaryDirectory() as folder, patch.object(module, '_run_job', row_runner):
            success = asyncio.run(original(client, Path(folder)))
        self.assertFalse(success)
        self.assertEqual([item['data_index'] for item in client.results], [1, 2, 3])
