"""Data rows are snapshots; each row runs in a fresh browser session."""
import asyncio
import copy
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.utils import timezone
from rest_framework.exceptions import ValidationError

COLUMN_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
PARAMETER = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')
MAX_ROWS = 1000


def validate_rows(rows):
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValidationError({'data_rows': f'数据必须是数组，最多 {MAX_ROWS} 行'})
    columns = None
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not row or len(row) > 100:
            raise ValidationError({'data_rows': f'第 {index} 行必须是非空数据对象，最多 100 列'})
        if any(not isinstance(key, str) or not COLUMN_NAME.fullmatch(key) for key in row):
            raise ValidationError({'data_rows': '列名必须以字母或下划线开头，只能包含字母、数字、下划线'})
        if columns is not None and set(row) != columns:
            raise ValidationError({'data_rows': f'第 {index} 行的列名与第一行不一致'})
        columns = set(row)
        if any(value is not None and not isinstance(value, (str, int, float, bool)) for value in row.values()):
            raise ValidationError({'data_rows': f'第 {index} 行只能包含文本、数字、布尔值或空值'})
    return rows


def resolve_parameters(text, row):
    if not isinstance(text, str):
        return text

    def replace(match):
        key = match.group(1)
        if key not in row:
            raise ValidationError({'data_rows': f'缺少步骤引用的参数：{key}'})
        value = row[key]
        return '' if value is None else str(value)

    return PARAMETER.sub(replace, text)


def validate_step_bindings(rows, steps):
    """Reject data runs that would execute every row with unchanged step values."""
    if not rows or rows[0][0] is None:
        return

    columns = set(rows[0][1])
    referenced = set()
    for step in steps:
        source = step.get('step', step)
        if isinstance(source, dict):
            values = (source.get('input_value', ''), source.get('assert_value', ''))
        else:
            values = (getattr(source, 'input_value', ''), getattr(source, 'assert_value', ''))
        for value in values:
            if isinstance(value, str):
                referenced.update(PARAMETER.findall(value))

    if not columns.intersection(referenced):
        examples = '、'.join(f'${{{column}}}' for column in sorted(columns))
        raise ValidationError({
            'data_rows': (
                f'测试步骤尚未绑定任何数据列。请把步骤中的固定输入值替换为数据变量，'
                f'例如：{examples}'
            )
        })


def execution_rows(case, request_data=None):
    """Retry one immutable execution snapshot, or expand the case's saved rows."""
    from .models import TestCaseExecution

    request_data = request_data or {}
    if request_data.get('retry_execution_id') is not None:
        try:
            execution = TestCaseExecution.objects.get(
                pk=request_data['retry_execution_id'], test_case=case,
                data_index__isnull=False,
            )
        except (TestCaseExecution.DoesNotExist, ValueError, TypeError):
            raise ValidationError({'retry_execution_id': '找不到该用例的数据行执行记录'})
        return [(execution.data_index, execution.data_row)]
    if not case.data_driven_enabled:
        return [(None, None)]
    rows = validate_rows(case.data_rows)
    if not rows:
        raise ValidationError({'data_rows': '启用数据驱动时请至少配置一行数据'})
    return list(enumerate(rows, 1))


def prepare_steps(steps_data, row):
    prepared = []
    for info in steps_data:
        info = dict(info)
        if row is not None:
            step = copy.copy(info['step'])
            step.input_value = resolve_parameters(step.input_value, row)
            step.assert_value = resolve_parameters(step.assert_value, row)
            info['step'] = step
        prepared.append(info)
    return prepared


def execute_rows(case, user, *, engine='playwright', browser='chrome', headless=True,
                 source='manual', suite=None, request_data=None, batch_id=None):
    from .mcp_runner import _collect_steps_data

    headless = True  # 数据驱动服务端执行固定无头，本机任务使用独立执行器。
    if engine not in {'playwright', 'selenium'}:
        raise ValidationError({'engine': '不支持的执行引擎'})
    rows = execution_rows(case, request_data)
    steps = _collect_steps_data(case)
    if not steps:
        raise ValidationError({'steps': '请先添加测试步骤'})
    validate_step_bindings(rows, steps)
    # Validate every row before starting any browser or creating execution records.
    prepared = [(index, row, prepare_steps(steps, row)) for index, row in rows]
    batch_id = batch_id or uuid.uuid4()
    executions = _create_row_executions(case, user, prepared, batch_id, engine, browser, headless, source, suite)
    _execute_prepared(case, prepared, executions, engine, browser, headless)
    return executions


