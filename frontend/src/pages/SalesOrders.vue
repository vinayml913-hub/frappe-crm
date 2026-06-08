<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Sales Orders') }]" />
    </template>
    <template #right-header>
      <select
        v-model="statusFilter"
        class="rounded-md border border-outline-gray-2 bg-surface-gray-1 py-1.5 px-3 text-sm text-ink-gray-7 focus:outline-none"
        @change="loadOrders"
      >
        <option value="">{{ __('All Orders') }}</option>
        <option>Open</option>
        <option>In Progress</option>
        <option>Delivered</option>
        <option>Closed</option>
      </select>
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <div v-if="loading" class="flex items-center justify-center mt-20">
      <div class="text-ink-gray-5 text-sm">{{ __('Loading…') }}</div>
    </div>

    <div v-else-if="salesOrders.length === 0" class="flex flex-col items-center justify-center mt-20 gap-3">
      <SalesOrderIcon class="h-12 w-12 text-ink-gray-3" />
      <p class="text-ink-gray-5 text-base font-medium">{{ __('No Sales Orders yet') }}</p>
      <p class="text-ink-gray-4 text-sm">{{ __('Sales Orders are created automatically when a Deal is marked as Won') }}</p>
    </div>

    <div v-else class="space-y-5 max-w-5xl mx-auto">
      <div
        v-for="order in salesOrders"
        :key="order.name"
        class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-sm overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-surface-gray-1 to-surface-white border-b border-outline-gray-1">
          <div class="flex items-center gap-3 cursor-pointer flex-1" @click="toggleOrder(order.name)">
            <div class="h-10 w-10 rounded-lg bg-surface-blue-1 flex items-center justify-center flex-shrink-0">
              <SalesOrderIcon class="h-5 w-5 text-ink-blue-3" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-ink-gray-9 text-base">{{ order.name }}</span>
                <span v-if="order.lab_required" class="text-xs px-2 py-0.5 rounded-full bg-surface-orange-1 text-ink-orange-3">Lab</span>
                <span v-if="order.training_required" class="text-xs px-2 py-0.5 rounded-full bg-surface-blue-1 text-ink-blue-3">Training</span>
              </div>
              <p class="text-sm text-ink-gray-5">{{ order.organization || '—' }}{{ order.company ? ' · ' + order.company : '' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-3 py-1 text-xs font-semibold rounded-full" :class="statusClass(order.status)">{{ order.status || 'Open' }}</span>
            <span v-if="order.payment_status" class="px-2 py-1 text-xs rounded-full" :class="paymentStatusClass(order.payment_status)">{{ order.payment_status }}</span>
            <Button size="sm" variant="outline" icon="edit-2" :label="__('Edit')" @click.stop="openEditModal(order)" />
            <FeatherIcon
              :name="expandedOrders.has(order.name) ? 'chevron-up' : 'chevron-down'"
              class="h-4 w-4 text-ink-gray-4 cursor-pointer"
              @click="toggleOrder(order.name)"
            />
          </div>
        </div>

        <!-- Expanded body -->
        <div v-if="expandedOrders.has(order.name)">
          <div class="grid grid-cols-2 divide-x divide-outline-gray-1">
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Basic Information') }}</p>
              <div class="space-y-2.5">
                <div v-for="row in basicInfo(order)" :key="row.label" class="flex items-start gap-2">
                  <span class="text-xs text-ink-gray-4 w-28 flex-shrink-0 pt-0.5">{{ row.label }}</span>
                  <span class="text-sm text-ink-gray-7">{{ row.value || '—' }}</span>
                </div>
              </div>
            </div>
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Financial Information') }}</p>
              <div class="space-y-2.5">
                <div v-for="row in financialInfo(order)" :key="row.label" class="flex items-start gap-2">
                  <span class="text-xs text-ink-gray-4 w-28 flex-shrink-0 pt-0.5">{{ row.label }}</span>
                  <span class="text-sm" :class="row.bold ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-7'">{{ row.value || '—' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 divide-x divide-outline-gray-1 border-t border-outline-gray-1">
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Project Information') }}</p>
              <div class="space-y-2.5">
                <div v-for="row in projectInfo(order)" :key="row.label" class="flex items-start gap-2">
                  <span class="text-xs text-ink-gray-4 w-28 flex-shrink-0 pt-0.5">{{ row.label }}</span>
                  <span class="text-sm text-ink-gray-7">{{ row.value || '—' }}</span>
                </div>
              </div>
            </div>
            <div class="p-5">
              <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Team Information') }}</p>
              <div class="space-y-2.5">
                <div v-for="row in teamInfo(order)" :key="row.label" class="flex items-start gap-2">
                  <span class="text-xs text-ink-gray-4 w-28 flex-shrink-0 pt-0.5">{{ row.label }}</span>
                  <span class="text-sm text-ink-gray-7">{{ row.value || '—' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Delivery Orders -->
          <div class="border-t border-outline-gray-1">
            <div class="flex items-center justify-between px-5 py-3 bg-surface-gray-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-ink-gray-8">{{ __('Delivery Orders') }}</p>
                <span class="text-xs px-2 py-0.5 rounded-full bg-surface-gray-3 text-ink-gray-6">{{ order.delivery_orders?.length || 0 }}</span>
              </div>
              <Button size="sm" variant="outline" icon-left="plus" :label="__('Add Delivery Order')" @click.stop="openDeliveryModal(order)" />
            </div>

            <div v-if="order.delivery_orders && order.delivery_orders.length" class="p-5 grid grid-cols-1 gap-3">
              <div
                v-for="(di, idx) in order.delivery_orders"
                :key="di.name || idx"
                class="rounded-lg border border-outline-gray-2 p-4 hover:bg-surface-gray-1 transition-colors"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-ink-gray-9 text-sm">{{ di.delivery_order_number || di.item || 'Delivery ' + (idx + 1) }}</span>
                    <span class="text-xs px-2 py-0.5 rounded-full" :class="doStatusClass(di.status)">{{ di.status || 'Open' }}</span>
                  </div>
                  <span v-if="di.trainers" class="text-xs text-ink-gray-5">👤 {{ di.trainers }}</span>
                </div>
                <div class="flex items-center gap-4 text-xs text-ink-gray-5 mb-2">
                  <span v-if="di.description">{{ di.description }}</span>
                  <span v-if="di.start_date">📅 {{ formatDate(di.start_date) }}</span>
                  <span v-if="di.end_date">→ {{ formatDate(di.end_date) }}</span>
                </div>
                <div class="flex items-center justify-between text-xs">
                  <span v-if="di.amount" class="font-semibold text-ink-gray-8">{{ formatCurrency(di.amount) }}</span>
                  <span v-if="di.account" class="text-ink-gray-5">{{ di.account }}</span>
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

  <!-- ── Edit Sales Order Modal ──────────────────────────────────── -->
  <Dialog v-model="showEditModal" :options="{ size: '2xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Edit Sales Order') }}</h3>
            <p class="text-sm text-ink-gray-5 mt-0.5">{{ editForm.name }}</p>
          </div>
          <Button variant="ghost" class="w-7" icon="x" @click="showEditModal = false" />
        </div>

        <div class="space-y-5">
          <!-- Basic -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Basic') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Status') }}</label>
                <select v-model="editForm.status" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option>Open</option>
                  <option>In Progress</option>
                  <option>Delivered</option>
                  <option>Closed</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Payment Status') }}</label>
                <select v-model="editForm.payment_status" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option value="">—</option>
                  <option>Pending</option>
                  <option>Partial</option>
                  <option>Paid</option>
                  <option>Overdue</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Email') }}</label>
                <input v-model="editForm.email" type="email" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Phone') }}</label>
                <input v-model="editForm.phone" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
            </div>
          </div>

          <!-- Financial -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Financial') }}</p>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Amount') }}</label>
                <input v-model.number="editForm.amount" type="number" min="0" step="0.01" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Tax') }}</label>
                <input v-model.number="editForm.tax" type="number" min="0" step="0.01" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Discount') }}</label>
                <input v-model.number="editForm.discount" type="number" min="0" step="0.01" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div class="col-span-3 bg-surface-gray-1 rounded-md px-3 py-2">
                <span class="text-xs text-ink-gray-5">{{ __('Final Amount') }}: </span>
                <strong class="text-sm text-ink-gray-9">{{ formatCurrency((editForm.amount || 0) + (editForm.tax || 0) - (editForm.discount || 0)) }}</strong>
              </div>
            </div>
          </div>

          <!-- Project -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Project') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Technology') }}</label>
                <input v-model="editForm.technology" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Delivery Type') }}</label>
                <select v-model="editForm.delivery_type" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option value="">—</option>
                  <option>Onsite</option>
                  <option>Online</option>
                  <option>Hybrid</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Start Date') }}</label>
                <input v-model="editForm.start_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('End Date') }}</label>
                <input v-model="editForm.end_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none" />
              </div>
            </div>
          </div>

          <!-- Team — user dropdowns, not free-text inputs -->
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Team') }}</p>
            <div v-if="usersLoading" class="text-xs text-ink-gray-4 py-2">{{ __('Loading users…') }}</div>
            <div v-else class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Sales Manager') }}</label>
                <!-- value = user email (the Frappe User Link value) -->
                <select v-model="editForm.sales_manager" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option value="">— {{ __('None') }} —</option>
                  <option v-for="u in crmUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Account Manager') }}</label>
                <select v-model="editForm.account_manager" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option value="">— {{ __('None') }} —</option>
                  <option v-for="u in crmUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Delivery Manager') }}</label>
                <select v-model="editForm.delivery_manager" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
                  <option value="">— {{ __('None') }} —</option>
                  <option v-for="u in crmUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
              </div>
            </div>
          </div>

          <p v-if="editError" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-3 py-2">{{ editError }}</p>
        </div>
      </div>
      <div class="px-6 pb-5 pt-3 flex justify-end gap-2 border-t border-outline-gray-1">
        <Button variant="outline" :label="__('Cancel')" @click="showEditModal = false" />
        <Button variant="solid" :label="__('Save Changes')" :loading="saving" @click="submitEdit" />
      </div>
    </template>
  </Dialog>

  <!-- ── Delivery Order Modal ────────────────────────────────────── -->
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
          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Delivery Information') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">
                  {{ __('Item / Title') }} <span class="text-ink-red-3">*</span>
                </label>
                <input
                  v-model="doForm.item"
                  type="text"
                  :class="['w-full rounded-md border px-3 py-1.5 text-sm focus:outline-none', doFormItemError ? 'border-ink-red-3' : 'border-outline-gray-2 focus:border-outline-gray-4']"
                />
                <p v-if="doFormItemError" class="text-xs text-ink-red-3 mt-0.5">{{ doFormItemError }}</p>
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('DO Number') }}</label>
                <input v-model="doForm.delivery_order_number" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Trainers') }}</label>
                <input v-model="doForm.trainers" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Type') }}</label>
                <select v-model="doForm.delivery_product_type" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
                  <option value="">{{ __('Select') }}</option>
                  <option>Product</option>
                  <option>Service</option>
                  <option>License</option>
                  <option>Training</option>
                  <option>Support</option>
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

          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Schedule') }}</p>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Start Date') }}</label>
                <input v-model="doForm.start_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('End Date') }}</label>
                <input v-model="doForm.end_date" type="date" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
            </div>
          </div>

          <div>
            <p class="text-xs font-semibold text-ink-gray-4 uppercase tracking-wider mb-3">{{ __('Commercial') }}</p>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Qty') }}</label>
                <input v-model.number="doForm.qty" type="number" min="1" step="1" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Rate (₹)') }}</label>
                <input v-model.number="doForm.rate" type="number" min="0" step="0.01" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
              </div>
              <div>
                <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Amount (₹)') }}</label>
                <input
                  :value="doForm.qty && doForm.rate ? formatCurrency(doForm.qty * doForm.rate) : '—'"
                  readonly
                  class="w-full rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-1.5 text-sm text-ink-gray-5"
                />
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Status') }}</label>
              <select v-model="doForm.status" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
                <option>Open</option>
                <option>In Progress</option>
                <option>Delivered</option>
                <option>Cancelled</option>
                <option>On Hold</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Sales Manager') }}</label>
              <select v-model="doForm.sales_manager" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
                <option value="">— {{ __('None') }} —</option>
                <option v-for="u in crmUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
              </select>
            </div>
          </div>

          <p v-if="doFormError" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-3 py-2">{{ doFormError }}</p>
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
import { ref, reactive, onMounted } from 'vue'

