"""Suite snapshots and result aggregation for one on-demand local runner."""

import copy
import json
import secrets
import uuid
from datetime import timedelta
from urllib.parse import quote

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .data_driven import execution_rows, resolve_parameters, validate_step_bindings
from .models import LocalExecutionJob, TestCaseExecution, TestExecution, TestSuite


class SuiteRunOptions(serializers.Serializer):
    engine = serializers.ChoiceField(choices=['playwright'], default='playwright')
    browser = serializers.ChoiceField(
        choices=['chrome', 'chromium', 'firefox', 'safari', 'webkit', 'edge'], default='chrome',
    )
    headless = serializers.BooleanField(default=False)


def suite_rows(job):
    ids = [item['execution_id'] for item in job.payload['suite_items']]
    return TestCaseExecution.objects.filter(pk__in=ids, batch_id=job.id).order_by('id')


def refresh_suite(job, *, finished=False, error_message='', duration=None):
    """Called under the job transaction; only the latest run updates the suite badge."""
    execution = job.suite_execution
    rows = list(suite_rows(job).select_related('test_case'))
    execution.passed_cases = sum(row.status == 'passed' for row in rows)
    execution.failed_cases = sum(row.status in {'failed', 'error'} for row in rows)
    execution.total_cases = len(rows)
    execution.result_data = {
        'local': True,
        'test_cases': [{
            'test_case_id': row.test_case_id,
            'test_case_name': row.test_case.name + (f' [数据行 {row.data_index}]' if row.data_index is not None else ''),
            'execution_id': row.id,
            'data_index': row.data_index,
            'status': row.status,
            'steps': json.loads(row.execution_logs or '[]'),
            'error': row.error_message or '',
            'duration': row.execution_time or 0,
            'screenshots': row.screenshots,
        } for row in rows],
        'summary': {
            'total': len(rows), 'passed': execution.passed_cases,
            'failed': execution.failed_cases, 'skipped': 0,
            'pass_rate': execution.pass_rate,
        },
    }
    if finished:
        execution.status = 'SUCCESS' if execution.passed_cases == len(rows) and rows else 'FAILED'
        execution.finished_at = timezone.now()
        execution.error_message = error_message
        execution.duration = duration or 0
    execution.save()
    suite = TestSuite.objects.select_for_update().get(pk=execution.test_suite_id)
    latest = TestExecution.objects.filter(test_suite=suite).order_by('-id').values_list('id', flat=True).first()
    if latest == execution.id:
        suite.execution_status = ('passed' if execution.status == 'SUCCESS' else 'failed') if finished else 'running'
        suite.passed_count = execution.passed_cases
        suite.failed_count = execution.failed_cases
        suite.save(update_fields=['execution_status', 'passed_count', 'failed_count'])


def expire_suite(job):
    if job.status != 'waiting_runner' or job.expires_at > timezone.now():
        return
    message = '本地执行器未在有效时间内启动，请安装或更新执行器后重试'
    job.status = 'expired'
    job.completed_at = timezone.now()
    job.error_message = message
    job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
    suite_rows(job).filter(status='pending').update(
        status='failed', error_message=message, finished_at=job.completed_at,
    )
    refresh_suite(job, finished=True, error_message=message)


def _save_result(row, result):
    row.status = 'passed' if result['success'] else 'failed'
    row.execution_time = result['duration']
    row.execution_logs = json.dumps(result['step_results'], ensure_ascii=False)
    row.error_message = result['error_message']
    row.finished_at = timezone.now()
    row.started_at = row.started_at or row.finished_at
    row.save()


class SuiteCaseResult(serializers.Serializer):
    execution_id = serializers.IntegerField()
    success = serializers.BooleanField()
    duration = serializers.FloatField(min_value=0, default=0)
    step_results = serializers.ListField(child=serializers.DictField(), default=list)
    error_message = serializers.CharField(allow_blank=True, default='')


def suite_event(job, event):
    execution_id = serializers.IntegerField().run_validation(event.get('execution_id'))
    row = suite_rows(job).select_for_update().filter(pk=execution_id).first()
    if not row:
        raise ValidationError('执行记录不属于当前套件任务')
    if event.get('type') == 'case_finished':
        result = SuiteCaseResult(data=event)
        result.is_valid(raise_exception=True)
        _save_result(row, result.validated_data)
    elif row.status in {'pending', 'running'}:
        row.status = 'running'
        row.started_at = row.started_at or timezone.now()
        if event.get('type') == 'step_finished':
            steps = json.loads(row.execution_logs or '[]')
            steps.append(event)
            row.execution_logs = json.dumps(steps, ensure_ascii=False)
        row.save(update_fields=['status', 'started_at', 'execution_logs'])
    refresh_suite(job)


