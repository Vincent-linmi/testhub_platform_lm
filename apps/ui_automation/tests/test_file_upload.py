import hashlib
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.ui_automation.models import (
    Element,
    LocatorStrategy,
    TestCase,
    TestFileAsset,
    TestCaseStep,
    UiProject,
)


class TestFileUploadApiTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix='testhub-ui-assets-')
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()

        self.user = get_user_model().objects.create_user(
            username='ui-file-owner', password='password'
        )
        self.project = UiProject.objects.create(
            name='UI file project',
            base_url='https://example.test',
            owner=self.user,
        )
        self.client.force_authenticate(self.user)

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_upload_asset_and_attach_it_to_upload_step(self):
        content = b'test attachment content'
        response = self.client.post(
            '/api/ui-automation/test-file-assets/',
            {
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'invoice.pdf', content, content_type='application/pdf'
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201, response.data)
        asset = TestFileAsset.objects.get(pk=response.data['id'])
        self.assertEqual(asset.name, 'invoice.pdf')
        self.assertEqual(asset.file_size, len(content))
        self.assertEqual(asset.sha256, hashlib.sha256(content).hexdigest())

        strategy = LocatorStrategy.objects.create(name='css')
        element = Element.objects.create(
            project=self.project,
            name='从设备添加',
            locator_strategy=strategy,
            locator_value='button.upload',
            created_by=self.user,
        )
        test_case = TestCase.objects.create(
            project=self.project,
            name='上传附件',
            created_by=self.user,
        )

        update_response = self.client.patch(
            f'/api/ui-automation/test-cases/{test_case.id}/',
            {
                'steps': [{
                    'action_type': 'uploadFile',
                    'element_id': element.id,
                    'file_asset_id': asset.id,
                    'wait_time': 30000,
                    'description': '选择 invoice.pdf',
                }]
            },
            format='json',
        )

        self.assertEqual(update_response.status_code, 200, update_response.data)
        step = test_case.steps.get()
        self.assertEqual(step.action_type, 'uploadFile')
        self.assertEqual(step.file_asset_id, asset.id)
        self.assertEqual(list(step.file_assets.values_list('id', flat=True)), [asset.id])
        self.assertEqual(update_response.data['steps'][0]['file_asset_name'], 'invoice.pdf')
        self.assertEqual(update_response.data['steps'][0]['file_asset_ids'], [asset.id])

    def test_upload_step_accepts_multiple_assets_in_one_step(self):
        assets = [
            TestFileAsset.objects.create(
                project=self.project,
                name=name,
                file=SimpleUploadedFile(name, content),
                file_size=len(content),
                created_by=self.user,
            )
            for name, content in [('one.txt', b'one'), ('two.txt', b'two')]
        ]
        strategy = LocatorStrategy.objects.create(name='css')
        element = Element.objects.create(
            project=self.project,
            name='多文件输入框',
            locator_strategy=strategy,
            locator_value='input[type=file][multiple]',
            created_by=self.user,
        )
        test_case = TestCase.objects.create(
            project=self.project,
            name='一次上传多个附件',
            created_by=self.user,
        )

        response = self.client.patch(
            f'/api/ui-automation/test-cases/{test_case.id}/',
            {
                'steps': [{
                    'action_type': 'uploadFile',
                    'element_id': element.id,
                    'file_asset_ids': [asset.id for asset in assets],
                    'wait_time': 30000,
                }]
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        step = test_case.steps.get()
        self.assertEqual(step.file_asset_id, assets[0].id)
        self.assertCountEqual(
            list(step.file_assets.values_list('id', flat=True)),
            [asset.id for asset in assets],
        )
        self.assertEqual(step.file_asset_order, [asset.id for asset in assets])
        self.assertEqual(
            response.data['steps'][0]['file_asset_names'],
            ['one.txt', 'two.txt'],
        )

    def test_upload_step_rejects_asset_from_another_project(self):
        other_project = UiProject.objects.create(
            name='Other project',
            base_url='https://other.example.test',
            owner=self.user,
        )
        asset = TestFileAsset.objects.create(
            project=other_project,
            name='foreign.txt',
            file=SimpleUploadedFile('foreign.txt', b'foreign'),
            file_size=7,
            created_by=self.user,
        )
        strategy = LocatorStrategy.objects.create(name='css')
        element = Element.objects.create(
            project=self.project,
            name='上传按钮',
            locator_strategy=strategy,
            locator_value='button.upload',
            created_by=self.user,
        )
        test_case = TestCase.objects.create(
            project=self.project,
            name='越权文件',
            created_by=self.user,
        )

        response = self.client.patch(
            f'/api/ui-automation/test-cases/{test_case.id}/',
            {
                'steps': [{
                    'action_type': 'uploadFile',
                    'element_id': element.id,
                    'file_asset_id': asset.id,
                }]
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(test_case.steps.exists())

    def test_wait_until_enabled_step_can_guard_send_action(self):
        strategy = LocatorStrategy.objects.create(name='css')
        send_button = Element.objects.create(
            project=self.project,
            name='发送',
            locator_strategy=strategy,
            locator_value='button[aria-label="发送"]',
            created_by=self.user,
        )
        test_case = TestCase.objects.create(
            project=self.project,
            name='等待上传完成再发送',
            created_by=self.user,
        )

        response = self.client.patch(
            f'/api/ui-automation/test-cases/{test_case.id}/',
            {
                'steps': [
                    {
                        'action_type': 'waitForEnabled',
                        'element_id': send_button.id,
                        'wait_time': 180000,
                        'description': '等待附件上传完成',
                    },
                    {
                        'action_type': 'click',
                        'element_id': send_button.id,
                        'wait_time': 10000,
                    },
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        steps = list(test_case.steps.order_by('step_number'))
        self.assertEqual([step.action_type for step in steps], ['waitForEnabled', 'click'])
        self.assertEqual(steps[0].wait_time, 180000)

    def test_library_exposes_storage_and_download_and_deletes_unused_file(self):
        uploaded = self.client.post('/api/ui-automation/test-file-assets/', {
            'project': self.project.id,
            'file': SimpleUploadedFile('accounts.csv', b'username,password\naccount1,secret'),
        }, format='multipart')
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        asset = TestFileAsset.objects.get(pk=uploaded.data['id'])
        stored_path = asset.file.path
        from pathlib import Path
        self.assertTrue(Path(stored_path).exists())
        listed = self.client.get('/api/ui-automation/test-file-assets/', {'project': self.project.id, 'search': 'accounts'})
        files = listed.data['results'] if isinstance(listed.data, dict) else listed.data
        self.assertEqual(files[0]['storage_key'], asset.file.name)
        download = self.client.get(f'/api/ui-automation/test-file-assets/{asset.id}/download/')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), b'username,password\naccount1,secret')
        deleted = self.client.delete(f'/api/ui-automation/test-file-assets/{asset.id}/')
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Path(stored_path).exists())

    def test_library_refuses_deleting_used_assets_and_other_projects(self):
        asset = TestFileAsset.objects.create(project=self.project, name='used.txt',
                                            file=SimpleUploadedFile('used.txt', b'content'))
        case = TestCase.objects.create(project=self.project, name='Uses file', created_by=self.user)
        step = TestCaseStep.objects.create(test_case=case, step_number=1, action_type='uploadFile', file_asset=asset)
        step.file_assets.add(asset)
        response = self.client.delete(f'/api/ui-automation/test-file-assets/{asset.id}/')
        self.assertEqual(response.status_code, 400, response.data)
        listed = self.client.get(f'/api/ui-automation/test-file-assets/{asset.id}/')
        self.assertEqual(listed.data['used_by'], [{'id': case.id, 'name': case.name}])
        other = get_user_model().objects.create_user(username='other-library-user', password='password')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f'/api/ui-automation/test-file-assets/{asset.id}/download/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/ui-automation/test-file-assets/{asset.id}/').status_code, 404)
