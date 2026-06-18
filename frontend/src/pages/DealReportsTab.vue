<template>
  <div class="space-y-6">
    <!-- ── KPI Cards ──────────────────────────────────────────────────── -->
    <div v-if="dashboard.loading && !dashboard.data" class="text-sm text-ink-gray-5 py-10 text-center">
      {{ __('Loading dashboard…') }}
    </div>
    <div v-else-if="dashboard.error" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-4 py-3">
      {{ __('Failed to load dashboard data. Please try refreshing.') }}
    </div>
    <div v-else class="grid grid-cols-4 gap-4">
      <KpiCard :label="__('Total Deals')" :value="cards.total_deals ?? 0" accent="blue" />
      <KpiCard :label="__('Won Deals')" :value="cards.won_deals ?? 0" accent="green" />
      <KpiCard :label="__('Lost Deals')" :value="cards.lost_deals ?? 0" accent="red" />
      <KpiCard :label="__('Open Deals')" :value="cards.open_deals ?? 0" accent="gray" />
      <KpiCard :label="__('Total Target')" :value="fmt(cards.total_target)" accent="purple" />
      <KpiCard :label="__('Achieved Target')" :value="fmt(cards.achieved_target)" accent="cyan" />
      <KpiCard
        :label="__('Achievement %')"
        :value="cards.achievement_pct != null ? cards.achievement_pct.toFixed(1) + '%' : '—'"
        accent="amber"
      />
      <KpiCard :label="__('Revenue Generated')" :value="fmt(cards.revenue_generated)" accent="teal" />
    </div>

    <!-- ── Charts ─────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-2 gap-5">
      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Deal Status Distribution') }}</p>
        <DonutChart v-if="dealStatus.data?.donut_chart?.data?.length" :config="dealStatus.data.donut_chart" />
        <EmptyState v-else :loading="dealStatus.loading" :error="dealStatus.error" />
      </div>

      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Deal Performance %') }}</p>
        <!-- frappe-ui has no separate "pie" component; DonutChart with the
             same category/value config renders the same percentage-of-whole
             data — reusing the donut chart data here avoids a duplicate
             query for what is visually a thin-vs-thick ring distinction. -->
        <DonutChart v-if="dealStatus.data?.donut_chart?.data?.length" :config="performanceChartConfig" />
        <EmptyState v-else :loading="dealStatus.loading" :error="dealStatus.error" />
      </div>

      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Monthly Deal Trends') }}</p>
        <AxisChart v-if="trends.data?.chart?.data?.length" :config="trends.data.chart" />
        <EmptyState v-else :loading="trends.loading" :error="trends.error" />
      </div>

      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Target vs Achievement') }}</p>
        <AxisChart v-if="targetAchievement.data?.chart?.data?.length" :config="targetAchievement.data.chart" />
        <EmptyState v-else :loading="targetAchievement.loading" :error="targetAchievement.error" />
      </div>
    </div>

    <!-- ── Leaderboard ────────────────────────────────────────────────── -->
    <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 overflow-hidden">
      <div class="px-4 py-3 border-b border-outline-gray-1 flex items-center justify-between">
        <p class="text-sm font-semibold text-ink-gray-8">{{ __('Leaderboard') }}</p>
        <span class="text-xs text-ink-gray-5">{{ __('Sorted by achievement %') }}</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[900px]">
          <thead class="bg-surface-gray-1 border-b border-outline-gray-1">
            <tr>
              <th class="text-left px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Rank') }}</th>
              <th class="text-left px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Employee') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Total') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Won') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Lost') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Open') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Target') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Achieved') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Achievement %') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Revenue') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-gray-1">
            <tr v-if="leaderboard.error">
              <td colspan="10" class="text-center py-8 text-ink-red-3">{{ __('Failed to load leaderboard') }}</td>
            </tr>
            <tr v-else-if="!leaderboard.data?.data?.length">
              <td colspan="10" class="text-center py-8 text-ink-gray-4">
                {{ leaderboard.loading ? __('Loading…') : __('No deals in this period') }}
              </td>
            </tr>
            <tr v-for="row in leaderboard.data?.data || []" :key="row.user" class="hover:bg-surface-gray-1">
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold"
                  :class="row.rank === 1 ? 'bg-surface-amber-1 text-ink-amber-3' : 'bg-surface-gray-2 text-ink-gray-6'"
                >{{ row.rank }}</span>
              </td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-2">
                  <UserAvatar :user="row.user" size="sm" />
                  <span class="text-ink-gray-8">{{ row.employee_name }}</span>
                </div>
              </td>
              <td class="px-4 py-2.5 text-right text-ink-gray-7">{{ row.total_deals }}</td>
              <td class="px-4 py-2.5 text-right text-ink-green-3">{{ row.won_deals }}</td>
              <td class="px-4 py-2.5 text-right text-ink-red-3">{{ row.lost_deals }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-6">{{ row.open_deals }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-7">{{ fmt(row.target_amount) }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-7">{{ fmt(row.achieved_amount) }}</td>
              <td class="px-4 py-2.5 text-right">
                <span v-if="row.achievement_pct == null" class="text-ink-gray-4">—</span>
                <span v-else :class="row.achievement_pct >= 100 ? 'text-ink-green-3 font-medium' : 'text-ink-gray-7'">
                  {{ row.achievement_pct.toFixed(1) }}%
                </span>
              </td>
              <td class="px-4 py-2.5 text-right font-medium text-ink-gray-9">{{ fmt(row.revenue) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import { AxisChart, DonutChart, createResource } from 'frappe-ui'
import { computed, h } from 'vue'

const props = defineProps({
  fromDate: { type: String, default: null },
  toDate: { type: String, default: null },
  quickRange: { type: String, default: null },
  userId: { type: String, default: null },
})

const KpiCard = {
  props: ['label', 'value', 'accent'],
  setup(p) {
    return () =>
      h('div', { class: 'rounded-md bg-surface-white shadow border border-outline-gray-1 p-4' }, [
        h('p', { class: 'text-xs font-medium text-ink-gray-5 mb-1.5' }, p.label),
        h('p', { class: 'text-xl font-semibold text-ink-gray-9' }, String(p.value ?? '—')),
      ])
  },
}

const EmptyState = {
  props: ['loading', 'error'],
  setup(p) {
    return () =>
      h('div', { class: 'h-full flex items-center justify-center text-sm text-ink-gray-4' },
        p.error ? __('Failed to load') : p.loading ? __('Loading chart…') : __('No data for this period'))
  },
}

function commonParams() {
  return {
    fromDate: props.fromDate,
    toDate: props.toDate,
    quickRange: props.quickRange,
    userId: props.userId,
  }
}

const dashboard = createResource({
  url: 'crm.api.reports.get_dashboard_kpis',
  makeParams: commonParams,
  auto: true,
})

const dealStatus = createResource({
  url: 'crm.api.reports.get_deal_status',
  makeParams: commonParams,
  auto: true,
})

const trends = createResource({
  url: 'crm.api.reports.get_monthly_trends',
  makeParams: commonParams,
  auto: true,
})

const targetAchievement = createResource({
  url: 'crm.api.reports.get_target_achievement',
  makeParams: commonParams,
  auto: true,
})

const leaderboard = createResource({
  url: 'crm.api.reports.get_leaderboard',
  makeParams: commonParams,
  auto: true,
})

const cards = computed(() => dashboard.data?.cards || {})

// Same underlying status counts as the donut, just framed as "performance %"
// — avoids issuing a duplicate backend query for a different chart shape.
const performanceChartConfig = computed(() => {
  const data = dealStatus.data?.donut_chart?.data || []
  return {
    data,
    title: __('Deal Performance %'),
    categoryColumn: 'status',
    valueColumn: 'count',
  }
})

function fmt(v) {
  if (v == null || v === '') return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}

function refresh() {
  dashboard.reload()
  dealStatus.reload()
  trends.reload()
  targetAchievement.reload()
  leaderboard.reload()
}

defineExpose({ refresh })
</script>