def complete_suite(job, data):
    results = SuiteCaseResult(data=data.get('case_results'), many=True)
    results.is_valid(raise_exception=True)
    rows = {row.id: row for row in suite_rows(job).select_for_update()}
    values = results.validated_data
    if len(values) != len(rows) or {item['execution_id'] for item in values} != set(rows):
        raise ValidationError('执行器未回传完整套件结果，请更新本地执行器后重跑')
    for item in values:
        _save_result(rows[item['execution_id']], item)
    success = all(item['success'] for item in values)
    job.status = 'passed' if success else 'failed'
    job.completed_at = timezone.now()
    job.error_message = '' if success else '套件中部分用例执行失败'
    job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
    duration = max(0, (job.completed_at - (job.claimed_at or job.created_at)).total_seconds())
    refresh_suite(job, finished=True, error_message=job.error_message, duration=duration)
    return Response({'status': job.status, 'suite_execution_id': job.suite_execution_id})


class LocalSuiteExecutionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, test_suite_id):
        from .local_runner_views import _build_payload, _digest, _public_request_origin
        from .operation_logger import log_operation

        suite = get_object_or_404(TestSuite.objects.filter(
            Q(project__owner=request.user) | Q(project__members=request.user),
        ).distinct(), pk=test_suite_id)
        options = SuiteRunOptions(data=request.data)
        options.is_valid(raise_exception=True)
        browser = options.validated_data['browser']
        headless = options.validated_data['headless']
        origin = _public_request_origin(request)
        cases = list(suite.suite_test_cases.select_related('test_case__project').order_by('order', 'id'))
        if not cases:
            raise ValidationError({'detail': '该测试套件未包含任何测试用例，无法执行'})
        job_id = uuid.uuid4()
        items, assets = [], {}
        for link in cases:
            case = link.test_case
            if case.project_id != suite.project_id:
                raise ValidationError({'detail': '套件包含其他项目的用例，请移除后重试'})
            payload = _build_payload(case, browser, headless)
            if not payload['steps']:
                raise ValidationError({'detail': f'用例「{case.name}」没有测试步骤'})
            assets.update({asset['id']: asset for asset in payload['assets']})
            rows = execution_rows(case)
            validate_step_bindings(rows, payload['steps'])
            for index, row in rows:
                case_payload = copy.deepcopy(payload)
                if row is not None:
                    for step in case_payload['steps']:
                        step['input_value'] = resolve_parameters(step['input_value'], row)
                        step['assert_value'] = resolve_parameters(step['assert_value'], row)
                execution = TestCaseExecution.objects.create(
                    test_case=case, project=suite.project, test_suite=suite,
                    execution_source='suite', status='pending', engine='playwright',
                    browser=browser, headless=headless, created_by=request.user,
                    batch_id=job_id, data_index=index, data_row=row or {},
                )
                items.append({'execution_id': execution.id, 'payload': case_payload})
        suite_execution = TestExecution.objects.create(
            project=suite.project, test_suite=suite, status='PENDING',
            engine='playwright', browser=browser, headless=headless,
            environment={'chromium': 'CHROME', 'webkit': 'SAFARI'}.get(browser, browser.upper()),
            executed_by=request.user, total_cases=len(items),
        )
        launch_code = secrets.token_urlsafe(32)
        job = LocalExecutionJob.objects.create(
            id=job_id, suite_execution=suite_execution, created_by=request.user,
            launch_code_hash=_digest(launch_code), expires_at=timezone.now() + timedelta(minutes=2),
            payload={'protocol_version': 3, 'runner_origin': origin,
                     'suite_items': items, 'assets': list(assets.values())},
        )
        refresh_suite(job)
        log_operation('run', 'suite', suite.id, suite.name, request.user)
        claim_url = f'{origin}/api/ui-automation/local-runner/jobs/claim/'
        return Response({
            'job_id': str(job.id), 'suite_execution_id': suite_execution.id,
            'status': job.status, 'expires_at': job.expires_at,
            'protocol_url': f'testhub-runner://execute?claim_url={quote(claim_url, safe="")}&code={quote(launch_code, safe="")}',
        }, status=status.HTTP_201_CREATED)


class LocalSuiteExecutionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def get(self, request, execution_id):
        execution = get_object_or_404(TestExecution.objects.filter(
            Q(project__owner=request.user) | Q(project__members=request.user),
        ).distinct(), pk=execution_id)
        job = get_object_or_404(LocalExecutionJob.objects.select_for_update(), suite_execution=execution)
        expire_suite(job)
        execution.refresh_from_db()
        return Response({
            'id': execution.id, 'status': execution.status, 'runner_status': job.status,
            'total_cases': execution.total_cases, 'passed_cases': execution.passed_cases,
            'failed_cases': execution.failed_cases, 'error_message': execution.error_message,
        })