// ── State ────────────────────────────────────────────────────────────
const salesOrders    = ref([])
const loading        = ref(true)
const expandedOrders = ref(new Set())
const statusFilter   = ref('')

// Users list for dropdowns — loaded once on mount
const crmUsers    = ref([])   // [{ value: "email@x.com", label: "Full Name" }]
const usersLoading = ref(true)

// Edit modal
const showEditModal = ref(false)
const saving        = ref(false)
const editError     = ref(null)
const editForm      = reactive({
  name: '', status: '', payment_status: '', email: '', phone: '',
  amount: 0, tax: 0, discount: 0, technology: '', delivery_type: '',
  start_date: '', end_date: '',
  // User Link fields — store the email (Frappe User name), not the display name
  sales_manager: '', account_manager: '', delivery_manager: '',
})

// Delivery order modal
const showDeliveryModal = ref(false)
const selectedOrder     = ref(null)
const savingDO          = ref(false)
const doFormError       = ref(null)
const doFormItemError   = ref(null)
const doForm = reactive({
  item: '', delivery_order_number: '', trainers: '', delivery_product_type: '',
  account: '', description: '', start_date: '', end_date: '',
  qty: 1, rate: 0,
  status: 'Open',          // must match DocType options exactly
  sales_manager: '',
})

