from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.projects.models import Project, ProjectMember
from apps.testcases.models import (
    TestCase as TCModel, TestCaseComment, TestCaseGroup, TestCaseStep,
)
from apps.users.models import User

# 注意：testcase-list / testcase-detail URL name 与 ui_automation 模块的 router 冲突，
# 这里直接使用路径常量以避免 reverse() 解析到错误的路由。
TC_LIST_URL = '/api/testcases/'
TC_GROUP_LIST_URL = '/api/testcases/groups/'
TC_BATCH_GROUP_URL = '/api/testcases/groups/assign/'


def tc_detail_url(pk):
    return f'/api/testcases/{pk}/'


class TestCaseApiTests(APITestCase):
    """Testcases 模块 - 测试用例 API 冒烟测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='tc_tester', password='pass123456')
        self.other_user = User.objects.create_user(username='tc_other', password='pass123456')
        self.project = Project.objects.create(name='用例测试项目', owner=self.user)
        ProjectMember.objects.create(project=self.project, user=self.user, role='tester')
        self.client.force_authenticate(self.user)
        self.list_url = TC_LIST_URL

    def test_list_requires_authentication(self):
        """未认证用户无法访问用例列表"""
        anon_client = APIClient()
        response = anon_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_testcase(self):
        """创建测试用例"""
        payload = {
            'title': '登录功能验证',
            'description': '验证正常登录流程',
            'preconditions': '用户已注册',
            'steps': '1. 打开登录页\n2. 输入账号密码\n3. 点击登录',
            'expected_result': '登录成功进入首页',
            'priority': 'high',
            'test_type': 'functional',
            'project_id': self.project.id,
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], '登录功能验证')
        self.assertEqual(TCModel.objects.count(), 1)

    def test_list_testcases_with_pagination(self):
        """列表查询支持分页"""
        for i in range(15):
            TCModel.objects.create(
                title=f'用例{i}', expected_result='通过', project=self.project, author=self.user,
            )

        response = self.client.get(self.list_url, {'page': 1, 'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['count'], 15)

    def test_retrieve_testcase_detail(self):
        """获取用例详情"""
        tc = TCModel.objects.create(
            title='详情测试', expected_result='通过', project=self.project, author=self.user,
        )
        TestCaseStep.objects.create(testcase=tc, step_number=1, action='点击按钮', expected='跳转')
        detail_url = tc_detail_url(tc.id)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], '详情测试')
        self.assertEqual(len(response.data['step_details']), 1)

    def test_update_testcase(self):
        """更新测试用例"""
        tc = TCModel.objects.create(
            title='旧标题', expected_result='通过', project=self.project, author=self.user,
        )
        detail_url = tc_detail_url(tc.id)
        response = self.client.patch(detail_url, {'title': '新标题'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tc.refresh_from_db()
        self.assertEqual(tc.title, '新标题')

    def test_delete_testcase(self):
        """删除测试用例"""
        tc = TCModel.objects.create(
            title='待删除', expected_result='通过', project=self.project, author=self.user,
        )
        detail_url = tc_detail_url(tc.id)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(TCModel.objects.count(), 0)

    def test_search_testcase_by_title(self):
        """按标题搜索用例"""
        TCModel.objects.create(
            title='支付流程验证', expected_result='通过', project=self.project, author=self.user,
        )
        TCModel.objects.create(
            title='登录流程验证', expected_result='通过', project=self.project, author=self.user,
        )
        response = self.client.get(self.list_url, {'search': '支付'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('支付', response.data['results'][0]['title'])

    def test_filter_by_priority(self):
        """按优先级过滤用例"""
        TCModel.objects.create(
            title='高优用例', expected_result='通过', project=self.project, author=self.user, priority='high',
        )
        TCModel.objects.create(
            title='低优用例', expected_result='通过', project=self.project, author=self.user, priority='low',
        )
        response = self.client.get(self.list_url, {'priority': 'high'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['priority'], 'high')

    def test_only_project_members_see_testcases(self):
        """非项目成员无法看到用例"""
        TCModel.objects.create(
            title='内部用例', expected_result='通过', project=self.project, author=self.user,
        )
        self.client.force_authenticate(self.other_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_create_group_and_assign_when_creating_testcase(self):
        """可在项目内创建分组，并在创建用例时归入该分组。"""
        group_response = self.client.post(TC_GROUP_LIST_URL, {
            'project_id': self.project.id,
            'name': '登录模块',
        }, format='json')
        self.assertEqual(group_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.list_url, {
            'title': '登录分组用例',
            'expected_result': '登录成功',
            'project_id': self.project.id,
            'group_id': group_response.data['id'],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        testcase = TCModel.objects.get(pk=response.data['id'])
        self.assertEqual(testcase.group_id, group_response.data['id'])

    def test_filter_grouped_and_ungrouped_testcases(self):
        """列表可按分组或未分组筛选。"""
        group = TestCaseGroup.objects.create(project=self.project, name='支付模块')
        TCModel.objects.create(
            title='已分组用例', expected_result='通过', project=self.project,
            author=self.user, group=group,
        )
        TCModel.objects.create(
            title='未分组用例', expected_result='通过', project=self.project,
            author=self.user,
        )

        grouped_response = self.client.get(self.list_url, {'group': group.id})
        ungrouped_response = self.client.get(self.list_url, {'group': 'ungrouped'})

        self.assertEqual(grouped_response.data['count'], 1)
        self.assertEqual(grouped_response.data['results'][0]['group']['id'], group.id)
        self.assertEqual(ungrouped_response.data['count'], 1)
        self.assertIsNone(ungrouped_response.data['results'][0]['group'])

    def test_batch_move_testcases_to_group(self):
        """选中的用例可批量移入同项目分组。"""
        group = TestCaseGroup.objects.create(project=self.project, name='批量分组')
        testcases = [
            TCModel.objects.create(
                title=f'批量用例{i}', expected_result='通过',
                project=self.project, author=self.user,
            )
            for i in range(2)
        ]

        response = self.client.post(TC_BATCH_GROUP_URL, {
            'testcase_ids': [testcase.id for testcase in testcases],
            'group_id': group.id,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(TCModel.objects.filter(group=group).count(), 2)

    def test_cannot_assign_group_from_another_project(self):
        """用例不能归入其他项目的分组。"""
        other_project = Project.objects.create(name='其他项目', owner=self.user)
        other_group = TestCaseGroup.objects.create(project=other_project, name='其他分组')
        testcase = TCModel.objects.create(
            title='当前项目用例', expected_result='通过',
            project=self.project, author=self.user,
        )

        response = self.client.post(TC_BATCH_GROUP_URL, {
            'testcase_ids': [testcase.id],
            'group_id': other_group.id,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        testcase.refresh_from_db()
        self.assertIsNone(testcase.group_id)

    def test_delete_group_keeps_testcases_as_ungrouped(self):
        """删除分组不会删除其中的测试用例。"""
        group = TestCaseGroup.objects.create(project=self.project, name='待删除分组')
        testcase = TCModel.objects.create(
            title='保留用例', expected_result='通过', project=self.project,
            author=self.user, group=group,
        )

        response = self.client.delete(f'{TC_GROUP_LIST_URL}{group.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        testcase.refresh_from_db()
        self.assertIsNone(testcase.group_id)
