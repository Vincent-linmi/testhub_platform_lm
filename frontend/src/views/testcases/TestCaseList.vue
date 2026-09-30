<template>
  <div class="page-container th-list-page">
    <PageHeader :title="$t('testcase.title')">
      <div class="header-actions">
        <el-button
          v-if="selectedTestCases.length > 0"
          @click="openMoveGroupDialog">
          <el-icon><FolderOpened /></el-icon>
          {{ $t('testcase.moveToGroup') }} ({{ selectedTestCases.length }})
        </el-button>
        <el-button
          v-if="selectedTestCases.length > 0"
          type="danger"
          @click="batchDeleteTestCases"
          :disabled="isDeleting">
          <el-icon><Delete /></el-icon>
          {{ $t('testcase.batchDelete') }} ({{ selectedTestCases.length }})
        </el-button>
        <el-button :loading="exporting" @click="exportToExcel">
          <el-icon><Download /></el-icon>
          {{ $t('testcase.exportExcel') }}
        </el-button>
        <el-button @click="downloadImportTemplate">
          <el-icon><Download /></el-icon>
          {{ $t('testcase.downloadImportTemplate') }}
        </el-button>
        <el-button @click="openImportDialog">
          <el-icon><Upload /></el-icon>
          {{ $t('testcase.importCases') }}
        </el-button>
        <el-button @click="goToImportRecords">
          {{ $t('testcase.importRecords') }}
        </el-button>
        <el-button @click="openGroupDialog">
          <el-icon><Folder /></el-icon>
          {{ $t('testcase.manageGroups') }}
        </el-button>
        <el-button type="primary" @click="$router.push('/ai-generation/testcases/create')">
          <el-icon><Plus /></el-icon>
          {{ $t('testcase.newCase') }}
        </el-button>
      </div>
    </PageHeader>
    
    <div class="card-container">
      <div class="list-toolbar">
        <el-input
          v-model="searchText"
          :placeholder="$t('testcase.searchPlaceholder')" :aria-label="$t('testcase.searchPlaceholder')"
          clearable
          @input="handleSearch"
          @keyup.enter="handleFilter"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="projectFilter" :placeholder="$t('testcase.relatedProject')" :aria-label="$t('testcase.relatedProject')" clearable @change="handleProjectFilter">
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-select v-model="groupFilter" :placeholder="$t('testcase.groupFilter')" :aria-label="$t('testcase.groupFilter')" clearable @change="handleFilter">
          <el-option :label="$t('testcase.ungrouped')" value="ungrouped" />
          <el-option
            v-for="group in filterGroups"
            :key="group.id"
            :label="projectFilter ? group.name : `${group.project_name} / ${group.name}`"
            :value="group.id"
          />
        </el-select>
        <el-select v-model="priorityFilter" :placeholder="$t('testcase.priorityFilter')" :aria-label="$t('testcase.priorityFilter')" clearable @change="handleFilter">
          <el-option :label="$t('testcase.low')" value="low" />
          <el-option :label="$t('testcase.medium')" value="medium" />
          <el-option :label="$t('testcase.high')" value="high" />
          <el-option :label="$t('testcase.critical')" value="critical" />
        </el-select>

        <el-button @click="resetFilters">{{ $t('common.resetFilters') }}</el-button>
      </div>
      
      <el-alert v-if="listError" type="error" :closable="false" show-icon class="list-error" :title="$t('testcase.fetchListFailed')">
        <el-button link type="primary" @click="fetchTestCases">{{ $t('common.retry') }}</el-button>
      </el-alert>
      <div class="table-container">
        <el-table 
          :data="testcases"
          row-key="id"
          v-loading="loading" :empty-text="listError ? $t('common.loadFailed') : $t('common.noResults')"
          style="width: 100%"
          :max-height="isMobile ? undefined : 'max(240px, calc(100dvh - 320px))'"
          @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column type="index" :label="$t('testcase.serialNumber')" width="80" :index="getSerialNumber" />
          <el-table-column prop="title" :label="$t('testcase.caseTitle')" min-width="250">
            <template #default="{ row }">
              <el-link @click="goToTestCase(row.id)" type="primary">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="project.name" :label="$t('testcase.relatedProject')" width="150">
            <template #default="{ row }">
              {{ row.project?.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="group.name" :label="$t('testcase.group')" width="150">
            <template #default="{ row }">
              <el-tag v-if="row.group" size="small" type="info">{{ row.group.name }}</el-tag>
              <span v-else class="no-version">{{ $t('testcase.ungrouped') }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="versions" :label="$t('testcase.relatedVersions')" width="200">
            <template #default="{ row }">
              <div v-if="row.versions && row.versions.length > 0" class="version-tags">
                <el-tag 
                  v-for="version in row.versions.slice(0, 2)" 
                  :key="version.id" 
                  size="small" 
                  :type="version.is_baseline ? 'warning' : 'info'"
                  class="version-tag"
                >
                  {{ version.name }}
                </el-tag>
                <el-tooltip v-if="row.versions.length > 2" :content="getVersionsTooltip(row.versions)">
                  <el-tag size="small" type="info" class="version-tag">
                    +{{ row.versions.length - 2 }}
                  </el-tag>
                </el-tooltip>
              </div>
              <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="priority" :label="$t('testcase.priority')" width="100">
            <template #default="{ row }">
              <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="test_type" :label="$t('testcase.testType')" width="120">
            <template #default="{ row }">
              {{ getTypeText(row.test_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="author.username" :label="$t('testcase.author')" width="120" />
          <el-table-column prop="created_at" :label="$t('testcase.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('project.actions')" width="150" :fixed="isMobile ? false : 'right'">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="editTestCase(row)">{{ $t('common.edit') }}</el-button>
              <el-button link size="small" type="danger" @click="deleteTestCase(row)">{{ $t('common.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :page-sizes="[15, 25, 35, 50, 100]"
          :total="total"
          :layout="isMobile ? 'total, prev, pager, next' : 'total, sizes, prev, pager, next'"
          :pager-count="5"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="groupDialogVisible"
      :title="$t('testcase.manageGroups')"
      width="680px"
    >
      <div class="group-dialog-toolbar">
        <el-select
          v-model="manageProjectId"
          :placeholder="$t('testcase.selectProjectForGroup')"
          filterable
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-button type="primary" :disabled="!manageProjectId" @click="createGroup">
          <el-icon><Plus /></el-icon>
          {{ $t('testcase.newGroup') }}
        </el-button>
      </div>
      <el-table :data="managedGroups" max-height="420" :empty-text="$t('testcase.noGroups')">
        <el-table-column prop="name" :label="$t('testcase.groupName')" min-width="220" />
        <el-table-column prop="testcase_count" :label="$t('testcase.caseCount')" width="110" />
        <el-table-column :label="$t('project.actions')" width="150" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="renameGroup(row)">{{ $t('common.edit') }}</el-button>
            <el-button link type="danger" @click="deleteGroup(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog
      v-model="moveGroupDialogVisible"
      :title="$t('testcase.moveToGroup')"
      width="460px"
    >
      <el-form label-width="100px">
        <el-form-item :label="$t('testcase.targetGroup')">
          <el-select v-model="moveGroupId" style="width: 100%" :placeholder="$t('testcase.selectTargetGroup')" clearable>
            <el-option :label="$t('testcase.ungrouped')" :value="null" />
            <el-option
              v-for="group in moveTargetGroups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveGroupDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="isMovingGroup" @click="moveSelectedToGroup">
          {{ $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="importDialogVisible"
      :title="$t('testcase.importDialogTitle')"
      width="560px"
    >
      <el-alert
        :title="$t('testcase.uploadTip')"
        type="info"
        :closable="false"
        show-icon
        class="import-alert"
      />

      <el-form label-width="100px">
        <el-form-item :label="$t('testcase.importProject')">
          <el-select
            v-model="importForm.projectId"
            style="width: 100%"
            :placeholder="$t('testcase.selectImportProject')" :aria-label="$t('testcase.selectImportProject')"
            filterable
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('testcase.selectImportFile')">
          <el-upload
            class="import-upload"
            drag
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx"
            :show-file-list="false"
            :before-upload="beforeImportUpload"
            :on-change="handleImportFileChange"
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">
              {{ $t('testcase.chooseFile') }}
            </div>
            <template #tip>
              <div class="el-upload__tip">
                {{ $t('testcase.selectedFile') }}: {{ selectedImportFile?.name || '-' }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="importDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button @click="downloadImportTemplate">
          {{ $t('testcase.downloadImportTemplate') }}
        </el-button>
        <el-button type="primary" :loading="isCreatingImport" @click="submitImport">
          {{ isCreatingImport ? $t('testcase.uploading') : $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Download, Delete, Upload, Folder, FolderOpened } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { useListRequest } from '@/composables/useListRequest'
import { useMediaQuery } from '@/composables/useMediaQuery'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const router = useRouter()
const isMobile = useMediaQuery('(max-width: 768px)')
const testcases = ref([])
const projects = ref([])
const groups = ref([])
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)
const searchText = ref('')
const projectFilter = ref('')
const groupFilter = ref('')
const priorityFilter = ref('')
const selectedTestCases = ref([])
const isDeleting = ref(false)
const isMovingGroup = ref(false)
const groupDialogVisible = ref(false)
const moveGroupDialogVisible = ref(false)
const manageProjectId = ref('')
const moveProjectId = ref('')
const moveGroupId = ref(null)
const exporting = ref(false)
const importDialogVisible = ref(false)
const isCreatingImport = ref(false)
const selectedImportFile = ref(null)
const importForm = ref({
  projectId: ''
})

const { loading, error: listError, load: fetchTestCases, schedule: scheduleSearch } = useListRequest(
  (signal) => api.get('/testcases/', { signal, params: {
    page: currentPage.value, page_size: pageSize.value, search: searchText.value,
    project: projectFilter.value, group: groupFilter.value, priority: priorityFilter.value
  } }),
  (response) => {
    testcases.value = response.data.results || []
    total.value = response.data.count || 0
  }
)

const handleSearch = () => { currentPage.value = 1; scheduleSearch() }
const handleFilter = () => { currentPage.value = 1; fetchTestCases() }
const filterGroups = computed(() => projectFilter.value
  ? groups.value.filter(group => group.project_id === projectFilter.value)
  : groups.value)
const managedGroups = computed(() => groups.value.filter(group => group.project_id === manageProjectId.value))
const moveTargetGroups = computed(() => groups.value.filter(group => group.project_id === moveProjectId.value))
const handleProjectFilter = () => {
  if (groupFilter.value !== 'ungrouped' && !filterGroups.value.some(group => group.id === groupFilter.value)) {
    groupFilter.value = ''
  }
  handleFilter()
}
const handlePageChange = (page) => {
  if (page === currentPage.value) return
  currentPage.value = page
  fetchTestCases()
}
const handleSizeChange = (size) => {
  if (size === pageSize.value) return
  pageSize.value = size
  handleFilter()
}
const resetFilters = () => {
  searchText.value = ''
  projectFilter.value = ''
  groupFilter.value = ''
  priorityFilter.value = ''
  handleFilter()
}

const goToTestCase = (id) => {
  router.push(`/ai-generation/testcases/${id}`)
}

const editTestCase = (testcase) => {
  router.push(`/ai-generation/testcases/${testcase.id}/edit`)
}

const deleteTestCase = async (testcase) => {
  try {
    await ElMessageBox.confirm(t('testcase.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    
    await api.delete(`/testcases/${testcase.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTestCases.value = selection
}

const getErrorMessage = (error, fallbackKey) => {
  const data = error.response?.data
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') {
    const firstValue = Object.values(data)[0]
    if (Array.isArray(firstValue)) return firstValue[0]
    if (firstValue) return firstValue
  }
  return t(fallbackKey)
}

const fetchGroups = async () => {
  try {
    const response = await api.get('/testcases/groups/')
    groups.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('testcase.fetchGroupsFailed'))
  }
}

const openGroupDialog = () => {
  manageProjectId.value = projectFilter.value || projects.value[0]?.id || ''
  groupDialogVisible.value = true
}

const createGroup = async () => {
  if (!manageProjectId.value) return
  try {
    const { value } = await ElMessageBox.prompt(
      t('testcase.groupNamePlaceholder'),
      t('testcase.newGroup'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        inputPattern: /\S+/,
        inputErrorMessage: t('testcase.groupNameRequired')
      }
    )
    await api.post('/testcases/groups/', { project_id: manageProjectId.value, name: value.trim() })
    ElMessage.success(t('testcase.groupCreateSuccess'))
    await fetchGroups()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getErrorMessage(error, 'testcase.groupCreateFailed'))
  }
}

const renameGroup = async (group) => {
  try {
    const { value } = await ElMessageBox.prompt(
      t('testcase.groupNamePlaceholder'),
      t('testcase.renameGroup'),
      {
        inputValue: group.name,
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        inputPattern: /\S+/,
        inputErrorMessage: t('testcase.groupNameRequired')
      }
    )
    await api.patch(`/testcases/groups/${group.id}/`, { name: value.trim() })
    ElMessage.success(t('testcase.groupRenameSuccess'))
    await Promise.all([fetchGroups(), fetchTestCases()])
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getErrorMessage(error, 'testcase.groupRenameFailed'))
  }
}

const deleteGroup = async (group) => {
  try {
    await ElMessageBox.confirm(
      t('testcase.groupDeleteConfirm', { name: group.name, count: group.testcase_count }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    await api.delete(`/testcases/groups/${group.id}/`)
    if (groupFilter.value === group.id) groupFilter.value = ''
    ElMessage.success(t('testcase.groupDeleteSuccess'))
    await Promise.all([fetchGroups(), fetchTestCases()])
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(t('testcase.groupDeleteFailed'))
  }
}

const openMoveGroupDialog = () => {
  const projectIds = [...new Set(selectedTestCases.value.map(testcase => testcase.project?.id))]
  if (projectIds.length !== 1 || !projectIds[0]) {
    ElMessage.warning(t('testcase.sameProjectRequired'))
    return
  }
  moveProjectId.value = projectIds[0]
  const currentGroupIds = [...new Set(selectedTestCases.value.map(testcase => testcase.group?.id || null))]
  moveGroupId.value = currentGroupIds.length === 1 ? currentGroupIds[0] : null
  moveGroupDialogVisible.value = true
}

const moveSelectedToGroup = async () => {
  isMovingGroup.value = true
  try {
    const response = await api.post('/testcases/groups/assign/', {
      testcase_ids: selectedTestCases.value.map(testcase => testcase.id),
      group_id: moveGroupId.value
    })
    ElMessage.success(t('testcase.moveGroupSuccess', { count: response.data.updated_count }))
    moveGroupDialogVisible.value = false
    selectedTestCases.value = []
    await Promise.all([fetchGroups(), fetchTestCases()])
  } catch (error) {
    ElMessage.error(getErrorMessage(error, 'testcase.moveGroupFailed'))
  } finally {
    isMovingGroup.value = false
  }
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeleteTestCases = async () => {
  if (selectedTestCases.value.length === 0) {
    ElMessage.warning(t('testcase.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('testcase.batchDeleteConfirm', { count: selectedTestCases.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    // 逐个删除选中的测试用例
    for (const testcase of selectedTestCases.value) {
      try {
        await api.delete(`/testcases/${testcase.id}/`)
        successCount++
      } catch (error) {
        console.error(`Delete test case ${testcase.id} failed:`, error)
        failCount++
      }
    }

    // 显示删除结果
    if (successCount > 0) {
      if (failCount > 0) {
        ElMessage.success(t('testcase.batchDeletePartialSuccess', { successCount, failCount }))
      } else {
        ElMessage.success(t('testcase.batchDeleteSuccess', { successCount }))
      }
    } else {
      ElMessage.error(t('testcase.batchDeleteFailed'))
    }

    // 清空选择并重新加载列表
    selectedTestCases.value = []
    fetchTestCases()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('Batch delete failed:', error)
      ElMessage.error(t('testcase.batchDeleteError') + ': ' + (error.message || t('common.error')))
    }
  } finally {
    isDeleting.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    low: t('testcase.low'),
    medium: t('testcase.medium'),
    high: t('testcase.high'),
    critical: t('testcase.critical')
  }
  return textMap[priority] || priority
}

const getTypeText = (type) => {
  const textMap = {
    functional: t('testcase.functional'),
    integration: t('testcase.integration'),
    api: t('testcase.api'),
    ui: t('testcase.ui'),
    performance: t('testcase.performance'),
    security: t('testcase.security')
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const getVersionsTooltip = (versions) => {
  return versions.map(v => v.name + (v.is_baseline ? ' (' + t('testcase.baseline') + ')' : '')).join('、')
}

// 将HTML的<br>标签转换为换行符（用于Excel导出）
const convertBrToNewline = (text) => {
  if (!text) return ''
  return text.replace(/<br\s*\/?>/gi, '\n')
}

const exportToExcel = async () => {
  if (exporting.value) return
  exporting.value = true
  const selectedForExport = [...selectedTestCases.value]
  const exportFilters = { search: searchText.value, project: projectFilter.value, group: groupFilter.value, priority: priorityFilter.value }
  try {
    const XLSX = await import('xlsx')

    // 确定要导出的数据
    let testCasesToExport = []

    if (selectedForExport.length > 0) {
      // 如果有勾选，导出勾选的数据
      testCasesToExport = selectedForExport
    } else {
      // 如果没有勾选，分页获取所有数据
      const pageSize = 100  // 使用后端允许的最大值
      let page = 1
      let hasMore = true
      let allData = []

      while (hasMore) {
        const response = await api.get('/testcases/', {
          params: {
            page: page,
            page_size: pageSize,
            ...exportFilters
          }
        })

        const results = response.data.results || []
        allData.push(...results)

        // 检查是否还有更多数据
        // 如果返回的数据少于pageSize，说明已经是最后一页
        if (results.length < pageSize) {
          hasMore = false
        } else {
          page++
        }
      }

      testCasesToExport = allData
    }

    if (testCasesToExport.length === 0) {
      ElMessage.warning(t('testcase.noDataToExport'))
      exporting.value = false
      return
    }

    // 创建工作簿
    const workbook = XLSX.utils.book_new()

    // 准备Excel数据
    const worksheetData = [
      [t('testcase.excelNumber'), t('testcase.excelTitle'), t('testcase.excelProject'), t('testcase.excelGroup'), t('testcase.excelVersions'), t('testcase.excelPreconditions'), t('testcase.excelSteps'), t('testcase.excelExpectedResult'), t('testcase.excelPriority'), t('testcase.excelTestType'), t('testcase.excelAuthor'), t('testcase.excelCreatedAt')]
    ]

    testCasesToExport.forEach((testcase, index) => {
      const versions = testcase.versions && testcase.versions.length > 0
        ? testcase.versions.map(v => v.name + (v.is_baseline ? '(' + t('testcase.baseline') + ')' : '')).join('、')
        : t('testcase.noVersion')

      worksheetData.push([
        `TC${String(index + 1).padStart(3, '0')}`,
        testcase.title || '',
        testcase.project?.name || '',
        testcase.group?.name || t('testcase.ungrouped'),
        versions,
        convertBrToNewline(testcase.preconditions || ''),
        convertBrToNewline(testcase.steps || ''),
        convertBrToNewline(testcase.expected_result || ''),
        getPriorityText(testcase.priority),
        getTypeText(testcase.test_type),
        testcase.author?.username || '',
        formatDate(testcase.created_at)
      ])
    })
    
    // 创建工作表
    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)
    
    // 设置列宽
    const colWidths = [
      { wch: 15 }, // Test case number
      { wch: 30 }, // Case title
      { wch: 20 }, // Related project
      { wch: 20 }, // Group
      { wch: 25 }, // Related versions
      { wch: 30 }, // Preconditions
      { wch: 40 }, // Steps
      { wch: 30 }, // Expected result
      { wch: 10 }, // Priority
      { wch: 15 }, // Test type
      { wch: 15 }, // Author
      { wch: 20 }  // Created at
    ]
    worksheet['!cols'] = colWidths
    
    // 设置表头样式
    for (let col = 0; col < worksheetData[0].length; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col })
      if (!worksheet[cellAddress]) continue
      worksheet[cellAddress].s = {
        font: { bold: true },
        alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
      }
    }
    
    // 设置其他行的样式
    for (let row = 1; row < worksheetData.length; row++) {
      for (let col = 0; col < worksheetData[row].length; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
        if (worksheet[cellAddress]) {
          worksheet[cellAddress].s = {
            alignment: { vertical: 'top', wrapText: true }
          }
        }
      }
    }

    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(workbook, worksheet, t('testcase.excelSheetName'))

    // Generate filename
    const fileName = t('testcase.excelFileName', { date: new Date().toISOString().slice(0, 10) })

    // Export file
    XLSX.writeFile(workbook, fileName)

    ElMessage.success(t('testcase.exportSuccess'))
  } catch (error) {
    console.error('Export test cases failed:', error)
    ElMessage.error(t('testcase.exportFailed') + ': ' + (error.message || t('common.error')))
  } finally {
    exporting.value = false
  }
}

const downloadBlob = (blob, fileName) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const downloadImportTemplate = async () => {
  try {
    const response = await api.get('/testcases/import/template/', {
      responseType: 'blob'
    })
    downloadBlob(response.data, 'testcase_import_template_v1.xlsx')
    ElMessage.success(t('testcase.downloadTemplateSuccess'))
  } catch (error) {
    console.error('Download import template failed:', error)
    ElMessage.error(t('testcase.downloadTemplateFailed'))
  }
}

const openImportDialog = () => {
  importForm.value.projectId = projectFilter.value || ''
  selectedImportFile.value = null
  importDialogVisible.value = true
}

const beforeImportUpload = (file) => {
  const isXlsx = file.name.toLowerCase().endsWith('.xlsx')
  if (!isXlsx) {
    ElMessage.error(t('testcase.invalidImportFile'))
  }
  return isXlsx
}

const handleImportFileChange = (uploadFile) => {
  if (uploadFile?.raw) {
    selectedImportFile.value = uploadFile.raw
  }
}

const submitImport = async () => {
  if (!importForm.value.projectId) {
    ElMessage.warning(t('testcase.importProjectRequired'))
    return
  }
  if (!selectedImportFile.value) {
    ElMessage.warning(t('testcase.importFileRequired'))
    return
  }

  const formData = new FormData()
  formData.append('project_id', importForm.value.projectId)
  formData.append('file', selectedImportFile.value)

  isCreatingImport.value = true
  try {
    await api.post('/testcases/import-records/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(t('testcase.importCreated'))
    importDialogVisible.value = false
    goToImportRecords()
  } catch (error) {
    console.error('Create import record failed:', error)
    ElMessage.error(error.response?.data?.error || t('testcase.importCreateFailed'))
  } finally {
    isCreatingImport.value = false
  }
}

const goToImportRecords = () => {
  router.push('/ai-generation/testcases/import-records')
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('testcase.fetchProjectsFailed'))
  }
}

onMounted(() => {
  fetchProjects()
  fetchGroups()
  fetchTestCases()
})
</script>

<style lang="scss" scoped>
.header-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.header-actions .el-button + .el-button { margin-left: 0; }
.group-dialog-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  .el-select { flex: 1; }
}
.import-alert {
  margin-bottom: 20px;
}

.import-upload {
  width: 100%;

  :deep(.el-upload),
  :deep(.el-upload-dragger) {
    width: 100%;
  }
}

.priority-tag {
  &.low { color: var(--th-success); }
  &.medium { color: var(--th-warning); }
  &.high { color: var(--th-danger); }
  &.critical { color: var(--th-danger); font-weight: bold; }
}

.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .version-tag {
    margin: 0;
  }
}

.no-version {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

</style>
