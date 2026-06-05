<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Sales Orders') }]" />
    </template>
    <template #right-header>
      <div class="flex items-center gap-2">
        <select v-model="statusFilter" class="rounded-md border border-outline-gray-2 bg-surface-gray-1 py-1.5 px-3 text-sm text-ink-gray-7 focus:outline-none" @change="loadOrders">
          <option value="">{{ __('All Orders') }}</option>
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Delivered">Delivered</option>
          <option value="Closed">Closed</option>
        </select>
      </div>
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center mt-20">
      <div class="text-ink-gray-5 text-sm">{{ __('Loading...') }}</div>
    </div>

    <!-- Empty -->
    <div v-else-if="salesOrders.length === 0" class="flex flex-col items-center justify-center mt-20 gap-3">
      <SalesOrderIcon class="h-12 w-12 text-ink-gray-3" />
      <p class="text-ink-gray-5 text-base font-medium">{{ __('No Sales Orders yet') }}</p>
      <p class="text-ink-gray-4 text-sm">{{ __('Sales Orders are created automatically when a Deal is marked as Won') }}</p>
    </div>

    <!-- Orders -->
    <div v-else class="space-y-5 max-w-5xl mx-auto">
      <div v-for="order in salesOrders" :key="order.name" class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-sm overflow-hidden">

        <!-- Card Header -->
        <div class="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-surface-gray-1 to-surface-white border-b border-outline-gray-1 cursor-pointer" @click="toggleOrder(order.name)">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-lg bg-surface-blue-1 flex items-center justify-center">
              <SalesOrderIcon class="h-5 w-5 text-ink-blue-3" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-ink-gray-9 text-base">{{ order.name }}</span>
                <span v-if="order.lab_required" class="text-xs px-2 py-0.5 rounded-full bg-surface-orange-1 text-ink-orange-3">Lab</span>
                <span v-if="order.training_required" class="text-xs px-2 py-0.5 rounded-full bg-surface-blue-1 text-ink-blue-3">Training</span>
              </div>
              <p class="text-sm text-ink-gray-5">{{ order.organization || '—' }} {{ order.company ? '· ' + order.company : '' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="px-3 py-1 text-xs font-semibold rounded-full" :class="statusClass(order.status)">{{ order.status || 'Open' }}</span>
            <span v-if="order.payment_status" class="px-2 py-1 text-xs rounded-full" :class="paymentStatusClass(order.payment_status)">{{ order.payment_status }}</span>
            <FeatherIcon :name="expandedOrders.has(order.name) ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-4" />
          </div>
        </div>

        <!-- Expanded Content -->
        <div v-if="expandedOrders.has(order.name)">

          <!-- Section 1: Basic Info + Financial in grid -->
          <div class="grid grid-cols-2 gap-0 divide-x divide-outline-gray-1">

            <!-- Basic Information -->
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Basic Information') }}</p>
              <div class="space-y-2.5">
                <InfoRow :label="__('Client')" :value="order.organization" />
                <InfoRow :label="__('Company')" :value="order.company" />
                <InfoRow :label="__('Deal')" :value="order.deal" />
                <InfoRow :label="__('Contact')" :value="order.contact_person" />
                <InfoRow :label="__('Email')" :value="order.email" />
                <InfoRow :label="__('Phone')" :value="order.phone" />
              </div>
            </div>

            <!-- Financial Information -->
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Financial Information') }}</p>
              <div class="space-y-2.5">
                <InfoRow :label="__('Amount')" :value="formatCurrency(order.amount)" />
                <InfoRow :label="__('Tax')" :value="formatCurrency(order.tax)" />
                <InfoRow :label="__('Discount')" :value="formatCurrency(order.discount)" />
                <InfoRow :label="__('Final Amount')" :value="formatCurrency(order.final_amount)" bold />
                <InfoRow :label="__('Gross Profit')" :value="formatCurrency(order.gross_profit)" />
                <InfoRow :label="__('GP %')" :value="order.gross_profit_percentage ? order.gross_profit_percentage.toFixed(1) + '%' : '—'" />
              </div>
            </div>
          </div>

          <!-- Section 2: Project + Team -->
          <div class="grid grid-cols-2 gap-0 divide-x divide-outline-gray-1 border-t border-outline-gray-1">

            <!-- Project Information -->
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Project Information') }}</p>
              <div class="space-y-2.5">
                <InfoRow :label="__('Technology')" :value="order.technology" />
                <InfoRow :label="__('Trainer Assigned')" :value="order.trainer_assigned" />
                <InfoRow :label="__('Delivery Type')" :value="order.delivery_type" />
                <InfoRow :label="__('Duration')" :value="order.project_duration" />
                <InfoRow :label="__('Start Date')" :value="order.start_date ? formatDate(order.start_date) : null" />
                <InfoRow :label="__('End Date')" :value="order.end_date ? formatDate(order.end_date) : null" />
              </div>
            </div>

            <!-- Team Information -->
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Team Information') }}</p>
              <div class="space-y-2.5">
                <InfoRow :label="__('Sales Manager')" :value="order.sales_manager" />
                <InfoRow :label="__('Account Manager')" :value="order.account_manager" />
                <InfoRow :label="__('Delivery Manager')" :value="order.delivery_manager" />
              </div>
            </div>
          </div>

          <!-- Section 3: Delivery Orders -->
          <div class="border-t border-outline-gray-1">
            <div class="flex items-center justify-between px-5 py-3 bg-surface-gray-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-ink-gray-8">{{ __('Delivery Orders') }}</p>
                <span class="text-xs px-2 py-0.5 rounded-full bg-surface-gray-3 text-ink-gray-6">{{ order.delivery_orders?.length || 0 }}</span>
              </div>
              <Button size="sm" variant="outline" icon-left="plus" :label="__('Add Delivery Order')" @click.stop="openDeliveryModal(order)" />
            </div>

            <!-- Delivery Order Cards -->
            <div v-if="order.delivery_orders && order.delivery_orders.length" class="p-5 grid grid-cols-1 gap-3">
              <div v-for="(do_item, idx) in order.delivery_orders" :key="idx" class="rounded-lg border border-outline-gray-2 p-4 hover:bg-surface-gray-1 transition-colors">
                <!-- Row 1: Name + Status + Trainer -->
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-ink-gray-9 text-sm">{{ do_item.delivery_order_number || do_item.item || 'Delivery ' + (idx + 1) }}</span>
                    <span class="text-xs px-2 py-0.5 rounded-full" :class="doStatusClass(do_item.status)">{{ do_item.status || 'Pending' }}</span>
                  </div>
                  <span v-if="do_item.trainers" class="text-xs text-ink-gray-5 flex items-center gap-1">
                    <svg class="h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    {{ do_item.trainers }}
                  </span>
                </div>
                <!-- Row 2: Technology + Dates -->
                <div class="flex items-center gap-4 text-xs text-ink-gray-5 mb-2">
                  <span v-if="do_item.description">{{ do_item.description }}</span>
                  <span v-if="do_item.start_date" class="flex items-center gap-1">
                    <svg class="h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                    {{ formatDate(do_item.start_date) }}
                  </span>
                  <span v-if="do_item.end_date">→ {{ formatDate(do_item.end_date) }}</span>
                </div>
                <!-- Row 3: Commercial + Account -->
                <div class="flex items-center justify-between text-xs">
                  <span v-if="do_item.amount" class="font-semibold text-ink-gray-8">{{ formatCurrency(do_item.amount) }}</span>
                  <span v-if="do_item.account" class="text-ink-gray-5">{{ do_item.account }}</span>
                </div>
              </div>
            </div>

            <div v-else class="px-5 py-6 text-center text-sm text-ink-gray-4">
              {{ __('No delivery orders yet. Click "Add Delivery Order" to create one.') }}
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>

  <!-- Delivery Order Modal -->
  <Dialog v-model="showDeliveryModal" :options="{ size: '2xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Create Delivery Order') }}</h3>
            <p class="text-sm text-ink-gray-5 mt-0.5">{{ selectedOrder?.name }}</p>
          </div>
          <Button variant="ghost" class="w-7" icon="x" @click="showDeliveryModal = false" />
        </div>

        <div class="space-y-5">
          <!-- Delivery Information -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Delivery Information') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Item / Delivery Title') }} <span class="text-ink-red-3">*</span></label>
                <input v-model="doForm.item" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('DO Number') }}</label>
                <input v-model="doForm.delivery_order_number" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Trainers') }}</label>
                <input v-model="doForm.trainers" type="text" :placeholder="__('Trainer name(s)')" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Delivery Product Type') }}</label>
                <select v-model="doForm.delivery_product_type" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
                  <option value="">{{ __('Select') }}</option>
                  <option>Product</option><option>Service</option><option>License</option><option>Training</option><option>Support</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Account / Client') }}</label>
                <input v-model="doForm.account" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Description') }}</label>
                <input v-model="doForm.description" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
            </div>
          </div>

          <!-- Schedule Information -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Schedule Information') }}</p>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Start Date') }}</label>
                <input v-model="doForm.start_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('End Date') }}</label>
                <input v-model="doForm.end_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Delivery Date') }}</label>
                <input v-model="doForm.delivery_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
            </div>
          </div>

          <!-- Commercial Information -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Commercial Information') }}</p>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Qty') }}</label>
                <input v-model="doForm.qty" type="number" min="1" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Rate (₹)') }}</label>
                <input v-model="doForm.rate" type="number" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Amount (₹)') }}</label>
                <input :value="doForm.qty && doForm.rate ? (doForm.qty * doForm.rate).toLocaleString('en-IN') : ''" type="text" readonly class="w-full rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-1.5 text-sm text-ink-gray-5" />
              </div>
            </div>
          </div>

          <!-- Delivery Status -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Status') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Delivery Status') }}</label>
                <select v-model="doForm.status" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
                  <option>Pending</option><option>In Transit</option><option>Delivered</option><option>Cancelled</option><option>On Hold</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Sales Manager') }}</label>
                <input v-model="doForm.sales_manager" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
            </div>
          </div>

          <!-- Remarks -->
          <div v-if="doFormError" class="text-sm text-ink-red-3 mt-1">{{ doFormError }}</div>
        </div>
      </div>
      <div class="px-6 pb-5 pt-3 flex justify-end gap-2 border-t border-outline-gray-1">
        <Button variant="outline" :label="__('Cancel')" @click="showDeliveryModal = false" />
        <Button variant="solid" :label="__('Create Delivery Order')" :loading="savingDO" @click="submitDeliveryOrder" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import SalesOrderIcon from '@/components/Icons/SalesOrderIcon.vue'
