"""HTTP rendezvous endpoints for the on-demand local Playwright runner."""

import hashlib
import json
import secrets
import copy
import uuid
from datetime import timedelta
from urllib.parse import quote, urlparse

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    LocalExecutionArtifact,
    LocalExecutionJob,
    TestCase,
    TestCaseExecution,
    TestFileAsset,
)


def _digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _public_request_origin(request):
    """Return the browser-facing origin, including the Vite dev-server proxy."""
    supplied = str(request.data.get('runner_origin', '')).rstrip('/')
    browser_origin = str(request.headers.get('Origin', '')).rstrip('/')
    candidate = supplied or browser_origin
    if not candidate:
        return request.build_absolute_uri('/').rstrip('/')

    parsed = urlparse(candidate)
    if (
        parsed.scheme not in {'http', 'https'}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {'', '/'}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError({'runner_origin': '本机执行服务地址格式无效'})
    if browser_origin and supplied and browser_origin.lower() != supplied.lower():
        raise ValidationError({'runner_origin': '本机执行服务地址必须与当前网页地址一致'})
    return candidate


def _selected_assets(step):
    assets = list(step.file_assets.all())
    if not assets and step.file_asset_id:
        assets = [step.file_asset]
    positions = {int(asset_id): index for index, asset_id in enumerate(step.file_asset_order or [])}
    assets.sort(key=lambda asset: positions.get(asset.id, len(positions)))
    return assets


def _build_payload(test_case, browser, headless):
    steps = []
    asset_ids = set()
    for step in test_case.steps.all().order_by('step_number'):
        assets = _selected_assets(step)
        asset_ids.update(asset.id for asset in assets)
        element = step.element
        steps.append({
            'id': step.id,
            'step_number': step.step_number,
            'action_type': step.action_type,
            'description': step.description or '',
            'input_value': step.input_value or '',
            'wait_time': step.wait_time or 1000,
            'assert_type': step.assert_type or '',
            'assert_value': step.assert_value or '',
            'element': ({
                'name': element.name,
                'locator_strategy': element.locator_strategy.name if element.locator_strategy else 'css',
                'locator_value': element.locator_value,
                'wait_timeout': element.wait_timeout,
                'force_action': element.force_action,
            } if element else None),
            'file_asset_ids': [asset.id for asset in assets],
        })

    assets = TestFileAsset.objects.filter(id__in=asset_ids).order_by('id')
    return {
        'protocol_version': 1,
        'case': {
            'id': test_case.id,
            'name': test_case.name,
            'base_url': test_case.project.base_url,
            'global_wait_enabled': test_case.global_wait_enabled,
            'global_wait_time': test_case.global_wait_time,
        },
        'browser': browser,
        'headless': bool(headless),
        'steps': steps,
        'assets': [
            {
                'id': asset.id,
                'name': asset.name,
                'sha256': asset.sha256,
                'size': asset.file_size,
            }
            for asset in assets
        ],
    }


def _job_from_token(request, job_id, *, allow_terminal=False):
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        raise AuthenticationFailed('缺少本机执行任务令牌')
    token = authorization[7:].strip()
    if not token:
        raise AuthenticationFailed('本机执行任务令牌无效')

    job = get_object_or_404(LocalExecutionJob, pk=job_id)
    if not job.upload_token_hash or not secrets.compare_digest(job.upload_token_hash, _digest(token)):
        raise AuthenticationFailed('本机执行任务令牌无效')
    if not allow_terminal and job.status in {'passed', 'failed', 'cancelled', 'expired'}:
        raise ValidationError('本机执行任务已结束')
    return job


class LocalExecutionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, test_case_id):
        test_case = get_object_or_404(
            TestCase.objects.filter(
                Q(project__owner=request.user) | Q(project__members=request.user)
            ).select_related('project').prefetch_related(
                'steps__element__locator_strategy',
                'steps__file_assets',
                'steps__file_asset',
            ).distinct(),
            pk=test_case_id,
        )
        browser = request.data.get('browser', 'chrome')
        if browser not in {'chrome', 'chromium', 'firefox', 'safari', 'webkit', 'edge'}:
            raise ValidationError({'browser': '不支持的浏览器类型'})

        launch_code = secrets.token_urlsafe(32)
        public_origin = _public_request_origin(request)
        payload = _build_payload(test_case, browser, request.data.get('headless', False))
        from .data_driven import execution_rows, resolve_parameters, validate_step_bindings
        rows = execution_rows(test_case, request.data)
        validate_step_bindings(rows, payload['steps'])
        batch_id = uuid.uuid4() if rows[0][0] is not None else None
        iterations = []
        if batch_id:
            for index, row in rows:
                row_steps = copy.deepcopy(payload['steps'])
                for step in row_steps:
                    step['input_value'] = resolve_parameters(step['input_value'], row)
                    step['assert_value'] = resolve_parameters(step['assert_value'], row)
                iterations.append({'data_index': index, 'steps': row_steps, 'data_row': row})
            # An older runner must not silently run one unparameterized row.
            payload['protocol_version'] = 2
            payload['steps'] = []
        payload['runner_origin'] = public_origin
        execution = TestCaseExecution.objects.create(
            test_case=test_case,
            project=test_case.project,
            execution_source='manual',
            status='pending',
            engine='playwright',
            browser=browser,
            headless=bool(request.data.get('headless', False)),
            created_by=request.user, batch_id=batch_id,
        )
        for iteration in iterations:
            child = TestCaseExecution.objects.create(
                test_case=test_case, project=test_case.project, execution_source='manual',
                status='pending', engine='playwright', browser=browser,
                headless=bool(request.data.get('headless', False)), created_by=request.user,
                batch_id=batch_id, data_index=iteration['data_index'], data_row=iteration.pop('data_row'),
            )
            iteration['execution_id'] = child.id
        if iterations:
            payload['iterations'] = iterations
        job = LocalExecutionJob.objects.create(
            execution=execution,
            created_by=request.user,
            launch_code_hash=_digest(launch_code),
            payload=payload,
            expires_at=timezone.now() + timedelta(minutes=2),
        )

        claim_url = f'{public_origin}/api/ui-automation/local-runner/jobs/claim/'
        protocol_url = (
            'testhub-runner://execute'
            f'?claim_url={quote(claim_url, safe="")}'
            f'&code={quote(launch_code, safe="")}'
        )
        return Response({
            'job_id': str(job.id),
            'execution_id': execution.id,
            'attempt_id': str(job.attempt_id),
            'status': job.status,
            'expires_at': job.expires_at,
            'protocol_url': protocol_url,
        }, status=status.HTTP_201_CREATED)


