import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { trackPageView } from '@/utils/tracker'

// Keep login and the shared shell small; load feature screens on navigation.
import Login from '@/views/auth/Login.vue'
const Register = () => import('@/views/auth/Register.vue')
import Layout from '@/layout/index.vue'
const ProjectList = () => import('@/views/projects/ProjectList.vue')
const Home = () => import('@/views/Home.vue')
const DataFactory = () => import('@/views/data-factory/DataFactory.vue')
const ApiDashboard = () => import('@/views/api-testing/Dashboard.vue')
const ApiProjectManagement = () => import('@/views/api-testing/ProjectManagement.vue')
const ApiInterfaceManagement = () => import('@/views/api-testing/InterfaceManagement.vue')
const ApiAutomationTesting = () => import('@/views/api-testing/AutomationTesting.vue')
const ApiRequestHistory = () => import('@/views/api-testing/RequestHistory.vue')
const ApiEnvironmentManagement = () => import('@/views/api-testing/EnvironmentManagement.vue')
const ApiReportView = () => import('@/views/api-testing/ReportView.vue')
const ApiScheduledTasks = () => import('@/views/api-testing/ScheduledTasks.vue')
const ApiAIServiceConfig = () => import('@/views/api-testing/AIServiceConfig.vue')
const NotificationLogs = () => import('@/views/notification/NotificationLogs.vue')
const UiDashboard = () => import('@/views/ui-automation/dashboard/Dashboard.vue')
const UiProjectList = () => import('@/views/ui-automation/projects/ProjectList.vue')
const UiElementManagerEnhanced = () => import('@/views/ui-automation/elements/ElementManagerEnhanced.vue')
const UiTestCaseManager = () => import('@/views/ui-automation/test-cases/TestCaseManager.vue')
const UiScriptEditorEnhanced = () => import('@/views/ui-automation/scripts/ScriptEditorEnhanced.vue')
const UiScriptList = () => import('@/views/ui-automation/scripts/ScriptList.vue')
const UiSuiteList = () => import('@/views/ui-automation/suites/SuiteList.vue')
const UiExecutionList = () => import('@/views/ui-automation/executions/ExecutionList.vue')
const UiReportList = () => import('@/views/ui-automation/reports/ReportList.vue')
const UiScheduledTasks = () => import('@/views/ui-automation/scheduled-tasks/ScheduledTasks.vue')
const UiNotificationLogs = () => import('@/views/ui-automation/notification/NotificationLogs.vue')
const UiAITesting = () => import('@/views/ui-automation/ai/AITesting.vue')
const UiAICaseList = () => import('@/views/ui-automation/ai/AICaseList.vue')
const UiAIExecutionRecords = () => import('@/views/ui-automation/ai/AIExecutionRecords.vue')
const MonitorDashboard = () => import('@/views/monitor/Dashboard.vue')
const MonitorCheckLogs = () => import('@/views/monitor/CheckLogs.vue')
const MonitorAlerts = () => import('@/views/monitor/Alerts.vue')
const MonitorTargets = () => import('@/views/monitor/MonitorTargets.vue')
const NotificationChannels = () => import('@/views/monitor/NotificationChannels.vue')
const PerfIndex = () => import('@/views/performance-testing/index.vue')
const PerfDashboard = () => import('@/views/performance-testing/Dashboard.vue')
const PerfProjectManagement = () => import('@/views/performance-testing/ProjectManagement.vue')
const PerfScenarioList = () => import('@/views/performance-testing/ScenarioList.vue')
const PerfScenarioEditor = () => import('@/views/performance-testing/ScenarioEditor.vue')
const PerfExecutionList = () => import('@/views/performance-testing/ExecutionList.vue')
const PerfExecutionMonitor = () => import('@/views/performance-testing/ExecutionMonitor.vue')
const PerfExecutionReport = () => import('@/views/performance-testing/ExecutionReport.vue')
const PerfComparison = () => import('@/views/performance-testing/Comparison.vue')
const PerfComparisonReports = () => import('@/views/performance-testing/ComparisonReports.vue')
const PerfScheduledTasks = () => import('@/views/performance-testing/ScheduledTasks.vue')

