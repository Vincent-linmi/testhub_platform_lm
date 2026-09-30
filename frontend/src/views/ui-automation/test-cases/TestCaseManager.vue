<template>
  <div class="test-case-manager">
    <div class="page-header">
      <h1 class="page-title">{{ t('uiAutomation.testCase.title') }}</h1>
      <div class="header-actions">
        <el-select v-model="projectId" :placeholder="t('uiAutomation.project.selectProject')" class="project-select" @change="onProjectChange">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-button type="primary" :disabled="!projectId" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          {{ t('uiAutomation.testCase.newTestCase') }}
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧：测试用例列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <div class="panel-title case-list-title">
            <h3>{{ t('uiAutomation.testCase.testCaseList') }}</h3>
            <span class="count-badge">{{ filteredTestCases.length }}</span>
            <el-button link type="primary" size="small" :disabled="!projectId" @click="openGroupDialog">
              <el-icon><Folder /></el-icon>
              {{ t('uiAutomation.testCase.manageGroups') }}
            </el-button>
          </div>
          <el-input
            v-model="searchKeyword"
            :placeholder="t('uiAutomation.testCase.searchPlaceholder')"
            clearable
            size="small"
            class="case-search"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="groupFilter" size="small" class="group-filter" @change="onGroupFilterChange">
            <el-option :label="t('uiAutomation.testCase.allGroups')" value="all" />
            <el-option :label="t('uiAutomation.testCase.ungrouped')" value="ungrouped" />
            <el-option v-for="group in testCaseGroups" :key="group.id" :label="group.name" :value="group.id" />
          </el-select>
        </div>

        <div class="test-case-list">
          <el-empty v-if="groupedTestCases.length === 0" :description="t('uiAutomation.testCase.noTestCases')" :image-size="72" />
          <section v-for="section in groupedTestCases" :key="section.key" class="case-group-section">
            <div
              class="case-group-heading"
              role="button"
              tabindex="0"
              :aria-expanded="!isGroupCollapsed(section.key)"
              @click="toggleGroup(section.key)"
              @keydown.enter.prevent="toggleGroup(section.key)"
              @keydown.space.prevent="toggleGroup(section.key)"
            >
              <span class="case-group-heading__name">
                <el-icon><component :is="isGroupCollapsed(section.key) ? ArrowRight : ArrowDown" /></el-icon>
                {{ section.name }}
              </span>
              <span class="case-group-count">{{ section.cases.length }}</span>
            </div>
            <template v-if="!isGroupCollapsed(section.key)">
              <div
                v-for="testCase in section.cases"
                :key="testCase.id"
                class="test-case-item"
                :class="{ active: selectedTestCase?.id === testCase.id }"
                @click="selectTestCase(testCase)"
              >
              <div class="case-header">
                <div class="case-info">
                  <h4 class="case-name">{{ testCase.name }}</h4>
                  <p class="case-description">{{ testCase.description || t('uiAutomation.testCase.noDescription') }}</p>
                </div>
                <div class="case-actions">
                  <el-button size="small" text :title="t('uiAutomation.testCase.runLabel')" :aria-label="t('uiAutomation.testCase.runLabel')" @click.stop="runTestCase(testCase)">
                    <el-icon><CaretRight /></el-icon>
                  </el-button>
                  <el-button size="small" text :title="t('uiAutomation.testCase.editTestCase')" :aria-label="t('uiAutomation.testCase.editTestCase')" @click.stop="editTestCase(testCase)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" text :title="t('uiAutomation.testCase.moveToGroup')" :aria-label="t('uiAutomation.testCase.moveToGroup')" @click.stop="openMoveGroupDialog(testCase)">
                    <el-icon><FolderOpened /></el-icon>
                  </el-button>
                  <el-button size="small" text :title="t('uiAutomation.testCase.copyTestCase')" :aria-label="t('uiAutomation.testCase.copyTestCase')" @click.stop="copyTestCase(testCase)">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                  <el-button size="small" text type="danger" :title="t('common.delete')" :aria-label="t('common.delete')" @click.stop="deleteTestCase(testCase)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <div class="case-meta">
                <span class="step-count">{{ testCase.steps?.length || 0 }} {{ t('uiAutomation.testCase.stepsCount') }}</span>
                <span class="update-time">{{ formatTime(testCase.updated_at) }}</span>
              </div>
              </div>
            </template>
          </section>
        </div>
      </div>

      <!-- 右侧：测试用例详情和步骤编辑 -->
      <div class="right-panel">
        <div v-if="selectedTestCase" class="test-case-detail">
          <div class="detail-header">
            <div class="detail-title">
              <span class="detail-title__eyebrow">{{ t('uiAutomation.testCase.caseType') }}</span>
              <h3>{{ selectedTestCase.name }}</h3>
              <el-tag size="small" type="info" class="detail-group-tag">
                {{ selectedTestCase.group?.name || t('uiAutomation.testCase.ungrouped') }}
              </el-tag>
              <p v-if="selectedTestCase.description">{{ selectedTestCase.description }}</p>
            </div>
            <div class="detail-actions">
              <el-button size="small" :loading="isSaving" :disabled="executionBusy" @click="saveTestCase()">
                <el-icon><Check /></el-icon>
                {{ t('uiAutomation.testCase.saveCaseLabel') }}
              </el-button>
              <el-button size="small" type="primary" :loading="isRunning" :disabled="executionBusy || isSaving" @click="saveAndRun()">
                <el-icon v-if="!isRunning"><CaretRight /></el-icon>
                {{ t('uiAutomation.testCase.saveAndRunLabel') }}
              </el-button>
              <el-button size="small" :loading="isLocalStarting" :disabled="executionBusy || isSaving || selectedEngine !== 'playwright'" :title="t('uiAutomation.testCase.localRunHint')" @click="saveAndRun(true)">
                <el-icon v-if="!isLocalStarting"><Monitor /></el-icon>
                {{ t('uiAutomation.testCase.localRunLabel') }}
              </el-button>
            </div>
          </div>

          <el-tabs v-model="activeEditorTab" class="case-editor-tabs">
          <!-- 测试步骤编辑 -->
          <el-tab-pane name="steps" :label="t('uiAutomation.testCase.testSteps')" class="editor-pane">
          <div class="steps-container">
            <div class="steps-header">
              <div class="steps-heading">
                <div class="panel-title">
                  <h4>{{ t('uiAutomation.testCase.testSteps') }}</h4>
                  <span class="count-badge">{{ currentSteps.length }}</span>
                </div>
                <p>{{ t('uiAutomation.testCase.stepsEditorHint') }}</p>
              </div>
              <div class="steps-header__actions">
                <el-button v-if="currentSteps.length" size="small" text @click="expandAllSteps">
                  {{ allStepsExpanded ? t('uiAutomation.testCase.foldAll') : t('uiAutomation.testCase.expandAll') }}
                </el-button>
                <el-button size="small" type="primary" :disabled="isSaving || executionBusy" @click="addStep()">
                  <el-icon><Plus /></el-icon>
                  {{ t('uiAutomation.testCase.addStep') }}
                </el-button>
              </div>
            </div>

            <div ref="stepsScrollContainer" class="steps-scroll-container" :inert="isSaving || executionBusy" :aria-busy="isSaving || executionBusy">
              <div class="steps-list">
                <draggable
                  v-model="currentSteps"
                  item-key="id"
                  handle=".drag-handle"
                  ghost-class="step-item--ghost"
                  :disabled="isSaving || executionBusy"
                  @change="onStepsReorder"
                >
                  <template #item="{ element, index }">
                    <div class="step-item" :class="{ expanded: element.expanded, 'is-new': highlightedStepId === element.id }" :data-step-id="element.id">
                      <div class="step-header">
                        <div class="step-left">
                          <div class="step-index">
                            <el-icon class="drag-handle" :title="t('uiAutomation.testCase.stepsEditorHint')"><Rank /></el-icon>
                            <span class="step-number">{{ index + 1 }}</span>
                          </div>
                          <div class="step-field step-field--action">
                            <span class="step-field__label">{{ t('uiAutomation.testCase.selectAction') }}</span>
                          <el-select
                            v-model="element.action_type"
                            :placeholder="t('uiAutomation.testCase.selectAction')"
                            size="small"
                            :aria-label="t('uiAutomation.testCase.selectAction')"
                            @change="onActionTypeChange(element)"
                          >
                            <el-option :label="t('uiAutomation.testCase.actionClick')" value="click" />
                            <el-option :label="t('uiAutomation.testCase.actionFill')" value="fill" />
                            <el-option :label="t('uiAutomation.testCase.actionGetText')" value="getText" />
                            <el-option :label="t('uiAutomation.testCase.actionWaitFor')" value="waitFor" />
                            <el-option :label="t('uiAutomation.testCase.actionWaitForEnabled')" value="waitForEnabled" />
                            <el-option :label="t('uiAutomation.testCase.actionHover')" value="hover" />
                            <el-option :label="t('uiAutomation.testCase.actionScroll')" value="scroll" />
                            <el-option :label="t('uiAutomation.testCase.actionScreenshot')" value="screenshot" />
                            <el-option :label="t('uiAutomation.testCase.actionAssert')" value="assert" />
                            <el-option :label="t('uiAutomation.testCase.actionWait')" value="wait" />
                            <el-option :label="t('uiAutomation.testCase.actionSwitchTab')" value="switchTab" />
                            <el-option :label="t('uiAutomation.testCase.actionUploadFile')" value="uploadFile" />
                            <el-option v-for="action in extraActions" :key="action" :value="action" :label="t(`uiAutomation.testCase.extendedActions.${action}`)" />
                          </el-select>
                          </div>
                          <div v-if="needsStepElement(element)" class="step-field step-field--element">
                            <span class="step-field__label">{{ t('uiAutomation.testCase.selectElement') }}</span>
                          <el-select
                            v-model="element.element_id"
                            :placeholder="t('uiAutomation.testCase.selectElement')"
                            size="small"
                            :aria-label="t('uiAutomation.testCase.selectElement')"
                            filterable
                            fit-input-width
                            autocomplete="new-password"
                            name="testhub-ui-element-picker"
                            :filter-method="filterElementOptions"
                            popper-class="test-case-element-dropdown"
                            @visible-change="onElementPickerVisibleChange"
                            @change="onElementChange(element)"
                          >
                            <el-option-group
                              v-for="group in groupedAvailableElements"
                              :key="group.page"
                              :label="`${group.page}（${group.elements.length}）`"
                            >
                              <el-option
                                v-for="elem in group.elements"
                                :key="elem.id"
                                :label="getElementSelectedLabel(elem)"
                                :value="elem.id"
                              >
                                <div class="element-option" :title="elem.locator_value">
                                  <div class="element-option__header">
                                    <span class="element-option__name">{{ elem.name }}</span>
                                    <span v-if="elem.component_name" class="element-option__badge">
                                      {{ elem.component_name }}
                                    </span>
                                    <span class="element-option__badge element-option__badge--strategy">
                                      {{ elem.locator_strategy || '未知策略' }}
                                    </span>
                                  </div>
                                  <div class="element-option__locator">{{ elem.locator_value }}</div>
                                </div>
                              </el-option>
                            </el-option-group>
                          </el-select>
                          </div>
                        </div>

                        <div class="step-right">
                          <el-button size="small" text :disabled="isSaving || executionBusy" :title="t('uiAutomation.testCase.insertStepAfter')" :aria-label="t('uiAutomation.testCase.insertStepAfter')" @click="addStep(index + 1)">
                            <el-icon><Plus /></el-icon>
                          </el-button>
                          <el-button
                            size="small"
                            text
                            :title="element.expanded ? t('uiAutomation.testCase.collapseStep') : t('uiAutomation.testCase.expandStep')"
                            :aria-label="element.expanded ? t('uiAutomation.testCase.collapseStep') : t('uiAutomation.testCase.expandStep')"
                            :aria-expanded="element.expanded"
                            @click="element.expanded = !element.expanded"
                          >
                            <el-icon>
                              <component :is="element.expanded ? ArrowUp : ArrowDown" />
                            </el-icon>
                          </el-button>
                          <el-button size="small" text type="danger" :title="t('common.delete')" :aria-label="t('common.delete')" @click="removeStep(index)">
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </div>
                      </div>

                      <p v-if="!element.expanded && element.description" class="step-summary">{{ element.description }}</p>

                      <div v-if="element.expanded" class="step-content" :class="{ 'step-content--assert': element.action_type === 'assert' }">
                        <!-- 输入参数 -->
                        <div v-if="needsStepInput(element)" class="step-param">
                          <label>{{ t(`uiAutomation.testCase.${stepInputLabel(element)}`) }}</label>
                          <div class="step-input-tools">
                            <el-input
                              v-model="element.input_value"
                              :placeholder="t(`uiAutomation.testCase.${stepInputHint(element)}`, { reference: '${runtime.orderId}' })"
                              size="small"
                            >
                              <template #append>
                                <el-button
                                  size="small"
                                  :icon="MagicStick"
                                  @click="openDataFactorySelector(element, 'input_value')"
                                  :title="t('uiAutomation.testCase.referenceDataFactory')"
                                  class="data-factory-btn"
                                />
                              </template>
                            </el-input>
                            <el-tooltip :content="t('uiAutomation.testCase.insertVariable')" placement="top" v-if="element.action_type !== 'switchTab'">
                              <el-button size="small" @click="openVariableHelper(element, 'input_value')" class="variable-helper-btn">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>

                        <!-- 上传文件 -->
                        <div v-if="element.action_type === 'uploadFile'" class="step-param step-param--wide">
                          <label>{{ t('uiAutomation.testCase.testFile') }}</label>
                          <div class="step-file-tools">
                          <el-select
                            v-model="element.file_asset_ids"
                            :placeholder="t('uiAutomation.testCase.selectTestFile')"
                            size="small"
                            filterable
                            multiple
                            collapse-tags
                            collapse-tags-tooltip
                            class="step-file-select"
                          >
                            <el-option
                              v-for="asset in testFileAssets"
                              :key="asset.id"
                              :label="`${asset.name} (${formatFileSize(asset.file_size)})`"
                              :value="asset.id"
                            />
                          </el-select>
                          <el-upload
                            :show-file-list="false"
                            :http-request="options => uploadStepFile(element, options)"
                            :disabled="uploadingFile"
                            multiple
                          >
                            <el-button size="small" type="primary" plain :loading="uploadingFile">
                              {{ t('uiAutomation.testCase.uploadFromComputer') }}
                            </el-button>
                          </el-upload>
                          </div>
                        </div>

                        <div v-if="['getText', 'selectOption', 'press'].includes(element.action_type)" class="step-param step-param--wide">
                          {{ t(`uiAutomation.testCase.${stepInputHint(element)}`, { reference: '${runtime.orderId}' }) }}
                        </div>
                        <!-- 等待时间 -->
                        <div v-if="needsWaitTime(element.action_type)" class="step-param">
                          <label>{{ t(element.action_type === 'assert' ? 'uiAutomation.testCase.assertTimeout' : 'uiAutomation.testCase.waitTime') }}</label>
                          <el-input-number
                            v-model="element.wait_time"
                            :min="100"
                            :max="30000"
                            :step="100"
                            size="small"
                          />
                        </div>

                        <!-- 断言参数 -->
                        <div v-if="element.action_type === 'assert'" class="step-param step-param--assert-type">
                          <label>{{ t('uiAutomation.testCase.assertType') }}</label>
                          <el-select v-model="element.assert_type" size="small">
                            <el-option :label="t('uiAutomation.testCase.assertTextContains')" value="textContains" />
                            <el-option :label="t('uiAutomation.testCase.assertTextEquals')" value="textEquals" />
                            <el-option :label="t('uiAutomation.testCase.assertIsVisible')" value="isVisible" />
                            <el-option :label="t('uiAutomation.testCase.assertExists')" value="exists" />
                            <el-option :label="t('uiAutomation.testCase.assertHasAttribute')" value="hasAttribute" />
                            <el-option v-for="assertion in extraAssertions" :key="assertion" :value="assertion" :label="t(`uiAutomation.testCase.extendedAssertions.${assertion}`)" />
                          </el-select>
                        </div>
                        <div v-if="needsExpectedValue(element)" class="step-param step-param--expected-value">
                          <label>{{ t('uiAutomation.testCase.expectedValue') }}</label>
                          <div class="step-input-tools">
                            <el-input
                              v-model="element.assert_value"
                              :placeholder="t('uiAutomation.testCase.expectedValue')"
                              size="small"
                            >
                              <template #append>
                                <el-button
                                  size="small"
                                  :icon="MagicStick"
                                  @click="openDataFactorySelector(element, 'assert_value')"
                                  :title="t('uiAutomation.testCase.referenceDataFactory')"
                                  class="data-factory-btn"
                                />
                              </template>
                            </el-input>
                            <el-tooltip :content="t('uiAutomation.testCase.insertVariable')" placement="top">
                              <el-button size="small" @click="openVariableHelper(element, 'assert_value')" class="variable-helper-btn">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>

                        <!-- 步骤描述 -->
                        <div class="step-param" :class="{ 'step-param--wide': !needsStepInput(element) }">
                          <label>{{ t('uiAutomation.testCase.stepDescription') }}</label>
                          <el-input
                            v-model="element.description"
                            :placeholder="t('uiAutomation.testCase.stepDescPlaceholder')"
                            size="small"
                          />
                        </div>
                      </div>
                    </div>
                  </template>
                </draggable>
                <el-empty v-if="currentSteps.length === 0" :image-size="88" :description="t('uiAutomation.testCase.stepsEmpty')">
                  <el-button type="primary" plain :disabled="isSaving || executionBusy" @click="addStep()">
                    <el-icon><Plus /></el-icon>
                    {{ t('uiAutomation.testCase.addStep') }}
                  </el-button>
                </el-empty>
                <el-button v-else class="append-step-button" plain :disabled="isSaving || executionBusy" @click="addStep()">
                  <el-icon><Plus /></el-icon>
                  {{ t('uiAutomation.testCase.appendStep') }}
                </el-button>
              </div>
            </div>
          </div>
          </el-tab-pane>

          <el-tab-pane name="data" :label="t('uiAutomation.testCase.dataTab')" class="editor-pane settings-pane">
            <DataDrivenEditor
              :key="selectedTestCase.id"
              ref="dataDrivenEditor"
              :case-id="selectedTestCase.id"
              :project-id="projectId"
              :initial-enabled="selectedTestCase.data_driven_enabled"
              :initial-rows="selectedTestCase.data_rows || []"
              :steps="currentSteps"
              :busy="isSaving || executionBusy"
              @saved="onDataSaved"
            />
          </el-tab-pane>

          <el-tab-pane name="settings" :label="t('uiAutomation.testCase.settingsTab')" class="editor-pane settings-pane">
          <section class="run-settings">
            <div class="section-heading">
              <div>
                <h4>{{ t('uiAutomation.testCase.runSettingsTitle') }}</h4>
                <p>{{ t('uiAutomation.testCase.runSettingsHint') }}</p>
              </div>
              <el-button size="small" plain @click="showFileLibrary = true">{{ t('uiAutomation.testCase.manageTestFiles') }}</el-button>
            </div>
            <div class="detail-toolbar">
              <div class="detail-actions__run-config">
                <label class="run-field">
                  <span>{{ t('uiAutomation.testCase.engineLabel') }}</span>
                  <el-select v-model="selectedEngine" :disabled="isSaving || executionBusy" :placeholder="t('uiAutomation.testCase.selectEngine')" :aria-label="t('uiAutomation.testCase.selectEngine')" size="small" class="engine-select">
                    <el-option label="Playwright" value="playwright" />
                    <el-option label="Selenium" value="selenium" />
                  </el-select>
                </label>
                <label class="run-field">
                  <span>{{ t('uiAutomation.testCase.browserLabel') }}</span>
                  <el-select v-model="selectedBrowser" :disabled="isSaving || executionBusy" :placeholder="t('uiAutomation.testCase.selectBrowser')" :aria-label="t('uiAutomation.testCase.selectBrowser')" size="small" class="browser-select">
                    <el-option label="Chrome" value="chrome" />
                    <el-option label="Firefox" value="firefox" />
                    <el-option label="Safari" value="safari" />
                    <el-option label="Edge" value="edge" />
                  </el-select>
                </label>
                <label class="run-field">
                  <span>{{ t('uiAutomation.testCase.serverRunMode') }}</span>
                  <el-tag type="info">{{ t('uiAutomation.testCase.headlessMode') }}</el-tag>
                </label>
                <label v-if="selectedEngine === 'playwright'" class="run-field">
                  <span>{{ t('uiAutomation.testCase.localRunMode') }}</span>
                  <el-select v-model="localHeadlessMode" :disabled="isSaving || executionBusy" :placeholder="t('uiAutomation.testCase.localRunMode')" :aria-label="t('uiAutomation.testCase.localRunMode')" size="small" class="mode-select">
                    <el-option :label="t('uiAutomation.testCase.headedMode')" :value="false" />
                    <el-option :label="t('uiAutomation.testCase.headlessMode')" :value="true" />
                  </el-select>
                </label>
              </div>
            </div>
          </section>

          <section class="optional-settings">
            <div class="section-heading section-heading--compact">
              <div>
                <h4>{{ t('uiAutomation.testCase.globalWaitTitle') }}</h4>
                <p>{{ t('uiAutomation.testCase.globalWaitDisabledTip') }}</p>
              </div>
              <el-tag size="small" type="info" effect="plain">{{ t('uiAutomation.testCase.optionalLabel') }}</el-tag>
            </div>
            <GlobalStepWait
              :key="selectedTestCase.id"
              ref="globalStepWait"
              :case-id="selectedTestCase.id"
              :initial-enabled="selectedTestCase.global_wait_enabled"
              :initial-time="selectedTestCase.global_wait_time"
              :busy="isSaving || executionBusy"
              :on-persisted="onGlobalWaitSaved"
            />

          </section>
          </el-tab-pane>

          <!-- 执行结果 -->
          <el-tab-pane name="result" :label="t('uiAutomation.testCase.executionResult')" :disabled="!executionResult" class="editor-pane">
          <div v-if="executionResult" class="execution-result">
            <div class="result-header">
              <h4>{{ t('uiAutomation.testCase.executionResult') }}</h4>
              <el-tag :type="executionResult.pending ? 'info' : executionResult.success ? 'success' : 'danger'">
                {{ executionResult.pending ? (executionResult.local ? (executionResult.status === 'pending' ? '等待本机执行器启动' : '本机执行中') : '数据驱动执行中') : executionResult.success ? t('uiAutomation.testCase.executionSuccess') : t('uiAutomation.testCase.executionFailed') }}
              </el-tag>
            </div>
            <p v-if="localProgressMessage" class="result-progress">{{ localProgressMessage }}</p>
            <div class="result-content">
              <el-tabs v-model="resultActiveTab">
                <el-tab-pane v-if="executionResult.data_results?.length" label="数据行结果" name="data">
                  <el-table :data="executionResult.data_results" border>
                    <el-table-column type="expand"><template #default="{ row }"><div class="data-row-details">
                      <p v-for="(log, index) in row.logs" :key="index">步骤 {{ log.step_number }}：{{ log.success ? '通过' : '失败' }} {{ log.description }} {{ log.error }}</p>
                      <p v-for="(error, index) in row.errors" :key="index">{{ error.message }}</p>
                      <img v-for="(shot, index) in row.screenshots" :key="index" :src="shot.url" @click="previewScreenshot(shot)" />
                    </div></template></el-table-column>
                    <el-table-column prop="data_index" label="数据行" width="100" />
                    <el-table-column prop="data_label" label="数据标识" />
                    <el-table-column label="结果"><template #default="{ row }"><el-tag :type="row.success ? 'success' : ['pending', 'running'].includes(row.status) ? 'info' : 'danger'">{{ row.success ? '通过' : row.status === 'pending' ? '待执行' : row.status === 'running' ? '执行中' : '失败' }}</el-tag></template></el-table-column>
                    <el-table-column prop="execution_time" label="耗时（秒）" />
                    <el-table-column label="操作"><template #default="{ row }"><el-button text type="primary" :disabled="isRunning || executionResult.pending" @click="runTestCase(selectedTestCase, row.execution_id)">重跑此行</el-button></template></el-table-column>
                  </el-table>
                </el-tab-pane>
                <el-tab-pane :label="t('uiAutomation.testCase.executionLogs')" name="logs">
                  <div class="logs-container">
                    <div v-if="parsedExecutionLogs.length > 0">
                      <div v-for="(step, index) in parsedExecutionLogs" :key="index" class="log-item">
                        <div class="log-header">
                          <el-tag :type="step.success ? 'success' : 'danger'" size="small">
                            {{ t('uiAutomation.testCase.step') }} {{ step.step_number }}
                          </el-tag>
                          <span class="log-action">{{ getActionText(step.action_type) }}</span>
                          <span class="log-desc">{{ step.description }}</span>
                        </div>
                        <div v-if="step.error" class="log-error">
                          <el-icon><WarningFilled /></el-icon>
                          <pre class="error-message">{{ step.error }}</pre>
                        </div>
                      </div>
                    </div>
                    <el-empty v-else :description="t('uiAutomation.testCase.noLogs')" />
                  </div>
                </el-tab-pane>
                <el-tab-pane :label="t('uiAutomation.testCase.failedScreenshots')" name="screenshots" v-if="executionResult.screenshots?.length || (!executionResult.pending && !executionResult.success)">
                  <div v-if="executionResult.screenshots?.length" class="screenshots-container">
                    <div
                      v-for="(screenshot, index) in executionResult.screenshots"
                      :key="index"
                      class="screenshot-item"
                    >
                      <button
                        type="button"
                        class="screenshot-wrapper"
                        :disabled="!screenshot.url || screenshot.error"
                        :aria-label="t('uiAutomation.testCase.screenshotPreview') + ': ' + (screenshot.description || (index + 1))"
                        @click="previewScreenshot(screenshot)"
                      >
                        <img
                          v-if="screenshot.url"
                          :src="screenshot.url"
                          :alt="`${t('uiAutomation.testCase.screenshot')} ${index + 1}`"
                          @error="handleImageError(screenshot)"
                          @load="handleImageLoad(screenshot)"
                        />
                        <div class="screenshot-placeholder" v-if="!screenshot.loaded">
                          <el-icon><Picture /></el-icon>
                          <span>{{ t('uiAutomation.testCase.loadingImage') }}</span>
                        </div>
                        <div class="screenshot-error" v-if="screenshot.error">
                          <el-icon><Warning /></el-icon>
                          <span>{{ t('uiAutomation.testCase.imageLoadFailed') }}</span>
                        </div>
                        <div v-if="screenshot.url && !screenshot.error" class="screenshot-overlay">
                          <el-icon class="zoom-icon"><ZoomIn /></el-icon>
                        </div>
                      </button>
                      <div class="screenshot-info">
                        <p class="screenshot-description">{{ screenshot.description || t('uiAutomation.testCase.screenshot') + ' ' + (index + 1) }}</p>
                        <p class="screenshot-meta" v-if="screenshot.data_index != null">{{ t('uiAutomation.testCase.screenshotDataRow', { row: screenshot.data_index + 1 }) }}</p>
                        <p class="screenshot-meta" v-if="screenshot.step_number">{{ t('uiAutomation.testCase.step') }} {{ screenshot.step_number }}</p>
                        <p class="screenshot-time" v-if="screenshot.timestamp">{{ formatTime(screenshot.timestamp) }}</p>
                        <el-button v-if="screenshot.error" text type="primary" @click="retryScreenshot(screenshot)">{{ t('uiAutomation.testCase.retryScreenshot') }}</el-button>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else :description="t(executionResult.local && !executionResult.local_artifacts?.some(item => item.type === 'playwright_trace') ? 'uiAutomation.testCase.screenshotNotReceived' : 'uiAutomation.testCase.noFailedScreenshots')" />
                </el-tab-pane>
                <el-tab-pane :label="t('uiAutomation.testCase.errorInfo')" name="errors" v-if="executionResult.errors && executionResult.errors.length > 0">
                  <div class="errors-container">
                    <div
                      v-for="(error, index) in executionResult.errors"
                      :key="index"
                      class="error-item"
                    >
                      <div class="error-header">
                        <span class="error-heading">
                          <el-icon><WarningFilled /></el-icon>
                          {{ t('uiAutomation.testCase.errorInfo') }}
                        </span>
                        <span v-if="error.step_number" class="error-step">
                          {{ t('uiAutomation.testCase.step') }} {{ error.step_number }}
                        </span>
                      </div>
                      <pre class="error-summary">{{ error.message || error }}</pre>

                      <div v-if="error.action_type || error.element || error.description" class="error-meta">
                        <div v-if="error.action_type" class="meta-item">
                          <span class="meta-label">{{ t('uiAutomation.testCase.operationType') }}</span>
                          <span class="meta-value">{{ error.action_type }}</span>
                        </div>
                        <div v-if="error.element" class="meta-item">
                          <span class="meta-label">{{ t('uiAutomation.testCase.targetElement') }}</span>
                          <span class="meta-value">{{ error.element }}</span>
                        </div>
                        <div v-if="error.description" class="meta-item">
                          <span class="meta-label">{{ t('uiAutomation.testCase.stepDesc') }}</span>
                          <span class="meta-value">{{ error.description }}</span>
                        </div>
                      </div>

                      <div v-if="error.details || error.stack" class="error-details">
                        <div class="details-header">{{ t('uiAutomation.testCase.detailErrorInfo') }}</div>
                        <pre class="details-content">{{ error.details || error.stack }}</pre>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </div>
          </el-tab-pane>
          </el-tabs>
        </div>

        <div v-else class="no-selection">
          <el-empty :description="t('uiAutomation.testCase.selectTestCase')" />
        </div>
      </div>
    </div>

    <!-- 新建/编辑测试用例对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTestCase ? t('uiAutomation.testCase.editTestCase') : t('uiAutomation.testCase.createTestCase')"
      :close-on-click-modal="false"
      width="500px"
    >
      <el-form :model="testCaseForm" label-width="100px">
        <el-form-item :label="t('uiAutomation.testCase.caseName')" required>
          <el-input v-model="testCaseForm.name" :placeholder="t('uiAutomation.testCase.caseNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.caseDescription')">
          <el-input
            v-model="testCaseForm.description"
            type="textarea"
            :rows="3"
            :placeholder="t('uiAutomation.testCase.caseDescPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.priority')">
          <el-select v-model="testCaseForm.priority" style="width: 100%">
            <el-option :label="t('uiAutomation.testCase.priorityHigh')" value="high" />
            <el-option :label="t('uiAutomation.testCase.priorityMedium')" value="medium" />
            <el-option :label="t('uiAutomation.testCase.priorityLow')" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.group')">
          <el-select v-model="testCaseForm.group_id" clearable style="width: 100%" :placeholder="t('uiAutomation.testCase.selectGroup')">
            <el-option v-for="group in testCaseGroups" :key="group.id" :label="group.name" :value="group.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">{{ t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" @click="saveTestCaseForm">{{ t('uiAutomation.common.confirm') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showGroupDialog"
      :title="t('uiAutomation.testCase.manageGroups')"
      width="600px"
    >
      <div class="group-dialog-toolbar">
        <el-input
          v-model="newGroupName"
          :placeholder="t('uiAutomation.testCase.groupNamePlaceholder')"
          maxlength="100"
          @keyup.enter="createGroup"
        />
        <el-button type="primary" :loading="savingGroup" @click="createGroup">
          <el-icon><Plus /></el-icon>
          {{ t('uiAutomation.testCase.addGroup') }}
        </el-button>
      </div>
      <el-table :data="testCaseGroups" max-height="380" :empty-text="t('uiAutomation.testCase.noGroups')">
        <el-table-column prop="name" :label="t('uiAutomation.testCase.groupName')" min-width="220" />
        <el-table-column prop="test_case_count" :label="t('uiAutomation.testCase.caseCount')" width="100" />
        <el-table-column :label="t('uiAutomation.testCase.operation')" width="140" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="renameGroup(row)">{{ t('common.edit') }}</el-button>
            <el-button link type="danger" @click="removeGroup(row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog
      v-model="showMoveGroupDialog"
      :title="t('uiAutomation.testCase.moveToGroup')"
      width="440px"
    >
      <el-form label-width="90px">
        <el-form-item :label="t('uiAutomation.testCase.testCase')">
          <span>{{ movingTestCase?.name }}</span>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.targetGroup')">
          <el-select v-model="moveGroupId" style="width: 100%">
            <el-option :label="t('uiAutomation.testCase.ungrouped')" :value="null" />
            <el-option v-for="group in testCaseGroups" :key="group.id" :label="group.name" :value="group.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMoveGroupDialog = false">{{ t('uiAutomation.common.cancel') }}</el-button>
        <el-button type="primary" :loading="movingGroup" @click="moveTestCaseToGroup">
          {{ t('uiAutomation.common.confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 截图预览对话框 -->
    <el-dialog
      v-model="showScreenshotPreview"
      :title="t('uiAutomation.testCase.screenshotPreview')"
      width="80%"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
    >
      <div v-if="currentScreenshot" class="screenshot-preview">
        <div class="preview-info">
          <h4>{{ currentScreenshot.description }}</h4>
          <p v-if="currentScreenshot.step_number">{{ t('uiAutomation.testCase.failedStep') }}: {{ t('uiAutomation.testCase.step') }} {{ currentScreenshot.step_number }}</p>
          <p v-if="currentScreenshot.timestamp">{{ t('uiAutomation.testCase.screenshotTime') }}: {{ formatTime(currentScreenshot.timestamp) }}</p>
        </div>
        <div class="preview-image">
          <img :src="currentScreenshot.url" :alt="currentScreenshot.description" />
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showFileLibrary" title="数据工厂 · 测试文件" width="1100px" @closed="loadTestFileAssets">
      <TestFileLibrary v-if="showFileLibrary" :initial-project="projectId" />
    </el-dialog>
    <!-- 变量助手对话框 -->
    <el-dialog
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      v-model="showVariableHelper"
      :title="t('uiAutomation.testCase.variableHelper')"
      :close-on-click-modal="false"
      width="900px"
    >
      <el-tabs tab-position="left" style="height: 450px">
        <el-tab-pane
          v-for="(category, index) in variableCategoriesComputed"
          :key="index"
          :label="category.label"
        >
          <div style="height: 450px; overflow-y: auto; padding: 10px;">
            <el-table :data="category.variables" style="width: 100%" @row-click="insertVariable" highlight-current-row>
              <el-table-column prop="name" :label="t('uiAutomation.testCase.functionName')" width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag size="small">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="t('uiAutomation.testCase.description')" min-width="150" />
              <el-table-column prop="syntax" :label="t('uiAutomation.testCase.syntax')" min-width="200" show-overflow-tooltip />
              <el-table-column prop="example" :label="t('uiAutomation.testCase.example')" min-width="200" show-overflow-tooltip />
              <el-table-column :label="t('uiAutomation.testCase.operation')" width="80" fixed="right">
                <template #default>
                  <el-button link type="primary" size="small">{{ t('uiAutomation.testCase.insert') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
    
    <DataFactorySelector
      v-model="showDataFactorySelector"
      @select="handleDataFactorySelect"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Edit, Delete, Check, CaretRight, ArrowUp, ArrowDown, Rank, Picture, Warning, ZoomIn, WarningFilled, MagicStick, Monitor,
  CopyDocument, Folder, FolderOpened
} from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import DataDrivenEditor from './DataDrivenEditor.vue'
import TestFileLibrary from '@/views/data-factory/TestFileLibrary.vue'
import GlobalStepWait from './GlobalStepWait.vue'
import { extraActions, extraAssertions, needsStepElement, needsStepInput, needsExpectedValue, stepInputLabel, stepInputHint } from './stepContract'
import { collectExecutionScreenshots, createExecutionScreenshotLoader } from './executionScreenshots'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

import {
  getUiProjects,
  getElementTree,
  getTestCaseGroups,
  createTestCaseGroup,
  updateTestCaseGroup,
  deleteTestCaseGroup,
  createTestCase,
  updateTestCase,
  deleteTestCase as deleteTestCaseApi,
  getTestCases,
  runTestCase as runTestCaseApi,
  runTestCaseLocally as runTestCaseLocallyApi,
  getTestCaseExecution,
  downloadLocalExecutionArtifact,
  copyTestCase as copyTestCaseApi,
  getLocatorStrategies,
  getTestFileAssets,
  uploadTestFileAsset
} from '@/api/ui_automation'
import { getVariableFunctions } from '@/api/data-factory'

// 响应式数据
const projects = ref([])
const projectId = ref('')
const testCases = ref([])
const testCaseGroups = ref([])
const groupFilter = ref('all')
const collapsedGroupKeys = ref(new Set())
const showGroupDialog = ref(false)
const newGroupName = ref('')
const savingGroup = ref(false)
const showMoveGroupDialog = ref(false)
const movingTestCase = ref(null)
const moveGroupId = ref(null)
const movingGroup = ref(false)
const selectedTestCase = ref(null)
const currentSteps = ref([])
const stepsScrollContainer = ref(null)
const highlightedStepId = ref(null)
let stepHighlightTimer
let nextDraftStepId = Date.now()
const availableElements = ref([])
const elementFilterKeyword = ref('')
const searchKeyword = ref('')
const showCreateDialog = ref(false)
const editingTestCase = ref(null)
const executionResult = ref(null)
const resultActiveTab = ref('logs')
const allStepsExpanded = computed(() => currentSteps.value.length > 0 && currentSteps.value.every(step => step.expanded))
const activeEditorTab = ref('steps')
const showScreenshotPreview = ref(false)
const currentScreenshot = ref(null)
const screenshotLoader = createExecutionScreenshotLoader({ downloadArtifact: downloadLocalExecutionArtifact })
const resetExecutionScreenshots = () => {
  screenshotLoader.reset()
  showScreenshotPreview.value = false
  currentScreenshot.value = null
}
const loadScreenshot = async (screenshot, result = executionResult.value, options) => {
  const loaded = await screenshotLoader.load(screenshot, options)
  if (loaded && executionResult.value === result) Object.assign(screenshot, loaded)
}
const setExecutionResult = (data, { reset = false } = {}) => {
  if (reset) resetExecutionScreenshots()
  const previous = reset ? [] : (executionResult.value?.screenshots || [])
  const screenshots = collectExecutionScreenshots(data).map(screenshot => {
    const existing = previous.find(item => (item.data_index ?? null) === (screenshot.data_index ?? null) && (screenshot.artifact_id != null
      ? String(item.artifact_id) === String(screenshot.artifact_id)
      : item.url === screenshot.url))
    return existing ? { ...screenshot, url: existing.url, loaded: existing.loaded, error: existing.error } : screenshot
  })
  executionResult.value = { ...data, screenshots }
  const result = executionResult.value
  result.screenshots.forEach(screenshot => {
    if (screenshot.artifact_id != null && !screenshot.url && !screenshot.error) loadScreenshot(screenshot, result)
  })
}
const isRunning = ref(false)
const isLocalStarting = ref(false)
const isSaving = ref(false)
const executionBusy = computed(() => isRunning.value || isLocalStarting.value || Boolean(executionResult.value?.pending))
const selectedEngine = ref('playwright')  // 默认使用Playwright
const selectedBrowser = ref('chrome')  // 默认使用Chrome
const localHeadlessMode = ref(false)  // 本机执行默认展示浏览器窗口
const showVariableHelper = ref(false)
const currentEditingStep = ref(null)
const currentEditingField = ref('')
const showDataFactorySelector = ref(false)
const currentStepForDataFactory = ref(null)
const currentFieldForDataFactory = ref('')
const variableCategories = ref([])
const loading = ref(false)
const testFileAssets = ref([])
const uploadingFileCount = ref(0)
const uploadingFile = computed(() => uploadingFileCount.value > 0)
const globalStepWait = ref(null)
const dataDrivenEditor = ref(null)
const showFileLibrary = ref(false)
const onDataSaved = data => {
  const fields = { data_driven_enabled: data.data_driven_enabled, data_rows: data.data_rows }
  const index = testCases.value.findIndex(item => item.id === data.id)
  if (index !== -1) Object.assign(testCases.value[index], fields)
  if (selectedTestCase.value?.id === data.id) Object.assign(selectedTestCase.value, fields)
}
// 表单数据
const testCaseForm = reactive({
  name: '',
  description: '',
  priority: 'medium',
  group_id: null
})

// 计算属性
const filteredTestCases = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return testCases.value.filter(tc => {
    const matchesKeyword = !keyword || tc.name.toLowerCase().includes(keyword) || tc.description?.toLowerCase().includes(keyword)
    const matchesGroup = groupFilter.value === 'all'
      || (groupFilter.value === 'ungrouped' ? !tc.group : tc.group?.id === groupFilter.value)
    return matchesKeyword && matchesGroup
  })
})

const groupedTestCases = computed(() => {
  const sections = new Map(testCaseGroups.value.map(group => [group.id, {
    key: `group-${group.id}`,
    name: group.name,
    cases: []
  }]))
  const ungrouped = {
    key: 'ungrouped',
    name: t('uiAutomation.testCase.ungrouped'),
    cases: []
  }

  filteredTestCases.value.forEach(testCase => {
    const section = testCase.group ? sections.get(testCase.group.id) : ungrouped
    const targetSection = section || ungrouped
    targetSection.cases.push(testCase)
  })

  if (groupFilter.value === 'ungrouped') return ungrouped.cases.length ? [ungrouped] : []
  if (groupFilter.value !== 'all') {
    const selected = sections.get(groupFilter.value)
    return selected?.cases.length ? [selected] : []
  }
  return [...sections.values()].filter(section => section.cases.length).concat(
    ungrouped.cases.length ? [ungrouped] : []
  )
})

const isGroupCollapsed = key => collapsedGroupKeys.value.has(key)

const toggleGroup = key => {
  const next = new Set(collapsedGroupKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  collapsedGroupKeys.value = next
}

const onGroupFilterChange = value => {
  if (value === 'all') return
  const key = value === 'ungrouped' ? 'ungrouped' : `group-${value}`
  if (!collapsedGroupKeys.value.has(key)) return
  const next = new Set(collapsedGroupKeys.value)
  next.delete(key)
  collapsedGroupKeys.value = next
}

const getElementSearchText = element => [
  element.page,
  element.group_name,
  element.component_name,
  element.name,
  element.locator_strategy,
  element.locator_value
].filter(Boolean).join(' ').toLowerCase()

const filteredAvailableElements = computed(() => {
  const keyword = elementFilterKeyword.value
  if (!keyword) return availableElements.value
  return availableElements.value.filter(element => getElementSearchText(element).includes(keyword))
})

const groupedAvailableElements = computed(() => {
  const groups = new Map()

  filteredAvailableElements.value.forEach(element => {
    const page = element.page?.trim() || element.group_name?.trim() || '未分类页面'
    if (!groups.has(page)) {
      groups.set(page, [])
    }
    groups.get(page).push(element)
  })

  return Array.from(groups, ([page, elements]) => ({ page, elements }))
})

// 搜索内容和选中后的回显分离，避免把完整 locator 塞进输入框。
const getElementSelectedLabel = element => {
  const page = element.page?.trim() || element.group_name?.trim()
  return page ? `${element.name} · ${page}` : element.name
}

const filterElementOptions = keyword => {
  elementFilterKeyword.value = (keyword || '').trim().toLowerCase()
}

const onElementPickerVisibleChange = visible => {
  if (!visible) {
    elementFilterKeyword.value = ''
  }
}

// 解析执行日志
const parsedExecutionLogs = computed(() => {
  if (!executionResult.value || !executionResult.value.logs) return []
  try {
    return typeof executionResult.value.logs === 'string'
      ? JSON.parse(executionResult.value.logs)
      : executionResult.value.logs
  } catch (e) {
    console.error('解析执行日志失败:', e)
    return []
  }
})

// 方法定义
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  }
}

const loadTestCases = async () => {
  if (!projectId.value) {
    testCases.value = []
    return
  }

  try {
    const response = await getTestCases({ project: projectId.value })
    testCases.value = response.data.results || response.data
  } catch (error) {
    console.error('获取测试用例失败:', error)
  }
}

const loadTestCaseGroups = async () => {
  if (!projectId.value) {
    testCaseGroups.value = []
    return
  }
  try {
    const response = await getTestCaseGroups({ project: projectId.value })
    testCaseGroups.value = response.data.results || response.data
  } catch (error) {
    testCaseGroups.value = []
    console.error('获取测试用例分组失败:', error)
    ElMessage.error(t('uiAutomation.testCase.messages.loadGroupsFailed'))
  }
}

const getApiError = (error, fallback) => {
  const data = error.response?.data
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') {
    const first = Object.values(data)[0]
    if (Array.isArray(first)) return first[0]
    if (first) return String(first)
  }
  return fallback
}

const openCreateDialog = () => {
  editingTestCase.value = null
  resetForm()
  if (groupFilter.value !== 'all' && groupFilter.value !== 'ungrouped') {
    testCaseForm.group_id = groupFilter.value
  }
  showCreateDialog.value = true
}

const openGroupDialog = () => {
  newGroupName.value = ''
  showGroupDialog.value = true
}

const createGroup = async () => {
  const name = newGroupName.value.trim()
  if (!name || savingGroup.value) {
    if (!name) ElMessage.warning(t('uiAutomation.testCase.groupNameRequired'))
    return
  }
  savingGroup.value = true
  try {
    await createTestCaseGroup({ project_id: projectId.value, name })
    newGroupName.value = ''
    await loadTestCaseGroups()
    ElMessage.success(t('uiAutomation.testCase.messages.groupCreated'))
  } catch (error) {
    ElMessage.error(getApiError(error, t('uiAutomation.testCase.messages.groupCreateFailed')))
  } finally {
    savingGroup.value = false
  }
}

const renameGroup = async group => {
  try {
    const { value } = await ElMessageBox.prompt(
      t('uiAutomation.testCase.groupNamePlaceholder'),
      t('uiAutomation.testCase.renameGroup'),
      {
        inputValue: group.name,
        inputPattern: /\S+/,
        inputErrorMessage: t('uiAutomation.testCase.groupNameRequired'),
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel')
      }
    )
    await updateTestCaseGroup(group.id, { name: value.trim() })
    await Promise.all([loadTestCaseGroups(), loadTestCases()])
    ElMessage.success(t('uiAutomation.testCase.messages.groupRenamed'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(getApiError(error, t('uiAutomation.testCase.messages.groupRenameFailed')))
    }
  }
}

const removeGroup = async group => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.testCase.groupDeleteConfirm', { name: group.name, count: group.test_case_count }),
      t('uiAutomation.testCase.delete.title'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )
    await deleteTestCaseGroup(group.id)
    if (groupFilter.value === group.id) groupFilter.value = 'all'
    await Promise.all([loadTestCaseGroups(), loadTestCases()])
    if (selectedTestCase.value?.group?.id === group.id) selectedTestCase.value.group = null
    ElMessage.success(t('uiAutomation.testCase.messages.groupDeleted'))
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(t('uiAutomation.testCase.messages.groupDeleteFailed'))
  }
}

const loadElements = async () => {
  if (!projectId.value) {
    availableElements.value = []
    return
  }

  try {
    // 普通元素列表接口使用全局分页（默认仅返回 20 条）。元素树接口返回
    // 当前项目的完整扁平元素列表，适合步骤编辑器一次性搜索和选择。
    const response = await getElementTree({ project: projectId.value })
    availableElements.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    availableElements.value = []
    console.error('获取元素列表失败:', error)
    ElMessage.error('获取元素列表失败')
  }
}

const loadTestFileAssets = async () => {
  if (!projectId.value) {
    testFileAssets.value = []
    return
  }
  try {
    const response = await getTestFileAssets({ project: projectId.value, page_size: 200 })
    testFileAssets.value = response.data.results || response.data
  } catch (error) {
    testFileAssets.value = []
    console.error('获取测试文件失败:', error)
    ElMessage.error(t('uiAutomation.testCase.messages.loadTestFilesFailed'))
  }
}

const onProjectChange = async () => {
  selectedTestCase.value = null
  currentSteps.value = []
  executionResult.value = null
  groupFilter.value = 'all'
  collapsedGroupKeys.value = new Set()

  await Promise.all([
    loadTestCases(),
    loadTestCaseGroups(),
    loadElements(),
    loadTestFileAssets()
  ])
}

const selectTestCase = async (testCase) => {
  // 如果点击的是同一个用例，不做任何处理
  if (selectedTestCase.value && selectedTestCase.value.id === testCase.id) {
    return
  }

  if (dataDrivenEditor.value?.dirty && !await dataDrivenEditor.value.flush()) return
  selectedTestCase.value = {
    ...testCase,
    global_wait_enabled: Boolean(testCase.global_wait_enabled),
    global_wait_time: testCase.global_wait_time || 1000
  }
  // 确保步骤数据格式正确，添加前端需要的字段
  if (testCase.steps && testCase.steps.length > 0) {
    currentSteps.value = testCase.steps.map(step => ({
      ...step,
      element_id: step.element || '',
      file_asset_ids: step.file_asset_ids?.length
        ? [...step.file_asset_ids]
        : (step.file_asset ? [step.file_asset] : []),
      expanded: false
    }))
  } else {
    currentSteps.value = []
  }
  // 只有在切换到不同用例时才清空执行结果
  executionResult.value = null
  activeEditorTab.value = 'steps'
  highlightedStepId.value = null
  await nextTick()
  stepsScrollContainer.value?.scrollTo({ top: 0 })
}

const addStep = async (insertIndex = currentSteps.value.length) => {
  if (!selectedTestCase.value || isSaving.value || executionBusy.value) return

  activeEditorTab.value = 'steps'

  const newStep = {
    id: ++nextDraftStepId,
    action_type: 'click',
    element_id: '',
    input_value: '',
    wait_time: 1000,
    assert_type: 'textContains',
    assert_value: '',
    file_asset_ids: [],
    description: '',
    expanded: true
  }
  currentSteps.value.splice(insertIndex, 0, newStep)
  highlightedStepId.value = newStep.id
  clearTimeout(stepHighlightTimer)
  stepHighlightTimer = setTimeout(() => { highlightedStepId.value = null }, 2500)

  await nextTick()
  const container = stepsScrollContainer.value
  const card = container?.querySelector(`[data-step-id="${newStep.id}"]`)
  if (!card) return
  // Reveal the start of the new card, not the bottom of the list. Focus must
  // stay inside the steps viewport so the page header never jumps away.
  container.scrollTo({ top: container.scrollTop + card.getBoundingClientRect().top - container.getBoundingClientRect().top - 16 })
  card.querySelector('.step-field--action [role="combobox"]')?.focus({ preventScroll: true })
}

onUnmounted(() => clearTimeout(stepHighlightTimer))

const removeStep = (index) => {
  currentSteps.value.splice(index, 1)
}

const onStepsReorder = () => {
  // 步骤重新排序后的处理
  console.log('步骤已重新排序')
}

const onActionTypeChange = (step) => {
  // 根据操作类型重置相关参数
  if (step.action_type !== 'fill') {
    step.input_value = ''
  }
  if (step.action_type !== 'wait') {
    step.wait_time = 1000
  }
  if (step.action_type === 'assert') step.wait_time = 5000
  if (step.action_type === 'uploadFile') {
    step.wait_time = 30000
  }
  if (step.action_type === 'waitForEnabled') {
    step.wait_time = 180000
  }
  if (step.action_type !== 'assert') {
    step.assert_type = 'textContains'
    step.assert_value = ''
  }
  if (step.action_type !== 'uploadFile') {
    step.file_asset_ids = []
  }
}

const uploadStepFile = async (step, options) => {
  const formData = new FormData()
  formData.append('project', projectId.value)
  formData.append('file', options.file)
  uploadingFileCount.value += 1
  try {
    const response = await uploadTestFileAsset(formData)
    testFileAssets.value.unshift(response.data)
    if (!step.file_asset_ids.includes(response.data.id)) {
      step.file_asset_ids.push(response.data.id)
    }
    options.onSuccess?.(response.data)
    ElMessage.success(t('uiAutomation.testCase.messages.testFileUploaded'))
  } catch (error) {
    options.onError?.(error)
    console.error('上传测试文件失败:', error)
    ElMessage.error(error.response?.data?.file?.[0] || t('uiAutomation.testCase.messages.testFileUploadFailed'))
  } finally {
    uploadingFileCount.value = Math.max(0, uploadingFileCount.value - 1)
  }
}

const formatFileSize = size => {
  const bytes = Number(size || 0)
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const onElementChange = (step) => {
  // 元素变化时的处理
  const element = availableElements.value.find(e => e.id === step.element_id)
  if (element && !step.description) {
    step.description = `${getActionTypeText(step.action_type)}${element.name}`
  }
}

const needsWaitTime = (actionType) => {
  return ['wait', 'waitFor', 'waitForEnabled', 'uploadFile', 'assert'].includes(actionType)
}

const expandAllSteps = () => {
  const expanded = !allStepsExpanded.value
  currentSteps.value.forEach(step => {
    step.expanded = expanded
  })
}

const onGlobalWaitSaved = ({ caseId, ...settings }) => {
  const index = testCases.value.findIndex(tc => tc.id === caseId)
  if (index !== -1) {
    testCases.value[index] = { ...testCases.value[index], ...settings }
  }
  if (selectedTestCase.value?.id === caseId) {
    Object.assign(selectedTestCase.value, settings)
  }
}

const flushGlobalWait = async () => {
  if (globalStepWait.value && !await globalStepWait.value.flush()) {
    ElMessage.error(t('uiAutomation.testCase.messages.globalWaitSaveFailed'))
    return false
  }
  return true
}

const saveTestCase = async ({ notify = true } = {}) => {
  if (!selectedTestCase.value || isSaving.value || executionBusy.value) return false
  const caseId = selectedTestCase.value.id
  isSaving.value = true
  try {
    if (!await flushGlobalWait() || selectedTestCase.value?.id !== caseId) return false
    if (dataDrivenEditor.value && !await dataDrivenEditor.value.flush()) {
      activeEditorTab.value = 'data'
      return false
    }
    if (selectedTestCase.value?.id !== caseId) return false

    const invalidUploadIndex = currentSteps.value.findIndex(step => (
      step.action_type === 'uploadFile' && (!step.element_id || !step.file_asset_ids?.length)
    ))
    if (invalidUploadIndex !== -1) {
      ElMessage.warning(t('uiAutomation.testCase.messages.uploadStepIncomplete', {
        step: invalidUploadIndex + 1
      }))
      activeEditorTab.value = 'steps'
      return false
    }

    const updateData = {
      ...selectedTestCase.value,
      steps: currentSteps.value
    }

    // The wait toolbar saves independently; a step save must not overwrite its settings.
    const stepUpdateData = { ...updateData }
    delete stepUpdateData.global_wait_enabled
    delete stepUpdateData.global_wait_time
    delete stepUpdateData.data_driven_enabled
    delete stepUpdateData.data_rows
    const response = await updateTestCase(caseId, stepUpdateData)
    const updatedCase = { ...response.data }
    delete updatedCase.global_wait_enabled
    delete updatedCase.global_wait_time
    if (notify) ElMessage.success(t('uiAutomation.testCase.save.success'))

    // 更新本地数据
    const index = testCases.value.findIndex(tc => tc.id === caseId)
    if (index !== -1) {
      testCases.value[index] = { ...testCases.value[index], ...updatedCase }
      if (selectedTestCase.value?.id === caseId) {
        selectedTestCase.value = { ...selectedTestCase.value, ...updatedCase }
      }
    }
    return true
  } catch (error) {
    console.error('保存测试用例失败:', error)
    ElMessage.error(t('uiAutomation.testCase.save.failed'))
    return false
  } finally {
    isSaving.value = false
  }
}

const saveAndRun = async (local = false) => {
  if (!selectedTestCase.value || executionBusy.value || isSaving.value) return
  const caseId = selectedTestCase.value.id
  if (!await saveTestCase({ notify: false }) || selectedTestCase.value?.id !== caseId) return
  if (local) await runTestCaseLocally(selectedTestCase.value)
  else await runTestCase(selectedTestCase.value)
}

const runTestCase = async (testCase, retryExecutionId = null) => {
  if (executionResult.value?.pending) return
  if (!await flushGlobalWait()) return
  if (selectedTestCase.value?.id === testCase.id && dataDrivenEditor.value && !await dataDrivenEditor.value.flush()) return
  stopLocalPolling()
  isRunning.value = true
  try {
    const modeText = t('uiAutomation.testCase.runMode.headless')
    ElMessage.info(t('uiAutomation.testCase.run.start', { engine: selectedEngine.value.toUpperCase(), browser: selectedBrowser.value.toUpperCase(), mode: modeText }))

    const response = await runTestCaseApi(testCase.id, {
      project_id: projectId.value,
      engine: selectedEngine.value,
      browser: selectedBrowser.value,
      headless: true,
      ...(retryExecutionId ? { retry_execution_id: retryExecutionId } : {})
    })

    if (response.data.pending) {
      watchLocalExecution(response.data.execution_id, false)
      ElMessage.success('数据驱动执行已开始，结果将自动刷新')
      return
    }
    setExecutionResult(response.data, { reset: true })
    resultActiveTab.value = response.data.data_results?.length ? 'data' : 'logs'
    activeEditorTab.value = 'result'

    if (response.data.success) {
      ElMessage.success(t('uiAutomation.testCase.run.success'))
    } else {
      ElMessage.error(t('uiAutomation.testCase.run.failed'))
      // 如果有截图，自动切换到截图标签页
      if (executionResult.value.screenshots.length > 0) {
        resultActiveTab.value = 'screenshots'
      }
    }
  } catch (error) {
    console.error('执行测试用例失败:', error)

    // 即使出错也要设置执行结果,显示错误信息
    const errorMessage = error.response?.data?.message || error.message || '执行失败'
    const errorLogs = error.response?.data?.logs || `测试用例执行出错\n\n错误信息: ${errorMessage}`

    // 格式化错误信息为统一的对象格式
    const errors = error.response?.data?.errors || [{
      message: errorMessage,
      details: error.stack || '',
      step_number: null,
      action_type: '',
      element: '',
      description: ''
    }]

    setExecutionResult({
      success: false,
      logs: errorLogs,
      screenshots: error.response?.data?.screenshots || [],
      local_artifacts: error.response?.data?.local_artifacts || [],
      execution_time: 0,
      errors: errors
    }, { reset: true })
    resultActiveTab.value = 'logs'
    activeEditorTab.value = 'result'

    ElMessage.error(t('uiAutomation.testCase.run.failedWithMessage', { message: errorMessage }))
  } finally {
    isRunning.value = false
  }
}

const runTestCaseLocally = async (testCase) => {
  if (!testCase || isLocalStarting.value) return
  if (executionResult.value?.pending) return
  if (!await flushGlobalWait()) return
  if (selectedTestCase.value?.id === testCase.id && dataDrivenEditor.value && !await dataDrivenEditor.value.flush()) return
  isLocalStarting.value = true
  try {
    const response = await runTestCaseLocallyApi(testCase.id, {
      browser: selectedBrowser.value,
      headless: localHeadlessMode.value,
      runner_origin: window.location.origin
    })
    watchLocalExecution(response.data.execution_id)
    window.location.href = response.data.protocol_url
    ElMessage.success(t('uiAutomation.testCase.localLaunchRequested'))
  } catch (error) {
    console.error('创建本机执行任务失败:', error)
    ElMessage.error(error.response?.data?.detail || t('uiAutomation.testCase.localLaunchFailed'))
  } finally {
    isLocalStarting.value = false
  }
}

const localProgressMessage = ref('')
let localPollTimer
let localPollGeneration = 0
const stopLocalPolling = () => {
  localPollGeneration += 1
  clearTimeout(localPollTimer)
  localProgressMessage.value = ''
}
onUnmounted(stopLocalPolling)
watch(() => selectedTestCase.value?.id, stopLocalPolling)
onUnmounted(resetExecutionScreenshots)
watch(() => selectedTestCase.value?.id, resetExecutionScreenshots)

const watchLocalExecution = (executionId, local = true) => {
  stopLocalPolling()
  resetExecutionScreenshots()
  const generation = localPollGeneration
  const started = Date.now()
  let finishedAt = null
  let failures = 0
  executionResult.value = { local, pending: true, status: 'pending', logs: [], local_artifacts: [] }
  activeEditorTab.value = 'result'
  resultActiveTab.value = 'logs'
  const poll = async () => {
    try {
      const { data } = await getTestCaseExecution(executionId)
      if (generation !== localPollGeneration) return
      failures = 0
      let logs = data.execution_logs || []
      if (typeof logs === 'string') {
        try { logs = JSON.parse(logs) } catch { logs = [] }
      }
      const pending = ['pending', 'running'].includes(data.status)
      const firstDataResults = data.data_results?.length && !executionResult.value?.data_results?.length
      setExecutionResult({
        local, pending, status: data.status, success: data.status === 'passed',
        logs: Array.isArray(logs) ? logs.filter(log => log.step_number != null) : [],
        local_artifacts: data.local_artifacts || [],
        screenshots: data.screenshots || [],
        errors: data.errors?.length ? data.errors : (data.error_message ? [{ message: data.error_message }] : []),
        execution_time: data.execution_time,
        data_results: data.data_results || []
      })
      if (firstDataResults) resultActiveTab.value = 'data'
      if (!pending && !local) { localProgressMessage.value = '所有数据行执行结束'; return }
      if (!pending) {
        finishedAt ||= Date.now()
        const hasTrace = data.local_artifacts?.some(item => item.type === 'playwright_trace')
        localProgressMessage.value = hasTrace ? '执行结果和 Trace 已回传' : '执行已结束，等待 Trace 上传；无需等待即可查看结果。'
        if (hasTrace) return
        if (Date.now() - finishedAt > 330000) {
          localProgressMessage.value = '执行已结束，Trace 暂未收到，请检查本机执行器日志。'
          return
        }
      } else if (local && data.status === 'pending' && Date.now() - started > 130000) {
        localProgressMessage.value = '尚未收到执行器响应，请检查安装和服务地址，再重新执行。'
        return
      } else {
        localProgressMessage.value = '步骤结果每秒自动刷新'
      }
    } catch {
      if (generation !== localPollGeneration) return
      failures += 1
      localProgressMessage.value = '暂时无法获取进度，正在重试；本机任务可能仍在执行。'
      if (failures >= 10) {
        localProgressMessage.value = '进度连接中断，请稍后到执行记录查看结果。'
        return
      }
    }
    if (generation === localPollGeneration) localPollTimer = setTimeout(poll, finishedAt ? 2000 : 1000)
  }
  poll()
}


const editTestCase = (testCase) => {
  editingTestCase.value = testCase
  testCaseForm.name = testCase.name
  testCaseForm.description = testCase.description || ''
  testCaseForm.priority = testCase.priority || 'medium'
  testCaseForm.group_id = testCase.group?.id || null
  showCreateDialog.value = true
}

const openMoveGroupDialog = testCase => {
  movingTestCase.value = testCase
  moveGroupId.value = testCase.group?.id || null
  showMoveGroupDialog.value = true
}

const moveTestCaseToGroup = async () => {
  if (!movingTestCase.value || movingGroup.value) return
  movingGroup.value = true
  try {
    const response = await updateTestCase(movingTestCase.value.id, {
      group_id: moveGroupId.value
    })
    const updatedCase = response.data
    const index = testCases.value.findIndex(testCase => testCase.id === updatedCase.id)
    if (index !== -1) testCases.value[index] = updatedCase
    if (selectedTestCase.value?.id === updatedCase.id) {
      selectedTestCase.value = { ...selectedTestCase.value, ...updatedCase }
    }
    showMoveGroupDialog.value = false
    movingTestCase.value = null
    await loadTestCaseGroups()
    ElMessage.success(t('uiAutomation.testCase.messages.moveGroupSuccess'))
  } catch (error) {
    ElMessage.error(getApiError(error, t('uiAutomation.testCase.messages.moveGroupFailed')))
  } finally {
    movingGroup.value = false
  }
}

const deleteTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.testCase.delete.confirm', { name: testCase.name }),
      t('uiAutomation.testCase.delete.title'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )

    await deleteTestCaseApi(testCase.id)
    ElMessage.success(t('uiAutomation.testCase.delete.success'))

    // 从列表中移除
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      testCases.value.splice(index, 1)
    }

    // 如果删除的是当前选中的用例，清空选择
    if (selectedTestCase.value?.id === testCase.id) {
      selectedTestCase.value = null
      currentSteps.value = []
      executionResult.value = null
    }
    await loadTestCaseGroups()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除测试用例失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const copyTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.testCase.copy.confirm', { name: testCase.name }),
      t('uiAutomation.testCase.copy.title'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'info'
      }
    )

    const response = await copyTestCaseApi(testCase.id)
    ElMessage.success(t('uiAutomation.testCase.copy.success'))

    // 找到原用例的位置
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      // 在原用例下方插入新用例
      testCases.value.splice(index + 1, 0, response.data)
    } else {
      // 如果找不到，就添加到末尾
      testCases.value.push(response.data)
    }
    await loadTestCaseGroups()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('复制测试用例失败:', error)
      ElMessage.error('复制失败')
    }
  }
}