import { Breadcrumbs, Button, Dialog, FeatherIcon, call, toast } from 'frappe-ui'
import { formatDate } from '@/utils'
import { ref, reactive, onMounted, defineComponent, h } from 'vue'

// InfoRow helper component
const InfoRow = defineComponent({
  props: { label: String, value: [String, Number], bold: Boolean },
  setup(props) {
    return () => h('div', { class: 'flex items-start gap-2' }, [
      h('span', { class: 'text-xs text-ink-gray-4 w-28 flex-shrink-0 pt-0.5' }, props.label),
      h('span', { class: `text-sm ${props.bold ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-7'}` }, props.value || '—'),
    ])
  }
})

const salesOrders = ref([])
const loading = ref(true)
const expandedOrders = ref(new Set())
const statusFilter = ref('')
const showDeliveryModal = ref(false)
const selectedOrder = ref(null)
const savingDO = ref(false)
const doFormError = ref(null)

const emptyDOForm = () => ({
  item: '', delivery_order_number: '', trainers: '', delivery_product_type: '',
  account: '', description: '', start_date: '', end_date: '', delivery_date: '',
  qty: 1, rate: 0, status: 'Pending', sales_manager: '',
})

const doForm = reactive(emptyDOForm())

function toggleOrder(name) {
  if (expandedOrders.value.has(name)) expandedOrders.value.delete(name)
  else expandedOrders.value.add(name)
}