/** @type {import('vue-router').RouteRecordRaw[]} */
const routes = [
    {
        path: '/',
        redirect: to => ({ path: '/home', query: to.query })
    },
    {
        path: '/home',
        name: 'Home',
        component: Home,
        meta: { requiresAuth: true }
    },
    {
        path: '/login',
        name: 'Login',
        component: Login,
        meta: { requiresGuest: true }
    },
    {
        path: '/register',
        name: 'Register',
        component: Register,
        meta: { requiresGuest: true }
    },
    {
        path: '/ai-generation/assistant',
        name: 'Assistant',
        component: () => import('@/views/assistant/AssistantView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/ai-generation',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'requirement-analysis'
            },
            {
                path: 'requirement-analysis',
                name: 'RequirementAnalysis',
                component: () => import('@/views/requirement-analysis/RequirementAnalysisView.vue')
            },
            {
                path: 'projects',
                name: 'Projects',
                component: ProjectList
            },
            {
                path: 'projects/:id',
                name: 'ProjectDetail',
                component: () => import('@/views/projects/ProjectDetail.vue')
            },
            {
                path: 'testcases',
                name: 'TestCases',
                component: () => import('@/views/testcases/TestCaseList.vue')
            },
            {
                path: 'testcases/import-records',
                name: 'TestCaseImportRecords',
                component: () => import('@/views/testcases/TestCaseImportRecordList.vue')
            },
            {
                path: 'testcases/create',
                name: 'CreateTestCase',
                component: () => import('@/views/testcases/TestCaseForm.vue')
            },
            {
                path: 'testcases/:id',
                name: 'TestCaseDetail',
                component: () => import('@/views/testcases/TestCaseDetail.vue')
            },
            {
                path: 'testcases/:id/edit',
                name: 'EditTestCase',
                component: () => import('@/views/testcases/TestCaseEdit.vue')
            },
            {
                path: 'versions',
                name: 'Versions',
                component: () => import('@/views/versions/VersionList.vue')
            },
            {
                path: 'reviews',
                name: 'Reviews',
                component: () => import('@/views/reviews/ReviewList.vue')
            },
            {
                path: 'reviews/create',
                name: 'CreateReview',
                component: () => import('@/views/reviews/ReviewForm.vue')
            },
            {
                path: 'reviews/:id',
                name: 'ReviewDetail',
                component: () => import('@/views/reviews/ReviewDetail.vue')
            },
            {
                path: 'reviews/:id/edit',
                name: 'EditReview',
                component: () => import('@/views/reviews/ReviewForm.vue')
            },
            {
                path: 'review-templates',
                name: 'ReviewTemplates',
                component: () => import('@/views/reviews/ReviewTemplateList.vue')
            },
            {
                path: 'testsuites',
                name: 'TestSuites',
                component: () => import('@/views/testsuites/TestSuiteList.vue')
            },
            {
                path: 'executions',
                name: 'Executions',
                component: () => import('@/views/executions/ExecutionListView.vue')
            },
            {
                path: 'executions/:id',
                name: 'ExecutionDetail',
                component: () => import('@/views/executions/ExecutionDetailView.vue')
            },
            {
                path: 'reports',
                name: 'AiTestReport',
                component: () => import('@/views/reports/AiTestReport.vue')
            },
            {
                path: 'generated-testcases',
                name: 'GeneratedTestCases',
                component: () => import('@/views/requirement-analysis/GeneratedTestCaseList.vue')
            },
            {
                path: 'task-detail/:taskId',
                name: 'TaskDetail',
                component: () => import('@/views/requirement-analysis/TaskDetail.vue')
            },
            {
                path: 'profile',
                name: 'Profile',
                component: () => import('@/views/profile/UserProfile.vue')
            }
        ]
    },
    {
        path: '/api-testing',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'ApiDashboard',
                component: ApiDashboard
            },
            {
                path: 'projects',
                name: 'ApiProjects',
                component: ApiProjectManagement
            },
            {
                path: 'interfaces',
                name: 'ApiInterfaces',
                component: ApiInterfaceManagement
            },
            {
                path: 'automation',
                name: 'ApiAutomation',
                component: ApiAutomationTesting
            },
            {
                path: 'history',
                name: 'ApiHistory',
                component: ApiRequestHistory
            },
            {
                path: 'environments',
                name: 'ApiEnvironments',
                component: ApiEnvironmentManagement
            },
            {
                path: 'reports',
                name: 'ApiReports',
                component: ApiReportView
            },
            {
                path: 'scheduled-tasks',
                name: 'ApiScheduledTasks',
                component: ApiScheduledTasks
            },
            {
                path: 'ai-service-config',
                name: 'ApiAIServiceConfig',
                component: ApiAIServiceConfig
            },
            {
                path: 'notification-logs',
                name: 'ApiNotificationLogs',
                component: NotificationLogs
            }
        ]
    },
    {
        path: '/ui-automation',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'UiDashboard',
                component: UiDashboard
            },
            {
                path: 'projects',
                name: 'UiProjects',
                component: UiProjectList
            },
            {
                path: 'elements-enhanced',
                name: 'UiElementsEnhanced',
                component: UiElementManagerEnhanced
            },
            {
                path: 'test-cases',
                name: 'UiTestCases',
                component: UiTestCaseManager
            },
            {
                path: 'scripts-enhanced',
                name: 'UiScriptsEnhanced',
                component: UiScriptEditorEnhanced
            },
            {
                path: 'scripts/editor',
                name: 'UiScriptEditor',
                component: UiScriptEditorEnhanced
            },
            {
                path: 'scripts',
                name: 'UiScripts',
                component: UiScriptList
            },
            {
                path: 'suites',
                name: 'UiSuites',
                component: UiSuiteList
            },
            {
                path: 'executions',
                name: 'UiExecutions',
                component: UiExecutionList
            },
            {
                path: 'reports',
                name: 'UiReports',
                component: UiReportList
            },
            {
                path: 'scheduled-tasks',
                name: 'UiScheduledTasks',
                component: UiScheduledTasks
            },
            {
                path: 'notification-logs',
                name: 'UiNotificationLogs',
                component: UiNotificationLogs
            }
        ]
    },
    {
        path: '/ai-intelligent-mode',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'testing'
            },
            {
                path: 'testing',
                name: 'AITesting',
                component: UiAITesting
            },
            {
                path: 'cases',
                name: 'AICaseList',
                component: UiAICaseList
            },
            {
                path: 'execution-records',
                name: 'AIExecutionRecords',
                component: UiAIExecutionRecords
            }
        ]
    },
    {
        path: '/defects',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'DefectDashboard',
                component: () => import('@/views/defects/DefectDashboard.vue')
            },
            {
                path: 'list',
                name: 'DefectList',
                component: () => import('@/views/defects/DefectList.vue')
            },
            {
                path: 'create',
                name: 'DefectCreate',
                component: () => import('@/views/defects/DefectForm.vue')
            },
            {
                path: 'reports',
                name: 'DefectReport',
                component: () => import('@/views/defects/DefectReport.vue')
            },
            {
                path: ':id',
                name: 'DefectDetail',
                component: () => import('@/views/defects/DefectDetail.vue')
            },
            {
                path: ':id/edit',
                name: 'DefectEdit',
                component: () => import('@/views/defects/DefectForm.vue')
            }
        ]
    },
    {
        path: '/data-factory',
        name: 'DataFactory',
        component: DataFactory,
        meta: { requiresAuth: true }
    },
    {
        path: '/configuration',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                component: () => import('@/views/configuration/ConfigurationCenter.vue'),
                children: [
                    {
                        path: '',
                        redirect: 'ai-model'
                    },
                    {
                        path: 'ai-model',
                        name: 'ConfigAIModel',
                        component: () => import('@/views/requirement-analysis/AIModelConfig.vue')
                    },
                    {
                        path: 'prompt-config',
                        name: 'ConfigPromptConfig',
                        component: () => import('@/views/requirement-analysis/PromptConfig.vue')
                    },
                    {
                        path: 'generation-config',
                        name: 'ConfigGenerationConfig',
                        component: () => import('@/views/requirement-analysis/GenerationConfigView.vue')
                    },
                    {
                        path: 'ui-env',
                        name: 'ConfigUIEnv',
                        component: () => import('@/views/configuration/UIEnvironmentConfig.vue')
                    },
                    {
                        path: 'app-env',
                        name: 'ConfigAppEnv',
                        component: () => import('@/views/app-automation/settings/AppSettings.vue')
                    },
                    {
                        path: 'ai-mode',
                        name: 'ConfigAIMode',
                        component: () => import('@/views/configuration/AIIntelligentModeConfig.vue')
                    },
                    {
                        path: 'scheduled-task',
                        name: 'ConfigScheduledTask',
                        component: () => import('@/views/ui-automation/notification/NotificationConfigs.vue')
                    },
                    {
                        path: 'dify',
                        name: 'DifyConfig',
                        component: () => import('@/views/configuration/DifyConfig.vue')
                    }
                ]
            }
        ]
    },
    // 智能评分器路由
    {
        path: '/llm-judge',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'JudgeDashboard',
                component: () => import('@/views/llm-judge/Dashboard.vue')
            },
            {
                path: 'single',
                name: 'JudgeSingle',
                component: () => import('@/views/llm-judge/SingleJudge.vue')
            },
            {
                path: 'batch',
                name: 'JudgeBatch',
                component: () => import('@/views/llm-judge/BatchJudge.vue')
            },
            {
                path: 'history',
                name: 'JudgeHistory',
                component: () => import('@/views/llm-judge/HistoryList.vue')
            },
            {
                path: 'rubrics',
                name: 'JudgeRubrics',
                component: () => import('@/views/llm-judge/RubricList.vue')
            },
            {
                path: 'knowledge',
                name: 'JudgeKnowledgeBase',
                component: () => import('@/views/llm-judge/KnowledgeBase.vue')

            }
        ]
    },
    // APP自动化测试路由
    {
        path: '/app-automation',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'AppAutomationDashboard',
                component: () => import('@/views/app-automation/dashboard/Dashboard.vue')
            },
            {
                path: 'projects',
                name: 'AppProjectList',
                component: () => import('@/views/app-automation/projects/ProjectList.vue')
            },
            {
                path: 'devices',
                name: 'AppDeviceList',
                component: () => import('@/views/app-automation/devices/DeviceList.vue')
            },
            {
                path: 'packages',
                name: 'AppPackageList',
                component: () => import('@/views/app-automation/packages/PackageList.vue')
            },
            {
                path: 'elements',
                name: 'AppElementList',
                component: () => import('@/views/app-automation/elements/ElementList.vue')
            },
            {
                path: 'scene-builder',
                name: 'AppSceneBuilder',
                component: () => import('@/views/app-automation/test-cases/SceneBuilder.vue'),
                meta: { title: '用例编排' }
            },
            {
                path: 'test-cases',
                name: 'AppTestCaseList',
                component: () => import('@/views/app-automation/test-cases/TestCaseList.vue')
            },
            {
                path: 'test-suites',
                name: 'AppTestSuiteList',
                component: () => import('@/views/app-automation/suites/SuiteList.vue')
            },
            {
                path: 'scheduled-tasks',
                name: 'AppScheduledTasks',
                component: () => import('@/views/app-automation/scheduled-tasks/ScheduledTasks.vue')
            },
            {
                path: 'notification-logs',
                name: 'AppNotificationLogs',
                component: () => import('@/views/app-automation/notification/NotificationLogs.vue')
            },
            {
                path: 'executions',
                name: 'AppExecutionList',
                component: () => import('@/views/app-automation/executions/ExecutionList.vue')
            },
            {
                path: 'reports',
                name: 'AppReportList',
                component: () => import('@/views/app-automation/reports/ReportList.vue')
            }
        ]
    },
    {
        path: '/monitor',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'MonitorDashboard',
                component: MonitorDashboard
            },
            {
                path: 'checks',
                name: 'MonitorCheckLogs',
                component: MonitorCheckLogs
            },
            {
                path: 'alerts',
                name: 'MonitorAlerts',
                component: MonitorAlerts
            },
            {
                path: 'targets',
                name: 'MonitorTargets',
                component: MonitorTargets
            },
            {
                path: 'channels',
                name: 'NotificationChannels',
                component: NotificationChannels
            }
        ]
    },
    {
        path: '/performance-testing',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'dashboard'
            },
            {
                path: 'dashboard',
                name: 'PerfDashboard',
                component: PerfDashboard
            },
            {
                path: 'projects',
                name: 'PerfProjects',
                component: PerfProjectManagement
            },
            {
                path: 'scenarios',
                name: 'PerfScenarios',
                component: PerfScenarioList
            },
            {
                path: 'scenarios/:id',
                name: 'PerfScenarioEditor',
                component: PerfScenarioEditor
            },
            {
                path: 'executions',
                name: 'PerfExecutions',
                component: PerfExecutionList
            },
            {
                path: 'executions/:id',
                name: 'PerfExecutionReport',
                component: PerfExecutionReport
            },
            {
                path: 'executions/:id/monitor',
                name: 'PerfExecutionMonitor',
                component: PerfExecutionMonitor
            },
            {
                path: 'comparison',
                name: 'PerfComparison',
                component: PerfComparison
            },
            {
                path: 'comparison-reports',
                name: 'PerfComparisonReports',
                component: PerfComparisonReports
            },
            {
                path: 'scheduled',
                name: 'PerfScheduled',
                component: PerfScheduledTasks
            }
        ]
    },
    {
        path: '/mcp',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: 'console'
            },
            {
                path: 'console',
                name: 'McpConsole',
                component: () => import('@/views/mcp/McpConsole.vue')
            }
        ]
    },
    {
        path: '/docs-center',
        component: Layout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'DocsCenter',
                component: () => import('@/views/docs-center/DocsCenter.vue')
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach(async (to, _from, next) => {
    const userStore = useUserStore()

    // SSO 授权码交换：在登录态检查之前，先把 URL 中的 code 换成 JWT
    const code = to.query.code
    if (code && !userStore.accessToken) {
        try {
            const api = (await import('@/utils/api')).default
            const response = await api.post('/auth/exchange-token/', {
                action: 'redeem',
                code: code,
            })
            const expiresAt = Date.now() + 30 * 60 * 1000
            localStorage.setItem('access_token', response.data.access)
            localStorage.setItem('refresh_token', response.data.refresh)
            localStorage.setItem('token_expires_at', expiresAt.toString())
            localStorage.setItem('user', JSON.stringify(response.data.user))
            userStore.accessToken = response.data.access
            userStore.refreshToken = response.data.refresh
            userStore.tokenExpiresAt = expiresAt
            userStore.user = response.data.user

            // 清除 URL 中的 code，使用 replace 避免产生多余历史记录
            const query = { ...to.query }
            delete query.code
            next({ path: to.path, query, replace: true })
            return
        } catch {
            // code 无效或已过期，继续正常流程
        }
    }

    // 有 token 但没有用户信息时，初始化认证
    if (!userStore.user && userStore.accessToken) {
        try {
            await userStore.initAuth()
        } catch (error) {
            console.error('认证初始化失败:', error)
        }
    }

    if (to.meta.requiresAuth && !userStore.isAuthenticated) {
        next('/login')
    } else if (to.meta.requiresGuest && userStore.isAuthenticated) {
        next('/home')
    } else {
        next()
    }
})

router.afterEach((to, from) => {
    trackPageView(to, from)
})

export default router
