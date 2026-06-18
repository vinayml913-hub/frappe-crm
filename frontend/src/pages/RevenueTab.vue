<template>
  <div class="space-y-6">
    <div class="flex justify-end" v-if="isAdmin()">
      <Button :label="__('Manage Targets')" icon-left="target" @click="showTargetsModal = true" />
    </div>

    <!-- ── KPI Cards ──────────────────────────────────────────────── -->
    <div v-if="summary.loading && !summary.data" class="text-sm text-ink-gray-5 py-10 text-center">
      {{ __('Loading revenue summary…') }}
    </div>
    <div v-else-if="summary.error" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-4 py-3">
      {{ __('Failed to load revenue summary. Please try refreshing.') }}
    </div>

    <div v-else-if="isAdminView" class="grid grid-cols-4 gap-4">
      <KpiCard :label="__('Total Company Revenue')" :value="fmt(cards.total_company_revenue)" accent="blue" />
      <KpiCard :label="__('Revenue by All Employees')" :value="fmt(cards.total_revenue_generated_by_all_employees)" accent="purple" />
      <KpiCard :label="__('Monthly Revenue')" :value="fmt(cards.monthly_revenue)" accent="green" />
      <KpiCard :label="__('Quarterly Revenue')" :value="fmt(cards.quarterly_revenue)" accent="orange" />
      <KpiCard :label="__('Yearly Revenue')" :value="fmt(cards.yearly_revenue)" accent="cyan" />
      <KpiCard :label="__('Avg Revenue / Employee')" :value="fmt(cards.average_revenue_per_employee)" accent="gray" />
      <KpiCard
        :label="__('Top Revenue Employee')"
        :value="cards.top_revenue_generating_employee?.full_name || '—'"
        :subvalue="cards.top_revenue_generating_employee ? fmt(cards.top_revenue_generating_employee.revenue) : null"
        accent="amber"
      />
      <KpiCard :label="__('Won Deals (range)')" :value="cards.total_won_deals ?? 0" accent="teal" />
    </div>

    <div v-else class="grid grid-cols-4 gap-4">
      <KpiCard :label="__('My Revenue Generated')" :value="fmt(cards.my_revenue_generated)" accent="blue" />
      <KpiCard :label="__('My Won Deal Revenue')" :value="fmt(cards.my_won_deal_revenue)" :subvalue="`${cards.my_won_deal_count ?? 0} ${__('deals')}`" accent="green" />
      <KpiCard :label="__('My Monthly Revenue')" :value="fmt(cards.my_monthly_revenue)" accent="purple" />
      <KpiCard :label="__('My Quarterly Revenue')" :value="fmt(cards.my_quarterly_revenue)" accent="orange" />
      <KpiCard :label="__('My Yearly Revenue')" :value="fmt(cards.my_yearly_revenue)" accent="cyan" />
    </div>

    <!-- ── Charts ─────────────────────────────────────────────────── -->
    <div class="grid grid-cols-2 gap-5">
      <div v-if="isAdminView" class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Revenue by Employee') }}</p>
        <AxisChart v-if="byEmployee.data?.chart?.data?.length" :config="byEmployee.data.chart" />
        <EmptyChartState v-else :loading="byEmployee.loading" :error="byEmployee.error" />
      </div>

      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Monthly Revenue Trend') }}</p>
        <AxisChart v-if="trends.data?.chart?.data?.length" :config="trends.data.chart" />
        <EmptyChartState v-else :loading="trends.loading" :error="trends.error" />
      </div>

      <div v-if="isAdminView" class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Revenue Contribution') }}</p>
        <DonutChart v-if="contribution.data?.chart?.data?.length" :config="contribution.data.chart" />
        <EmptyChartState v-else :loading="contribution.loading" :error="contribution.error" />
      </div>

      <div class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4 h-80">
        <p class="text-sm font-semibold text-ink-gray-8 mb-2">{{ __('Revenue vs Target') }}</p>
        <AxisChart v-if="targetComparison.data?.chart?.data?.length" :config="targetComparison.data.chart" />
        <EmptyChartState v-else :loading="targetComparison.loading" :error="targetComparison.error" />
      </div>
    </div>

    <!-- ── Top Performers ─────────────────────────────────────────── -->
    <div v-if="isAdminView" class="rounded-md bg-surface-white shadow border border-outline-gray-1 overflow-hidden">
      <div class="px-4 py-3 border-b border-outline-gray-1 flex items-center justify-between">
        <p class="text-sm font-semibold text-ink-gray-8">{{ __('Top Performers') }}</p>
        <span class="text-xs text-ink-gray-5">{{ __('Sorted by revenue generated') }}</span>
      </div>
      <table class="w-full text-sm">
        <thead class="bg-surface-gray-1 border-b border-outline-gray-1">
          <tr>
            <th class="text-left px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Rank') }}</th>
            <th class="text-left px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Employee') }}</th>
            <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Revenue') }}</th>
            <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Won Deals') }}</th>
            <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Achievement %') }}</th>
            <th class="text-right px-4 py-2 text-xs font-medium text-ink-gray-5">{{ __('Contribution %') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-gray-1">
          <tr v-if="topPerformers.error">
            <td colspan="6" class="text-center py-8 text-ink-red-3">{{ __('Failed to load top performers') }}</td>
          </tr>
          <tr v-else-if="!topPerformers.data?.data?.length">
            <td colspan="6" class="text-center py-8 text-ink-gray-4">
              {{ topPerformers.loading ? __('Loading…') : __('No won deals in this period') }}
            </td>
          </tr>
          <tr v-for="row in topPerformers.data?.data || []" :key="row.user" class="hover:bg-surface-gray-1">
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
            <td class="px-4 py-2.5 text-right font-medium text-ink-gray-9">{{ fmt(row.revenue_generated) }}</td>
            <td class="px-4 py-2.5 text-right text-ink-gray-7">{{ row.won_deals }}</td>
            <td class="px-4 py-2.5 text-right">
              <span v-if="row.achievement_pct == null" class="text-ink-gray-4">—</span>
              <span v-else :class="row.achievement_pct >= 100 ? 'text-ink-green-3' : 'text-ink-gray-7'">
                {{ row.achievement_pct.toFixed(1) }}%
              </span>
            </td>
            <td class="px-4 py-2.5 text-right text-ink-gray-7">{{ row.revenue_contribution_pct.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Employee-only: own target/achievement strip -->
    <div v-else class="rounded-md bg-surface-white shadow border border-outline-gray-1 p-4">
      <p class="text-sm font-semibold text-ink-gray-8 mb-3">{{ __('My Target Achievement') }}</p>
      <div v-if="myTarget.loading" class="text-sm text-ink-gray-5">{{ __('Loading…') }}</div>
      <div v-else-if="!myTarget.row" class="text-sm text-ink-gray-4">{{ __('No target set for this period') }}</div>
      <div v-else class="flex items-center gap-4">
        <div class="flex-1">
          <div class="h-2 rounded-full bg-surface-gray-2 overflow-hidden">
            <div
              class="h-full bg-ink-blue-3 rounded-full transition-all"
              :style="{ width: Math.min(myTarget.row.achievement_pct || 0, 100) + '%' }"
            />
          </div>
        </div>
        <span class="text-sm font-semibold text-ink-gray-8 whitespace-nowrap">
          {{ fmt(myTarget.row.actual_revenue) }} / {{ fmt(myTarget.row.target_amount) }}
          ({{ (myTarget.row.achievement_pct || 0).toFixed(1) }}%)
        </span>
      </div>
    </div>
  </div>

  <!-- ── Manage Targets Modal (Admin) ────────────────────────────────── -->
  <Dialog v-model="showTargetsModal" :options="{ size: '2xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-5 flex items-center justify-between">
          <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Revenue Targets') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showTargetsModal = false" />
        </div>

        <div class="grid grid-cols-5 gap-3 items-end mb-5 pb-5 border-b border-outline-gray-1">
          <div class="col-span-2">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Employee') }}</label>
            <Link
              class="form-control"
              variant="outline"
              :value="newTarget.user && getUser(newTarget.user).full_name"
              doctype="User"
              :filters="{ name: ['in', users.data?.crmUsers?.map((u) => u.name) || []], ignore_user_type: 1 }"
              :placeholder="__('Select user')"
              @change="(v) => (newTarget.user = v)"
            />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Period') }}</label>
            <select v-model="newTarget.period_type" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
              <option>Monthly</option>
              <option>Quarterly</option>
              <option>Yearly</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Year') }}</label>
            <input v-model.number="newTarget.year" type="number" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
          </div>
          <div v-if="newTarget.period_type === 'Monthly'">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Month') }}</label>
            <select v-model="newTarget.month" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
              <option v-for="m in 12" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div v-else-if="newTarget.period_type === 'Quarterly'">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Quarter') }}</label>
            <select v-model="newTarget.quarter" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
              <option>Q1</option><option>Q2</option><option>Q3</option><option>Q4</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Target Amount (₹)') }}</label>
            <input v-model.number="newTarget.target_amount" type="number" min="0" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
          </div>
          <div>
            <Button variant="solid" :label="__('Save Target')" :loading="savingTarget" @click="saveTarget" />
          </div>
        </div>
        <p v-if="targetFormError" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-3 py-2 mb-4">{{ targetFormError }}</p>

        <div class="max-h-72 overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="bg-surface-gray-1 sticky top-0">
              <tr>
                <th class="text-left px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Employee') }}</th>
                <th class="text-left px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Period') }}</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Target') }}</th>
                <th class="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-gray-1">
              <tr v-for="t in existingTargets" :key="t.name">
                <td class="px-3 py-2">{{ getUser(t.user)?.full_name || t.user }}</td>
                <td class="px-3 py-2 text-ink-gray-6">{{ t.period_type }} · {{ t.period_label }}</td>
                <td class="px-3 py-2 text-right font-medium">{{ fmt(t.target_amount) }}</td>
                <td class="px-3 py-2 text-right">
                  <button class="text-ink-red-3 text-xs hover:underline" @click="deleteTarget(t.name)">{{ __('Delete') }}</button>
                </td>
              </tr>
              <tr v-if="!existingTargets.length">
                <td colspan="4" class="text-center py-6 text-ink-gray-4">{{ __('No targets set yet') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { Button, Dialog, AxisChart, DonutChart, createResource, call, toast } from 'frappe-ui'
import { ref, reactive, computed, onMounted, watch, h } from 'vue'

// This tab no longer owns date-range/employee filter state — both are
// passed down from Reports.vue's SharedFilterBar so Deal Reports and
// Revenue Analytics always show the exact same period side-by-side.
const props = defineProps({
  fromDate: { type: String, default: null },
  toDate: { type: String, default: null },
  userId: { type: String, default: null },
})

const { users, getUser, isAdmin } = usersStore()

const KpiCard = {
  props: ['label', 'value', 'subvalue', 'accent'],
  setup(p) {
    return () =>
      h('div', { class: 'rounded-md bg-surface-white shadow border border-outline-gray-1 p-4' }, [
        h('p', { class: 'text-xs font-medium text-ink-gray-5 mb-1.5' }, p.label),
        h('p', { class: 'text-xl font-semibold text-ink-gray-9' }, String(p.value ?? '—')),
        p.subvalue ? h('p', { class: 'text-xs text-ink-gray-5 mt-0.5' }, p.subvalue) : null,
      ])
  },
}

const EmptyChartState = {
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
    userId: props.userId,
  }
}

const summary = createResource({ url: 'crm.api.revenue.get_revenue_summary', makeParams: commonParams, auto: true })
const byEmployee = createResource({ url: 'crm.api.revenue.get_revenue_by_employee', makeParams: commonParams, auto: true })
const trends = createResource({ url: 'crm.api.revenue.get_revenue_trends', makeParams: commonParams, auto: true })
const contribution = createResource({ url: 'crm.api.revenue.get_revenue_contribution', makeParams: commonParams, auto: true })
const targetComparison = createResource({ url: 'crm.api.revenue.get_revenue_target_comparison', makeParams: commonParams, auto: true })
const topPerformers = createResource({
  url: 'crm.api.revenue.get_top_performers',
  makeParams() { return { ...commonParams(), limit: 10 } },
  auto: true,
})

const cards = computed(() => summary.data?.cards || {})
const isAdminView = computed(() => isAdmin() && summary.data?.scope === 'admin')

const myTarget = reactive({ loading: false, row: null })
function loadMyTarget() {
  if (isAdmin()) return
  myTarget.loading = true
  myTarget.row = (targetComparison.data?.data || [])[0] || null
  myTarget.loading = false
}
watch(() => targetComparison.data, () => loadMyTarget(), { deep: false })

function fmt(v) {
  if (v == null || v === '') return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}

function refresh() {
  summary.reload()
  byEmployee.reload()
  trends.reload()
  contribution.reload()
  targetComparison.reload()
  topPerformers.reload()
}
defineExpose({ refresh })

// ── Manage Targets modal (admin only — unchanged from original page) ───
const showTargetsModal = ref(false)
const savingTarget = ref(false)
const targetFormError = ref(null)
const existingTargets = ref([])

const newTarget = reactive({
  user: null,
  period_type: 'Monthly',
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  quarter: 'Q1',
  target_amount: 0,
})

async function loadExistingTargets() {
  try {
    existingTargets.value = await call('crm.api.revenue.get_revenue_targets') || []
  } catch (err) {
    existingTargets.value = []
  }
}

async function saveTarget() {
  targetFormError.value = null
  if (!newTarget.user) { targetFormError.value = __('Please select an employee'); return }
  if (!newTarget.target_amount || newTarget.target_amount <= 0) {
    targetFormError.value = __('Target amount must be greater than 0')
    return
  }
  savingTarget.value = true
  try {
    await call('crm.api.revenue.set_revenue_target', { data: JSON.stringify({ ...newTarget }) })
    toast.success(__('Target saved'))
    await loadExistingTargets()
    targetComparison.reload()
    topPerformers.reload()
  } catch (err) {
    targetFormError.value = err?.messages?.[0]?.message || err?.message || __('Failed to save target')
  } finally {
    savingTarget.value = false
  }
}

async function deleteTarget(name) {
  try {
    await call('crm.api.revenue.delete_revenue_target', { name })
    toast.success(__('Target deleted'))
    await loadExistingTargets()
    targetComparison.reload()
    topPerformers.reload()
  } catch (err) {
    toast.error(__('Failed to delete target'))
  }
}

onMounted(() => {
  if (isAdmin()) loadExistingTargets()
})
</script>
