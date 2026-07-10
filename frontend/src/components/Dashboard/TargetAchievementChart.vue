<template>
  <div
    v-if="donutConfig"
    class="h-72 w-full rounded-md bg-surface-white shadow overflow-hidden"
  >
    <DonutChart :config="donutConfig" />
  </div>
</template>

<script setup>
import { createResource, DonutChart } from 'frappe-ui'
import { computed, watch } from 'vue'

const props = defineProps({
  employee: { type: String, default: null },
})

const target = createResource({
  url: 'crm.api.revenue_target.get_current_target',
  makeParams() {
    return { employee: props.employee || undefined }
  },
  auto: true,
})

watch(
  () => props.employee,
  () => target.reload(),
)

const periodLabel = computed(() => {
  if (!target.data) return ''
  if (target.data.target_type === 'Monthly') return `${target.data.month} ${target.data.year}`
  if (target.data.target_type === 'Quarterly') return `${target.data.quarter} ${target.data.year}`
  return `${target.data.year}`
})

const donutConfig = computed(() => {
  if (!target.data) return null
  const achieved = target.data.achieved_revenue || 0
  const remaining = Math.max(target.data.remaining_revenue || 0, 0)
  if (!achieved && !remaining) return null
  return {
    data: [
      { label: __('Achieved'), value: achieved },
      { label: __('Remaining'), value: remaining },
    ],
    title: __('Target Achievement'),
    subtitle: periodLabel.value,
    categoryColumn: 'label',
    valueColumn: 'value',
    colors: ['green', 'gray'],
  }
})
</script>
