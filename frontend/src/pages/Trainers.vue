<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Trainers') }]" />
    </template>
    <template #right-header>
      <Button variant="solid" :label="__('Create')" icon-left="plus" @click="openCreateModal" />
    </template>
  </LayoutHeader>

  <!-- Filters -->
  <div class="flex items-center gap-3 px-5 py-3 border-b border-outline-gray-1 flex-wrap">
    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="__('Search trainers...')"
        class="w-64 rounded-md border border-outline-gray-2 bg-surface-gray-1 py-1.5 pl-8 pr-3 text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:border-outline-gray-4 focus:bg-surface-white focus:outline-none"
        @input="onSearch"
      />
      <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-gray-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
      </svg>
    </div>
    <select v-model="statusFilter" class="rounded-md border border-outline-gray-2 bg-surface-gray-1 py-1.5 px-3 text-sm text-ink-gray-7 focus:outline-none" @change="loadTrainers">
      <option value="">{{ __('All Status') }}</option>
      <option>Active</option>
      <option>Inactive</option>
      <option>Blacklisted</option>
    </select>
    <select v-model="availabilityFilter" class="rounded-md border border-outline-gray-2 bg-surface-gray-1 py-1.5 px-3 text-sm text-ink-gray-7 focus:outline-none" @change="loadTrainers">
      <option value="">{{ __('All Availability') }}</option>
      <option>Available</option>
      <option>Partially Available</option>
      <option>Not Available</option>
    </select>
    <div class="ml-auto text-sm text-ink-gray-5">{{ total }} {{ __('trainers') }}</div>
  </div>

  <!-- Table -->
  <div class="flex-1 overflow-auto">
    <div v-if="loading" class="flex items-center justify-center mt-20">
      <div class="text-ink-gray-5 text-sm">{{ __('Loading...') }}</div>
    </div>
    <div v-else-if="trainers.length === 0" class="flex flex-col items-center justify-center mt-20 gap-3">
      <TrainersIcon class="h-12 w-12 text-ink-gray-3" />
      <p class="text-ink-gray-5 text-base font-medium">{{ __('No Trainers found') }}</p>
      <Button variant="solid" :label="__('Add Trainer')" icon-left="plus" @click="openCreateModal" />
    </div>
    <table v-else class="w-full text-sm">
      <thead class="sticky top-0 z-10 bg-surface-gray-2 border-b border-outline-gray-2">
        <tr>
          <th class="w-8 px-3 py-2.5">
            <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" class="rounded" />
          </th>
          <th v-for="col in visibleColumns" :key="col.key" class="text-left px-3 py-2.5 text-xs font-medium text-ink-gray-5 whitespace-nowrap cursor-pointer hover:text-ink-gray-8 select-none" @click="sortBy(col.key)">
            <div class="flex items-center gap-1">
              {{ col.label }}
              <span v-if="sortKey === col.key">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </div>
          </th>
          <th class="px-3 py-2.5">
            <button class="text-xs text-ink-blue-3 hover:underline flex items-center gap-1" @click="showColumnManager = true">
              + {{ __('Columns') }}
            </button>
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-gray-1">
        <tr v-for="trainer in trainers" :key="trainer.name" class="hover:bg-surface-gray-1 group cursor-pointer" @click="openEditModal(trainer)">
          <td class="px-3 py-2.5" @click.stop>
            <input type="checkbox" v-model="selected" :value="trainer.name" class="rounded" />
          </td>
          <td v-for="col in visibleColumns" :key="col.key" class="px-3 py-2.5 text-ink-gray-7 whitespace-nowrap">
            <template v-if="col.key === 'trainer_name'">
              <div class="flex items-center gap-2 font-medium text-ink-gray-9">
                <div class="h-6 w-6 rounded-full bg-surface-blue-1 flex items-center justify-center text-xs font-semibold text-ink-blue-3 flex-shrink-0">
                  {{ trainer.trainer_name?.charAt(0)?.toUpperCase() }}
                </div>
                {{ trainer.trainer_name }}
              </div>
            </template>
            <template v-else-if="col.key === 'linkedin_profile'">
              <a v-if="trainer.linkedin_profile" :href="trainer.linkedin_profile.startsWith('http') ? trainer.linkedin_profile : 'https://' + trainer.linkedin_profile" target="_blank" class="text-ink-blue-3 hover:underline flex items-center gap-1" @click.stop>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>
                LinkedIn
              </a>
              <span v-else class="text-ink-gray-4">—</span>
            </template>
            <template v-else-if="col.key === 'status'">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="statusClass(trainer.status)">{{ trainer.status || '—' }}</span>
            </template>
            <template v-else-if="col.key === 'availability'">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="availabilityClass(trainer.availability)">{{ trainer.availability || '—' }}</span>
            </template>
            <template v-else-if="col.key === 'commercial'">
              {{ trainer.commercial ? formatCurrency(trainer.commercial) : '—' }}
            </template>
            <template v-else-if="col.key === 'remarks'">
              <span class="truncate block max-w-xs">{{ stripHtml(trainer.remarks) }}</span>
            </template>
            <template v-else>{{ trainer[col.key] || '—' }}</template>
          </td>
          <td class="px-3 py-2.5" @click.stop>
            <div class="flex gap-1 opacity-0 group-hover:opacity-100">
              <button class="p-1 rounded hover:bg-surface-gray-3 text-ink-gray-5" @click.stop="openEditModal(trainer)">
                <svg class="h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
              </button>
              <button class="p-1 rounded hover:bg-surface-red-1 text-ink-gray-5 hover:text-ink-red-3" @click.stop="confirmDelete(trainer)">
                <svg class="h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination -->
    <div v-if="trainers.length > 0" class="flex items-center justify-between px-5 py-3 border-t border-outline-gray-1">
      <div class="text-sm text-ink-gray-5">{{ __('Showing {0}–{1} of {2}', [((page-1)*pageLength)+1, Math.min(page*pageLength, total), total]) }}</div>
      <div class="flex items-center gap-2">
        <Button :disabled="page === 1" variant="outline" icon="chevron-left" @click="prevPage" />
        <span class="text-sm text-ink-gray-7">{{ page }}</span>
        <Button :disabled="page*pageLength >= total" variant="outline" icon="chevron-right" @click="nextPage" />
      </div>
    </div>
  </div>

  <!-- Bulk bar -->
  <div v-if="selected.length > 0" class="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-lg bg-surface-gray-8 px-4 py-2.5 shadow-xl">
    <span class="text-sm text-white">{{ selected.length }} {{ __('selected') }}</span>
    <Button variant="outline" size="sm" :label="__('Delete Selected')" @click="bulkDelete" />
    <button class="text-white opacity-60 hover:opacity-100" @click="selected = []">✕</button>
  </div>

  <!-- Create/Edit Modal -->
  <Dialog v-model="showModal" :options="{ size: '2xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-5 flex items-center justify-between">
          <h3 class="text-xl font-semibold text-ink-gray-9">{{ editingTrainer ? __('Edit Trainer') : __('Add Trainer') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showModal = false" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Trainer Name') }} <span class="text-ink-red-3">*</span></label>
            <input v-model="form.trainer_name" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Phone Number') }}</label>
            <input v-model="form.phone" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Email') }}</label>
            <input v-model="form.email" type="email" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('LinkedIn Profile') }}</label>
            <input v-model="form.linkedin_profile" type="text" placeholder="https://linkedin.com/in/..." class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Location') }}</label>
            <input v-model="form.location" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Technology Expert In') }}</label>
            <input v-model="form.technology_expert_in" type="text" placeholder="e.g. SAP, AWS, Python..." class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Skill Level') }}</label>
            <select v-model="form.skill_level" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
              <option value="">{{ __('Select') }}</option>
              <option>Beginner</option><option>Intermediate</option><option>Advanced</option><option>Expert</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Experience') }}</label>
            <input v-model="form.experience" type="text" placeholder="e.g. 5 years" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Availability') }}</label>
            <select v-model="form.availability" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
              <option value="">{{ __('Select') }}</option>
              <option>Available</option><option>Partially Available</option><option>Not Available</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Status') }}</label>
            <select v-model="form.status" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4">
              <option>Active</option><option>Inactive</option><option>Blacklisted</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Commercial (₹/day)') }}</label>
            <input v-model="form.commercial" type="number" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Company') }}</label>
            <input v-model="form.company" type="text" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4" />
          </div>
          <div class="col-span-2">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Remarks') }}</label>
            <textarea v-model="form.remarks" rows="3" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:border-outline-gray-4 resize-none" />
          </div>
        </div>
        <p v-if="formError" class="mt-3 text-sm text-ink-red-3">{{ formError }}</p>
      </div>
      <div class="px-6 pb-5 pt-3 flex justify-end gap-2">
        <Button variant="outline" :label="__('Cancel')" @click="showModal = false" />
        <Button variant="solid" :label="editingTrainer ? __('Save') : __('Create')" :loading="saving" @click="submitForm" />
      </div>
    </template>
  </Dialog>

  <!-- Column Manager -->
  <Dialog v-model="showColumnManager" :options="{ size: 'sm' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-ink-gray-9">{{ __('Manage Columns') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showColumnManager = false" />
        </div>
        <div class="space-y-2">
          <div v-for="col in allColumns" :key="col.key" class="flex items-center gap-2">
            <input type="checkbox" :id="'col-' + col.key" v-model="col.visible" class="rounded" />
            <label :for="'col-' + col.key" class="text-sm text-ink-gray-8 cursor-pointer">{{ col.label }}</label>
          </div>
        </div>
        <div class="mt-4 flex justify-end">
          <Button variant="solid" :label="__('Apply')" @click="showColumnManager = false" />
        </div>
      </div>
    </template>
  </Dialog>

  <!-- Delete Confirm -->
  <Dialog v-model="showDeleteDialog" :options="{ size: 'sm' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-ink-gray-9">{{ __('Delete Trainer') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showDeleteDialog = false" />
        </div>
        <p class="text-sm text-ink-gray-7">{{ __('Are you sure you want to delete "{0}"?', [deletingTrainer?.trainer_name]) }}</p>
        <div class="mt-4 flex justify-end gap-2">
          <Button variant="outline" :label="__('Cancel')" @click="showDeleteDialog = false" />
          <Button variant="solid" theme="red" :label="__('Delete')" :loading="deleting" @click="doDelete" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import TrainersIcon from '@/components/Icons/TrainersIcon.vue'
import { Breadcrumbs, Button, Dialog, call, toast } from 'frappe-ui'
import { ref, computed, reactive, onMounted } from 'vue'

const trainers = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageLength = ref(20)
const searchQuery = ref('')
const statusFilter = ref('')
const availabilityFilter = ref('')
const sortKey = ref('modified')
const sortOrder = ref('desc')
const selected = ref([])
const selectAll = ref(false)
const searchTimeout = ref(null)
const showModal = ref(false)
const editingTrainer = ref(null)
const saving = ref(false)
const formError = ref(null)
const showDeleteDialog = ref(false)
const deletingTrainer = ref(null)
const deleting = ref(false)
const showColumnManager = ref(false)

const emptyForm = () => ({
  trainer_name: '', phone: '', email: '', linkedin_profile: '',
  location: '', technology_expert_in: '', skill_level: '', experience: '',
  availability: '', status: 'Active', commercial: '', company: '', remarks: '',
})

const form = reactive(emptyForm())

const allColumns = ref([
  { key: 'trainer_name', label: 'Trainer Name', visible: true },
  { key: 'phone', label: 'Phone Number', visible: true },
  { key: 'technology_expert_in', label: 'Technology Expert In', visible: true },
  { key: 'linkedin_profile', label: 'LinkedIn Profile', visible: true },
  { key: 'location', label: 'Location', visible: true },
  { key: 'commercial', label: 'Commercial', visible: true },
  { key: 'status', label: 'Status', visible: true },
  { key: 'remarks', label: 'Remarks', visible: true },
  { key: 'email', label: 'Email', visible: false },
  { key: 'skill_level', label: 'Skill Level', visible: false },
  { key: 'experience', label: 'Experience', visible: false },
  { key: 'availability', label: 'Availability', visible: false },
  { key: 'company', label: 'Company', visible: false },
])

const visibleColumns = computed(() => allColumns.value.filter(c => c.visible))

async function loadTrainers() {
  loading.value = true
  try {
    const filters = {}
    if (statusFilter.value) filters.status = statusFilter.value
    if (availabilityFilter.value) filters.availability = availabilityFilter.value

    const result = await call('crm.api.trainers.get_trainers', {
      filters: JSON.stringify(filters),
      order_by: `${sortKey.value} ${sortOrder.value}`,
      page_length: pageLength.value,
      page: page.value,
      search: searchQuery.value || null,
    })
    trainers.value = result?.data || []
    total.value = result?.total || 0
  } catch (err) {
    console.error('Failed to load trainers:', err)
    trainers.value = []
  } finally {
    loading.value = false
  }
}

function onSearch() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => { page.value = 1; loadTrainers() }, 300)
}

function sortBy(key) {
  sortOrder.value = sortKey.value === key && sortOrder.value === 'asc' ? 'desc' : 'asc'
  sortKey.value = key
  loadTrainers()
}

function prevPage() { if (page.value > 1) { page.value--; loadTrainers() } }
function nextPage() { if (page.value * pageLength.value < total.value) { page.value++; loadTrainers() } }
function toggleSelectAll() { selected.value = selectAll.value ? trainers.value.map(t => t.name) : [] }

function openCreateModal() {
  editingTrainer.value = null
  Object.assign(form, emptyForm())
  formError.value = null
  showModal.value = true
}

function openEditModal(trainer) {
  editingTrainer.value = trainer
  Object.assign(form, {
    trainer_name: trainer.trainer_name || '', phone: trainer.phone || '',
    email: trainer.email || '', linkedin_profile: trainer.linkedin_profile || '',
    location: trainer.location || '', technology_expert_in: trainer.technology_expert_in || '',
    skill_level: trainer.skill_level || '', experience: trainer.experience || '',
    availability: trainer.availability || '', status: trainer.status || 'Active',
    commercial: trainer.commercial || '', company: trainer.company || '',
    remarks: trainer.remarks || '',
  })
  formError.value = null
  showModal.value = true
}

async function submitForm() {
  if (!form.trainer_name) { formError.value = __('Trainer Name is mandatory'); return }
  saving.value = true
  try {
    if (editingTrainer.value) {
      await call('crm.api.trainers.update_trainer', { name: editingTrainer.value.name, trainer: JSON.stringify({ ...form }) })
      toast.success(__('Trainer updated successfully'))
    } else {
      await call('crm.api.trainers.create_trainer', { trainer: JSON.stringify({ ...form }) })
      toast.success(__('Trainer created successfully'))
    }
    showModal.value = false
    loadTrainers()
  } catch (err) {
    formError.value = err?.message || __('Something went wrong')
  } finally {
    saving.value = false
  }
}

function confirmDelete(trainer) { deletingTrainer.value = trainer; showDeleteDialog.value = true }

async function doDelete() {
  deleting.value = true
  try {
    await call('crm.api.trainers.delete_trainer', { name: deletingTrainer.value.name })
    toast.success(__('Trainer deleted'))
    showDeleteDialog.value = false
    loadTrainers()
  } catch { toast.error(__('Failed to delete')) } finally { deleting.value = false }
}

async function bulkDelete() {
  for (const name of selected.value) {
    await call('crm.api.trainers.delete_trainer', { name }).catch(() => {})
  }
  selected.value = []; selectAll.value = false
  toast.success(__('Selected trainers deleted'))
  loadTrainers()
}

function statusClass(s) {
  return { 'bg-surface-green-1 text-ink-green-3': s === 'Active', 'bg-surface-gray-2 text-ink-gray-6': s === 'Inactive', 'bg-surface-red-1 text-ink-red-3': s === 'Blacklisted' }
}
function availabilityClass(a) {
  return { 'bg-surface-green-1 text-ink-green-3': a === 'Available', 'bg-surface-orange-1 text-ink-orange-3': a === 'Partially Available', 'bg-surface-red-1 text-ink-red-3': a === 'Not Available' }
}
function formatCurrency(v) {
  if (!v) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}
function stripHtml(html) {
  if (!html) return ''
  const s = html.replace(/<[^>]*>/g, '')
  return s.length > 60 ? s.substring(0, 60) + '...' : s
}

onMounted(() => loadTrainers())
</script>
