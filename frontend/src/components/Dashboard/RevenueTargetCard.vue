<template>
<div class="mx-5 mb-4 rounded-lg border border-outline-gray-2 bg-surface-white p-5">
<div class="flex items-center justify-between mb-4">
<div>
<p class="text-base font-semibold text-ink-gray-9">{{ __('Revenue Target') }}</p>
<p v-if="target.data" class="text-sm text-ink-gray-5">

          {{ target.data.target_type }} {{ __('Target') }} · {{ periodLabel }}
</p>
<p class="text-xs text-ink-orange-4 mt-1">

          DEBUG · prop employee: "{{ props.employee || '(empty)' }}" · backend returned employee: "{{ target.data?.employee || '(none)' }}" · loading: {{ target.loading }}
</p>
</div>
<Button

        v-if="isAdmin()"

        variant="outline"

        :label="__('Set Target')"

        iconLeft="plus"

        @click="showTargetModal = true"

      />
</div>
 
    <div v-if="target.loading" class="text-sm text-ink-gray-4 py-2">

      {{ __('Loading...') }}
</div>
 
    <div v-else-if="target.error" class="text-sm text-ink-red-3 py-2">

      {{ __('Could not load revenue target') }}: {{ target.error.messages?.[0] || target.error.message }}
</div>
 
    <template v-else>
<div v-if="target.data" class="grid grid-cols-3 gap-4 mb-4">
<div>
<p class="text-xs text-ink-gray-5 mb-1">{{ __('Target') }}</p>
<p class="text-lg font-semibold text-ink-gray-9">{{ formatCurrency(target.data.target_amount) }}</p>
</div>
<div>
<p class="text-xs text-ink-gray-5 mb-1">{{ __('Achieved') }}</p>
<p class="text-lg font-semibold text-ink-green-3">{{ formatCurrency(target.data.achieved_revenue) }}</p>
</div>
<div>
<p class="text-xs text-ink-gray-5 mb-1">{{ __('Remaining') }}</p>
<p class="text-lg font-semibold text-ink-gray-8">{{ formatCurrency(Math.max(target.data.remaining_revenue, 0)) }}</p>
</div>
</div>
 
      <div v-if="target.data">
<div class="flex items-center justify-between mb-1.5">
<span class="text-sm font-medium text-ink-gray-7">{{ target.data.achievement_percentage }}%</span>
<span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="statusClass(target.data.status)">

            {{ __(target.data.status) }}
</span>
</div>
<div class="w-full h-2 rounded-full bg-surface-gray-2 overflow-hidden">
<div

            class="h-full rounded-full transition-all"

            :class="progressBarClass(target.data.status)"

            :style="{ width: Math.min(target.data.achievement_percentage, 100) + '%' }"

          />
</div>
</div>
 
      <div v-if="donutConfig" class="h-52 mt-4">
<DonutChart :config="donutConfig" />
</div>
 
      <div v-if="!target.data" class="text-sm text-ink-gray-4 py-2">

        {{ isAdmin() ? __('No target set for this period.') : __('No revenue target has been set for you yet.') }}
</div>
</template>
</div>
 
  <SetTargetModal

    v-if="showTargetModal"

    v-model="showTargetModal"

    @updated="target.reload()"

  />
</template>
 
<script setup>

import SetTargetModal from '@/components/Dashboard/SetTargetModal.vue'

import { usersStore } from '@/stores/users'

import { createResource, DonutChart } from 'frappe-ui'

import { ref, computed, watch } from 'vue'
 
const props = defineProps({

  employee: { type: String, default: null },

})
 
const { isAdmin } = usersStore()

const showTargetModal = ref(false)
 
const target = createResource({

  url: 'crm.api.revenue_target.get_current_target',

  makeParams() {

    return { employee: props.employee || undefined }

  },

  auto: true,

})
 
// Refetch whenever the admin picks a different salesperson from the

// dashboard's "Sales User" dropdown (Dashboard.vue passes it in as the

// `employee` prop).

watch(

  () => props.employee,

  () => target.reload(),

)
 
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
 
const periodLabel = computed(() => {

  if (!target.data) return ''

  if (target.data.target_type === 'Monthly') return `${target.data.month} ${target.data.year}`

  if (target.data.target_type === 'Quarterly') return `${target.data.quarter} ${target.data.year}`

  return `${target.data.year}`

})
 
function formatCurrency(value) {

  return new Intl.NumberFormat('en-IN', {

    style: 'currency',

    currency: 'INR',

    maximumFractionDigits: 0,

  }).format(value || 0)

}
 
function statusClass(status) {

  return {

    'bg-surface-green-1 text-ink-green-3': status === 'Completed',

    'bg-surface-blue-1 text-ink-blue-3': status === 'On Track',

    'bg-surface-red-1 text-ink-red-3': status === 'Behind Target',

  }

}
 
function progressBarClass(status) {

  return {

    'bg-surface-green-6': status === 'Completed',

    'bg-surface-blue-6': status === 'On Track',

    'bg-surface-red-6': status === 'Behind Target',

  }

}
</script>
 
