<template>
  <nav class="app-navigation" :aria-label="$t('common.navigation')">
    <router-link class="logo" to="/home" @click="$emit('navigate')">
      <img :src="logoImage" alt="TestHub" />
    </router-link>
        <el-menu
          :default-active="$route.path"
          @select="$emit('navigate')"
          router
          background-color="transparent"
          text-color="#aeb9d3"
          active-text-color="#ffffff"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation'">
            <el-sub-menu index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.intelligentCaseGeneration') }}</span>
              </template>
              <el-menu-item index="/ai-generation/requirement-analysis">{{ $t('menu.aiCaseGeneration') }}</el-menu-item>
              <el-menu-item index="/ai-generation/generated-testcases">{{ $t('menu.aiGeneratedTestcases') }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.testCases') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/versions">
              <el-icon><Flag /></el-icon>
              <span>{{ $t('menu.versionManagement') }}</span>
            </el-menu-item>
            <el-sub-menu index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>{{ $t('menu.reviewManagement') }}</span>
              </template>
              <el-menu-item index="/ai-generation/reviews">{{ $t('menu.reviewList') }}</el-menu-item>
              <el-menu-item index="/ai-generation/review-templates">{{ $t('menu.reviewTemplates') }}</el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.testPlan') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing'">
            <el-menu-item index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>{{ $t('menu.interfaceManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.automationTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.requestHistory') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/environments">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('menu.environmentManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- Bug缺陷管理模块菜单 -->
          <template v-else-if="currentModule === 'defects'">
            <el-menu-item index="/defects/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.defectDashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/defects/list">
              <el-icon><Tickets /></el-icon>
              <span>{{ $t('menu.defectList') }}</span>
            </el-menu-item>
            <el-menu-item index="/defects/create">
              <el-icon><Plus /></el-icon>
              <span>{{ $t('menu.defectCreate') }}</span>
            </el-menu-item>
            <el-menu-item index="/defects/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.defectReport') }}</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation'">
            <el-menu-item index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.elementManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.caseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts-enhanced">
              <el-icon><Edit /></el-icon>
              <span>{{ $t('menu.scriptGeneration') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts">
              <el-icon><DocumentCopy /></el-icon>
              <span>{{ $t('menu.scriptList') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.suiteManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.executionRecords') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- APP自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'app-automation'">
            <el-menu-item index="/app-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/devices">
              <el-icon><Cellphone /></el-icon>
              <span>{{ $t('menu.deviceManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/packages">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.packageManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/elements">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.elementManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/scene-builder">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.caseDesign') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.testCases') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/test-suites">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ $t('menu.suiteManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.executionRecords') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- AI 智能模式模块菜单 -->
          <template v-else-if="currentModule === 'ai-intelligent-mode'">
            <el-menu-item index="/ai-intelligent-mode/testing">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.aiIntelligentTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.aiCaseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/execution-records">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.aiExecutionRecords') }}</span>
            </el-menu-item>

          </template>

          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration'">
            <el-sub-menu index="ai-case-generation">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.aiCaseGenerationConfig') }}</span>
              </template>
              <el-menu-item index="/configuration/ai-model">
                <el-icon><Cpu /></el-icon>
                <span>{{ $t('menu.aiModelConfig') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/prompt-config">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('menu.promptConfig') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/generation-config">
                <el-icon><Setting /></el-icon>
                <span>{{ $t('menu.generationConfig') }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>{{ $t('menu.uiEnvConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/app-env">
              <el-icon><Cellphone /></el-icon>
              <span>APP环境配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ai-mode">
              <el-icon><MagicStick /></el-icon>
              <span>{{ $t('menu.aiModeConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/scheduled-task">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.scheduledTaskConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ $t('menu.difyConfig') }}</span>
            </el-menu-item>
          </template>
          <!-- 智能评分器模块菜单 -->
          <template v-else-if="currentModule === 'llm-judge'">
            <el-menu-item index="/llm-judge/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.judgeDashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/llm-judge/single">
              <el-icon><Edit /></el-icon>
              <span>{{ $t('menu.judgeSingle') }}</span>
            </el-menu-item>
            <el-menu-item index="/llm-judge/batch">
              <el-icon><DocumentCopy /></el-icon>
              <span>{{ $t('menu.judgeBatch') }}</span>
            </el-menu-item>
            <el-menu-item index="/llm-judge/history">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.judgeHistory') }}</span>
            </el-menu-item>
            <el-menu-item index="/llm-judge/knowledge">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.judgeKnowledgeBase') }}</span>
            </el-menu-item>
            <el-menu-item index="/llm-judge/rubrics">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('menu.judgeRubrics') }}</span>
            </el-menu-item>
          </template>

          <!-- 监控中心模块菜单 -->
          <template v-else-if="currentModule === 'monitor'">
            <el-menu-item index="/monitor/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.monitorDashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/monitor/checks">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.monitorChecks') }}</span>
            </el-menu-item>
            <el-menu-item index="/monitor/alerts">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.monitorAlerts') }}</span>
            </el-menu-item>
            <el-menu-item index="/monitor/targets">
              <el-icon><Monitor /></el-icon>
              <span>{{ $t('menu.monitorTargets') }}</span>
            </el-menu-item>
            <el-menu-item index="/monitor/channels">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.monitorChannels') }}</span>
            </el-menu-item>
          </template>

          <!-- 性能测试模块菜单 -->
          <template v-else-if="currentModule === 'performance-testing'">
            <el-menu-item index="/performance-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.perfDashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.perfProjects') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/scenarios">
              <el-icon><SetUp /></el-icon>
              <span>{{ $t('menu.perfScenarios') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.perfExecutions') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/comparison">
              <el-icon><TrendCharts /></el-icon>
              <span>{{ $t('menu.perfComparison') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/comparison-reports">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.perfComparisonReports') }}</span>
            </el-menu-item>
            <el-menu-item index="/performance-testing/scheduled">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.perfScheduled') }}</span>
            </el-menu-item>
          </template>

          <!-- MCP 管理端模块菜单 -->
          <template v-else-if="currentModule === 'mcp'">
            <el-menu-item index="/mcp/console">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.mcpConsole') }}</span>
            </el-menu-item>
          </template>

          <!-- 文档中心模块菜单 -->
          <template v-else-if="currentModule === 'docs'">
            <el-menu-item index="/docs-center">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.docsCenter') }}</span>
            </el-menu-item>
          </template>
        </el-menu>
  </nav>
</template>

<script setup>
import {
  Monitor, Folder, Document, Flag, Check, Collection, VideoPlay,
  DataAnalysis, ChatDotRound, DocumentCopy, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu, Cellphone, Connection, FolderOpened, Tickets, Plus,
  SetUp, TrendCharts
} from '@element-plus/icons-vue'
import logoImage from '@/assets/images/logo_home.png'

defineProps({ currentModule: { type: String, default: '' } })
defineEmits(['navigate'])
</script>

<style scoped lang="scss">
.app-navigation {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--th-sidebar);
  color: #aeb9d3;
}
.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 72px;
  margin: 0 16px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  img { width: 100%; height: 44px; object-fit: contain; }
}
.el-menu {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  border: 0;
  padding: 12px 10px 24px;
  scrollbar-width: thin;
  scrollbar-color: #46516b transparent;
  :deep(.el-menu-item), :deep(.el-sub-menu__title) {
    height: 46px;
    margin: 4px 0;
    border-radius: var(--th-radius-sm);
    font-size: 14px;
  }
  :deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) {
    background: rgba(255, 255, 255, 0.08);
    color: white;
  }
  :deep(.el-menu-item.is-active) {
    background: var(--th-primary);
    color: white;
  }
  :deep(.el-sub-menu .el-menu-item) { min-width: 0; }
}
</style>
