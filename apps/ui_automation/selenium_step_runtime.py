"""Selenium implementation of the portable step contract."""
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from local_playwright_agent.step_runtime import PAGE_ASSERTIONS, parse_keys, parse_selection


def execute_selenium_extension(driver, locator_factory, element_data, step, variables, timeout):
    action = step['action_type']
    value = step['input_value']
    assertion = step.get('assert_type')
    expected = step.get('assert_value', '')
    wait = WebDriverWait(driver, timeout / 1000, poll_frequency=0.1,
                         ignored_exceptions=(NoSuchElementException, StaleElementReferenceException))
    locator = None if action == 'assert' and assertion in PAGE_ASSERTIONS else locator_factory(
        element_data.get('locator_strategy', 'css'), element_data.get('locator_value', ''))

    if action == 'assert':
        def matches(browser):
            if assertion in PAGE_ASSERTIONS:
                return browser.current_url == expected if assertion == 'urlEquals' else expected in browser.current_url
            elements = browser.find_elements(*locator)
            if assertion == 'countEquals':
                return len(elements) == int(expected)
            if assertion == 'exists':
                return bool(elements)
            if assertion == 'notExists':
                return not elements
            if len(elements) > 1:
                raise ValueError('断言需要唯一目标元素，请收窄定位器')
            if not elements:
                return assertion == 'notVisible'
            element = elements[0]
            if assertion in {'textContains', 'textEquals'}:
                actual = browser.execute_script('return arguments[0].innerText', element)
                return expected in actual if assertion == 'textContains' else expected == actual
            if assertion == 'hasAttribute':
                return element.get_dom_attribute(value) == expected
            if assertion == 'valueEquals':
                return element.get_property('value') == expected
            if assertion in {'isVisible', 'notVisible'}:
                return element.is_displayed() == (assertion == 'isVisible')
            if assertion in {'isChecked', 'notChecked'}:
                if element.get_attribute('type') not in {'checkbox', 'radio'}:
                    raise ValueError('选中状态断言需要 checkbox 或 radio 元素')
                return element.is_selected() == (assertion == 'isChecked')
            if assertion in {'isEnabled', 'isDisabled'}:
                enabled = element.is_enabled() and element.get_attribute('aria-disabled') != 'true'
                return enabled == (assertion == 'isEnabled')
            raise ValueError(f'不支持的断言类型: {assertion}')
        wait.until(matches, message=f'断言未在 {timeout}ms 内满足: {assertion}，期望={expected!r}')
        return f'断言通过: {assertion}'

    def unique_element(browser):
        elements = browser.find_elements(*locator)
        if len(elements) > 1:
            raise ValueError('操作需要唯一目标元素，请收窄定位器')
        if not elements:
            return False
        element = elements[0]
        return element if action == 'getText' or (element.is_displayed() and element.is_enabled()) else False

    element = wait.until(unique_element)
    if action == 'getText':
        text = driver.execute_script('return arguments[0].innerText', element)
        if value:
            variables[value] = text
            return f'文本已保存到运行变量 runtime.{value}'
        return f'获取文本: {text}'
    if action == 'selectOption':
        selection = parse_selection(value)
        mode, option = next(iter(selection.items()))
        select = Select(element)
        {'value': select.select_by_value, 'label': select.select_by_visible_text,
         'index': select.select_by_index}[mode](option)
    elif action in {'check', 'uncheck'}:
        if element.get_attribute('type') not in {'checkbox', 'radio'}:
            raise ValueError('勾选操作需要 checkbox 或 radio 元素')
        desired = action == 'check'
        if element.is_selected() != desired:
            element.click()
        wait.until(lambda browser: browser.find_element(*locator).is_selected() == desired,
                   message='控件未达到目标选中状态')
    elif action == 'press':
        parts = parse_keys(value)
        mapping = {'Control': Keys.CONTROL, 'Meta': Keys.META, 'Alt': Keys.ALT,
                   'Shift': Keys.SHIFT, 'ControlOrMeta': Keys.META if 'mac' in str(
                       driver.capabilities.get('platformName', '')).lower() else Keys.CONTROL,
                   'Enter': Keys.ENTER, 'Tab': Keys.TAB, 'Escape': Keys.ESCAPE,
                   'Backspace': Keys.BACKSPACE, 'Delete': Keys.DELETE, 'Space': Keys.SPACE,
                   'ArrowUp': Keys.ARROW_UP, 'ArrowDown': Keys.ARROW_DOWN,
                   'ArrowLeft': Keys.ARROW_LEFT, 'ArrowRight': Keys.ARROW_RIGHT,
                   'Home': Keys.HOME, 'End': Keys.END, 'PageUp': Keys.PAGE_UP,
                   'PageDown': Keys.PAGE_DOWN, 'Insert': Keys.INSERT,
                   **{f'F{i}': getattr(Keys, f'F{i}') for i in range(1, 13)}}
        # send_keys focuses the element without an extra click (which could toggle it).
        modifiers = [mapping[key] for key in parts[:-1]]
        element.send_keys(*modifiers, mapping.get(parts[-1], parts[-1]), Keys.NULL)
    else:
        raise ValueError(f'不支持的操作类型: {action}')
    return f'{action} 执行成功'
