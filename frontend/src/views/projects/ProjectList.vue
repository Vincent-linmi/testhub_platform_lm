<template>
  <div class="page-container th-list-page">
    <PageHeader :title="$t('project.projectManagement')">
      <el-button type="primary" @click="handleCreateProject">
        <el-icon><Plus /></el-icon>
        {{ $t('project.newProject') }}
      </el-button>
    </PageHeader>

    <div class="card-container">
      <div class="list-toolbar">
        <el-input
          v-model="searchText"
          :placeholder="$t('project.searchPlaceholder')" :aria-label="$t('project.searchPlaceholder')"
          clearable
          @input="handleSearch"
          @keyup.enter="handleFilter"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" :placeholder="$t('project.statusFilter')" :aria-label="$t('project.statusFilter')" clearable @change="handleFilter">
          <el-option :label="$t('project.active')" value="active" />
          <el-option :label="$t('project.paused')" value="paused" />
          <el-option :label="$t('project.completed')" value="completed" />
          <el-option :label="$t('project.archived')" value="archived" />
        </el-select>

        <el-button @click="resetFilters">{{ $t('common.resetFilters') }}</el-button>
      </div>
      
      <el-alert v-if="listError" type="error" :closable="false" show-icon class="list-error" :title="$t('project.fetchListFailed')">
        <el-button link type="primary" @click="fetchProjects">{{ $t('common.retry') }}</el-button>
      </el-alert>
      <el-table row-key="id" :data="projects" v-loading="loading" :empty-text="listError ? $t('common.loadFailed') : $t('common.noResults')" style="width: 100%">
        <el-table-column prop="name" :label="$t('project.projectName')" min-width="200">
          <template #default="{ row }">
            <el-link @click="goToProject(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('project.description')" min-width="300" show-overflow-tooltip />
        <el-table-column prop="status" :label="$t('project.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner.username" :label="$t('project.owner')" width="120" />
        <el-table-column prop="created_at" :label="$t('project.createdAt')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.actions')" width="150" :fixed="isMobile ? false : 'right'">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editProject(row)">{{ $t('common.edit') }}</el-button>
            <el-button link size="small" type="danger" @click="deleteProject(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          :pager-count="5"
          @current-change="handlePageChange"
        />
      </div>
    </div>
    
    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      :title="isEdit ? $t('project.editProject') : $t('project.createProject')"
      v-model="showCreateDialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" :label-position="isMobile ? 'top' : 'right'">
        <el-form-item :label="$t('project.projectName')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('project.projectNamePlaceholder')" :aria-label="$t('project.projectNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('project.projectDescription')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            :placeholder="$t('project.projectDescriptionPlaceholder')" :aria-label="$t('project.projectDescriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('project.status')" prop="status">
          <el-select v-model="form.status" :placeholder="$t('project.selectStatus')" :aria-label="$t('project.selectStatus')">
            <el-option :label="$t('project.active')" value="active" />
            <el-option :label="$t('project.paused')" value="paused" />
            <el-option :label="$t('project.completed')" value="completed" />
            <el-option :label="$t('project.archived')" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? $t('project.update') : $t('project.create') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { useListRequest } from '@/composables/useListRequest'
import { useMediaQuery } from '@/composables/useMediaQuery'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 768px)')
const submitting = ref(false)
const showCreateDialog = ref(false)
const isEdit = ref(false)
const formRef = ref()

const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const statusFilter = ref('')

const form = reactive({
  id: null,
  name: '',
  description: '',
  status: 'active'
})

const rules = computed(() => ({
  name: [
    { required: true, message: t('project.projectNameRequired'), trigger: 'blur' },
    { min: 2, max: 200, message: t('project.projectNameLength'), trigger: 'blur' }
  ],
  status: [
    { required: true, message: t('project.projectStatusRequired'), trigger: 'change' }
  ]
}))

const { loading, error: listError, load: fetchProjects, schedule: scheduleSearch } = useListRequest(
  (signal) => api.get('/projects/', { signal, params: {
    page: currentPage.value, search: searchText.value, status: statusFilter.value
  } }),
  (response) => {
    projects.value = response.data.results || []
    total.value = response.data.count || 0
  }
)

const handleSearch = () => { currentPage.value = 1; scheduleSearch() }
const handleFilter = () => { currentPage.value = 1; fetchProjects() }
const handlePageChange = (page) => {
  if (page === currentPage.value) return
  currentPage.value = page
  fetchProjects()
}
const resetFilters = () => {
  searchText.value = ''
  statusFilter.value = ''
  handleFilter()
}

const goToProject = (id) => {
  router.push(`/ai-generation/projects/${id}`)
}

const handleCreateProject = () => {
  resetForm()
  showCreateDialog.value = true
}

const editProject = (project) => {
  isEdit.value = true
  form.id = project.id
  form.name = project.name
  form.description = project.description
  form.status = project.status
  showCreateDialog.value = true
}

const handleDialogClose = () => {
  resetForm()
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.description = ''
  form.status = 'active'
  isEdit.value = false
  // 清除表单验证错误
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const handleSubmit = async () => {
  if (!formRef.value || submitting.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await api.put(`/projects/${form.id}/`, form)
          ElMessage.success(t('project.updateSuccess'))
        } else {
          await api.post('/projects/', form)
          ElMessage.success(t('project.createSuccess'))
        }
        showCreateDialog.value = false
        resetForm()
        fetchProjects()
      } catch (error) {
        ElMessage.error(isEdit.value ? t('project.updateFailed') : t('project.createFailed'))
      } finally {
        submitting.value = false
      }
    }
  })
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm(t('project.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })

    await api.delete(`/projects/${project.id}/`)
    ElMessage.success(t('project.deleteSuccess'))
    fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('project.deleteFailed'))
    }
  }
}

const getStatusType = (status) => {
  const typeMap = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    active: t('project.active'),
    paused: t('project.paused'),
    completed: t('project.completed'),
    archived: t('project.archived')
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.el-form .el-select { width: 100%; }
</style>
