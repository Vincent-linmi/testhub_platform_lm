"""Portable step contract shared by the server and the packaged local runner."""
import json
import re

ACTIONS = {'click', 'fill', 'getText', 'waitFor', 'waitForEnabled', 'hover', 'scroll',
           'screenshot', 'assert', 'wait', 'switchTab', 'uploadFile',
           'selectOption', 'check', 'uncheck', 'press'}
ASSERTIONS = {'textContains', 'textEquals', 'isVisible', 'exists', 'hasAttribute',
              'notVisible', 'notExists', 'valueEquals', 'isChecked', 'notChecked',
              'isEnabled', 'isDisabled', 'countEquals', 'urlEquals', 'urlContains'}
PAGE_ASSERTIONS = {'urlEquals', 'urlContains'}
EXTENDED_ACTIONS = {'assert', 'selectOption', 'check', 'uncheck', 'press', 'getText'}
RUNNER_VERSION = '0.5'
CAPABILITY = 'step-runtime-v2'
DEFAULT_TIMEOUT_MS = 60_000
VARIABLE_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
RUNTIME_REFERENCE = re.compile(r'\$\{runtime\.([^}]+)\}')
MODIFIERS = {'Control', 'Shift', 'Alt', 'Meta', 'ControlOrMeta'}
KEYS = {'Enter', 'Tab', 'Escape', 'Backspace', 'Delete', 'Space', 'ArrowUp',
        'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'PageUp', 'PageDown',
        'Insert', *{f'F{i}' for i in range(1, 13)}}


def resolve_timeout_ms(element=None, step_wait_time=None):
    """Return the maximum wait for an element operation or assertion."""
    element_timeout = (element or {}).get('wait_timeout')
    if element_timeout is not None and element_timeout > 0:
        return int(element_timeout * 1000)
    if step_wait_time is not None and step_wait_time > 0:
        return int(step_wait_time)
    return DEFAULT_TIMEOUT_MS


def resolve_runtime(value, variables):
    def replace(match):
        name = match.group(1)
        if name not in variables:
            raise ValueError(f'运行变量未定义: runtime.{name}')
        return str(variables[name])
    return RUNTIME_REFERENCE.sub(replace, value or '')


def resolve_step_value(value, variables, external_resolver):
    # Resolve factory expressions only in literal segments, never inside extracted data.
    pieces, previous = [], 0
    for match in RUNTIME_REFERENCE.finditer(value or ''):
        pieces.extend([external_resolver(value[previous:match.start()]),
                       resolve_runtime(match.group(0), variables)])
        previous = match.end()
    pieces.append(external_resolver((value or '')[previous:]))
    return ''.join(pieces)


def prepare_contract(step, variables, external_resolver=lambda value: value):
    action = step['action_type']
    assertion = step.get('assert_type', '')
    uses_input = action in {'fill', 'getText', 'selectOption', 'press', 'switchTab'} or (
        action == 'assert' and assertion == 'hasAttribute')
    uses_expected = action == 'assert' and assertion in {
        'textContains', 'textEquals', 'hasAttribute', 'valueEquals', 'countEquals',
        'urlEquals', 'urlContains'}
    contract = {'action_type': action, 'assert_type': assertion,
                'input_value': resolve_step_value(step.get('input_value', ''), variables, external_resolver) if uses_input else '',
                'assert_value': resolve_step_value(step.get('assert_value', ''), variables, external_resolver) if uses_expected else ''}
    validate_step(contract)
    return contract


def parse_selection(value):
    mode, separator, option = value.partition(':')
    if not separator or mode not in {'value', 'label', 'index'}:
        return {'value': value}
    if mode == 'index':
        if not option.isdigit():
            raise ValueError('下拉索引必须为非负整数，例如 index:0')
        return {'index': int(option)}
    return {mode: option}


def parse_keys(value):
    parts = value.split('+')
    if (not parts or any(key not in MODIFIERS for key in parts[:-1])
            or len(set(parts[:-1])) != len(parts[:-1])
            or not (len(parts[-1]) == 1 or parts[-1] in KEYS)):
        raise ValueError('按键格式无效，例如 Enter、Tab、ControlOrMeta+a')
    return parts


