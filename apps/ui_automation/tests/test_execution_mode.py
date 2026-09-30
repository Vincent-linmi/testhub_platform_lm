from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ui_automation.models import LocalExecutionJob, TestCase, TestCaseExecution, UiProject
from apps.ui_automation.test_executor import TestExecutor


class ExecutionModeTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='execution-mode-owner')
        self.project = UiProject.objects.create(name='Modes', owner=self.user)
        self.case = TestCase.objects.create(project=self.project, name='Modes', created_by=self.user)
        self.client.force_authenticate(self.user)

    def test_server_records_headless_even_when_client_requests_headed(self):
        for engine, check in (
            ('playwright', 'playwright_engine.PlaywrightTestEngine.check_execution_environment_sync'),
            ('selenium', 'selenium_engine.SeleniumTestEngine.check_execution_environment'),
        ):
            with self.subTest(engine=engine), patch(
                f'apps.ui_automation.{check}', return_value=(False, 'No test browser')
            ):
                response = self.client.post(
                    f'/api/ui-automation/test-cases/{self.case.id}/run/',
                    {'engine': engine, 'headless': False}, format='json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertTrue(TestCaseExecution.objects.latest('id').headless)

    def test_data_execution_and_retry_force_headless(self):
        for data_driven, extra in ((True, {}), (False, {'retry_execution_id': 1})):
            self.case.data_driven_enabled = data_driven
            self.case.save()
            with patch('apps.ui_automation.data_driven.start_data_execution') as start:
                start.return_value = SimpleNamespace(id=1, batch_id='batch')
                response = self.client.post(
                    f'/api/ui-automation/test-cases/{self.case.id}/run/',
                    {'headless': False, **extra}, format='json',
                )
                self.assertEqual(response.status_code, 202)
                self.assertIs(start.call_args.kwargs['headless'], True)

    def test_local_execution_preserves_selected_mode(self):
        from apps.ui_automation.models import TestCaseStep
        TestCaseStep.objects.create(test_case=self.case, step_number=1, action_type='wait', wait_time=100)
        for headless in (False, True):
            response = self.client.post(
                f'/api/ui-automation/test-cases/{self.case.id}/run-local/',
                {'browser': 'chrome', 'headless': headless}, format='json',
            )
            self.assertEqual(response.status_code, 201, response.data)
            self.assertIs(TestCaseExecution.objects.get(pk=response.data['execution_id']).headless, headless)
            self.assertIs(LocalExecutionJob.objects.get(pk=response.data['job_id']).payload['headless'], headless)

    def test_server_suite_ignores_legacy_headed_setting(self):
        self.assertTrue(TestExecutor(None, headless=False).headless)