// 加载变量函数
const loadVariableFunctions = async () => {
  try {
    loading.value = true
    console.log('开始加载变量函数...')
    const apiResponse = await getVariableFunctions()
    console.log('变量函数响应:', apiResponse)
    console.log('变量函数响应.data:', apiResponse.data)
    
    // 检查不同可能的数据结构
    let functionsData = []
    if (apiResponse && apiResponse.data) {
      if (Array.isArray(apiResponse.data)) {
        // 后端返回的是数组，直接使用
        functionsData = apiResponse.data
      } else if (apiResponse.data.functions) {
        // 如果data中有functions字段，使用它
        functionsData = apiResponse.data.functions
      } else if (typeof apiResponse.data === 'object') {
        // 如果data是对象但没有functions字段，假设整个对象就是按分类组织的函数
        functionsData = apiResponse.data
      }
    }
    
    console.log('处理后的函数数据:', functionsData)
    
    // 处理函数数据，按分类组织
    const grouped = {}
    
    if (Array.isArray(functionsData)) {
      // 如果是数组格式
      functionsData.forEach(func => {
        const category = func.category || '未分类'
        if (!grouped[category]) {
          grouped[category] = []
        }
        grouped[category].push({
          name: func.name,
          syntax: func.syntax,
          desc: func.description || func.desc || '',
          example: func.example
        })
      })
    } else if (typeof functionsData === 'object') {
      // 如果是按分类组织的对象格式
      for (const [category, funcs] of Object.entries(functionsData)) {
        if (Array.isArray(funcs)) {
          grouped[category] = funcs.map(func => ({
            name: func.name,
            syntax: func.syntax,
            desc: func.description || func.desc || '',
            example: func.example
          }))
        }
      }
    }
    
    console.log('按分类组织后的函数:', grouped)
    
    // 定义固定的分类顺序
    const categoryOrder = ['随机数', '测试数据', '字符串', '编码转换', '加密', '时间日期', 'Crontab', '未分类']
    
    // 按固定顺序构建分类列表
    const orderedCategories = []
    categoryOrder.forEach(category => {
      if (grouped[category]) {
        orderedCategories.push({
          label: category,
          variables: grouped[category]
        })
        delete grouped[category]
      }
    })
    
    // 添加剩余的分类
    for (const [category, funcs] of Object.entries(grouped)) {
      orderedCategories.push({
        label: category,
        variables: funcs
      })
    }
    
    console.log('最终的分类列表:', orderedCategories)
    variableCategories.value = orderedCategories
  } catch (error) {
    console.error('加载变量函数失败:', error)
    ElMessage.error('加载变量函数失败，使用本地数据')
    useLocalVariableCategories()
  } finally {
    loading.value = false
  }
}

