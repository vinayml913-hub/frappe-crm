<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center justify-between px-5 py-4 border-b">
      <h1 class="text-xl font-semibold">Sales Orders</h1>
    </div>
    <div class="flex-1 overflow-y-auto p-5">
      <div v-if="salesOrders.length === 0" class="text-center text-gray-500 mt-10">
        No Sales Orders yet. Win a deal to create one!
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="order in salesOrders"
          :key="order.name"
          class="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
        >
          <div class="flex justify-between items-start">
            <div>
              <p class="font-semibold text-blue-600">{{ order.name }}</p>
              <p class="text-sm text-gray-600">{{ order.organization }}</p>
            </div>
            <span
              class="px-2 py-1 text-xs rounded-full"
              :class="{
                'bg-green-100 text-green-700': order.status === 'Open',
                'bg-blue-100 text-blue-700': order.status === 'In Progress',
                'bg-purple-100 text-purple-700': order.status === 'Delivered',
                'bg-gray-100 text-gray-700': order.status === 'Closed',
              }"
            >
              {{ order.status }}
            </span>
          </div>
          <div class="mt-2 grid grid-cols-3 gap-2 text-sm">
            <div>
              <p class="text-gray-500">Amount</p>
              <p class="font-medium">{{ order.amount }}</p>
            </div>
            <div>
              <p class="text-gray-500">Gross Profit</p>
              <p class="font-medium">{{ order.gross_profit }}</p>
            </div>
            <div>
              <p class="text-gray-500">GP %</p>
              <p class="font-medium">{{ order.gross_profit_percentage }}%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'

const salesOrders = ref([])

onMounted(async () => {
  const result = await call('frappe.client.get_list', {
    doctype: 'PBS Sales Order',
    fields: ['name', 'organization', 'status', 'amount', 'gross_profit', 'gross_profit_percentage'],
    order_by: 'modified desc',
  })
  salesOrders.value = result || []
})
</script>