// ── Helpers ──────────────────────────────────────────────────────────
function toggleOrder(name) {
  if (expandedOrders.value.has(name)) expandedOrders.value.delete(name)
  else expandedOrders.value.add(name)
}

/** Look up a user's display label by email value, for the info panels */
function userLabel(email) {
  if (!email) return null
  const u = crmUsers.value.find(x => x.value === email)
  return u ? u.label : email   // fall back to raw email if not in list
}

function openEditModal(order) {
  Object.assign(editForm, {
    name:             order.name,
    status:           order.status           || 'Open',
    payment_status:   order.payment_status   || '',
    email:            order.email            || '',
    phone:            order.phone            || '',
    amount:           order.amount           || 0,
    tax:              order.tax              || 0,
    discount:         order.discount         || 0,
    technology:       order.technology       || '',
    delivery_type:    order.delivery_type    || '',
    start_date:       order.start_date       || '',
    end_date:         order.end_date         || '',
    // These are already stored as user emails in the DB
    sales_manager:    order.sales_manager    || '',
    account_manager:  order.account_manager  || '',
    delivery_manager: order.delivery_manager || '',
  })
  editError.value = null
  showEditModal.value = true
}

async function submitEdit() {
  editError.value = null
  saving.value = true
  try {
    const { name, ...data } = editForm
    data.amount   = parseFloat(data.amount)   || 0
    data.tax      = parseFloat(data.tax)      || 0
    data.discount = parseFloat(data.discount) || 0

    const updated = await call('crm.api.sales_order.update_sales_order', {
      name,
      data: JSON.stringify(data),
    })

    // Patch local list immediately — no full reload needed
    const idx = salesOrders.value.findIndex(o => o.name === name)
    if (idx !== -1) Object.assign(salesOrders.value[idx], updated)

    toast.success(__('Sales Order updated'))
    showEditModal.value = false
  } catch (err) {
    editError.value = _extractError(err, __('Failed to save Sales Order'))
    toast.error(editError.value)
  } finally {
    saving.value = false
  }
}