// 使用本地变量分类数据作为 fallback
const useLocalVariableCategories = () => {
  variableCategories.value = [
    {
      label: t('uiAutomation.testCase.variableCategory.randomNumber'),
      variables: [
        { name: 'random_int', syntax: '${random_int(min, max, count)}', desc: t('uiAutomation.testCase.variable.randomInt.desc'), example: '${random_int(100, 999, 1)}' },
        { name: 'random_float', syntax: '${random_float(min, max, precision, count)}', desc: t('uiAutomation.testCase.variable.randomFloat.desc'), example: '${random_float(0, 1, 2, 1)}' }
      ]
    },
    {
      label: t('uiAutomation.testCase.variableCategory.randomString'),
      variables: [
        { name: 'random_string', syntax: '${random_string(length, char_type, count)}', desc: t('uiAutomation.testCase.variable.randomString.desc'), example: '${random_string(8, "all", 1)}' }
      ]
    }
  ]
}

// 计算属性提供变量分类数据
const variableCategoriesComputed = computed(() => {
  const categories = variableCategories.value.length > 0 ? variableCategories.value : [
    {
      label: t('uiAutomation.testCase.variableCategory.randomNumber'),
      variables: []
    }
  ]
  const columns = Object.keys(selectedTestCase.value?.data_rows?.[0] || {})
  if (!columns.length) return categories
  return [{
    label: '数据驱动',
    variables: columns.map(name => ({
      name,
      syntax: `\${${name}}`,
      example: `\${${name}}`,
      desc: `使用当前数据行的 ${name} 列`,
      replaceCurrent: true,
    })),
  }, ...categories]
})

