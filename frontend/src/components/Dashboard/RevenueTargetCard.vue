<template>
  <div
    class="mx-5 mb-4 rounded-[24px] border border-outline-gray-1 bg-white p-6 shadow-[0_2px_8px_rgba(16,24,40,0.04)] transition-shadow duration-300 hover:shadow-[0_8px_24px_rgba(16,24,40,0.08)]"
  >
    <div class="flex items-start justify-between mb-6">
      <div class="flex items-center gap-2.5">
        <span
          class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-100 to-purple-100"
        >
          <LucideTarget class="size-4 text-blue-600" />
        </span>
        <div>
          <p class="text-base font-semibold text-ink-gray-9 leading-tight">{{ __('Revenue Target') }}</p>
          <p v-if="target.data" class="text-xs text-ink-gray-5 mt-0.5">
            {{ __(target.data.target_type) }} · {{ periodLabel }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span
          v-if="target.data"
          class="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-transform duration-200 hover:scale-105"
          :class="statusBadgeClass(target.data.status)"
        >
          <span>{{ statusEmoji(target.data.status) }}</span>
          {{ statusLabel(target.data.status) }}
        </span>
        <Button
          v-if="isAdmin()"
          variant="outline"
          :label="__('Set Target')"
          iconLeft="plus"
          @click="showTargetModal = true"
        />
      </div>
    </div>

    <div v-if="target.loading" class="flex items-center gap-2 text-sm text-ink-gray-4 py-6">
      <LoadingIndicator class="size-4" />
      {{ __('Loading...') }}
    </div>

    <div v-else-if="target.error" class="text-sm text-ink-red-3 py-6">
      {{ __('Could not load revenue target') }}: {{ target.error.messages?.[0] || target.error.message }}
    </div>

    <template v-else>
      <div v-if="target.data" class="flex flex-col sm:flex-row items-center sm:items-start gap-6">
        <!-- Animated circular progress -->
        <div class="shrink-0 relative h-[120px] w-[120px]">
          <svg viewBox="0 0 120 120" class="h-[120px] w-[120px] -rotate-90">
            <defs>
              <linearGradient :id="gradientId" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#2563eb" />
                <stop offset="55%" stop-color="#06b6d4" />
                <stop offset="100%" stop-color="#8b5cf6" />
              </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--surface-gray-2, #eef1f5)" stroke-width="10" />
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              :stroke="`url(#${gradientId})`"
              stroke-width="10"
              stroke-linecap="round"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="dashOffset"
              class="transition-[stroke-dashoffset] duration-1000 ease-out"
            />
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-2xl font-bold text-ink-gray-9 tabular-nums">
              {{ Math.round(target.data.achievement_percentage) }}%
            </span>
            <span class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-4">{{ __('Target') }}</span>
          </div>
        </div>

        <!-- Figures + bar -->
        <div class="flex-1 w-full">
          <div class="grid grid-cols-3 gap-4 mb-5">
            <div>
              <p class="text-xs font-medium uppercase tracking-wide text-ink-gray-4 mb-1.5">{{ __('Target') }}</p>
              <p class="text-xl font-bold text-ink-gray-9 tabular-nums">{{ formatCurrency(target.data.target_amount) }}</p>
            </div>
            <div>
              <p class="text-xs font-medium uppercase tracking-wide text-ink-gray-4 mb-1.5">{{ __('Achieved') }}</p>
              <p class="text-xl font-bold text-emerald-600 tabular-nums">{{ formatCurrency(target.data.achieved_revenue) }}</p>
            </div>
            <div>
              <p class="text-xs font-medium uppercase tracking-wide text-ink-gray-4 mb-1.5">{{ __('Remaining') }}</p>
              <p class="text-xl font-bold text-ink-gray-8 tabular-nums">
                {{ formatCurrency(Math.max(target.data.remaining_revenue, 0)) }}
              </p>
            </div>
          </div>

          <div class="w-full h-2.5 rounded-full bg-surface-gray-2 overflow-hidden">
            <div
              class="h-full rounded-full bg-gradient-to-r from-blue-500 via-cyan-400 to-purple-500 transition-[width] duration-1000 ease-out"
              :style="{ width: Math.min(target.data.achievement_percentage, 100) + '%' }"
            />
          </div>
        </div>
      </div>

      <div v-if="!target.data" class="flex flex-col items-center justify-center text-center py-8 gap-1">
        <LucideTarget class="size-6 text-ink-gray-3 mb-1" />
        <p class="text-sm text-ink-gray-4">
          {{ isAdmin() ? __('No target set for this period.') : __('No revenue target has been set for you yet.') }}
        </p>
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
import { createResource, LoadingIndicator } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import LucideTarget from '~icons/lucide/target'

const props = defineProps({
  employee: { type: String, default: null },
  period: { type: String, default: 'last_30_days' },
})

const { isAdmin } = usersStore()
const showTargetModal = ref(false)

const target = createResource({
  url: 'crm.api.revenue_target.get_target_for_period',
  makeParams() {
    return { employee: props.employee || undefined, period: props.period }
  },
  auto: true,
})

// Refetch whenever the admin picks a different salesperson, or a different
// quarter/date preset, from the dashboard's filter bar.
watch(
  () => [props.employee, props.period],
  () => target.reload(),
)

const periodLabel = computed(() => {
  if (!target.data) return ''
  if (target.data.target_type === 'Monthly') return `${target.data.month} ${target.data.year}`
  if (target.data.target_type === 'Quarterly') return `${target.data.quarter} ${target.data.year}`
  if (target.data.target_type === 'Overall') return __('All Time')
  return `${target.data.year}`
})

// Unique per-instance gradient id so multiple cards on one page don't clash
const gradientId = `revenue-target-ring-${Math.random().toString(36).slice(2, 9)}`

const RADIUS = 52
const circumference = 2 * Math.PI * RADIUS

const dashOffset = computed(() => {
  const pct = Math.min(Math.max(target.data?.achievement_percentage || 0, 0), 100)
  return circumference * (1 - pct / 100)
})

function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value || 0)
}

// Same underlying `status` values as before (Completed / On Track /
// Behind Target) - only the presentation (emoji, label, colors) changes.
function statusEmoji(status) {
  return {
    Completed: '✅',
    'On Track': '🔥',
    'Behind Target': '⚠️',
  }[status] || '🎯'
}

function statusLabel(status) {
  return {
    Completed: __('Completed'),
    'On Track': __('On Pace'),
    'Behind Target': __('Behind Target'),
  }[status] || __(status)
}

function statusBadgeClass(status) {
  return {
    'bg-emerald-50 text-emerald-600': status === 'Completed',
    'bg-amber-50 text-amber-600': status === 'On Track',
    'bg-red-50 text-red-600': status === 'Behind Target',
  }
}
</script>
