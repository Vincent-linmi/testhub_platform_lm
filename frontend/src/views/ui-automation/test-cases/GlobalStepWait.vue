<template>
  <div class="global-step-wait" :class="{ 'is-enabled': enabled }">
    <div class="global-step-wait__control">
      <el-icon><Timer /></el-icon>
      <span class="global-step-wait__title">{{ t('uiAutomation.testCase.globalWaitTitle') }}</span>
      <el-switch
        :model-value="enabled"
        :aria-label="t('uiAutomation.testCase.globalWaitTitle')"
        :loading="saving"
        :disabled="busy || saving"
        @change="toggle"
      />
      <span class="global-step-wait__state">{{ t(`uiAutomation.testCase.${enabled ? 'globalWaitOn' : 'globalWaitOff'}`) }}</span>
    </div>
    <div v-if="enabled" class="global-step-wait__interval">
      <span>{{ t('uiAutomation.testCase.globalWaitInterval') }}</span>
      <el-input-number
        :model-value="seconds"
        :min="0.1"
        :max="60"
        :step="0.1"
        :precision="1"
        controls-position="right"
        size="small"
        :aria-label="t('uiAutomation.testCase.globalWaitInterval')"
        :disabled="busy || saving"
        @update:model-value="changeTime"
      />
      <span>{{ t('uiAutomation.testCase.globalWaitSeconds') }}</span>
    </div>
    <span class="global-step-wait__hint">{{ t(`uiAutomation.testCase.${enabled ? 'globalWaitTip' : 'globalWaitDisabledTip'}`) }}</span>
    <span v-if="saving || pending || saveFailed" class="global-step-wait__status" :class="{ 'is-error': saveFailed }" role="status">
      {{ t(`uiAutomation.testCase.${saving ? 'globalWaitSaving' : saveFailed ? 'globalWaitSaveFailed' : pending ? 'globalWaitPending' : 'globalWaitSaved'}`) }}
    </span>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { Timer } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { updateTestCase } from '@/api/ui_automation'

const props = defineProps({
  caseId: { type: Number, required: true },
  initialEnabled: { type: Boolean, default: false },
  initialTime: { type: Number, default: 1000 },
  onPersisted: { type: Function, required: true },
  busy: { type: Boolean, default: false }
})
const { t } = useI18n()
// Each keyed instance owns one case, including requests that finish after a selection change.
const caseId = props.caseId
const onPersisted = props.onPersisted
const enabled = ref(props.initialEnabled)
const seconds = ref(props.initialTime / 1000)
const saving = ref(false)
const pending = ref(false)
const saveFailed = ref(false)
let saved = { global_wait_enabled: enabled.value, global_wait_time: props.initialTime }
let timer
let inFlight

const flush = async () => {
  clearTimeout(timer)
  if (inFlight) return inFlight
  if (!pending.value) return true

  const payload = {
    global_wait_enabled: enabled.value,
    global_wait_time: Math.round(seconds.value * 1000)
  }
  if (payload.global_wait_enabled === saved.global_wait_enabled && payload.global_wait_time === saved.global_wait_time) {
    pending.value = false
    saveFailed.value = false
    return true
  }

  saving.value = true
  saveFailed.value = false
  inFlight = (async () => {
    try {
      await updateTestCase(caseId, payload)
      saved = payload
      // Vue drops emits from unmounted instances; this callback also updates an old case.
      onPersisted({ caseId, ...payload })
      return true
    } catch (error) {
      enabled.value = saved.global_wait_enabled
      seconds.value = saved.global_wait_time / 1000
      saveFailed.value = true
      return false
    } finally {
      pending.value = false
      saving.value = false
      inFlight = undefined
    }
  })()
  return inFlight
}

const toggle = value => {
  enabled.value = value
  pending.value = true
  void flush()
}

const changeTime = value => {
  // Clearing the numeric field restores the last valid value instead of sending null.
  if (!Number.isFinite(value)) return
  seconds.value = Math.min(60, Math.max(0.1, value))
  pending.value = true
  saveFailed.value = false
  clearTimeout(timer)
  timer = setTimeout(flush, 400)
}

onBeforeUnmount(() => { void flush() })
defineExpose({ flush })
</script>

<style scoped>
.global-step-wait {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 18px;
  padding: 12px 14px;
  margin-bottom: 14px;
  border: 1px solid var(--th-border);
  border-radius: 10px;
  background: var(--th-surface-subtle);
  font-size: 12px;
  color: var(--th-text-secondary);
}
.global-step-wait.is-enabled {
  border-color: var(--el-color-primary-light-7);
  background: var(--el-color-primary-light-9);
}
.global-step-wait__control,
.global-step-wait__interval {
  display: flex;
  align-items: center;
  gap: 8px;
}
.global-step-wait__title { color: var(--th-text); font-weight: 600; }
.global-step-wait__state { color: var(--th-text-secondary); font-weight: 500; }
.global-step-wait__control > .el-icon { color: var(--el-color-primary); font-size: 16px; }
.global-step-wait__interval :deep(.el-input-number) { width: 100px; }
.global-step-wait__hint { flex: 1 1 240px; color: var(--el-text-color-secondary); line-height: 1.5; }
.global-step-wait__status { color: var(--th-text-secondary); font-size: 11px; }
.global-step-wait__status.is-error { color: var(--el-color-danger); }
</style>
