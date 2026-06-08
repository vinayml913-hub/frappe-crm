<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Sales Orders') }]" />
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center mt-20">
      <div class="text-ink-gray-5 text-base">{{ __('Loading...') }}</div>
    </div>

    <!-- Empty -->
    <div v-else-if="salesOrders.length === 0" class="flex flex-col items-center justify-center mt-20 gap-3">
      <SalesOrderIcon class="h-12 w-12 text-ink-gray-3" />
      <p class="text-ink-gray-5 text-base font-medium">{{ __('No Sales Orders yet') }}</p>
      <p class="text-ink-gray-4 text-sm">{{ __('Sales Orders are created automatically when a Deal is marked as Won') }}</p>
    </div>

    <!-- Orders list -->
    <div v-else class="space-y-4 max-w-6xl">
      <div
        v-for="order in salesOrders"
        :key="order.name"
        class="border border-outline-gray-2 rounded-lg overflow-hidden bg-surface-white shadow-sm"
      >
        <!-- Order Header -->
        <div
          class="flex justify-between items-start p-4 cursor-pointer hover:bg-surface-gray-1 transition-colors"
          @click="toggleOrder(order.name)"
        >
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <p class="font-semibold text-ink-blue-3 text-base">{{ order.name }}</p>
              <span v-if="order.lab_required" class="text-xs px-2 py-0.5 rounded bg-surface-orange-1 text-ink-orange-3">{{ __('Lab') }}</span>
              <span v-if="order.training_required" class="text-xs px-2 py-0.5 rounded bg-surface-blue-1 text-ink-blue-3">{{ __('Training') }}</span>
            </div>
            <p class="text-sm text-ink-gray-6">{{ order.organization || '—' }}</p>
            <p v-if="order.delivery_date" class="text-xs text-ink-gray-5">{{ __('Delivery: {0}', [formatDate(order.delivery_date)]) }}</p>
          </div>
          <div class="flex items-center gap-3">
            <span class="px-2.5 py-1 text-xs font-medium rounded-full" :class="statusClass(order.status)">
              {{ order.status || 'Open' }}
            </span>
            <FeatherIcon :name="expandedOrders.has(order.name) ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
          </div>
        </div>

        <!-- Financial Summary -->
        <div class="grid grid-cols-3 gap-3 px-4 pb-4 text-sm border-t border-outline-gray-1 pt-3">
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
            <p class="font-medium text-ink-gray-9">{{ order.gross_profit_percentage ? order.gross_profit_percentage.toFixed(1) + '%' : '—' }}</p>
          </div>
        </div>

        <!-- Delivery Orders Section -->
        <div v-if="expandedOrders.has(order.name)" class="border-t border-outline-gray-2">
          <div class="px-4 py-3 bg-surface-gray-1 flex items-center justify-between">
            <p class="text-sm font-semibold text-ink-gray-8">{{ __('Delivery Orders') }}</p>
            <span class="text-xs text-ink-gray-5">{{ order.delivery_orders?.length || 0 }} {{ __('items') }}</span>
          </div>

          <div v-if="order.delivery_orders && order.delivery_orders.length">
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-surface-gray-2 border-b border-outline-gray-1">
                  <tr>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('DO Number') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Product Code') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Item') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Type') }}</th>
                    <th class="text-right px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Qty') }}</th>
                    <th class="text-right px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Rate') }}</th>
                    <th class="text-right px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Amount') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Start Date') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('End Date') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Account') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Sales Manager') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Account Manager') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Delivery Person') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Trainers') }}</th>
                    <th class="text-left px-3 py-2 text-xs text-ink-gray-5 font-medium whitespace-nowrap">{{ __('Status') }}</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-outline-gray-1">
                  <tr v-for="(item, idx) in order.delivery_orders" :key="idx" class="hover:bg-surface-gray-1">
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.delivery_order_number || '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.product_code || '—' }}</td>
                    <td class="px-3 py-2 font-medium text-ink-gray-9 whitespace-nowrap">{{ item.item }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.delivery_product_type || '—' }}</td>
                    <td class="px-3 py-2 text-right text-ink-gray-9 whitespace-nowrap">{{ item.qty }}</td>
                    <td class="px-3 py-2 text-right text-ink-gray-9 whitespace-nowrap">{{ formatCurrency(item.rate) }}</td>
                    <td class="px-3 py-2 text-right font-medium text-ink-gray-9 whitespace-nowrap">{{ formatCurrency(item.amount) }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.start_date ? formatDate(item.start_date) : '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.end_date ? formatDate(item.end_date) : '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.account || '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.sales_manager || '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.account_manager || '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.delivery_person || '—' }}</td>
                    <td class="px-3 py-2 text-ink-gray-6 whitespace-nowrap">{{ item.trainers || '—' }}</td>
                    <td class="px-3 py-2 whitespace-nowrap">
                      <span class="px-2 py-0.5 text-xs rounded-full" :class="deliveryStatusClass(item.status)">
                        {{ item.status || 'Open' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else class="px-4 py-6 text-center text-ink-gray-4 text-sm">
            {{ __('No delivery orders added yet') }}
          </div>

          <!-- Manual Add Note -->
          <div class="px-4 py-2 bg-surface-gray-1 border-t border-outline-gray-1">
            <p class="text-xs text-ink-gray-4">
              {{ __('To add or edit delivery orders, go to') }}
              <a :href="`/desk/pbs-sales-order/${order.name}`" target="_blank" class="text-ink-blue-3 hover:underline">
                {{ order.name }} in Frappe Desk
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import SalesOrderIcon from '@/components/Icons/SalesOrderIcon.vue'
import { formatDate } from '@/utils'
import { Breadcrumbs, FeatherIcon, call } from 'frappe-ui'
import { ref, onMounted } from 'vue'

const salesOrders = ref([])
const loading = ref(true)
const expandedOrders = ref(new Set())

function toggleOrder(name) {
  if (expandedOrders.value.has(name)) {
    expandedOrders.value.delete(name)
  } else {
    expandedOrders.value.add(name)
  }
}

function formatCurrency(value) {
  if (!value && value !== 0) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)
}

function statusClass(status) {
  return {
    'bg-surface-green-1 text-ink-green-3': status === 'Open',
    'bg-surface-blue-1 text-ink-blue-3': status === 'In Progress',
    'bg-surface-purple-1 text-ink-purple-3': status === 'Delivered',
    'bg-surface-gray-2 text-ink-gray-6': status === 'Closed' || !status,
  }
}

function deliveryStatusClass(status) {
  return {
    'bg-surface-gray-2 text-ink-gray-6': status === 'Open' || !status,
    'bg-surface-blue-1 text-ink-blue-3': status === 'In Progress',
    'bg-surface-green-1 text-ink-green-3': status === 'Delivered',
    'bg-surface-red-1 text-ink-red-3': status === 'Cancelled',
    'bg-surface-orange-1 text-ink-orange-3': status === 'On Hold',
  }
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
