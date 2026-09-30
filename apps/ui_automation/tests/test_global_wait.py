from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ui_automation.mcp_runner import _run_selenium_sync
from apps.ui_automation.models import TestCase, TestCaseStep, UiProject


class GlobalWaitApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='global-wait-owner', password='password'
        )
        self.project = UiProject.objects.create(
            name='Global wait project',
            base_url='https://example.test',
            owner=self.user,
        )
        self.test_case = TestCase.objects.create(
            project=self.project,
            name='Debug case',
            created_by=self.user,
        )
        TestCaseStep.objects.create(
            test_case=self.test_case,
            step_number=1,
            action_type='wait',
            wait_time=100,
        )
        self.client.force_authenticate(self.user)

    def test_global_wait_can_be_enabled_without_replacing_steps(self):
        response = self.client.patch(
            f'/api/ui-automation/test-cases/{self.test_case.id}/',
            {'global_wait_enabled': True, 'global_wait_time': 1500},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.test_case.refresh_from_db()
        self.assertTrue(self.test_case.global_wait_enabled)
        self.assertEqual(self.test_case.global_wait_time, 1500)
        self.assertEqual(self.test_case.steps.count(), 1)
        self.assertTrue(response.data['global_wait_enabled'])

    def test_global_wait_time_is_bounded(self):
        for invalid_value in (99, 60001):
            response = self.client.patch(
                f'/api/ui-automation/test-cases/{self.test_case.id}/',
                {'global_wait_time': invalid_value},
                format='json',
            )
            self.assertEqual(response.status_code, 400, response.data)


class GlobalWaitExecutionTests(APITestCase):
    def test_selenium_runner_waits_only_between_successful_steps(self):
        class FakeEngine:
            def __init__(self, **kwargs):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def execute_step(self, step, element):
                return True, 'ok', None

        case = SimpleNamespace(
            project=SimpleNamespace(base_url=''),
            global_wait_enabled=True,
            global_wait_time=1500,
        )
        steps_data = [
            {'step': object(), 'element_data': None, 'action_type': 'click', 'description': ''},
            {'step': object(), 'element_data': None, 'action_type': 'fill', 'description': ''},
        ]

        with (
            patch('apps.ui_automation.selenium_engine.SeleniumTestEngine', FakeEngine),
            patch('apps.ui_automation.mcp_runner.time.sleep') as sleep,
        ):
            result, step_results, _ = _run_selenium_sync(
                None, case, steps_data, browser='chrome', headless=True
            )

        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(step_results), 2)
        sleep.assert_called_once_with(1.5)