function openDeliveryModal(order) {
  selectedOrder.value = order
  Object.assign(doForm, {
    item: '', delivery_order_number: '', trainers: '', delivery_product_type: '',
    account: '', description: '', start_date: '', end_date: '',
    qty: 1, rate: 0,
    status: 'Open',
    sales_manager: order.sales_manager || '',
  })
  doFormError.value     = null
  doFormItemError.value = null
  showDeliveryModal.value = true
}

async function submitDeliveryOrder() {
  doFormItemError.value = null
  doFormError.value     = null

  if (!doForm.item || !doForm.item.trim()) {
    doFormItemError.value = __('Item / Title is required')
    return
  }

  savingDO.value = true
  try {
    const qty    = parseFloat(doForm.qty)  || 1
    const rate   = parseFloat(doForm.rate) || 0

    const payload = {
      item:   doForm.item.trim(),
      qty,
      rate,
      amount: qty * rate,
      status: doForm.status || 'Open',
    }

    const optionalStr = ['delivery_order_number', 'trainers', 'delivery_product_type', 'account', 'description']
    optionalStr.forEach(k => { if (doForm[k]) payload[k] = doForm[k] })

    const optionalDate = ['start_date', 'end_date']
    optionalDate.forEach(k => { if (doForm[k]) payload[k] = doForm[k] })

    // sales_manager is now a user email from the dropdown — safe to pass as Link value
    if (doForm.sales_manager) payload.sales_manager = doForm.sales_manager

    const updatedDOs = await call('crm.api.sales_order.create_delivery_order', {
      sales_order_name: selectedOrder.value.name,
      delivery_order:   JSON.stringify(payload),
    })

    const order = salesOrders.value.find(o => o.name === selectedOrder.value.name)
    if (order) order.delivery_orders = updatedDOs

    toast.success(__('Delivery Order created'))
    showDeliveryModal.value = false
  } catch (err) {
    doFormError.value = _extractError(err, __('Something went wrong'))
    toast.error(doFormError.value)
  } finally {
    savingDO.value = false
  }
}