const openVariableHelper = (step, field) => {
  console.log('TestCaseManager openVariableHelper 被调用, step:', step, 'field:', field)
  console.log('variableCategories.value:', variableCategories.value)
  console.log('variableCategories.value.length:', variableCategories.value.length)
  currentEditingStep.value = step
  currentEditingField.value = field
  showVariableHelper.value = true
  console.log('showVariableHelper.value:', showVariableHelper.value)
}

const openDataFactorySelector = (step, field) => {
  currentStepForDataFactory.value = step
  currentFieldForDataFactory.value = field
  showDataFactorySelector.value = true
}

const handleDataFactorySelect = (record) => {
  const step = currentStepForDataFactory.value
  const field = currentFieldForDataFactory.value
  
  if (record && record.output_data && step && field) {
    let valueToSet = ''
    
    if (typeof record.output_data === 'string') {
      valueToSet = record.output_data
    } else if (record.output_data.result) {
      valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
      valueToSet = record.output_data.output_data
    } else {
      valueToSet = JSON.stringify(record.output_data)
    }
    
    step[field] = valueToSet
    ElMessage.success(t('uiAutomation.testCase.messages.dataFactorySelected', { toolName: record.tool_name }))
  }
  
  showDataFactorySelector.value = false
}

const insertVariable = (variable) => {
  if (currentEditingStep.value && currentEditingField.value) {
    const example = variable.example
    const currentValue = currentEditingStep.value[currentEditingField.value] || ''
    
    // 简单起见，这里直接追加到末尾，或者如果为空则替换
    if (variable.replaceCurrent) {
      currentEditingStep.value[currentEditingField.value] = example
    } else if (!currentValue) {
      currentEditingStep.value[currentEditingField.value] = example
    } else {
      currentEditingStep.value[currentEditingField.value] = currentValue + example
    }
    
    ElMessage.success(t('uiAutomation.testCase.messages.variableInserted', { name: variable.name }))
    showVariableHelper.value = false
  }
}