def _fail_data_job(job, message):
    """Finish an incompatible data job so the UI does not poll indefinitely."""
    now = timezone.now()
    job.status = 'failed'
    job.error_message = message
    job.completed_at = now
    job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
    execution = job.execution
    execution.status = 'failed'
    execution.error_message = message
    execution.finished_at = now
    execution.save(update_fields=['status', 'error_message', 'finished_at'])
    TestCaseExecution.objects.filter(
        batch_id=execution.batch_id, test_case=execution.test_case,
        data_index__isnull=False, status__in=['pending', 'running'],
    ).update(status='failed', error_message=message, finished_at=now)


class LocalExecutionClaimView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        launch_code = request.data.get('launch_code', '')
        if not launch_code:
            raise ValidationError({'launch_code': '缺少一次性领取码'})

        job = LocalExecutionJob.objects.select_for_update().select_related('execution').filter(
            launch_code_hash=_digest(launch_code)
        ).first()
        if not job:
            raise ValidationError({'launch_code': '领取码无效'})
        if job.suite_execution_id:
            from .local_suite_runner import expire_suite
            expire_suite(job)
            if job.status == 'expired':
                return Response({'launch_code': '领取码已过期'}, status=status.HTTP_400_BAD_REQUEST)
            if request.data.get('protocol_version', 0) != 3:
                raise ValidationError({'detail': '套件本地运行需要更新 TestHub Runner，请安装最新执行器'})
        if job.expires_at <= timezone.now():
            if job.status == 'waiting_runner':
                job.status = 'expired'
                job.save(update_fields=['status', 'updated_at'])
                job.execution.status = 'failed'
                job.execution.error_message = '本机执行器未在有效时间内启动'
                job.execution.finished_at = timezone.now()
                job.execution.save(update_fields=['status', 'error_message', 'finished_at'])
                if job.execution.batch_id:
                    TestCaseExecution.objects.filter(
                        batch_id=job.execution.batch_id, data_index__isnull=False,
                        status__in=['pending', 'running'],
                    ).update(status='failed', error_message='本机执行器未在有效时间内启动',
                             finished_at=timezone.now())
            raise ValidationError({'launch_code': '领取码已过期'})
        if job.status != 'waiting_runner':
            raise ValidationError({'launch_code': '任务已被领取'})

        if job.payload.get('iterations'):
            protocol = request.data.get('protocol_version', 0)
            # Runner 0.3 supports rows but predates explicit protocol negotiation.
            supports_rows = (type(protocol) is int and protocol >= 2) or (
                request.headers.get('User-Agent', '').split(' ', 1)[0] == 'TestHub-Local-Runner/0.3'
            )
            if not supports_rows:
                message = '数据驱动需要更新 TestHub Runner，请安装最新执行器后重新运行'
                _fail_data_job(job, message)
                return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        from local_playwright_agent.step_runtime import CAPABILITY, needs_runtime_v2
        capabilities = request.data.get('capabilities', [])
        if needs_runtime_v2(job.payload) and (
                not isinstance(capabilities, list) or CAPABILITY not in capabilities):
            return Response({'detail': '此用例使用新版动作或断言，请安装 TestHub Runner 0.5 或以上版本后重新运行'},
                            status=status.HTTP_400_BAD_REQUEST)

        upload_token = secrets.token_urlsafe(48)
        now = timezone.now()
        job.status = 'claimed'
        job.claimed_at = now
        job.upload_token_hash = _digest(upload_token)
        job.save(update_fields=['status', 'claimed_at', 'upload_token_hash', 'updated_at'])
        execution = job.suite_execution if job.suite_execution_id else job.execution
        execution.status = 'RUNNING' if job.suite_execution_id else 'running'
        execution.started_at = now
        execution.save(update_fields=['status', 'started_at'])

        public_origin = job.payload.get('runner_origin') or request.build_absolute_uri('/').rstrip('/')
        root = f'{public_origin}/api/ui-automation/local-runner/jobs/'
        return Response({
            'job_id': str(job.id),
            'execution_id': job.execution_id,
            'suite_execution_id': job.suite_execution_id,
            'attempt_id': str(job.attempt_id),
            'upload_token': upload_token,
            'payload': job.payload,
            'urls': {
                'events': f'{root}{job.id}/events/',
                'artifacts': f'{root}{job.id}/artifacts/',
                'complete': f'{root}{job.id}/complete/',
                'files': f'{root}{job.id}/files/',
            },
        })


