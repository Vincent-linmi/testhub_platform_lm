import shutil
import tempfile
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.ui_automation.models import (
    Element,
    LocalExecutionArtifact,
    LocalExecutionJob,
    LocatorStrategy,
    TestCase,
    TestCaseExecution,
    TestCaseStep,
    TestFileAsset,
    UiProject,
)


class LocalRunnerApiTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix='testhub-local-runner-')
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()

        self.user = get_user_model().objects.create_user(
            username='local-runner-owner', password='password'
        )
        self.project = UiProject.objects.create(
            name='Local runner project',
            base_url='https://example.test',
            owner=self.user,
        )
        strategy = LocatorStrategy.objects.create(name='css')
        element = Element.objects.create(
            project=self.project,
            name='登录按钮',
            locator_strategy=strategy,
            locator_value='#login',
            created_by=self.user,
        )
        self.test_case = TestCase.objects.create(
            project=self.project,
            name='本机登录测试',
            created_by=self.user,
        )
        TestCaseStep.objects.create(
            test_case=self.test_case,
            step_number=1,
            action_type='click',
            element=element,
        )
        self.client.force_authenticate(self.user)

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _create_and_claim(self):
        create_response = self.client.post(
            f'/api/ui-automation/test-cases/{self.test_case.id}/run-local/',
            {'browser': 'chrome', 'headless': True},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        query = parse_qs(urlparse(create_response.data['protocol_url']).query)
        launch_code = query['code'][0]
        claim_response = self.client.post(
            '/api/ui-automation/local-runner/jobs/claim/',
            {'launch_code': launch_code},
            format='json',
        )
        self.assertEqual(claim_response.status_code, 200, claim_response.data)
        return create_response, claim_response, launch_code

    def test_job_is_claimed_once_and_payload_is_a_snapshot(self):
        create_response, claim_response, launch_code = self._create_and_claim()

        job = LocalExecutionJob.objects.get(pk=create_response.data['job_id'])
        execution = TestCaseExecution.objects.get(pk=create_response.data['execution_id'])
        self.assertEqual(job.status, 'claimed')
        self.assertEqual(execution.status, 'running')
        self.assertEqual(claim_response.data['payload']['case']['name'], self.test_case.name)
        self.assertEqual(claim_response.data['payload']['steps'][0]['element']['locator_value'], '#login')

        duplicate = self.client.post(
            '/api/ui-automation/local-runner/jobs/claim/',
            {'launch_code': launch_code},
            format='json',
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_claim_url_uses_browser_facing_dev_server_origin(self):
        response = self.client.post(
            f'/api/ui-automation/test-cases/{self.test_case.id}/run-local/',
            {
                'browser': 'chrome',
                'headless': True,
                'runner_origin': 'http://192.168.1.20:3000',
            },
            format='json',
            HTTP_ORIGIN='http://192.168.1.20:3000',
        )
        self.assertEqual(response.status_code, 201, response.data)
        query = parse_qs(urlparse(response.data['protocol_url']).query)
        self.assertEqual(
            query['claim_url'][0],
            'http://192.168.1.20:3000/api/ui-automation/local-runner/jobs/claim/',
        )
        claim_response = self.client.post(
            '/api/ui-automation/local-runner/jobs/claim/',
            {'launch_code': query['code'][0]},
            format='json',
        )
        self.assertEqual(claim_response.status_code, 200, claim_response.data)
        self.assertEqual(
            claim_response.data['urls']['artifacts'],
            f"http://192.168.1.20:3000/api/ui-automation/local-runner/jobs/"
            f"{response.data['job_id']}/artifacts/",
        )

    def test_runner_origin_must_match_browser_origin(self):
        response = self.client.post(
            f'/api/ui-automation/test-cases/{self.test_case.id}/run-local/',
            {
                'browser': 'chrome',
                'runner_origin': 'http://192.168.1.99:3000',
            },
            format='json',
            HTTP_ORIGIN='http://192.168.1.20:3000',
        )
        self.assertEqual(response.status_code, 400)

    def test_task_token_scopes_events_artifacts_and_completion(self):
        create_response, claim_response, _ = self._create_and_claim()
        job_id = create_response.data['job_id']
        token = claim_response.data['upload_token']
        authorization = f'Bearer {token}'

        bad_event = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/events/',
            {'type': 'started'},
            format='json',
            HTTP_AUTHORIZATION='Bearer wrong-token',
        )
        self.assertEqual(bad_event.status_code, 403)

        event = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/events/',
            {'type': 'started', 'message': 'running'},
            format='json',
            HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(event.status_code, 202, event.data)

        artifact = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/artifacts/',
            {
                'artifact_type': 'playwright_trace',
                'file': SimpleUploadedFile('trace.zip', b'trace-content', content_type='application/zip'),
            },
            format='multipart',
            HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(artifact.status_code, 201, artifact.data)
        stored = LocalExecutionArtifact.objects.get(pk=artifact.data['id'])
        self.assertIn(job_id, stored.file.name)
        self.assertIn(str(stored.job.attempt_id), stored.file.name)
        download = self.client.get(
            f'/api/ui-automation/local-runner/artifacts/{stored.id}/download/'
        )
        self.assertEqual(download.status_code, 200)

        complete = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/complete/',
            {
                'success': True,
                'duration': 1.25,
                'step_results': [{'step_number': 1, 'success': True}],
            },
            format='json',
            HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(complete.status_code, 200, complete.data)
        job = LocalExecutionJob.objects.get(pk=job_id)
        job.execution.refresh_from_db()
        self.assertEqual(job.status, 'passed')
        self.assertEqual(job.execution.status, 'passed')
        late_trace = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/artifacts/',
            {'artifact_type': 'playwright_trace', 'file': SimpleUploadedFile('late.zip', b'trace')},
            format='multipart', HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(late_trace.status_code, 201, late_trace.data)
        job.completed_at = job.completed_at - timedelta(minutes=16)
        job.save(update_fields=['completed_at'])
        expired_upload = self.client.post(
            f'/api/ui-automation/local-runner/jobs/{job_id}/artifacts/',
            {'file': SimpleUploadedFile('expired.zip', b'trace')},
            format='multipart', HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(expired_upload.status_code, 400)
        detail = self.client.get(
            f'/api/ui-automation/test-case-executions/{job.execution_id}/'
        )
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data['local_artifacts'][0]['id'], stored.id)

    def test_agent_can_only_download_assets_in_its_snapshot(self):
        asset = TestFileAsset.objects.create(
            project=self.project,
            name='fixture.txt',
            file=SimpleUploadedFile('fixture.txt', b'fixture'),
            file_size=7,
            created_by=self.user,
        )
        step = self.test_case.steps.get()
        step.action_type = 'uploadFile'
        step.file_asset = asset
        step.file_asset_order = [asset.id]
        step.save(update_fields=['action_type', 'file_asset', 'file_asset_order'])
        step.file_assets.add(asset)

        create_response, claim_response, _ = self._create_and_claim()
        job_id = create_response.data['job_id']
        authorization = f"Bearer {claim_response.data['upload_token']}"
        download = self.client.get(
            f'/api/ui-automation/local-runner/jobs/{job_id}/files/{asset.id}/',
            HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(download.status_code, 200)

        other_asset = TestFileAsset.objects.create(
            project=self.project,
            name='other.txt',
            file=SimpleUploadedFile('other.txt', b'other'),
            file_size=5,
            created_by=self.user,
        )
        denied = self.client.get(
            f'/api/ui-automation/local-runner/jobs/{job_id}/files/{other_asset.id}/',
            HTTP_AUTHORIZATION=authorization,
        )
        self.assertEqual(denied.status_code, 400)