const saveTestCaseForm = async () => {
  if (!testCaseForm.name.trim()) {
    ElMessage.warning(t('uiAutomation.testCase.form.nameRequired'))
    return
  }

  try {
    const data = {
      name: testCaseForm.name,
      description: testCaseForm.description,
      priority: testCaseForm.priority,
      group_id: testCaseForm.group_id,
      project: projectId.value,
      steps: []
    }

    if (editingTestCase.value) {
      // 编辑现有用例
      const response = await updateTestCase(editingTestCase.value.id, data)
      ElMessage.success(t('uiAutomation.testCase.update.success'))

      // 更新本地数据
      const index = testCases.value.findIndex(tc => tc.id === editingTestCase.value.id)
      if (index !== -1) {
        testCases.value[index] = response.data
        if (selectedTestCase.value?.id === response.data.id) {
          selectedTestCase.value = { ...selectedTestCase.value, ...response.data }
        }
      }
    } else {
      // 创建新用例
      const response = await createTestCase(data)
      ElMessage.success(t('uiAutomation.testCase.create.success'))
      testCases.value.push(response.data)
    }

    await loadTestCaseGroups()

    showCreateDialog.value = false
    editingTestCase.value = null
    resetForm()
  } catch (error) {
    console.error('保存测试用例失败:', error)
    ElMessage.error(t('uiAutomation.testCase.save.failed'))
  }
}