def _create_row_executions(case, user, prepared, batch_id, engine, browser, headless, source, suite):
    from .models import TestCaseExecution
    return [TestCaseExecution.objects.create(
        test_case=case, project=case.project, test_suite=suite,
        execution_source=source, status='pending', engine=engine,
        browser=browser, headless=headless, created_by=user,
        batch_id=batch_id, data_index=index, data_row=row or {},
    ) for index, row, _ in prepared]


def _execute_prepared(case, prepared, executions, engine, browser, headless):
    from .mcp_runner import _finish_execution, _run_playwright_async, _run_selenium_sync
    for (_, _, row_steps), execution in zip(prepared, executions):
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.save(update_fields=['status', 'started_at'])
        started = time.time()
        try:
            if engine == 'selenium':
                result, logs, screenshots = _run_selenium_sync(
                    execution, case, row_steps, browser, headless,
                )
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    result, logs, screenshots = pool.submit(
                        lambda: asyncio.run(_run_playwright_async(
                            execution, case, row_steps, browser, headless,
                        ))
                    ).result()
        except Exception as exc:
            result = {'status': 'error', 'error_message': str(exc)}
            logs, screenshots = [], []
        _finish_execution(execution, result['status'], logs, screenshots,
                          result['error_message'], started)


def start_data_execution(case, user, *, engine='playwright', browser='chrome', headless=True,
                         request_data=None):
    """Create all immutable rows now and return a pollable batch record immediately."""
    import threading
    from django.db import close_old_connections
    from .models import TestCaseExecution
    from .mcp_runner import _collect_steps_data, _finish_execution
    headless = True  # 数据驱动服务端执行固定无头，本机任务使用独立执行器。
    if engine not in {'playwright', 'selenium'}:
        raise ValidationError({'engine': '不支持的执行引擎'})
    if browser not in {'chrome', 'chromium', 'firefox', 'edge', 'safari', 'webkit'}:
        raise ValidationError({'browser': '不支持的浏览器类型'})
    steps = _collect_steps_data(case)
    if not steps:
        raise ValidationError({'steps': '请先添加测试步骤'})
    rows = execution_rows(case, request_data)
    validate_step_bindings(rows, steps)
    prepared = [(index, row, prepare_steps(steps, row)) for index, row in rows]
    from django.db import transaction
    with transaction.atomic():
        batch_id = uuid.uuid4()
        parent = TestCaseExecution.objects.create(
            test_case=case, project=case.project, created_by=user, status='pending',
            engine=engine, browser=browser, headless=headless, batch_id=batch_id,
        )
        executions = _create_row_executions(case, user, prepared, batch_id, engine, browser, headless, 'manual', None)

    def worker():
        close_old_connections()
        started = time.time()
        try:
            parent.status = 'running'
            parent.started_at = timezone.now()
            parent.save(update_fields=['status', 'started_at'])
            _execute_prepared(case, prepared, executions, engine, browser, headless)
            success = all(item.status == 'passed' for item in executions)
            _finish_execution(parent, 'passed' if success else 'failed', [], [],
                              '' if success else '部分数据行执行失败', started)
        except Exception as exc:
            TestCaseExecution.objects.filter(
                batch_id=batch_id, status__in=['pending', 'running'],
            ).update(status='error', error_message=str(exc), finished_at=timezone.now())
        finally:
            close_old_connections()

    transaction.on_commit(lambda: threading.Thread(target=worker, name=f'ui-data-{parent.id}', daemon=False).start())
    return parent


def data_label(execution):
    for key in ('username', 'account', 'name'):
        value = execution.data_row.get(key)
        if value is not None:
            return str(value)
    return f'数据行 {execution.data_index}' if execution.data_index is not None else ''


def execution_response(execution):
    import json
    return {
        'execution_id': execution.id, 'data_index': execution.data_index, 'data_label': data_label(execution),
        'status': execution.status, 'success': execution.status == 'passed',
        'logs': json.loads(execution.execution_logs or '[]'),
        'screenshots': execution.screenshots, 'execution_time': execution.execution_time,
        'errors': [{'message': execution.error_message}] if execution.error_message else [],
    }
