<template>
  <div class="file-library" v-loading="loading">
    <el-alert title="文件按 UI 项目管理；上传或创建后可直接在用例的上传步骤中选择。" type="info" :closable="false" />
    <div class="toolbar">
      <el-select v-model="projectId" class="project-filter" placeholder="选择项目" @change="loadFiles">
        <el-option v-for="project in projects" :key="project.id" :value="project.id" :label="project.name" />
      </el-select>
      <el-input v-model="search" placeholder="搜索文件名" clearable @input="searchFiles" />
      <el-upload :show-file-list="false" :auto-upload="false" :on-change="upload" :disabled="!projectId || uploading">
        <el-button type="primary" :disabled="!projectId" :loading="uploading">上传本地文件</el-button>
      </el-upload>
      <el-button :disabled="!projectId" @click="showCreate = true">创建文本文件</el-button>
      <el-button @click="loadFiles">刷新</el-button>
    </div>
    <el-table :data="files" empty-text="当前项目还没有测试文件">
      <el-table-column prop="name" label="文件名" min-width="190" show-overflow-tooltip />
      <el-table-column label="大小" width="110"><template #default="{ row }">{{ formatSize(row.file_size) }}</template></el-table-column>
      <el-table-column prop="storage_key" label="存储位置（media 目录下）" min-width="230" show-overflow-tooltip />
      <el-table-column label="引用用例" min-width="180" show-overflow-tooltip>
        <template #default="{ row }"><span>{{ row.used_by.map(item => item.name).join('、') || '未引用' }}</span></template>
      </el-table-column>
      <el-table-column prop="created_by_name" label="上传人" width="110" />
      <el-table-column label="操作" width="150" align="center" class-name="file-action-column">
        <template #default="{ row }">
          <div class="file-actions">
            <el-button text type="primary" @click="download(row)">下载</el-button>
            <el-button text type="danger" :disabled="row.used_by.length > 0" @click="remove(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="fetchFiles" />
    <el-dialog v-model="showCreate" title="创建测试文件" width="640px" append-to-body>
      <el-form label-width="80px">
        <el-form-item label="文件名"><el-input v-model="fileName" placeholder="例如 accounts.csv、payload.json、sample.txt" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="content" type="textarea" :rows="12" placeholder="填写 UTF-8 文本内容" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate = false">取消</el-button><el-button type="primary" :loading="uploading" @click="createFile">创建并保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUiProjects, getTestFileAssets, uploadTestFileAsset, downloadTestFileAsset, deleteTestFileAsset } from '@/api/ui_automation'
const props = defineProps({ initialProject: { type: [String, Number], default: '' } })
const projects = ref([])
const projectId = ref(props.initialProject ? Number(props.initialProject) : '')
const files = ref([])
const loading = ref(false)
const uploading = ref(false)
const search = ref('')
const page = ref(1)
const total = ref(0)
const showCreate = ref(false)
const fileName = ref('sample.txt')
const content = ref('')
let searchTimer
let generation = 0
const errorText = error => error.response?.data?.detail || error.response?.data?.file?.[0] || '操作失败，请稍后重试'
const formatSize = size => size < 1024 ? `${size} B` : size < 1048576 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1048576).toFixed(1)} MB`
const fetchFiles = async () => {
  const current = ++generation
  if (!projectId.value) { files.value = []; total.value = 0; return }
  loading.value = true
  try {
    const { data } = await getTestFileAssets({ project: projectId.value, search: search.value, page: page.value, page_size: 20 })
    if (current !== generation) return
    files.value = data.results || data
    total.value = data.count ?? files.value.length
  } catch (error) { if (current === generation) ElMessage.error(errorText(error)) }
  finally { if (current === generation) loading.value = false }
}
const loadFiles = () => { page.value = 1; return fetchFiles() }
const searchFiles = () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadFiles, 250) }
const saveFile = async file => {
  if (!projectId.value || uploading.value) return false
  if (file.size > 100 * 1024 * 1024) { ElMessage.warning('文件不能超过 100 MB'); return false }
  uploading.value = true
  try {
    const form = new FormData()
    form.append('project', projectId.value)
    form.append('file', file)
    await uploadTestFileAsset(form)
    await loadFiles()
    ElMessage.success('文件已保存，可在 UI 用例中选择')
    return true
  } catch (error) { ElMessage.error(errorText(error)); return false }
  finally { uploading.value = false }
}
const upload = file => saveFile(file.raw)
const createFile = async () => {
  if (!fileName.value.trim() || /[/\\]/.test(fileName.value)) { ElMessage.warning('请填写不含路径的文件名'); return }
  if (await saveFile(new File([content.value], fileName.value.trim(), { type: 'text/plain;charset=utf-8' }))) showCreate.value = false
}
const download = async file => {
  try {
    const { data } = await downloadTestFileAsset(file.id)
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url; link.download = file.name; link.click()
    URL.revokeObjectURL(url)
  } catch (error) { ElMessage.error(errorText(error)) }
}
const remove = async file => {
  try {
    await ElMessageBox.confirm(`删除测试文件“${file.name}”？`, '删除文件', { type: 'warning' })
    await deleteTestFileAsset(file.id)
    await loadFiles()
    ElMessage.success('文件已删除')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(errorText(error)) }
}
onMounted(async () => {
  try {
    const { data } = await getUiProjects({ page_size: 1000 })
    projects.value = data.results || data
    if (!projectId.value) projectId.value = projects.value[0]?.id || ''
    await loadFiles()
  } catch (error) { ElMessage.error(errorText(error)) }
})
onBeforeUnmount(() => { generation++; clearTimeout(searchTimer) })
</script>
<style scoped>
.toolbar { display: flex; gap: 12px; margin: 18px 0; flex-wrap: wrap; }
.toolbar .project-filter { width: 200px; }
.toolbar .el-input { width: 200px; }
.file-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}
.file-actions :deep(.el-button) { margin: 0; padding: 5px 8px; }
:deep(.file-action-column .cell) { overflow: visible; white-space: nowrap; }
.el-pagination { margin-top: 16px; }
</style>