async function loadOrders() {
  loading.value = true
  try {
    let orders = await call('crm.api.sales_order.get_sales_orders') || []
    if (statusFilter.value) orders = orders.filter(o => o.status === statusFilter.value)
    salesOrders.value = orders
  } catch (err) {
    console.error('loadOrders error:', err)
    salesOrders.value = []
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  usersLoading.value = true
  try {
    crmUsers.value = await call('crm.api.sales_order.get_crm_users') || []
  } catch (err) {
    console.error('loadUsers error:', err)
    crmUsers.value = []
  } finally {
    usersLoading.value = false
  }
}

function _extractError(err, fallback) {
  if (!err) return fallback
  try {
    if (err.messages && err.messages.length && err.messages[0].message) {
      return err.messages[0].message
    }
  } catch (e) { /* ignore */ }
  if (err.message) return err.message
  if (typeof err === 'string') return err
  return fallback
}

// ── Info builders (use userLabel() for Link→User fields) ─────────────
function basicInfo(o) {
  return [
    { label: __('Client'),  value: o.organization },
    { label: __('Company'), value: o.company },
    { label: __('Deal'),    value: o.deal },
    { label: __('Contact'), value: o.contact_person },
    { label: __('Email'),   value: o.email },
    { label: __('Phone'),   value: o.phone },
  ]
}
function financialInfo(o) {
  return [
    { label: __('Amount'),       value: formatCurrency(o.amount) },
    { label: __('Tax'),          value: formatCurrency(o.tax) },
    { label: __('Discount'),     value: formatCurrency(o.discount) },
    { label: __('Final Amount'), value: formatCurrency(o.final_amount), bold: true },
    { label: __('Gross Profit'), value: formatCurrency(o.gross_profit) },
    { label: __('GP %'),         value: o.gross_profit_percentage ? o.gross_profit_percentage.toFixed(1) + '%' : null },
  ]
}
function projectInfo(o) {
  return [
    { label: __('Technology'),    value: o.technology },
    { label: __('Trainer'),       value: o.trainer_assigned },
    { label: __('Delivery Type'), value: o.delivery_type },
    { label: __('Duration'),      value: o.project_duration },
    { label: __('Start Date'),    value: o.start_date ? formatDate(o.start_date) : null },
    { label: __('End Date'),      value: o.end_date   ? formatDate(o.end_date)   : null },
  ]
}
function teamInfo(o) {
  return [
    { label: __('Sales Manager'),    value: userLabel(o.sales_manager) },
    { label: __('Account Manager'),  value: userLabel(o.account_manager) },
    { label: __('Delivery Manager'), value: userLabel(o.delivery_manager) },
  ]
}

// ── Formatters ───────────────────────────────────────────────────────
function formatCurrency(v) {
  if (v == null || v === '') return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}
function statusClass(s) {
  return {
    'bg-surface-green-1 text-ink-green-3':   s === 'Open',
    'bg-surface-blue-1 text-ink-blue-3':     s === 'In Progress',
    'bg-surface-purple-1 text-ink-purple-3': s === 'Delivered',
    'bg-surface-gray-2 text-ink-gray-6':     s === 'Closed' || !s,
    'bg-surface-red-1 text-ink-red-3':       s === 'Cancelled',
  }
}
function paymentStatusClass(s) {
  return {
    'bg-surface-gray-2 text-ink-gray-6':     s === 'Pending',
    'bg-surface-orange-1 text-ink-orange-3': s === 'Partial',
    'bg-surface-green-1 text-ink-green-3':   s === 'Paid',
    'bg-surface-red-1 text-ink-red-3':       s === 'Overdue',
  }
}
function doStatusClass(s) {
  return {
    'bg-surface-gray-2 text-ink-gray-6':     s === 'Open'         || !s,
    'bg-surface-blue-1 text-ink-blue-3':     s === 'In Progress',
    'bg-surface-green-1 text-ink-green-3':   s === 'Delivered',
    'bg-surface-red-1 text-ink-red-3':       s === 'Cancelled',
    'bg-surface-orange-1 text-ink-orange-3': s === 'On Hold',
  }
}

onMounted(() => {
  loadUsers()    // load user list first (needed for dropdowns)
  loadOrders()
})
</script>
