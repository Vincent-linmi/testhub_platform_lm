<template>
  <section class="data-driven-editor">
        <div class="data-collapse-title">
          <div class="data-collapse-title__text">
            <strong>数据驱动</strong>
            <span>用多组数据重复执行同一套步骤</span>
          </div>
          <div class="data-collapse-title__status">
            <el-tag size="small" :type="enabled ? 'primary' : 'info'" effect="plain">{{ enabled ? `${rows.length} 行数据` : '未启用' }}</el-tag>
            <el-tag v-if="dirty" size="small" type="warning" effect="plain">未保存</el-tag>
          </div>
        </div>

      <div class="data-driven-content">
        <div class="data-enable-card" :class="{ 'is-enabled': enabled }">
          <div class="data-enable-card__copy">
            <strong>使用多组测试数据</strong>
            <span>开启后，每行数据会独立执行全部测试步骤，并分别保留结果。</span>
          </div>
          <div class="data-enable-card__actions">
            <el-switch v-model="enabled" :active-text="enabled ? '已启用' : '启用'" :disabled="busy" />
            <el-button size="small" :loading="saving" :disabled="busy || !dirty" @click="flush">保存测试数据</el-button>
          </div>
        </div>

        <template v-if="enabled">
          <div class="data-config-step">
            <span class="data-config-step__number">1</span>
            <div class="data-config-step__body">
              <div class="data-config-step__heading">
                <div>
                  <strong>定义数据列</strong>
                  <span>列名就是步骤中可引用的变量，例如 ${username}。</span>
                </div>
              </div>
              <div class="column-editor">
                <el-input v-model="columnText" :disabled="busy" placeholder="列名以逗号分隔，例如 username,password,expected" />
                <el-button :disabled="busy" @click="applyColumns">应用列名</el-button>
              </div>
            </div>
          </div>

          <div class="data-config-step">
            <span class="data-config-step__number">2</span>
            <div class="data-config-step__body">
              <div class="data-config-step__heading">
                <div>
                  <strong>准备测试数据</strong>
                  <span>手动添加数据行，或从本地及测试文件库导入。</span>
                </div>
                <el-button size="small" type="primary" plain :disabled="busy" @click="addRow">添加数据行</el-button>
              </div>

              <div class="data-source-bar">
                <span class="data-source-bar__label">导入数据</span>
                <el-button size="small" :disabled="busy" @click="fileInput.click()">选择 CSV / Excel</el-button>
                <el-select v-model="dataFileId" placeholder="从测试文件库选择" size="small" :disabled="busy" :loading="loadingFiles" @visible-change="loadDataFiles" @change="importStoredFile">
                  <el-option v-for="file in dataFiles" :key="file.id" :label="file.name" :value="file.id" />
                </el-select>
                <el-button size="small" text :disabled="!rows.length" @click="exportCsv">导出 CSV</el-button>
                <input ref="fileInput" type="file" accept=".csv,.xlsx,.xls" hidden @change="importFile" />
              </div>

              <el-table :data="rows" max-height="340" border empty-text="暂无数据，请添加数据行或导入文件">
                <el-table-column type="index" label="行" width="60" />
                <el-table-column v-for="column in columns" :key="column" :label="column" min-width="150">
                  <template #default="{ row }"><el-input v-model="row[column]" :disabled="busy" :type="/password|passwd|secret|token/i.test(column) ? 'password' : 'text'" :show-password="/password|passwd|secret|token/i.test(column)" /></template>
                </el-table-column>
                <el-table-column label="操作" width="96" align="center" class-name="data-action-column">
                  <template #default="{ $index }">
                    <el-popconfirm
                      title="确认删除该数据行吗？"
                      confirm-button-text="删除"
                      cancel-button-text="取消"
                      confirm-button-type="danger"
                      :disabled="busy"
                      @confirm="removeRow($index)"
                    >
                      <template #reference>
                        <el-button class="delete-row-button" text type="danger" :disabled="busy">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </template>
                </el-table-column>
              </el-table>
              <p class="data-tip">最多 1000 行。列名只能使用字母、数字和下划线，且不能以数字开头；导入会替换当前数据。</p>
            </div>
          </div>

          <div class="data-config-step">
            <span class="data-config-step__number">3</span>
            <div class="data-config-step__body">
              <div class="data-config-step__heading">
                <div>
                  <strong>绑定到测试步骤</strong>
                  <span>数据只会替换步骤中的 ${列名}；未绑定时不会再使用固定值误执行。</span>
                </div>
              </div>
              <div class="binding-list">
                <el-tag v-for="column in columns" :key="column" :type="boundColumns.has(column) ? 'success' : 'warning'" effect="plain">
                  {{ variableSyntax(column) }} · {{ boundColumns.has(column) ? '已绑定' : '未绑定' }}
                </el-tag>
              </div>
              <p v-if="columns.length && !boundColumns.size" class="binding-warning">当前没有任何数据列被步骤引用，执行前必须先完成绑定。</p>
            </div>
          </div>
        </template>

        <div v-else class="data-disabled-hint">
          当前用例将只执行一次。需要批量验证多组账号或输入时，再开启数据驱动。
        </div>
      </div>
  </section>
