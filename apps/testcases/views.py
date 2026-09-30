from django.http import FileResponse
from rest_framework import generics, permissions, serializers, status, pagination
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models, transaction
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView

from .models import (
    TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment,
    TestCaseGroup, TestCaseImportRecord,
)
from .serializers import (
    TestCaseSerializer, TestCaseListSerializer, TestCaseCreateSerializer, TestCaseUpdateSerializer,
    TestCaseGroupSerializer, TestCaseImportRecordListSerializer,
    TestCaseImportRecordDetailSerializer,
)
from apps.projects.models import Project
from .services import TestCaseImportTemplateService, TestCaseExcelImportService
from .tasks import import_testcases_from_excel

class TestCasePagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class TestCaseImportRecordPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_user_accessible_projects(user):
    return Project.objects.filter(
        models.Q(owner=user) | models.Q(members=user)
    ).distinct()

class TestCaseListCreateView(generics.ListCreateAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TestCasePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'test_type']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestCaseCreateSerializer
        return TestCaseListSerializer

    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_user_accessible_projects(user)
        queryset = TestCase.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'author', 'assignee', 'project', 'group'
        ).prefetch_related(
            'versions'
        ).distinct()
        # 支持多项目过滤：project=1,2,3（单值 project=1 同样兼容）
        project_param = self.request.query_params.get('project')
        if project_param:
            project_ids = [int(pid) for pid in project_param.split(',') if pid.strip().isdigit()]
            if project_ids:
                queryset = queryset.filter(project_id__in=project_ids)
        group_param = self.request.query_params.get('group')
        if group_param == 'ungrouped':
            queryset = queryset.filter(group__isnull=True)
        elif group_param and group_param.isdigit():
            queryset = queryset.filter(group_id=int(group_param))
        return queryset
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_user_accessible_projects(user)
    
    def perform_create(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        # 获取用户有权限的项目
        accessible_projects = self.get_user_accessible_projects(user)
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                project = accessible_projects.first()
                if not project:
                    # 如果用户没有任何项目，创建默认项目
                    project = Project.objects.create(
                        name="默认项目",
                        owner=user,
                        description='系统自动创建的默认项目'
                    )
        else:
            # 没有指定项目，使用第一个可访问的项目
            project = accessible_projects.first()
            if not project:
                # 如果用户没有任何项目，创建默认项目
                project = Project.objects.create(
                    name="默认项目",
                    owner=user,
                    description='系统自动创建的默认项目'
                )
        
        group = None
        group_id = self.request.data.get('group_id')
        if group_id not in (None, ''):
            group = TestCaseGroup.objects.filter(id=group_id, project=project).first()
            if not group:
                raise serializers.ValidationError({'group_id': '所选分组不属于该项目'})

        serializer.save(author=user, project=project, group=group)

class TestCaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TestCaseUpdateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_user_accessible_projects(user)
        return TestCase.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'author', 'assignee', 'project', 'group'
        ).prefetch_related(
            'versions', 'step_details', 'attachments', 'comments'
        )
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_user_accessible_projects(user)
    
    def perform_update(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        project = serializer.instance.project
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            accessible_projects = self.get_user_accessible_projects(user)
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                raise serializers.ValidationError({'project_id': '项目不存在或无权访问'})

        save_kwargs = {'project': project}
        if 'group_id' in self.request.data:
            group_id = self.request.data.get('group_id')
            group = None
            if group_id not in (None, ''):
                group = TestCaseGroup.objects.filter(id=group_id, project=project).first()
                if not group:
                    raise serializers.ValidationError({'group_id': '所选分组不属于该项目'})
            save_kwargs['group'] = group
        elif project != serializer.instance.project:
            # 切换项目时旧分组不再适用。
            save_kwargs['group'] = None

        serializer.save(**save_kwargs)


class TestCaseGroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TestCaseGroupSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = TestCaseGroup.objects.filter(
            project__in=get_user_accessible_projects(self.request.user)
        ).select_related('project').annotate(
            testcase_count=models.Count('testcases')
        )
        project_id = self.request.query_params.get('project')
        if project_id and project_id.isdigit():
            queryset = queryset.filter(project_id=int(project_id))
        return queryset

    def perform_create(self, serializer):
        project_id = self.request.data.get('project_id')
        try:
            project = get_user_accessible_projects(self.request.user).get(id=project_id)
        except (Project.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError({'project_id': '请选择有权访问的项目'})
        if TestCaseGroup.objects.filter(project=project, name__iexact=serializer.validated_data['name']).exists():
            raise serializers.ValidationError({'name': '该项目下已存在同名分组'})
        serializer.save(project=project)


class TestCaseGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TestCaseGroupSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return TestCaseGroup.objects.filter(
            project__in=get_user_accessible_projects(self.request.user)
        ).select_related('project').annotate(
            testcase_count=models.Count('testcases')
        )

    def perform_update(self, serializer):
        name = serializer.validated_data.get('name')
        if name and TestCaseGroup.objects.filter(
            project=serializer.instance.project,
            name__iexact=name,
        ).exclude(pk=serializer.instance.pk).exists():
            raise serializers.ValidationError({'name': '该项目下已存在同名分组'})
        serializer.save()


class TestCaseBatchGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        testcase_ids = request.data.get('testcase_ids')
        if not isinstance(testcase_ids, list) or not testcase_ids:
            return Response({'testcase_ids': '请选择要移动的测试用例'}, status=status.HTTP_400_BAD_REQUEST)
        if len(testcase_ids) > 1000:
            return Response({'testcase_ids': '一次最多移动 1000 条测试用例'}, status=status.HTTP_400_BAD_REQUEST)

        normalized_ids = set()
        for testcase_id in testcase_ids:
            try:
                normalized_ids.add(int(testcase_id))
            except (TypeError, ValueError):
                return Response({'testcase_ids': '测试用例ID格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

        testcases = TestCase.objects.filter(
            id__in=normalized_ids,
            project__in=get_user_accessible_projects(request.user),
        )
        if testcases.count() != len(normalized_ids):
            return Response({'testcase_ids': '部分测试用例不存在或无权访问'}, status=status.HTTP_400_BAD_REQUEST)

        group_id = request.data.get('group_id')
        group = None
        if group_id not in (None, ''):
            group = TestCaseGroup.objects.filter(
                id=group_id,
                project__in=get_user_accessible_projects(request.user),
            ).first()
            if not group:
                return Response({'group_id': '分组不存在或无权访问'}, status=status.HTTP_400_BAD_REQUEST)
            if testcases.exclude(project=group.project).exists():
                return Response({'group_id': '只能将用例移入同一项目下的分组'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = testcases.update(group=group)
        return Response({'updated_count': updated_count, 'group_id': group.id if group else None})


class TestCaseImportTemplateDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        template_stream = TestCaseImportTemplateService.build_template()
        return FileResponse(
            template_stream,
            as_attachment=True,
            filename='testcase_import_template_v1.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class TestCaseImportRecordListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TestCaseImportRecordPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return TestCaseImportRecordListSerializer

    def get_queryset(self):
        return TestCaseImportRecord.objects.filter(
            project__in=get_user_accessible_projects(self.request.user)
        ).select_related('project', 'created_by')

    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project_id')
        import_file = request.FILES.get('file')

        if not project_id:
            return Response({'error': '请选择导入项目'}, status=status.HTTP_400_BAD_REQUEST)
        if not import_file:
            return Response({'error': '请上传 Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not import_file.name.lower().endswith('.xlsx'):
            return Response({'error': '仅支持 .xlsx 格式文件'}, status=status.HTTP_400_BAD_REQUEST)

        accessible_projects = get_user_accessible_projects(request.user)
        try:
            project = accessible_projects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({'error': '项目不存在或无权限访问'}, status=status.HTTP_403_FORBIDDEN)

        record = TestCaseImportRecord.objects.create(
            import_no=TestCaseExcelImportService.generate_import_no(),
            project=project,
            import_file=import_file,
            created_by=request.user,
            template_version='v1'
        )

        celery_task = import_testcases_from_excel.delay(record.id)
        record.celery_task_id = celery_task.id
        record.save(update_fields=['celery_task_id', 'updated_at'])

        serializer = self.get_serializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TestCaseImportRecordDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TestCaseImportRecordDetailSerializer
    queryset = TestCaseImportRecord.objects.select_related('project', 'created_by')

    def get_queryset(self):
        return super().get_queryset().filter(
            project__in=get_user_accessible_projects(self.request.user)
        )


class TestCaseImportFailureReportDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        record = TestCaseImportRecord.objects.filter(
            pk=pk,
            project__in=get_user_accessible_projects(request.user)
        ).first()

        if not record:
            return Response({'error': '导入记录不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not record.failure_report_file:
            return Response({'error': '当前记录没有失败明细文件'}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            record.failure_report_file.open('rb'),
            as_attachment=True,
            filename=record.failure_report_file.name.split('/')[-1],
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
