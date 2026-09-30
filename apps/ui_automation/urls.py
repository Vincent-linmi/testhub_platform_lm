from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import (
    UiProjectViewSet,
    LocatorStrategyViewSet,
    ElementGroupViewSet,
    ElementViewSet,
    TestScriptViewSet,
    PageObjectViewSet,
    ScriptStepViewSet,
    TestSuiteViewSet,
    TestExecutionViewSet,
    ScreenshotViewSet,
    TestCaseGroupViewSet,
    TestCaseViewSet,
    TestFileAssetViewSet,
    TestCaseStepViewSet,
    TestCaseExecutionViewSet,
    UiScheduledTaskViewSet,
    AIExecutionRecordViewSet,
    AICaseViewSet,
    UiNotificationLogViewSet,
    OperationRecordViewSet,
    UiDashboardViewSet
)
from .views_config import EnvironmentConfigViewSet, AIIntelligentModeConfigViewSet
from .local_runner_views import (
    LocalExecutionArtifactView,
    LocalExecutionArtifactDownloadView,
    LocalExecutionClaimView,
    LocalExecutionCompleteView,
    LocalExecutionCreateView,
    LocalExecutionEventView,
    LocalExecutionFileView,
)

from .local_suite_runner import LocalSuiteExecutionCreateView, LocalSuiteExecutionStatusView

router = DefaultRouter()
router.register(r'dashboard', UiDashboardViewSet, basename='dashboard')
router.register(r'projects', UiProjectViewSet)
router.register(r'locator-strategies', LocatorStrategyViewSet)
router.register(r'element-groups', ElementGroupViewSet)
router.register(r'elements', ElementViewSet)
router.register(r'test-scripts', TestScriptViewSet)
router.register(r'page-objects', PageObjectViewSet)
router.register(r'steps', ScriptStepViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-executions', TestExecutionViewSet)
router.register(r'screenshots', ScreenshotViewSet)
router.register(r'test-case-groups', TestCaseGroupViewSet, basename='test-case-groups')
router.register(r'test-cases', TestCaseViewSet)
router.register(r'test-file-assets', TestFileAssetViewSet, basename='test-file-assets')
router.register(r'test-case-steps', TestCaseStepViewSet)
router.register(r'test-case-executions', TestCaseExecutionViewSet)
router.register(r'scheduled-tasks', UiScheduledTaskViewSet)
router.register(r'ai-execution-records', AIExecutionRecordViewSet)
router.register(r'ai-cases', AICaseViewSet, basename='ai-cases')
router.register(r'ai-case-generation', AICaseViewSet, basename='ai-case-generation')
router.register(r'notification-logs', UiNotificationLogViewSet)
router.register(r'operation-records', OperationRecordViewSet)


# Configuration Center APIs
router.register(r'config/environment', EnvironmentConfigViewSet, basename='config-environment')
router.register(r'config/ai-mode', AIIntelligentModeConfigViewSet, basename='config-ai-mode')
router.register(r'ai-models', AIIntelligentModeConfigViewSet, basename='ai-models')

urlpatterns = [
    path('test-suites/<int:test_suite_id>/run-local/', LocalSuiteExecutionCreateView.as_view(), name='local-suite-execution-create'),
    path('test-executions/<int:execution_id>/local-status/', LocalSuiteExecutionStatusView.as_view(), name='local-suite-execution-status'),
    path('test-cases/<int:test_case_id>/run-local/', LocalExecutionCreateView.as_view(), name='local-execution-create'),
    path('local-runner/jobs/claim/', LocalExecutionClaimView.as_view(), name='local-execution-claim'),
    path('local-runner/jobs/<uuid:job_id>/events/', LocalExecutionEventView.as_view(), name='local-execution-events'),
    path('local-runner/jobs/<uuid:job_id>/artifacts/', LocalExecutionArtifactView.as_view(), name='local-execution-artifacts'),
    path('local-runner/jobs/<uuid:job_id>/complete/', LocalExecutionCompleteView.as_view(), name='local-execution-complete'),
    path('local-runner/jobs/<uuid:job_id>/files/<int:asset_id>/', LocalExecutionFileView.as_view(), name='local-execution-file'),
    path('local-runner/artifacts/<int:artifact_id>/download/', LocalExecutionArtifactDownloadView.as_view(), name='local-execution-artifact-download'),
    path('', include(router.urls)),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
