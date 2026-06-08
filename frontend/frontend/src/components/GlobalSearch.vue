<template>
  <div class="relative mx-2 mb-1">
    <!-- Search Input -->
    <div class="relative">
      <input
        ref="searchInput"
        v-model="query"
        type="text"
        :placeholder="isSidebarCollapsed ? '' : __('Search...')"
        class="w-full rounded-md border border-outline-gray-2 bg-surface-gray-2 py-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:border-outline-gray-4 focus:bg-surface-white focus:outline-none transition-all"
        :class="isSidebarCollapsed ? 'pl-2 pr-2 cursor-pointer' : 'pl-8 pr-3'"
        @input="onSearch"
        @focus="showResults = true"
        @keydown.escape="close"
        @keydown.enter="goToFirst"
        @click="isSidebarCollapsed && expandSearch()"
      />
      <svg
        class="absolute top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-gray-4 pointer-events-none transition-all"
        :class="isSidebarCollapsed ? 'left-1.5' : 'left-2.5'"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
      </svg>
      <button
        v-if="query && !isSidebarCollapsed"
        class="absolute right-2 top-1/2 -translate-y-1/2 text-ink-gray-4 hover:text-ink-gray-7"
        @click="close"
      >
        <svg class="h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Results Dropdown -->
    <div
      v-if="showResults && query.length >= 2 && !isSidebarCollapsed"
      class="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-outline-gray-2 bg-surface-white shadow-xl overflow-hidden"
    >
      <!-- Loading -->
      <div v-if="loading" class="px-4 py-3 text-sm text-ink-gray-4 text-center">
        {{ __('Searching...') }}
      </div>

      <!-- Results -->
      <template v-else-if="hasResults">
        <!-- Leads -->
        <div v-if="results.leads.length">
          <div class="px-3 py-1.5 text-xs font-semibold text-ink-gray-4 bg-surface-gray-1 uppercase tracking-wide">
            {{ __('Leads') }}
          </div>
          <div
            v-for="item in results.leads"
            :key="'lead-' + item.name"
            class="flex items-center gap-2.5 px-3 py-2 hover:bg-surface-gray-2 cursor-pointer"
            @click="navigate('Lead', { leadId: item.name })"
          >
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-surface-blue-1 text-xs font-medium text-ink-blue-3">
              {{ (item.lead_name || item.name).charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink-gray-9">{{ item.lead_name || item.name }}</p>
              <p v-if="item.email" class="truncate text-xs text-ink-gray-5">{{ item.email }}</p>
            </div>
            <span class="flex-shrink-0 rounded-full bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-5">Lead</span>
          </div>
        </div>

        <!-- Deals -->
        <div v-if="results.deals.length">
          <div class="px-3 py-1.5 text-xs font-semibold text-ink-gray-4 bg-surface-gray-1 uppercase tracking-wide">
            {{ __('Deals') }}
          </div>
          <div
            v-for="item in results.deals"
            :key="'deal-' + item.name"
            class="flex items-center gap-2.5 px-3 py-2 hover:bg-surface-gray-2 cursor-pointer"
            @click="navigate('Deal', { dealId: item.name })"
          >
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-surface-green-1 text-xs font-medium text-ink-green-3">
              {{ (item.organization || item.name).charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink-gray-9">{{ item.organization || item.name }}</p>
              <p v-if="item.status" class="truncate text-xs text-ink-gray-5">{{ item.status }}</p>
            </div>
            <span class="flex-shrink-0 rounded-full bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-5">Deal</span>
          </div>
        </div>

        <!-- Contacts -->
        <div v-if="results.contacts.length">
          <div class="px-3 py-1.5 text-xs font-semibold text-ink-gray-4 bg-surface-gray-1 uppercase tracking-wide">
            {{ __('Contacts') }}
          </div>
          <div
            v-for="item in results.contacts"
            :key="'contact-' + item.name"
            class="flex items-center gap-2.5 px-3 py-2 hover:bg-surface-gray-2 cursor-pointer"
            @click="navigate('Contact', { contactId: item.name })"
          >
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-surface-purple-1 text-xs font-medium text-ink-purple-3">
              {{ (item.full_name || item.name).charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink-gray-9">{{ item.full_name || item.name }}</p>
              <p v-if="item.email_id" class="truncate text-xs text-ink-gray-5">{{ item.email_id }}</p>
            </div>
            <span class="flex-shrink-0 rounded-full bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-5">Contact</span>
          </div>
        </div>
      </template>

      <!-- No results -->
      <div v-else class="px-4 py-4 text-center text-sm text-ink-gray-4">
        {{ __('No results for "{0}"', [query]) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { call } from 'frappe-ui'

const props = defineProps({
  isSidebarCollapsed: { type: Boolean, default: false },
})

const router = useRouter()
const query = ref('')
const loading = ref(false)
const showResults = ref(false)
const searchInput = ref(null)
const searchTimeout = ref(null)

const results = ref({
  leads: [],
  deals: [],
  contacts: [],
})

const hasResults = computed(() =>
  results.value.leads.length > 0 ||
  results.value.deals.length > 0 ||
  results.value.contacts.length > 0
)

function onSearch() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  if (query.value.length < 2) {
    results.value = { leads: [], deals: [], contacts: [] }
    return
  }
  loading.value = true
  searchTimeout.value = setTimeout(() => fetchResults(), 300)
}

async function fetchResults() {
  const q = query.value
  if (!q || q.length < 2) return

  try {
    const [leads, deals, contacts] = await Promise.all([
      call('frappe.client.get_list', {
        doctype: 'CRM Lead',
        filters: [['lead_name', 'like', `%${q}%`]],
        fields: ['name', 'lead_name', 'email', 'mobile_no'],
        limit: 5,
      }).catch(() => []),
      call('frappe.client.get_list', {
        doctype: 'CRM Deal',
        filters: [['organization', 'like', `%${q}%`]],
        fields: ['name', 'organization', 'status'],
        limit: 5,
      }).catch(() => []),
      call('frappe.client.get_list', {
        doctype: 'Contact',
        filters: [['full_name', 'like', `%${q}%`]],
        fields: ['name', 'full_name', 'email_id', 'mobile_no'],
        limit: 5,
      }).catch(() => []),
    ])

    results.value = {
      leads: leads || [],
      deals: deals || [],
      contacts: contacts || [],
    }
  } catch (err) {
    console.error('Search error:', err)
  } finally {
    loading.value = false
  }
}

function navigate(routeName, params) {
  close()
  router.push({ name: routeName, params })
}

function goToFirst() {
  if (results.value.leads.length) {
    navigate('Lead', { leadId: results.value.leads[0].name })
  } else if (results.value.deals.length) {
    navigate('Deal', { dealId: results.value.deals[0].name })
  } else if (results.value.contacts.length) {
    navigate('Contact', { contactId: results.value.contacts[0].name })
  }
}

function close() {
  query.value = ''
  showResults.value = false
  results.value = { leads: [], deals: [], contacts: [] }
}

function expandSearch() {
  // When collapsed, clicking search icon should expand sidebar
}

function handleClickOutside(e) {
  if (searchInput.value && !searchInput.value.closest('.relative')?.contains(e.target)) {
    showResults.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))
</script>