</template>
<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateTestCase, getTestFileAssets, downloadTestFileAsset } from '@/api/ui_automation'
import { parseDataMatrix, dataToCsv, validateColumns } from './dataTable.js'
const props = defineProps({
  caseId: { type: Number, required: true },
  projectId: { type: [String, Number], required: true },
  initialEnabled: Boolean,
  initialRows: { type: Array, default: () => [] },
  steps: { type: Array, default: () => [] },
  busy: Boolean,
})
const emit = defineEmits(['saved'])
const enabled = ref(props.initialEnabled)
const rows = ref(JSON.parse(JSON.stringify(props.initialRows)))
const columns = ref(Object.keys(rows.value[0] || { username: '', password: '', expected: '' }))
const columnText = ref(columns.value.join(','))
const saving = ref(false)
const fileInput = ref(null)
const dataFileId = ref(null)
const dataFiles = ref([])
const loadingFiles = ref(false)
const loadDataFiles = async visible => {
  if (!visible) return
  loadingFiles.value = true
  try {
    const files = []
    let page = 1
    let more = true
    while (more) {
      const { data } = await getTestFileAssets({ project: props.projectId, page, page_size: 200 })
      files.push(...(data.results || data))
      more = Boolean(data.next)
      page++
    }
    dataFiles.value = files.filter(file => /\.(csv|xlsx|xls)$/i.test(file.name))
  } catch { ElMessage.error('加载测试文件失败') }
  finally { loadingFiles.value = false }
}
const importStoredFile = async id => {
  dataFileId.value = null
  try {
    const { data } = await downloadTestFileAsset(id)
    if (data.size > 10 * 1024 * 1024) { ElMessage.warning('数据文件不能超过 10 MB'); return }
    await importBuffer(await data.arrayBuffer())
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error.message || '导入失败') }
}
const snapshot = () => JSON.stringify({ enabled: enabled.value, rows: rows.value })
const savedSnapshot = ref(snapshot())
const dirty = computed(() => snapshot() !== savedSnapshot.value || columnText.value !== columns.value.join(','))
const variableSyntax = column => '${' + column + '}'
const boundColumns = computed(() => {
  const found = new Set()
  for (const step of props.steps) {
    const text = `${step.input_value || ''}\n${step.assert_value || ''}`
    for (const column of columns.value) {
      if (text.includes(`\${${column}}`)) found.add(column)
    }
  }
  return found
})
const applyColumns = () => {
  try {
    const next = columnText.value.split(',').map(value => value.trim())
    validateColumns(next)
    rows.value = rows.value.map(row => Object.fromEntries(next.map(column => [column, row[column] ?? ''])))
    columns.value = next
    columnText.value = next.join(',')
    return true
  } catch (error) { ElMessage.warning(error.message); return false }
}
const addRow = () => {
  if (rows.value.length >= 1000) { ElMessage.warning('最多 1000 行数据'); return }
  if (applyColumns()) rows.value.push(Object.fromEntries(columns.value.map(column => [column, ''])))
}
const removeRow = index => rows.value.splice(index, 1)
const flush = async () => {
  if (saving.value) return false
  if (!dirty.value) return true
  if (!applyColumns()) return false
  if (enabled.value && !rows.value.length) { ElMessage.warning('请至少配置一行测试数据'); return false }
  saving.value = true
  try {
    const submitted = snapshot()
    const { data } = await updateTestCase(props.caseId, { data_driven_enabled: enabled.value, data_rows: rows.value })
    savedSnapshot.value = submitted
    emit('saved', data)
    ElMessage.success('测试数据已保存')
    return true
  } catch (error) {
    const details = error.response?.data
    ElMessage.error(details ? Object.values(details).flat().join('；') : '保存测试数据失败')
    return false
  } finally { saving.value = false }
}
const importFile = async event => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (file.size > 10 * 1024 * 1024) { ElMessage.warning('数据文件不能超过 10 MB'); return }
  try {
    await importBuffer(await file.arrayBuffer())
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error.message || '导入失败') }
}
const importBuffer = async buffer => {
    const XLSX = await import('xlsx')
    const book = XLSX.read(buffer, { type: 'array', raw: true })
    const matrix = XLSX.utils.sheet_to_json(book.Sheets[book.SheetNames[0]], { header: 1, defval: '', raw: false, blankrows: false })
    const data = parseDataMatrix(matrix)
    if (rows.value.length) await ElMessageBox.confirm('导入将替换当前测试数据，是否继续？', '导入测试数据', { type: 'warning' })
    columns.value = data.columns
    columnText.value = data.columns.join(',')
    rows.value = data.rows
    enabled.value = true
    ElMessage.success(`已导入 ${rows.value.length} 行，请保存测试数据`)
}
const exportCsv = () => {
  const url = URL.createObjectURL(new Blob(['\ufeff' + dataToCsv(columns.value, rows.value)], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url; link.download = 'test-data.csv'; link.click(); URL.revokeObjectURL(url)
}
defineExpose({ flush, dirty })
</script>
<style scoped>
.data-driven-editor {
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--th-border);
  border-radius: 10px;
}
.data-collapse-title {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 14px;
}
.data-collapse-title__text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.data-collapse-title__text strong { color: var(--th-text); font-size: 13px; line-height: 1.5; }
.data-collapse-title__text span { overflow: hidden; color: var(--th-text-secondary); font-size: 12px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.data-collapse-title__status { display: flex; flex: none; gap: 6px; }
.data-driven-content { padding: 14px; border-top: 1px solid var(--th-border); background: #fff; }
.data-enable-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid var(--th-border);
  border-radius: 8px;
  background: var(--th-surface-subtle);
}
.data-enable-card.is-enabled { border-color: var(--el-color-primary-light-7); background: var(--el-color-primary-light-9); }
.data-enable-card__copy { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.data-enable-card__copy strong { color: var(--th-text); font-size: 13px; }
.data-enable-card__copy span { color: var(--th-text-secondary); font-size: 12px; line-height: 1.5; }
.data-enable-card__actions { display: flex; flex: none; align-items: center; gap: 12px; }
.data-config-step { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 12px; margin-top: 16px; }
.data-config-step__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: var(--th-primary);
  background: var(--th-primary-soft);
  font-size: 12px;
  font-weight: 700;
}
.data-config-step__body { min-width: 0; }
.data-config-step__heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.data-config-step__heading > div { display: flex; flex-direction: column; gap: 2px; }
.data-config-step__heading strong { color: var(--th-text); font-size: 13px; }
.data-config-step__heading span { color: var(--th-text-secondary); font-size: 12px; line-height: 1.5; }
.column-editor { display: flex; align-items: center; gap: 8px; }
.column-editor .el-input { max-width: 620px; }
.data-source-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.data-source-bar__label { margin-right: 2px; color: var(--th-text-secondary); font-size: 12px; }
.data-source-bar .el-select { width: 220px; }
.data-tip { margin: 8px 0 0; color: var(--th-text-secondary); font-size: 12px; line-height: 1.5; }
.binding-list { display: flex; flex-wrap: wrap; gap: 8px; }
.binding-warning { margin: 10px 0 0; color: var(--el-color-warning-dark-2); font-size: 12px; line-height: 1.5; }
.data-disabled-hint { padding: 12px 4px 2px; color: var(--th-text-secondary); font-size: 12px; line-height: 1.6; }
:deep(.data-action-column .cell) { overflow: visible; white-space: nowrap; }
.delete-row-button { padding: 5px 8px; }
@media (max-width: 760px) {
  .data-enable-card { align-items: flex-start; flex-direction: column; }
  .data-enable-card__actions { width: 100%; justify-content: space-between; }
  .column-editor { align-items: stretch; flex-direction: column; }
  .column-editor .el-input,
  .data-source-bar .el-select { width: 100%; max-width: none; }
}
</style>
