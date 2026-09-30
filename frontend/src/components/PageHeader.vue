<template>
  <header class="page-header">
    <h1 class="page-title">{{ title }}</h1>
    <div v-if="$slots.default" class="page-header-actions"><slot /></div>
  </header>
</template>

<script setup>
defineProps({ title: { type: String, required: true } })
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.page-title { margin: 0; color: var(--th-text); font-size: 24px; line-height: 1.3; font-weight: 650; }
.page-header-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.page-header-actions :deep(.el-button + .el-button) { margin-left: 0; }
@media (max-width: 768px) {
  .page-title { font-size: 21px; }
  .page-header-actions { width: 100%; }
}
</style>
