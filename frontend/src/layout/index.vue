<template>
  <div class="layout">
    <el-container>
      <el-aside class="desktop-navigation" width="224px">
        <AppNavigation :current-module="currentModule" />
      </el-aside>
      <el-drawer
        v-model="mobileNavigationOpen"
        class="th-navigation-drawer"
        direction="ltr"
        size="min(280px, 88vw)"
        :title="$t('common.navigation')"
      >
        <AppNavigation :current-module="currentModule" @navigate="mobileNavigationOpen = false" />
      </el-drawer>

      <!-- 主体内容 -->
      <el-container>
        <!-- 顶部导航 -->
        <el-header height="60px">
          <div class="header-content">
            <div class="header-left">
              <el-button
                class="mobile-navigation-toggle"
                :icon="Menu"
                :aria-label="$t('common.openNavigation')"
                :aria-expanded="mobileNavigationOpen"
                @click="mobileNavigationOpen = true"
              />
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/home' }">{{ $t('nav.home') }}</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <!-- 语言切换 -->
              <el-dropdown @command="handleLanguageChange" class="language-dropdown">
                <span class="language-selector">
                  <span class="language-flag">{{ appStore.language === 'zh-cn' ? '🇨🇳' : '🇺🇸' }}</span>
                  <span>{{ currentLanguage }}</span>
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="zh-cn" :disabled="appStore.language === 'zh-cn'">
                      <span class="dropdown-flag">🇨🇳</span> 简体中文
                    </el-dropdown-item>
                    <el-dropdown-item command="en" :disabled="appStore.language === 'en'">
                      <span class="dropdown-flag">🇺🇸</span> English
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- 用户信息 -->
              <el-dropdown @command="handleCommand" class="user-dropdown">
                <span class="user-info">
                  <el-avatar :size="32" :src="userStore.user?.avatar" />
                  <span class="username">{{ userStore.user?.username }}</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">{{ $t('nav.profile') }}</el-dropdown-item>
                    <el-dropdown-item divided command="logout">{{ $t('nav.logout') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppNavigation from './AppNavigation.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { ArrowDown, Menu } from '@element-plus/icons-vue'


const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const { t } = useI18n()

const mobileNavigationOpen = ref(false)
const isMobile = useMediaQuery('(max-width: 768px)')
watch(() => route.fullPath, () => { mobileNavigationOpen.value = false })
watch(isMobile, (mobile) => { if (!mobile) mobileNavigationOpen.value = false })

// 当前语言显示
const currentLanguage = computed(() => {
  return appStore.language === 'zh-cn' ? '简体中文' : 'English'
})

// 切换语言（无需刷新页面）
const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
  ElMessage.success(lang === 'zh-cn' ? '语言已切换为中文' : 'Language switched to English')
}

const currentModule = computed(() => {
  if (route.path.startsWith('/ai-generation')) return 'ai-generation'
  if (route.path.startsWith('/api-testing')) return 'api-testing'
  if (route.path.startsWith('/ui-automation')) return 'ui-automation'
  if (route.path.startsWith('/defects')) return 'defects'
  if (route.path.startsWith('/app-automation')) return 'app-automation'
  if (route.path.startsWith('/ai-intelligent-mode')) return 'ai-intelligent-mode'
  if (route.path.startsWith('/configuration')) return 'configuration'
  if (route.path.startsWith('/llm-judge')) return 'llm-judge'
  if (route.path.startsWith('/monitor')) return 'monitor'
  if (route.path.startsWith('/performance-testing')) return 'performance-testing'
  if (route.path.startsWith('/mcp')) return 'mcp'
  if (route.path.startsWith('/docs-center')) return 'docs'
  return ''
})

const moduleName = computed(() => {
  const map = {
    'ai-generation': t('modules.aiGeneration'),
    'api-testing': t('modules.apiTesting'),
    'ui-automation': t('modules.uiAutomation'),
    'defects': t('modules.defects'),
    'app-automation': t('modules.appAutomation'),
    'ai-intelligent-mode': t('modules.aiIntelligentMode'),
    'configuration': t('modules.configuration'),
    'llm-judge': t('modules.llmJudge'),
    'monitor': t('modules.monitor'),
    'performance-testing': t('modules.performanceTesting'),
    'mcp': t('modules.mcp'),
    'docs': t('modules.docs')
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // AI用例生成
    '/ai-generation/requirement-analysis': t('menu.aiCaseGeneration'),
    '/ai-generation/generated-testcases': t('menu.aiGeneratedTestcases'),
    '/ai-generation/projects': t('menu.projectManagement'),
    '/ai-generation/testcases': t('menu.testCases'),
    '/ai-generation/versions': t('menu.versionManagement'),
    '/ai-generation/reviews': t('menu.reviewList'),
    '/ai-generation/review-templates': t('menu.reviewTemplates'),
    '/ai-generation/testsuites': t('menu.suiteManagement'),
    '/ai-generation/executions': t('menu.executionRecords'),
    '/ai-generation/reports': t('menu.testReport'),

    // 接口测试
    '/api-testing/dashboard': t('menu.dashboard'),
    '/api-testing/projects': t('menu.projectManagement'),
    '/api-testing/interfaces': t('menu.interfaceManagement'),
    '/api-testing/automation': t('menu.automationTesting'),
    '/api-testing/history': t('menu.requestHistory'),
    '/api-testing/environments': t('menu.environmentManagement'),
    '/api-testing/reports': t('menu.testReport'),
    '/api-testing/scheduled-tasks': t('menu.scheduledTasks'),
    '/api-testing/notification-logs': t('menu.notificationList'),

    // Bug缺陷管理
    '/defects/dashboard': t('menu.defectDashboard'),
    '/defects/list': t('menu.defectList'),
    '/defects/create': t('menu.defectCreate'),
    '/defects/reports': t('menu.defectReport'),

    // UI自动化测试
    '/ui-automation/dashboard': t('menu.dashboard'),
    '/ui-automation/projects': t('menu.projectManagement'),
    '/ui-automation/elements-enhanced': t('menu.elementManagement'),
    '/ui-automation/test-cases': t('menu.caseManagement'),
    '/ui-automation/scripts-enhanced': t('menu.scriptGeneration'),
    '/ui-automation/scripts': t('menu.scriptList'),
    '/ui-automation/suites': t('menu.suiteManagement'),
    '/ui-automation/executions': t('menu.executionRecords'),
    '/ui-automation/reports': t('menu.testReport'),
    '/ui-automation/scheduled-tasks': t('menu.scheduledTasks'),
    '/ui-automation/notification-logs': t('menu.notificationList'),

    // APP自动化测试
    '/app-automation/dashboard': t('menu.dashboard'),
    '/app-automation/projects': t('menu.projectManagement'),
    '/app-automation/devices': t('menu.deviceManagement'),
    '/app-automation/packages': t('menu.packageManagement'),
    '/app-automation/elements': t('menu.elementManagement'),
    '/app-automation/scene-builder': t('menu.caseDesign'),
    '/app-automation/test-cases': t('menu.testCases'),
    '/app-automation/test-suites': t('menu.suiteManagement'),
    '/app-automation/scheduled-tasks': t('menu.scheduledTasks'),
    '/app-automation/notification-logs': t('menu.notificationList'),
    '/app-automation/executions': t('menu.executionRecords'),
    '/app-automation/reports': t('menu.testReport'),

    // AI 智能模式
    '/ai-intelligent-mode/testing': t('menu.aiIntelligentTesting'),
    '/ai-intelligent-mode/cases': t('menu.aiCaseManagement'),
    '/ai-intelligent-mode/execution-records': t('menu.aiExecutionRecords'),


    // 配置中心
    '/configuration/ai-model': t('menu.aiModelConfig'),
    '/configuration/prompt-config': t('menu.promptConfig'),
    '/configuration/generation-config': t('menu.generationConfig'),
    '/configuration/ui-env': t('menu.uiEnvConfig'),
    '/configuration/ai-mode': t('menu.aiModeConfig'),
    '/configuration/scheduled-task': t('menu.scheduledTaskConfig'),
    '/configuration/dify': t('menu.difyConfig'),
    
    // 智能评分器
    '/llm-judge/dashboard': t('menu.judgeDashboard'),
    '/llm-judge/single': t('menu.judgeSingle'),
    '/llm-judge/batch': t('menu.judgeBatch'),
    '/llm-judge/history': t('menu.judgeHistory'),
    '/llm-judge/rubrics': t('menu.judgeRubrics'),
    '/llm-judge/knowledge': t('menu.judgeKnowledgeBase'),

    '/profile': t('nav.profile')
  }
  return routeMap[route.path] || route.meta.title || ''
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/ai-generation/profile')
  }
}
</script>

<style scoped lang="scss">
.layout { height: 100vh; height: 100dvh; background: var(--th-canvas); }
.layout > .el-container { height: 100%; overflow: hidden; }
.desktop-navigation { height: 100%; flex-shrink: 0; }
.el-container .el-container { min-width: 0; height: 100%; flex-direction: column; }
.el-header {
  flex-shrink: 0;
  height: 64px;
  padding: 0 24px;
  background: var(--th-surface);
  border-bottom: 1px solid var(--th-border);
}
.header-content, .header-left, .header-right, .user-info, .language-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-content { height: 100%; justify-content: space-between; }
.header-left { min-width: 0; flex: 1; }
.header-right { flex-shrink: 0; }
.el-breadcrumb { line-height: 1.6; }
.user-info, .language-selector {
  min-height: 40px;
  padding: 4px 8px;
  border-radius: var(--th-radius-sm);
  cursor: pointer;
  white-space: nowrap;
  color: var(--th-text-secondary);
  &:hover { background: var(--th-surface-subtle); }
}
.username { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.dropdown-flag { margin-right: 6px; }
.mobile-navigation-toggle { display: none; }
.el-main { min-width: 0; min-height: 0; padding: 24px; overflow: auto; }
:global(.th-navigation-drawer) {
  --el-drawer-bg-color: var(--th-sidebar);
}
:global(.th-navigation-drawer .el-drawer__header) {
  padding: 16px;
  color: white;
  border-color: rgba(255,255,255,.1);
}
:global(.th-navigation-drawer .el-drawer__body) { padding: 0; overflow: hidden; }
@media (max-width: 1024px) {
  .el-header { padding: 0 16px; }
  .el-main { padding: 16px; }
  .username { display: none; }
}
@media (max-width: 768px) {
  .desktop-navigation { display: none; }
  .mobile-navigation-toggle { display: inline-flex; flex-shrink: 0; width: 40px; height: 40px; }
  .el-header { height: 60px; padding: 0 12px; }
  .el-main { padding: 16px 12px; }
  .header-content, .header-left, .header-right { gap: 8px; }
  .language-selector { gap: 4px; padding: 4px; font-size: 13px; }
  .el-breadcrumb { overflow: hidden; white-space: nowrap; }
  :deep(.el-breadcrumb__item:not(:last-child)) { display: none; }
  :deep(.el-breadcrumb__inner) { display: block; max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
}
</style>