def validate_step(step, *, templates=False):
    action = step.get('action_type')
    if action not in ACTIONS:
        raise ValueError(f'不支持的操作类型: {action}')
    value = step.get('input_value') or ''
    assertion = step.get('assert_type')
    expected = step.get('assert_value') or ''
    if not isinstance(value, str) or not isinstance(expected, str):
        raise ValueError('输入值和断言期望值必须为字符串')
    if action == 'assert':
        if assertion not in ASSERTIONS:
            raise ValueError(f'不支持的断言类型: {assertion}')
        if assertion == 'hasAttribute' and not value.strip():
            raise ValueError('属性断言必须填写属性名称')
        if assertion == 'countEquals' and not (templates and '${' in expected):
            if not expected.isdigit():
                raise ValueError('元素数量必须为非负整数')
    if action == 'getText' and value and not VARIABLE_NAME.fullmatch(value):
        raise ValueError('变量名须以字母或下划线开头，仅包含字母、数字、下划线')
    if not (templates and '${' in value):
        if action == 'selectOption':
            parse_selection(value)
        if action == 'press':
            parse_keys(value)


def needs_runtime_v2(payload):
    for step in payload.get('steps', []):
        if (step['action_type'] in EXTENDED_ACTIONS - {'getText'}
                or (step['action_type'] == 'getText' and step.get('input_value'))
                or '${runtime.' in step.get('input_value', '')
                or '${runtime.' in step.get('assert_value', '')):
            return True
    return any(needs_runtime_v2(row) for row in payload.get('iterations', [])) or any(
        needs_runtime_v2(item['payload']) for item in payload.get('suite_items', []))


def playwright_locator(page, element):
    strategy = (element.get('locator_strategy') or 'css').lower()
    value = element.get('locator_value', '')
    if strategy == 'id':
        return page.locator(f'[id={json.dumps(value)}]')
    if strategy in {'css', 'css selector'}:
        return page.locator(value)
    if strategy == 'xpath':
        return page.locator(f'xpath={value}')
    if strategy == 'name':
        return page.locator(f'[name={json.dumps(value)}]')
    methods = {'text': 'get_by_text', 'placeholder': 'get_by_placeholder',
               'role': 'get_by_role', 'label': 'get_by_label', 'title': 'get_by_title',
               'test-id': 'get_by_test_id'}
    if strategy in methods:
        return getattr(page, methods[strategy])(value)
    raise ValueError(f'不支持的定位策略: {strategy}')


async def execute_playwright_extension(page, locator, step, variables, timeout, force=False):
    from playwright.async_api import expect

    action = step['action_type']
    value = step.get('input_value') or ''
    if action == 'assert':
        assertion = step['assert_type']
        expected = step.get('assert_value') or ''
        target = expect(page if assertion in PAGE_ASSERTIONS else locator)
        if assertion == 'textContains':
            await target.to_contain_text(re.compile(re.escape(expected)), use_inner_text=True, timeout=timeout)
        elif assertion == 'textEquals':
            # Regex preserves exact whitespace instead of Playwright string normalization.
            await target.to_have_text(re.compile(r'^' + re.escape(expected) + r'(?![\s\S])'),
                                      use_inner_text=True, timeout=timeout)
        elif assertion == 'hasAttribute':
            await target.to_have_attribute(value, expected, timeout=timeout)
        elif assertion == 'valueEquals':
            await target.to_have_value(expected, timeout=timeout)
        elif assertion == 'countEquals':
            await target.to_have_count(int(expected), timeout=timeout)
        elif assertion == 'exists':
            await target.not_to_have_count(0, timeout=timeout)
        elif assertion == 'notExists':
            await target.to_have_count(0, timeout=timeout)
        elif assertion == 'urlEquals':
            await target.to_have_url(expected, timeout=timeout)
        elif assertion == 'urlContains':
            await target.to_have_url(re.compile(re.escape(expected)), timeout=timeout)
        else:
            method = {'isVisible': 'to_be_visible', 'notVisible': 'to_be_hidden',
                      'isChecked': 'to_be_checked', 'notChecked': 'not_to_be_checked',
                      'isEnabled': 'to_be_enabled', 'isDisabled': 'to_be_disabled'}[assertion]
            await getattr(target, method)(timeout=timeout)
        return f'断言通过: {assertion}'
    if action == 'selectOption':
        await locator.select_option(**parse_selection(value), timeout=timeout, force=force)
    elif action in {'check', 'uncheck'}:
        await locator.set_checked(action == 'check', timeout=timeout, force=force)
    elif action == 'press':
        parse_keys(value)
        await locator.press(value, timeout=timeout)
    elif action == 'getText':
        text = await locator.inner_text(timeout=timeout)
        if value:
            variables[value] = text
            return f'文本已保存到运行变量 runtime.{value}'
        return f'获取文本: {text}'
    else:
        raise ValueError(f'不支持的操作类型: {action}')
    return f'{action} 执行成功'
