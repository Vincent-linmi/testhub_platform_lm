import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.ui_automation.models import (
    LocalExecutionJob, TestCase, TestCaseExecution, TestCaseStep,
    TestExecution, TestFileAsset, TestSuite, TestSuiteTestCase, UiProject,
)


class LocalSuiteRunnerTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='suite-owner')
        self.outsider = get_user_model().objects.create_user(username='suite-outsider')
        self.project = UiProject.objects.create(name='Local suite', owner=self.owner)
        self.suite = TestSuite.objects.create(name='Suite', project=self.project)
        self.first = TestCase.objects.create(name='first', project=self.project, created_by=self.owner)
        self.second = TestCase.objects.create(
            name='rows', project=self.project, created_by=self.owner,
            data_driven_enabled=True, data_rows=[{'value': 'one'}, {'value': 'two'}],
        )
        for case in [self.first, self.second]:
            TestCaseStep.objects.create(test_case=case, step_number=1, action_type='wait',
                                        wait_time=1, input_value='${value}' if case == self.second else '')
        TestSuiteTestCase.objects.create(test_suite=self.suite, test_case=self.second, order=2)
        TestSuiteTestCase.objects.create(test_suite=self.suite, test_case=self.first, order=1)
        self.url = f'/api/ui-automation/test-suites/{self.suite.pk}/run-local/'
        self.client.force_authenticate(self.owner)

    def create_job(self):
        response = self.client.post(self.url, {'headless': True}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data, parse_qs(urlparse(response.data['protocol_url']).query)['code'][0]

    def claim(self, code, version=3):
        return self.client.post('/api/ui-automation/local-runner/jobs/claim/',
                                {'launch_code': code, 'protocol_version': version}, format='json')

    def call(self, job, action, data):
        return self.client.post(job['urls'][action], data, format='json',
                                HTTP_AUTHORIZATION=f"Bearer {job['upload_token']}")

    def test_snapshot_preserves_order_parameters_and_configuration(self):
        created, code = self.create_job()
        self.second.data_rows = [{'value': 'changed'}]
        self.second.save()
        claim = self.claim(code)
        self.assertEqual(claim.status_code, 200, claim.data)
        items = claim.data['payload']['suite_items']
        self.assertEqual([item['payload']['case']['name'] for item in items], ['first', 'rows', 'rows'])
        self.assertEqual([item['payload']['steps'][0]['input_value'] for item in items], ['', 'one', 'two'])
        self.assertTrue(all(item['payload']['headless'] for item in items))
        rows = TestCaseExecution.objects.filter(batch_id=created['job_id']).order_by('id')
        self.assertEqual(list(rows.values_list('data_index', flat=True)), [None, 1, 2])
        self.assertTrue(all(row.execution_source == 'suite' for row in rows))
        self.assertEqual(self.claim(code).status_code, 400)

    def test_result_progress_artifacts_and_idempotent_completion(self):
        created, code = self.create_job()
        job = self.claim(code).data
        items = job['payload']['suite_items']
        ids = [item['execution_id'] for item in items]
        results = [{'execution_id': pk, 'success': index != 1, 'duration': 1.2,
                    'step_results': [{'step_number': 1, 'success': index != 1}],
                    'error_message': 'expected failure' if index == 1 else ''}
                   for index, pk in enumerate(ids)]
        self.assertEqual(self.call(job, 'events', {'type': 'started', 'execution_id': ids[0]}).status_code, 202)
        self.assertEqual(self.call(job, 'events', {'type': 'case_finished', **results[0]}).status_code, 202)
        progress = self.client.get(f"/api/ui-automation/test-executions/{created['suite_execution_id']}/local-status/")
        self.assertEqual(progress.data['status'], 'RUNNING')
        self.assertEqual(progress.data['passed_cases'], 1)
        missing = self.call(job, 'complete', {'success': True, 'case_results': results[:1]})
        self.assertEqual(missing.status_code, 400)
        duplicate = self.call(job, 'complete', {'case_results': [results[0]] * 3})
        self.assertEqual(duplicate.status_code, 400)
        complete = self.call(job, 'complete', {'success': True, 'case_results': results})
        self.assertEqual(complete.status_code, 200, complete.data)
        execution = TestExecution.objects.get(pk=created['suite_execution_id'])
        self.assertEqual((execution.status, execution.passed_cases, execution.failed_cases), ('FAILED', 2, 1))
        self.assertEqual([row['execution_id'] for row in execution.result_data['test_cases']], ids)
        self.suite.refresh_from_db()
        self.assertEqual((self.suite.execution_status, self.suite.passed_count), ('failed', 2))
        self.assertEqual(self.call(job, 'complete', {}).status_code, 200)
        self.assertEqual(self.call(job, 'events', {'type': 'started', 'execution_id': ids[0]}).status_code, 400)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            artifact = self.client.post(job['urls']['artifacts'], {
                'artifact_type': 'playwright_trace',
                'file': SimpleUploadedFile(f'execution-{ids[0]}-trace.zip', b'trace'),
            }, format='multipart', HTTP_AUTHORIZATION=f"Bearer {job['upload_token']}")
            self.assertEqual(artifact.status_code, 201, artifact.data)
            first = self.client.get(f'/api/ui-automation/test-case-executions/{ids[0]}/').data
            second = self.client.get(f'/api/ui-automation/test-case-executions/{ids[1]}/').data
            self.assertEqual(len(first['local_artifacts']), 1)
            self.assertEqual(second['local_artifacts'], [])
            url = f"/api/ui-automation/local-runner/artifacts/{artifact.data['id']}/download/"
            self.assertEqual(self.client.get(url).status_code, 200)
            self.client.force_authenticate(self.outsider)
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_permissions_and_job_scoping(self):
        created, code = self.create_job()
        _, other_code = self.create_job()
        job, other_job = self.claim(code).data, self.claim(other_code).data
        foreign_id = other_job['payload']['suite_items'][0]['execution_id']
        self.assertEqual(self.call(job, 'events', {'type': 'started', 'execution_id': foreign_id}).status_code, 400)
        self.assertEqual(self.call(job, 'events', {'type': 'started', 'execution_id': 'invalid'}).status_code, 400)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 404)
        self.assertEqual(self.client.get(f"/api/ui-automation/test-executions/{created['suite_execution_id']}/local-status/").status_code, 404)

    def test_older_runner_is_rejected_and_expiry_is_persisted(self):
        created, code = self.create_job()
        self.assertEqual(self.claim(code, version=2).status_code, 400)
        job = LocalExecutionJob.objects.get(pk=created['job_id'])
        self.assertEqual(job.status, 'waiting_runner')
        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=['expires_at'])
        self.assertEqual(self.claim(code).status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.status, 'expired')
        self.assertEqual(job.suite_execution.status, 'FAILED')
        self.assertFalse(TestCaseExecution.objects.filter(batch_id=job.id, status='pending').exists())

    def test_polling_expires_unclaimed_job(self):
        created, _ = self.create_job()
        LocalExecutionJob.objects.filter(pk=created['job_id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.get(f"/api/ui-automation/test-executions/{created['suite_execution_id']}/local-status/")
        self.assertEqual(response.data['runner_status'], 'expired')
        self.assertEqual(response.data['failed_cases'], 3)

    def test_report_deletion_allows_mysql_nullable_cascade(self):
        created, _ = self.create_job()
        with patch.object(connection.features, 'can_defer_constraint_checks', False):
            TestExecution.objects.get(pk=created['suite_execution_id']).delete()
        self.assertFalse(LocalExecutionJob.objects.filter(pk=created['job_id']).exists())

    def test_empty_invalid_and_cross_project_suites_do_not_create_partial_jobs(self):
        self.assertEqual(self.client.post(self.url, {'engine': 'selenium'}, format='json').status_code, 400)
        self.second.data_rows = [{'wrong': 'x'}]
        self.second.save()
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 400)
        self.assertEqual(TestCaseExecution.objects.count(), 0)
        other_project = UiProject.objects.create(name='Other', owner=self.outsider)
        self.second.project = other_project
        self.second.save()
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 400)
        self.suite.suite_test_cases.all().delete()
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 400)
        self.assertEqual(LocalExecutionJob.objects.count(), 0)

    def test_finishing_older_run_does_not_overwrite_newer_suite_status(self):
        old, code = self.create_job()
        job = self.claim(code).data
        self.create_job()
        results = [{'execution_id': item['execution_id'], 'success': True} for item in job['payload']['suite_items']]
        self.assertEqual(self.call(job, 'complete', {'case_results': results}).status_code, 200)
        self.suite.refresh_from_db()
        self.assertEqual(self.suite.execution_status, 'running')
        self.assertEqual(TestExecution.objects.get(pk=old['suite_execution_id']).status, 'SUCCESS')

    def test_suite_snapshot_keeps_files_available_after_steps_change(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            asset = TestFileAsset.objects.create(project=self.project, name='fixture.txt',
                file=SimpleUploadedFile('fixture.txt', b'fixture'), created_by=self.owner, file_size=7)
            step = self.first.steps.get()
            step.file_assets.add(asset)
            _, code = self.create_job()
            job = self.claim(code).data
            step.file_assets.clear()
            delete = self.client.delete(f'/api/ui-automation/test-file-assets/{asset.id}/')
            self.assertEqual(delete.status_code, 400)
            download = self.client.get(f"{job['urls']['files']}{asset.id}/",
                HTTP_AUTHORIZATION=f"Bearer {job['upload_token']}")
            self.assertEqual(download.status_code, 200)


class LocalSuiteAgentTests(SimpleTestCase):
    async def test_runner_continues_after_failure_and_scopes_events_and_artifacts(self):
        from local_playwright_agent import agent

        class Client:
            def __init__(self):
                self.job = {'payload': {'suite_items': [
                    {'execution_id': pk, 'payload': {'case': {'id': pk}}} for pk in [7, 8, 9]
                ]}}
                self.events, self.artifacts, self.results = [], [], None

            def event(self, event_type, **data):
                self.events.append((event_type, data))

            def artifact(self, path, artifact_type):
                self.artifacts.append(path.name)

            def complete(self, success, duration, steps, error_message='', **kwargs):
                self.results = kwargs['case_results']

        client = Client()
        visited = []
        original = agent._run_job

        async def run_case(scoped_client, directory):
            pk = scoped_client.job['payload']['case']['id']
            visited.append(pk)
            if pk == 8:
                raise RuntimeError('browser startup failure')
            scoped_client.event('started')
            scoped_client.complete(True, 1.0, [])
            trace = directory / 'trace.zip'
            trace.write_bytes(b'trace')
            scoped_client.artifact(trace, 'playwright_trace')

        with tempfile.TemporaryDirectory() as directory, patch.object(agent, '_run_job', side_effect=run_case):
            success = await original(client, Path(directory))
        self.assertFalse(success)
        self.assertEqual(visited, [7, 8, 9])
        self.assertEqual([row['success'] for row in client.results], [True, False, True])
        self.assertEqual([row['execution_id'] for row in client.results], [7, 8, 9])
        self.assertEqual(client.artifacts, ['execution-7-trace.zip', 'execution-9-trace.zip'])
        self.assertTrue(all(event[1]['execution_id'] in visited for event in client.events))