const resetForm = () => {
  testCaseForm.name = ''
  testCaseForm.description = ''
  testCaseForm.priority = 'medium'
  testCaseForm.group_id = null
}

// 辅助方法
const getStatusTag = (status) => {
  const tagMap = {
    'draft': 'info',
    'ready': 'success',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger'
  }
  return tagMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'draft': t('uiAutomation.testCase.status.draft'),
    'ready': t('uiAutomation.testCase.status.ready'),
    'running': t('uiAutomation.testCase.status.running'),
    'passed': t('uiAutomation.testCase.status.passed'),
    'failed': t('uiAutomation.testCase.status.failed')
  }
  return textMap[status] || t('uiAutomation.testCase.status.unknown')
}

const getActionTypeText = (actionType) => {
  if (extraActions.includes(actionType)) return t(`uiAutomation.testCase.extendedActions.${actionType}`)
  const textMap = {
    'click': t('uiAutomation.testCase.actionType.click'),
    'fill': t('uiAutomation.testCase.actionType.fill'),
    'getText': t('uiAutomation.testCase.actionType.getText'),
    'waitFor': t('uiAutomation.testCase.actionType.waitFor'),
    'waitForEnabled': t('uiAutomation.testCase.actionType.waitForEnabled'),
    'hover': t('uiAutomation.testCase.actionType.hover'),
    'scroll': t('uiAutomation.testCase.actionType.scroll'),
    'screenshot': t('uiAutomation.testCase.actionType.screenshot'),
    'assert': t('uiAutomation.testCase.actionType.assert'),
    'wait': t('uiAutomation.testCase.actionType.wait'),
    'uploadFile': t('uiAutomation.testCase.actionType.uploadFile')
  }
  return textMap[actionType] || actionType
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// 获取操作类型文本
const getActionText = (actionType) => {
  if (extraActions.includes(actionType)) return t(`uiAutomation.testCase.extendedActions.${actionType}`)
  const actionMap = {
    'click': t('uiAutomation.testCase.actionText.click'),
    'fill': t('uiAutomation.testCase.actionText.fill'),
    'getText': t('uiAutomation.testCase.actionText.getText'),
    'waitFor': t('uiAutomation.testCase.actionText.waitFor'),
    'waitForEnabled': t('uiAutomation.testCase.actionText.waitForEnabled'),
    'hover': t('uiAutomation.testCase.actionText.hover'),
    'scroll': t('uiAutomation.testCase.actionText.scroll'),
    'screenshot': t('uiAutomation.testCase.actionText.screenshot'),
    'assert': t('uiAutomation.testCase.actionText.assert'),
    'wait': t('uiAutomation.testCase.actionText.wait'),
    'uploadFile': t('uiAutomation.testCase.actionText.uploadFile')
  }
  return actionMap[actionType] || actionType
}

// 图片处理方法
const handleImageError = (screenshot) => {
  screenshot.error = true
  screenshot.loaded = true
}

const handleImageLoad = (screenshot) => {
  screenshot.loaded = true
  screenshot.error = false
}

const retryScreenshot = async (screenshot) => {
  const result = executionResult.value
  const url = screenshot.url
  screenshot.error = false
  screenshot.loaded = false
  screenshot.url = null
  await nextTick()
  if (executionResult.value !== result) return
  if (screenshot.artifact_id != null) {
    await loadScreenshot(screenshot, result, { refresh: true })
  } else {
    screenshot.url = url
  }
}

const previewScreenshot = (screenshot) => {
  if (!screenshot.url || screenshot.error) return
  currentScreenshot.value = screenshot
  showScreenshotPreview.value = true
}

// 组件挂载
onMounted(async () => {
  console.log('TestCaseManager onMounted 开始执行...')
  await loadProjects()
  console.log('loadProjects 完成，准备加载变量函数...')
  await loadVariableFunctions()
  console.log('loadVariableFunctions 完成')

  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    await onProjectChange()
  }
})
</script>