class LocalExecutionEventView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @transaction.atomic
    def post(self, request, job_id):
        job = _job_from_token(request, job_id)
        event = request.data
        if not isinstance(event, dict):
            raise ValidationError('事件必须是 JSON 对象')

        if job.suite_execution_id:
            from .local_suite_runner import suite_event
            job = LocalExecutionJob.objects.select_for_update().get(pk=job.pk)
            if job.status not in {'claimed', 'running'}:
                raise ValidationError('本机执行任务已结束')
            suite_event(job, event)
            job.status = 'running'
            job.save(update_fields=['status', 'updated_at'])
            return Response({'accepted': True}, status=status.HTTP_202_ACCEPTED)

        execution = TestCaseExecution.objects.select_for_update().get(pk=job.execution_id)
        if event.get('data_index') is not None and execution.batch_id:
            child = TestCaseExecution.objects.select_for_update().filter(
                batch_id=execution.batch_id, test_case=execution.test_case,
                data_index=event['data_index'],
            ).first()
            if not child:
                raise ValidationError('数据行不属于当前执行任务')
            if event.get('type') == 'started':
                child.status = 'running'
                child.started_at = timezone.now()
            if event.get('type') == 'row_finished':
                child.status = 'passed' if event.get('success') else 'failed'
                child.finished_at = timezone.now()
                child.execution_time = event.get('duration')
                child.error_message = event.get('error_message', '')
                child.execution_logs = json.dumps(event.get('step_results', []), ensure_ascii=False)
            child.save()

        try:
            events = json.loads(execution.execution_logs or '[]')
            if not isinstance(events, list):
                events = []
        except (TypeError, json.JSONDecodeError):
            events = []
        events.append(event)
        execution.execution_logs = json.dumps(events[-2000:], ensure_ascii=False)
        execution.save(update_fields=['execution_logs'])
        if job.status == 'claimed':
            job.status = 'running'
            job.save(update_fields=['status', 'updated_at'])
        return Response({'accepted': True}, status=status.HTTP_202_ACCEPTED)


