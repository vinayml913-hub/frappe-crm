<template>
  <div class="flex flex-col h-full overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="[{ label: __('Reports') }]" />
      </template>
      <template #right-header>
        <Button :label="__('Refresh')" :iconLeft="LucideRefreshCcw" @click="refreshActiveTab" />
        <ExportButtons
          v-if="activeTabLabel === 'Deal Reports'"
          :fromDate="fromDate"
          :toDate="toDate"
          :userId="filters.user"
          source="leaderboard"
        />
      </template>
    </LayoutHeader>

    <SharedFilterBar
      :filters="filters"
      :preset="preset"
      @update:preset="onPresetChange"
      @update:customRange="onCustomRange"
      @update:user="onUserChange"
    />

    <Tabs v-model="tabIndex" as="div" :tabs="tabs" class="flex-1 overflow-hidden flex flex-col">
      <template #tab-panel="{ tab }">
        <div class="flex-1 overflow-y-auto p-5 pt-3">
          <DealReportsTab
            v-if="tab.label === 'Deal Reports'"
            ref="dealReportsRef"
            :fromDate="fromDate"
            :toDate="toDate"
            :quickRange="quickRange"
            :userId="filters.user"
          />
          <RevenueTab
            v-else-if="tab.label === 'Revenue Analytics'"
            ref="revenueTabRef"
            :fromDate="fromDate"
            :toDate="toDate"
            :userId="filters.user"
          />
        </div>
      </template>
    </Tabs>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import SharedFilterBar from '@/components/Reports/SharedFilterBar.vue'
import ExportButtons from '@/components/Reports/ExportButtons.vue'
import DealReportsTab from '@/components/Reports/DealReportsTab.vue'
import RevenueTab from '@/components/Reports/RevenueTab.vue'
import { Breadcrumbs, Button, Tabs } from 'frappe-ui'
import LucideRefreshCcw from '~icons/lucide/refresh-ccw'
import { ref, reactive, computed } from 'vue'

const tabs = [{ label: 'Deal Reports' }, { label: 'Revenue Analytics' }]
const tabIndex = ref(0)
const activeTabLabel = computed(() => tabs[tabIndex.value]?.label)

const dealReportsRef = ref(null)
const revenueTabRef = ref(null)

// ── Shared filter state (date range + employee) — drives BOTH tabs ─────
const preset = ref('last_30_days')
const filters = reactive({
  user: null,
  customFrom: null,
  customTo: null,
})

// Resolve the active preset into concrete ISO dates here, once, so both
// DealReportsTab (which also understands quickRange server-side) and
// RevenueTab (whose API has no quickRange concept — it only takes
// explicit dates) always render the exact same period.
const QUICK_RANGE_DAYS = {
  last_7_days: 7,
  last_30_days: 30,
  last_60_days: 60,
  last_90_days: 90,
  last_180_days: 180,
  last_360_days: 360,
}

function isoDate(d) {
  return d.toISOString().slice(0, 10)
}

const resolvedRange = computed(() => {
  const today = new Date()

  if (preset.value === 'custom') {
    return { from: filters.customFrom || null, to: filters.customTo || isoDate(today) }
  }
  if (preset.value === 'ever') {
    return { from: null, to: isoDate(today) }
  }
  const days = QUICK_RANGE_DAYS[preset.value] ?? 30
  const from = new Date(today)
  from.setDate(today.getDate() - days)
  return { from: isoDate(from), to: isoDate(today) }
})

const fromDate = computed(() => resolvedRange.value.from)
const toDate = computed(() => resolvedRange.value.to)
// Still forwarded to DealReportsTab so its backend can use the exact same
// "Ever" semantics as get_dashboard_kpis's own quickRange resolution when
// no explicit from_date is supplied (kept for parity/back-compat with
// crm/api/reports.py's _default_date_range signature).
const quickRange = computed(() => (preset.value === 'custom' ? null : preset.value))

function onPresetChange(value) {
  preset.value = value
  refreshActiveTab()
}

function onCustomRange({ from, to }) {
  preset.value = 'custom'
  filters.customFrom = from
  filters.customTo = to
  refreshActiveTab()
}

function onUserChange(userId) {
  filters.user = userId
  refreshActiveTab()
}

function refreshActiveTab() {
  if (activeTabLabel.value === 'Deal Reports') dealReportsRef.value?.refresh?.()
  else revenueTabRef.value?.refresh?.()
}
</script>