<style scoped>
.test-case-manager {
  height: calc(100dvh - 108px);
  min-height: 560px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: var(--th-text);
}

.page-header {
  display: flex;
  flex: 0 0 auto;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.project-select { width: 220px; }

.main-content {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
}

.left-panel,
.right-panel {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--th-border);
  border-radius: var(--th-radius-lg);
  background: var(--th-surface);
  box-shadow: var(--th-shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel { container-type: inline-size; }

.panel-header {
  padding: 18px 16px 16px;
  border-bottom: 1px solid var(--th-border);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title h3,
.panel-title h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}

.case-list-title :deep(.el-button) {
  margin-left: auto;
  padding: 4px;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  padding: 1px 7px;
  border-radius: 6px;
  color: var(--th-primary);
  background: var(--th-primary-soft);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.case-search { width: 100%; }
.group-filter { width: 100%; }

.case-group-section + .case-group-section { margin-top: 12px; }

.case-group-heading {
  position: sticky;
  top: -10px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 8px 7px;
  color: var(--th-text-secondary);
  background: var(--th-surface);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  border-radius: 8px;
  transition: color var(--th-transition), background-color var(--th-transition);
}

.case-group-heading:hover,
.case-group-heading:focus-visible {
  color: var(--th-primary);
  background: var(--th-surface-subtle);
  outline: none;
}

.case-group-heading__name {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 5px;
}

.case-group-count {
  min-width: 20px;
  padding: 1px 6px;
  border-radius: 999px;
  text-align: center;
  background: var(--th-surface-subtle);
  font-variant-numeric: tabular-nums;
}

.test-case-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: var(--th-border-strong) transparent;
}

.test-case-item {
  border: 1px solid transparent;
  border-radius: 10px;
  margin-bottom: 8px;
  padding: 14px;
  cursor: pointer;
  transition: border-color var(--th-transition), background-color var(--th-transition);
}

.test-case-item:hover {
  border-color: var(--th-border);
  background: var(--th-surface-subtle);
}

.test-case-item.active {
  border-color: var(--el-color-primary-light-7);
  background: var(--th-primary-soft);
}

.case-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 8px;
}

.case-info { min-width: 0; }

.case-name {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.case-description {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  margin: 0;
  color: var(--th-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.case-actions {
  display: flex;
  gap: 4px;
}

.case-actions :deep(.el-button) {
  margin: 0;
  min-height: 28px;
  padding: 6px 8px;
}

.case-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 8px;
  color: var(--th-text-secondary);
  font-size: 11px;
}

.detail-group-tag { width: fit-content; }

.group-dialog-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.group-dialog-toolbar :deep(.el-input) { flex: 1; }

.step-count {
  color: var(--th-primary);
  font-weight: 500;
}

.test-case-detail {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 22px;
  overflow: hidden;
}

.detail-header {
  display: flex;
  flex: 0 0 auto;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.detail-title {
  flex: 1;
  min-width: 0;
}

.detail-title h3 {
  margin: 2px 0 0;
  font-size: 18px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.detail-title__eyebrow {
  color: var(--th-primary);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.detail-title p {
  margin: 6px 0 0;
  color: var(--th-text-secondary);
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.detail-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.case-editor-tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.case-editor-tabs > :deep(.el-tabs__header) { flex: none; margin: 0 0 14px; }
.case-editor-tabs > :deep(.el-tabs__content) { flex: 1; min-height: 0; }
.editor-pane { height: 100%; min-height: 0; }
.settings-pane { overflow-y: auto; scrollbar-gutter: stable; }

.run-settings,
.optional-settings {
  flex: 0 0 auto;
  margin-bottom: 14px;
  overflow: hidden;
  border: 1px solid var(--th-border);
  border-radius: 10px;
  background: var(--th-surface);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--th-border);
  background: var(--th-surface-subtle);
}

.section-heading h4 { margin: 0; color: var(--th-text); font-size: 13px; }
.section-heading p { margin: 3px 0 0; color: var(--th-text-secondary); font-size: 11px; line-height: 1.5; }
.section-heading--compact { padding-block: 11px; }

.detail-toolbar {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
}

.detail-actions__run-config {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
}

.run-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: var(--th-text-secondary);
  font-size: 11px;
}

.detail-actions :deep(.el-button + .el-button),
.detail-toolbar :deep(.el-button + .el-button),
.steps-header__actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.engine-select { width: 130px; }
.browser-select { width: 115px; }
.mode-select { width: 110px; }

.optional-settings { padding-bottom: 14px; background: var(--th-surface-subtle); }
.optional-settings :deep(.global-step-wait) { margin: 14px 14px 10px; background: #fff; }
.optional-settings :deep(.data-driven-editor) { margin: 0 14px; background: #fff; }

.steps-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--th-border);
  border-radius: var(--th-radius);
  background: var(--th-surface-subtle);
  overflow: hidden;
}

.steps-header {
  display: flex;
  flex: 0 0 auto;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--th-border);
  background: var(--th-surface);
}

.steps-header__actions { display: flex; align-items: center; flex-shrink: 0; gap: 8px; }
.append-step-button { width: 100%; margin-top: 12px; border-style: dashed; }
.step-item.is-new { border-color: var(--th-primary); box-shadow: 0 0 0 2px var(--th-primary-soft); }

.steps-heading p {
  margin: 4px 0 0;
  color: var(--th-text-secondary);
  font-size: 12px;
}

.steps-list { padding: 16px; }

.steps-scroll-container {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: var(--th-border-strong) transparent;
}

.steps-scroll-container::-webkit-scrollbar { width: 6px; }
.steps-scroll-container::-webkit-scrollbar-thumb {
  background: var(--th-border-strong);
  border-radius: 6px;
}

.step-item {
  border: 1px solid var(--th-border);
  border-radius: 10px;
  margin-bottom: 12px;
  background: var(--th-surface);
  transition: border-color var(--th-transition), box-shadow var(--th-transition);
}

.step-item:last-child { margin-bottom: 0; }

.step-item:hover,
.step-item:focus-within {
  border-color: var(--el-color-primary-light-5);
}

.step-item.expanded {
  box-shadow: var(--th-shadow-sm);
}

.step-item--ghost {
  opacity: 0.45;
  border-color: var(--th-primary);
  background: var(--th-primary-soft);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.step-left {
  display: grid;
  grid-template-columns: 52px 160px minmax(0, 1fr);
  flex: 1;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.step-index {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drag-handle {
  flex: none;
  cursor: grab;
  color: var(--th-text-muted);
  font-size: 16px;
}

.drag-handle:active { cursor: grabbing; }
.drag-handle:hover { color: var(--th-primary); }

.step-number {
  flex: none;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--th-primary);
  background: var(--th-primary-soft);
  font-size: 12px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.step-field { min-width: 0; }
.step-field__label {
  display: block;
  margin-bottom: 5px;
  color: var(--th-text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.step-field :deep(.el-select) { width: 100%; }

.step-right {
  display: flex;
  flex: none;
  align-items: center;
  gap: 4px;
  padding-top: 20px;
}

.step-right :deep(.el-button) {
  margin: 0;
  min-height: 30px;
  padding: 6px 8px;
}

.step-summary {
  margin: -2px 16px 14px 82px;
  color: var(--th-text-secondary);
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.step-content {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 16px 14px 82px;
  border-top: 1px solid var(--th-border);
  border-radius: 0 0 10px 10px;
  background: var(--th-surface-subtle);
}

.step-param {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 7px;
  min-width: 0;
}

.step-param--wide { grid-column: 1 / -1; }

.step-content--assert {
  grid-template-columns: minmax(0, 200px) minmax(0, 360px);
  column-gap: 16px;
}

.step-content--assert .step-param--wide { max-width: 576px; }
.step-param--assert-type { max-width: 200px; }
.step-param--expected-value { max-width: 360px; }

.step-param label {
  color: var(--th-text-secondary);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
}

.step-input-tools,
.step-file-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.step-file-tools { flex-wrap: wrap; }
.step-file-select { flex: 1 1 240px; min-width: 0; }
.step-input-tools > :deep(.el-input) { flex: 1; min-width: 0; }
.step-input-tools > :deep(.el-button) { flex: none; }
.step-param :deep(.el-select) { width: 100%; }
.step-param :deep(.el-input-number) {
  width: 180px;
  max-width: 100%;
  height: 34px;
  line-height: 32px;
}

.step-field :deep(.el-select__wrapper),
.step-param :deep(.el-select__wrapper),
.step-param :deep(.el-input__wrapper) { min-height: 34px; }

.step-param :deep(.el-input-group__append) {
  color: var(--th-primary);
  background: var(--th-primary-soft);
}

@container (max-width: 760px) {
  .test-case-detail { padding: 16px; }
  .detail-header { flex-wrap: wrap; }
  .detail-actions { width: 100%; justify-content: flex-start; }
  .detail-toolbar { align-items: stretch; }
  .detail-actions__run-config { flex: 1 1 100%; }
  .step-left { grid-template-columns: 48px 140px minmax(0, 1fr); gap: 10px; }
  .step-header { padding: 12px; gap: 8px; }
  .step-content { padding: 16px; }
  .step-param { grid-column: 1 / -1; }
  .step-summary { margin-left: 70px; }
}

@container (max-width: 560px) {
  .detail-title { flex-basis: 100%; }
  .section-heading { align-items: flex-start; flex-direction: column; }
  .detail-actions__run-config { align-items: stretch; flex-direction: column; }
  .run-field,
  .engine-select,
  .browser-select,
  .mode-select { width: 100%; }
  .step-header { align-items: flex-start; }
  .step-left { grid-template-columns: 40px minmax(0, 1fr); }
  .step-index { gap: 4px; padding-top: 22px; }
  .step-number { width: 22px; height: 26px; }
  .step-field--element { grid-column: 2; }
  .step-right { padding-top: 20px; }
  .step-summary { margin-left: 62px; }
  .step-content { grid-template-columns: minmax(0, 1fr); }
  .steps-header { align-items: flex-start; padding: 12px; flex-wrap: wrap; }
  .steps-list { padding: 10px; }
}

@media (max-width: 1200px) {
  .main-content { grid-template-columns: 240px minmax(0, 1fr); gap: 14px; }
}

@media (max-width: 800px) {
  .test-case-manager { height: auto; min-height: calc(100dvh - 108px); }
  .main-content { grid-template-columns: minmax(0, 1fr); }
  .left-panel { max-height: 280px; }
  .test-case-list { flex: 1 1 auto; }
  .panel-header { padding: 12px; gap: 10px; }
  .right-panel { height: calc(100dvh - 32px); min-height: 520px; }
  .project-select { width: min(220px, 100%); }
}

.execution-result {
  height: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  background: white;
  overflow: hidden;
}

.execution-result.with-steps {
  margin-top: 0;
}

.execution-result .result-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.result-progress {
  margin: 0;
  padding: 12px 15px 0;
  color: #606266;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.execution-result .result-content {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 15px;
}

.result-content {
  flex: 1;
  overflow: hidden;
}

/* 为el-tabs和el-tab-pane添加flex布局支持 */
.result-content :deep(.el-tabs) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

.result-content :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.result-content :deep(.el-tab-pane) {
  height: 100%;
  overflow: auto;
}

.data-row-details {
  padding: 0 16px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.data-row-details img {
  display: block;
  max-width: min(500px, 100%);
  cursor: pointer;
}

/* .result-header 已在 .execution-result 中定义 */

.result-header h4 {
  margin: 0;
}

.logs-container {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.log-item {
  margin-bottom: 15px;
  padding: 12px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.log-item:last-child {
  margin-bottom: 0;
}

.log-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
}

.log-action {
  font-weight: 500;
  color: #606266;
  overflow-wrap: anywhere;
}

.log-desc {
  color: #909399;
  font-size: 14px;
  min-width: 0;
  overflow-wrap: anywhere;
}

.log-error {
  display: flex;
  align-items: flex-start;  /* 改为 flex-start，适配多行文本 */
  gap: 8px;
  color: #f56c6c;
  background: #fef0f0;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 14px;

  .error-message {
    margin: 0;
    padding: 0;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;  /* 保留换行符和空格 */
    word-break: break-word;  /* 长单词换行 */
    overflow-wrap: anywhere;
    min-width: 0;
    flex: 1;
  }

  .el-icon {
    margin-top: 2px;  /* 图标与文本顶部对齐 */
    flex-shrink: 0;  /* 图标不缩小 */
  }
}

.screenshots-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
  gap: 20px;
  padding: 10px;
}

.screenshot-item {
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: transform 0.2s ease;
}

.screenshot-item:hover {
  transform: translateY(-4px);
}

.screenshot-wrapper {
  display: block;
  position: relative;
  width: 100%;
  min-height: 200px;
  padding: 0;
  font: inherit;
  cursor: zoom-in;
  background: #f5f5f5;
  border-radius: 8px;
  border: 2px solid #e6e6e6;
  overflow: hidden;
  transition: border-color 0.3s ease;
}

.screenshot-wrapper:disabled { cursor: default; }
.screenshot-wrapper:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 3px; }

.screenshot-item:hover .screenshot-wrapper {
  border-color: #409eff;
}

.screenshot-wrapper img {
  width: 100%;
  height: auto;
  display: block;
  transition: opacity 0.3s ease;
}

.screenshot-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.screenshot-item:hover .screenshot-overlay {
  opacity: 1;
}

.zoom-icon {
  font-size: 48px;
  color: white;
}

.screenshot-placeholder,
.screenshot-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
  font-size: 14px;
}

.screenshot-placeholder .el-icon,
.screenshot-error .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.screenshot-error {
  color: #f56c6c;
}

.screenshot-info {
  margin-top: 10px;
}

.screenshot-description {
  margin: 0 0 5px 0;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  text-align: left;
  overflow-wrap: anywhere;
}

.screenshot-meta {
  margin: 0 0 3px 0;
  font-size: 12px;
  color: #666;
  text-align: left;
}

.screenshot-time {
  margin: 0;
  font-size: 11px;
  color: #999;
  text-align: left;
}

/* 截图预览对话框样式 */
.screenshot-preview {
  display: flex;
  flex-direction: column;
}

.preview-info {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.preview-info h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
  overflow-wrap: anywhere;
}

.preview-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #666;
}

.preview-image {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  max-height: 70vh;
  overflow: auto;
}

.preview-image img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.errors-container {
  padding: 10px;
}

.error-item {
  background: #fff;
  border: 2px solid #f56c6c;
  border-radius: 8px;
  padding: clamp(12px, 2vw, 20px);
  min-width: 0;
  margin-bottom: 15px;
}

.error-item:last-child {
  margin-bottom: 0;
}

.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.error-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #c45656;
  font-size: 14px;
  font-weight: 600;
}

.error-heading .el-icon {
  flex-shrink: 0;
}

.error-summary {
  margin: 0;
  padding: 12px;
  border-radius: 6px;
  background: #fef0f0;
  color: #b42318;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: normal;
}

.error-summary + .error-meta,
.error-summary + .error-details {
  margin-top: 15px;
}

.error-step {
  background: #fef0f0;
  color: #f56c6c;
  padding: 5px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
}

.error-meta {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.meta-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.meta-item:last-child {
  margin-bottom: 0;
}

.meta-label {
  font-weight: 600;
  color: #606266;
  min-width: 80px;
  margin-right: 10px;
}

.meta-value {
  color: #303133;
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}

.error-details {
  background: #2d2d2d;
  border-radius: 6px;
  overflow: hidden;
}

.details-header {
  background: #1e1e1e;
  color: #fff;
  padding: 10px 15px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #3d3d3d;
}

.details-content {
  color: #ff6b6b;
  padding: 15px;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: anywhere;
  max-height: 400px;
  overflow-y: auto;
}

.details-content::-webkit-scrollbar {
  width: 6px;
}

.details-content::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.details-content::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.details-content::-webkit-scrollbar-thumb:hover {
  background: #777;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.data-factory-btn,
.variable-helper-btn {
  color: var(--th-primary);
  background: var(--th-primary-soft);
  border-color: var(--el-color-primary-light-7);
}

.data-factory-btn:hover,
.variable-helper-btn:hover {
  color: var(--th-primary-hover);
  background: var(--el-color-primary-light-8);
  border-color: var(--el-color-primary-light-5);
}

/* 下拉层通过 Teleport 挂在 body 下，需使用 :global 才能从 scoped 样式命中。 */
:global(.test-case-element-dropdown .el-select-dropdown__wrap) {
  max-height: min(420px, 60vh);
}

:global(.test-case-element-dropdown .el-select-group__title) {
  position: sticky;
  top: 0;
  z-index: 1;
  height: 34px;
  padding-left: 16px;
  color: #606266;
  font-weight: 600;
  background: #f5f7fa;
}

:global(.test-case-element-dropdown .el-select-dropdown__item) {
  height: auto;
  min-height: 58px;
  padding: 8px 16px;
  line-height: 1.35;
}

.element-option {
  min-width: 0;
}

.element-option__header {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.element-option__name {
  overflow: hidden;
  color: #303133;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.element-option__badge {
  flex: none;
  padding: 1px 6px;
  border-radius: 4px;
  color: #606266;
  font-size: 11px;
  background: #f0f2f5;
}

.element-option__badge--strategy {
  color: #337ecc;
  background: #ecf5ff;
}

.element-option__locator {
  margin-top: 4px;
  overflow: hidden;
  color: #909399;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