function openDeliveryModal(order) {
  selectedOrder.value = order
  Object.assign(doForm, emptyDOForm())
  doFormError.value = null
  showDeliveryModal.value = true
}

async function submitDeliveryOrder() {
  if (!doForm.item) { doFormError.value = __('Item / Delivery Title is required'); return }
  savingDO.value = true
  try {
    const payload = {
      ...doForm,
      amount: (doForm.qty || 1) * (doForm.rate || 0),
    }
    await call('crm.api.sales_order.create_delivery_order', {
      sales_order_name: selectedOrder.value.name,
      delivery_order: JSON.stringify(payload),
    })
    toast.success(__('Delivery Order created successfully'))
    showDeliveryModal.value = false
    loadOrders()
  } catch (err) {
    doFormError.value = err?.message || __('Something went wrong')
  } finally {
    savingDO.value = false
  }
}

async function loadOrders() {
  loading.value = true
  try {
    const result = await call('crm.api.sales_order.get_sales_orders')
    let orders = result || []
    if (statusFilter.value) {
      orders = orders.filter(o => o.status === statusFilter.value)
    }
    salesOrders.value = orders
  } catch (err) {
    console.error('Failed to load sales orders:', err)
    salesOrders.value = []
  } finally {
    loading.value = false
  }
}

function formatCurrency(value) {
  if (!value && value !== 0) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value)
}

function statusClass(status) {
  return {
    'bg-surface-green-1 text-ink-green-3': status === 'Open',
    'bg-surface-blue-1 text-ink-blue-3': status === 'In Progress',
    'bg-surface-purple-1 text-ink-purple-3': status === 'Delivered',
    'bg-surface-gray-2 text-ink-gray-6': status === 'Closed' || !status,
    'bg-surface-red-1 text-ink-red-3': status === 'Cancelled',
    'bg-surface-yellow-1 text-ink-yellow-3': status === 'Archived',
  }
}

function paymentStatusClass(status) {
  return {
    'bg-surface-gray-2 text-ink-gray-6': status === 'Pending',
    'bg-surface-orange-1 text-ink-orange-3': status === 'Partial',
    'bg-surface-green-1 text-ink-green-3': status === 'Paid',
    'bg-surface-red-1 text-ink-red-3': status === 'Overdue',
  }
}

function doStatusClass(status) {
  return {
    'bg-surface-gray-2 text-ink-gray-6': status === 'Pending' || !status,
    'bg-surface-blue-1 text-ink-blue-3': status === 'In Transit',
    'bg-surface-green-1 text-ink-green-3': status === 'Delivered',
    'bg-surface-red-1 text-ink-red-3': status === 'Cancelled',
    'bg-surface-orange-1 text-ink-orange-3': status === 'On Hold',
  }
}

onMounted(() => loadOrders())
</script>
