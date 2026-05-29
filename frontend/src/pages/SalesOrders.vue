<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Sales Orders') }]" />
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center mt-20">
      <div class="text-ink-gray-5 text-base">{{ __('Loading...') }}</div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="salesOrders.length === 0"
      class="flex flex-col items-center justify-center mt-20 gap-3"
    >
      <SalesOrderIcon class="h-12 w-12 text-ink-gray-3" />
      <p class="text-ink-gray-5 text-base">
        {{ __('No Sales Orders yet. Win a deal to create one!') }}
      </p>
    </div>

    <!-- Orders list -->
    <div v-else class="space-y-3 max-w-4xl">
      <div
        v-for="order in salesOrders"
        :key="order.name"
        class="border border-outline-gray-2 rounded-lg p-4 hover:bg-surface-gray-2 cursor-pointer transition-colors"
      >
        <div class="flex justify-between items-start">
          <div class="flex flex-col gap-1">
            <p class="font-semibold text-ink-blue-3 text-base">{{ order.name }}</p>
            <p class="text-sm text-ink-gray-6">{{ order.organization || '—' }}</p>
            <p v-if="order.delivery_date" class="text-xs text-ink-gray-5">
              {{ __('Delivery: {0}', [formatDate(order.delivery_date)]) }}
            </p>
          </div>
          <span
            class="px-2.5 py-1 text-xs font-medium rounded-full"
            :class="{
              'bg-surface-green-1 text-ink-green-3': order.status === 'Open',
              'bg-surface-blue-1 text-ink-blue-3': order.status === 'In Progress',
              'bg-surface-purple-1 text-ink-purple-3': order.status === 'Delivered',
              'bg-surface-gray-2 text-ink-gray-6': order.status === 'Closed' || !order.status,
            }"
          >
            {{ order.status || 'Open' }}
          </span>
        </div>

        <div class="mt-3 grid grid-cols-3 gap-3 text-sm border-t border-outline-gray-1 pt-3">
          <div>
            <p class="text-ink-gray-5 text-xs mb-0.5">{{ __('Amount') }}</p>
            <p class="font-medium text-ink-gray-9">{{ formatCurrency(order.amount) }}</p>
          </div>
          <div>
            <p class="text-ink-gray-5 text-xs mb-0.5">{{ __('Gross Profit') }}</p>
            <p class="font-medium text-ink-gray-9">{{ formatCurrency(order.gross_profit) }}</p>
          </div>
          <div>
            <p class="text-ink-gray-5 text-xs mb-0.5">{{ __('GP %') }}</p>
            <p class="font-medium text-ink-gray-9">
              {{ order.gross_profit_percentage ? order.gross_profit_percentage.toFixed(1) + '%' : '—' }}
            </p>
          </div>
        </div>

        <div v-if="order.lab_required || order.training_required" class="mt-2 flex gap-2">
          <span v-if="order.lab_required" class="text-xs px-2 py-0.5 rounded bg-surface-orange-1 text-ink-orange-3">
            {{ __('Lab Required') }}
          </span>
          <span v-if="order.training_required" class="text-xs px-2 py-0.5 rounded bg-surface-blue-1 text-ink-blue-3">
            {{ __('Training Required') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import SalesOrderIcon from '@/components/Icons/SalesOrderIcon.vue'
import { formatDate } from '@/utils'
import { Breadcrumbs, call } from 'frappe-ui'
import { ref, onMounted } from 'vue'

const salesOrders = ref([])
const loading = ref(true)

function formatCurrency(value) {
  if (!value) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)
}

onMounted(async () => {
  try {
    const result = await call('crm.api.sales_order.get_sales_orders')
    salesOrders.value = result || []
  } catch (err) {
    console.error('Failed to fetch sales orders:', err)
    salesOrders.value = []
  } finally {
    loading.value = false
  }
})
</script>
