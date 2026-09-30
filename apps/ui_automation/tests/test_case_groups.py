from rest_framework import status
from rest_framework.test import APITestCase

from apps.ui_automation.models import TestCase, TestCaseGroup, UiProject
from apps.users.models import User


class TestCaseGroupApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='group_owner', password='pass123456')
        self.outsider = User.objects.create_user(username='group_outsider', password='pass123456')
        self.project = UiProject.objects.create(
            name='UI 项目',
            base_url='https://example.test',
            owner=self.owner,
        )
        self.other_project = UiProject.objects.create(
            name='其他项目',
            base_url='https://other.example.test',
            owner=self.outsider,
        )
        self.client.force_authenticate(self.owner)

    def test_create_group_and_assign_test_case(self):
        group_response = self.client.post(
            '/api/ui-automation/test-case-groups/',
            {'project_id': self.project.id, 'name': '登录页'},
            format='json',
        )
        self.assertEqual(group_response.status_code, status.HTTP_201_CREATED)

        case_response = self.client.post(
            '/api/ui-automation/test-cases/',
            {
                'project': self.project.id,
                'group_id': group_response.data['id'],
                'name': '账号密码登录',
            },
            format='json',
        )
        self.assertEqual(case_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(case_response.data['group']['name'], '登录页')

    def test_filter_test_cases_by_group(self):
        login_group = TestCaseGroup.objects.create(project=self.project, name='登录页')
        TestCase.objects.create(
            project=self.project,
            group=login_group,
            name='登录成功',
            created_by=self.owner,
        )
        TestCase.objects.create(
            project=self.project,
            name='首页加载',
            created_by=self.owner,
        )

        response = self.client.get(
            '/api/ui-automation/test-cases/',
            {'project': self.project.id, 'group': login_group.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual([item['name'] for item in results], ['登录成功'])

    def test_reject_group_from_another_project(self):
        foreign_group = TestCaseGroup.objects.create(project=self.other_project, name='其他页面')

        response = self.client.post(
            '/api/ui-automation/test-cases/',
            {
                'project': self.project.id,
                'group_id': foreign_group.id,
                'name': '错误分组用例',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('group_id', response.data)

    def test_delete_group_keeps_cases_ungrouped(self):
        group = TestCaseGroup.objects.create(project=self.project, name='登录页')
        test_case = TestCase.objects.create(
            project=self.project,
            group=group,
            name='登录成功',
            created_by=self.owner,
        )

        response = self.client.delete(f'/api/ui-automation/test-case-groups/{group.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        test_case.refresh_from_db()
        self.assertIsNone(test_case.group_id)

    def test_copy_case_keeps_group(self):
        group = TestCaseGroup.objects.create(project=self.project, name='登录页')
        test_case = TestCase.objects.create(
            project=self.project,
            group=group,
            name='登录成功',
            created_by=self.owner,
        )

        response = self.client.post(f'/api/ui-automation/test-cases/{test_case.id}/copy_case/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['group']['id'], group.id)
        self.assertEqual(TestCase.objects.get(pk=response.data['id']).group_id, group.id)

    def test_move_existing_case_into_and_out_of_group(self):
        group = TestCaseGroup.objects.create(project=self.project, name='登录页')
        test_case = TestCase.objects.create(
            project=self.project,
            name='历史登录用例',
            created_by=self.owner,
        )
        url = f'/api/ui-automation/test-cases/{test_case.id}/'

        move_response = self.client.patch(url, {'group_id': group.id}, format='json')
        self.assertEqual(move_response.status_code, status.HTTP_200_OK)
        self.assertEqual(move_response.data['group']['id'], group.id)

        ungroup_response = self.client.patch(url, {'group_id': None}, format='json')
        self.assertEqual(ungroup_response.status_code, status.HTTP_200_OK)
        self.assertIsNone(ungroup_response.data['group'])

    def test_cannot_list_or_create_groups_for_inaccessible_project(self):
        TestCaseGroup.objects.create(project=self.other_project, name='不可见分组')

        list_response = self.client.get('/api/ui-automation/test-case-groups/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data, [])

        create_response = self.client.post(
            '/api/ui-automation/test-case-groups/',
            {'project_id': self.other_project.id, 'name': '越权分组'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