class LocalExecutionArtifactView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, job_id):
        job = _job_from_token(request, job_id, allow_terminal=True)
        if job.status in {'cancelled', 'expired'} or (
            job.completed_at and timezone.now() > job.completed_at + timedelta(minutes=15)
        ):
            raise ValidationError('附件上传窗口已关闭')
        uploaded = request.FILES.get('file')
        if not uploaded:
            raise ValidationError({'file': '缺少附件文件'})
        if uploaded.size > 500 * 1024 * 1024:
            raise ValidationError({'file': '附件不能超过 500 MB'})
        artifact_type = request.data.get('artifact_type', 'other')
        if artifact_type not in {'playwright_trace', 'screenshot', 'video', 'log', 'other'}:
            raise ValidationError({'artifact_type': '不支持的附件类型'})

        digest = hashlib.sha256()
        for chunk in uploaded.chunks():
            digest.update(chunk)
        uploaded.seek(0)
        artifact = LocalExecutionArtifact.objects.create(
            job=job,
            artifact_type=artifact_type,
            file=uploaded,
            original_name=uploaded.name,
            content_type=uploaded.content_type or '',
            file_size=uploaded.size,
            sha256=digest.hexdigest(),
        )
        return Response({
            'id': artifact.id,
            'artifact_type': artifact.artifact_type,
            'size': artifact.file_size,
            'sha256': artifact.sha256,
        }, status=status.HTTP_201_CREATED)


class LocalExecutionFileView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, job_id, asset_id):
        job = _job_from_token(request, job_id)
        allowed_ids = {asset['id'] for asset in job.payload.get('assets', [])}
        if asset_id not in allowed_ids:
            raise ValidationError('文件不属于当前执行任务')
        asset = get_object_or_404(TestFileAsset, pk=asset_id)
        return FileResponse(asset.file.open('rb'), as_attachment=True, filename=asset.name)


class LocalExecutionArtifactDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artifact_id):
        artifact = get_object_or_404(
            LocalExecutionArtifact.objects.filter(
                Q(job__execution__project__owner=request.user)
                | Q(job__execution__project__members=request.user)
                | Q(job__suite_execution__project__owner=request.user)
                | Q(job__suite_execution__project__members=request.user)
            ).distinct(),
            pk=artifact_id,
        )
        return FileResponse(
            artifact.file.open('rb'),
            as_attachment=True,
            filename=artifact.original_name,
            content_type=artifact.content_type or 'application/octet-stream',
        )


class LocalExecutionCompleteView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @transaction.atomic
    def post(self, request, job_id):
        job = _job_from_token(request, job_id, allow_terminal=True)
        job = LocalExecutionJob.objects.select_for_update().get(pk=job.pk)
        if job.status in {'passed', 'failed'}:
            return Response({'status': job.status})

        if job.status in {'cancelled', 'expired'}:
            raise ValidationError('本机执行任务已结束')
        if job.suite_execution_id:
            from .local_suite_runner import complete_suite
            return complete_suite(job, request.data)
        iterations = job.payload.get('iterations', [])
        if iterations:
            row_results = request.data.get('row_results')
            expected = {item['data_index'] for item in iterations}
            if (not isinstance(row_results, list) or len(row_results) != len(expected)
                    or any(not isinstance(item, dict) or not isinstance(item.get('data_index'), int)
                           for item in row_results)
                    or {item['data_index'] for item in row_results} != expected):
                message = '执行器未回传完整数据行结果，请更新本机执行器后重跑'
                _fail_data_job(job, message)
                return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
            now = timezone.now()
            for item in row_results:
                child = TestCaseExecution.objects.get(
                    batch_id=job.execution.batch_id, test_case=job.execution.test_case,
                    data_index=item['data_index'],
                )
                child.status = 'passed' if item.get('success') else 'failed'
                child.execution_time = item.get('duration')
                child.execution_logs = json.dumps(item.get('step_results', []), ensure_ascii=False)
                child.error_message = item.get('error_message', '')
                child.finished_at = now
                child.save()
        success = (all(item.get('success') for item in row_results) if iterations
                   else bool(request.data.get('success', False)))
        final_status = 'passed' if success else 'failed'
        now = timezone.now()
        job.status = final_status
        job.completed_at = now
        job.error_message = request.data.get('error_message', '')
        job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])

        execution = job.execution
        execution.status = final_status
        execution.error_message = job.error_message
        execution.execution_time = request.data.get('duration')
        execution.finished_at = now
        step_results = request.data.get('step_results')
        if isinstance(step_results, list):
            execution.execution_logs = json.dumps(step_results, ensure_ascii=False)
        execution.save(update_fields=[
            'status', 'error_message', 'execution_time', 'finished_at', 'execution_logs'
        ])
        return Response({'status': final_status, 'execution_id': execution.id})
