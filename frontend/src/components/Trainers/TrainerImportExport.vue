<template>
  <!-- Toolbar buttons - rendered by the parent via the default slot pattern below -->

  <!-- ── Import Dialog ──────────────────────────────────────────────── -->
  <Dialog v-model="showImportModal" :options="{ size: '4xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Import Trainers') }}</h3>
            <p class="text-sm text-ink-gray-5 mt-0.5">{{ __('Upload an Excel or CSV file to bulk import trainers') }}</p>
          </div>
          <Button variant="ghost" class="w-7" icon="x" @click="closeImportModal" />
        </div>

        <!-- Step 1: Upload zone (shown until a file is parsed) -->
        <div v-if="!preview">
          <div class="flex justify-end mb-3">
            <Button variant="outline" icon-left="download" :label="__('Download Excel Template')" @click="downloadTemplate" />
          </div>

          <div
            class="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-outline-gray-modals min-h-64 text-ink-gray-5 transition-colors"
            :class="{ 'bg-surface-blue-1 border-outline-blue-2': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
          >
            <svg class="h-10 w-10 text-ink-gray-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <div class="text-center">
              <p>{{ __('Drag & drop your .xlsx or .csv file here') }}</p>
              <p class="text-xs text-ink-gray-4 mt-1">{{ __('or') }}</p>
            </div>
            <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" class="hidden" @change="onFileInput" />
            <Button variant="outline" :label="__('Browse Files')" @click="fileInput.click()" />
          </div>

          <p v-if="uploadError" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-3 py-2 mt-3">{{ uploadError }}</p>
          <div v-if="parsing" class="flex items-center gap-2 mt-3 text-sm text-ink-gray-5">
            <span class="inline-block h-3 w-3 rounded-full border-2 border-ink-gray-4 border-t-transparent animate-spin"></span>
            {{ __('Reading and validating file…') }}
          </div>
        </div>

        <!-- Step 2: Preview grid -->
        <div v-else>
          <div class="grid grid-cols-4 gap-3 mb-4">
            <div class="rounded-md bg-surface-gray-1 px-3 py-2">
              <p class="text-xs text-ink-gray-5">{{ __('Total Rows') }}</p>
              <p class="text-lg font-semibold text-ink-gray-9">{{ preview.total_rows }}</p>
            </div>
            <div class="rounded-md bg-surface-green-1 px-3 py-2">
              <p class="text-xs text-ink-green-4">{{ __('Valid') }}</p>
              <p class="text-lg font-semibold text-ink-green-4">{{ preview.valid_rows }}</p>
            </div>
            <div class="rounded-md bg-surface-orange-1 px-3 py-2">
              <p class="text-xs text-ink-orange-4">{{ __('Duplicates') }}</p>
              <p class="text-lg font-semibold text-ink-orange-4">{{ preview.duplicate_rows }}</p>
            </div>
            <div class="rounded-md bg-surface-red-1 px-3 py-2">
              <p class="text-xs text-ink-red-4">{{ __('Invalid') }}</p>
              <p class="text-lg font-semibold text-ink-red-4">{{ preview.invalid_rows }}</p>
            </div>
          </div>

          <div class="max-h-80 overflow-y-auto rounded-md border border-outline-gray-1 mb-4">
            <table class="w-full text-xs">
              <thead class="bg-surface-gray-1 sticky top-0">
                <tr>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Row') }}</th>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Name') }}</th>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Email') }}</th>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Phone') }}</th>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Status') }}</th>
                  <th class="text-left px-2 py-2 font-medium text-ink-gray-5">{{ __('Issue') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-gray-1">
                <tr
                  v-for="row in preview.rows"
                  :key="row.row_number"
                  :class="rowClass(row)"
                >
                  <td class="px-2 py-1.5 text-ink-gray-6">{{ row.row_number }}</td>
                  <td class="px-2 py-1.5 text-ink-gray-8">{{ row.data.trainer_name || '—' }}</td>
                  <td class="px-2 py-1.5 text-ink-gray-7">{{ row.data.email || '—' }}</td>
                  <td class="px-2 py-1.5 text-ink-gray-7">{{ row.data.phone || '—' }}</td>
                  <td class="px-2 py-1.5">
                    <span v-if="row.errors.length" class="text-ink-red-3 font-medium">{{ __('Invalid') }}</span>
                    <span v-else-if="row.duplicate_of || row.duplicate_in_file" class="text-ink-orange-4 font-medium">{{ __('Duplicate') }}</span>
                    <span v-else class="text-ink-green-4 font-medium">{{ __('Valid') }}</span>
                  </td>
                  <td class="px-2 py-1.5 text-ink-gray-5">
                    <span v-if="row.errors.length">{{ row.errors.join('; ') }}</span>
                    <span v-else-if="row.duplicate_of">{{ __('Matches existing trainer {0}', [row.duplicate_of]) }}</span>
                    <span v-else-if="row.duplicate_in_file">{{ __('Duplicate within file') }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="preview.duplicate_rows > 0" class="mb-4">
            <label class="text-xs font-medium text-ink-gray-6 mb-1.5 block">{{ __('How should duplicates be handled?') }}</label>
            <div class="flex gap-2">
              <button
                v-for="opt in importModeOptions"
                :key="opt.value"
                class="px-3 py-1.5 rounded-md text-sm border"
                :class="importMode === opt.value ? 'border-ink-blue-3 bg-surface-blue-1 text-ink-blue-3' : 'border-outline-gray-2 text-ink-gray-6'"
                @click="importMode = opt.value"
              >{{ opt.label }}</button>
            </div>
          </div>

          <p v-if="importError" class="text-sm text-ink-red-3 bg-surface-red-1 rounded-md px-3 py-2 mb-3">{{ importError }}</p>

          <div class="flex justify-between items-center">
            <Button variant="ghost" :label="__('Upload a different file')" @click="resetUpload" />
            <div class="flex gap-2">
              <Button variant="outline" :label="__('Cancel')" @click="closeImportModal" />
              <Button
                variant="solid"
                :label="__('Import {0} Records', [importableCount])"
                :loading="importing"
                :disabled="importableCount === 0"
                @click="runImport"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </Dialog>

  <!-- ── Import Result Summary Dialog ──────────────────────────────── -->
  <Dialog v-model="showResultModal" :options="{ size: 'lg' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Import Complete') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showResultModal = false" />
        </div>
        <div v-if="importResult?.queued" class="text-sm text-ink-gray-6 bg-surface-blue-1 rounded-md px-3 py-3">
          {{ importResult.message }}
        </div>
        <div v-else class="grid grid-cols-2 gap-3">
          <div class="rounded-md bg-surface-gray-1 px-3 py-3">
            <p class="text-xs text-ink-gray-5">{{ __('Total Rows') }}</p>
            <p class="text-xl font-semibold text-ink-gray-9">{{ importResult?.total_rows ?? 0 }}</p>
          </div>
          <div class="rounded-md bg-surface-green-1 px-3 py-3">
            <p class="text-xs text-ink-green-4">{{ __('Imported') }}</p>
            <p class="text-xl font-semibold text-ink-green-4">{{ importResult?.success_count ?? 0 }}</p>
          </div>
          <div class="rounded-md bg-surface-blue-1 px-3 py-3">
            <p class="text-xs text-ink-blue-4">{{ __('Updated') }}</p>
            <p class="text-xl font-semibold text-ink-blue-4">{{ importResult?.updated_count ?? 0 }}</p>
          </div>
          <div class="rounded-md bg-surface-gray-2 px-3 py-3">
            <p class="text-xs text-ink-gray-5">{{ __('Skipped') }}</p>
            <p class="text-xl font-semibold text-ink-gray-7">{{ importResult?.skipped_count ?? 0 }}</p>
          </div>
          <div class="rounded-md bg-surface-red-1 px-3 py-3 col-span-2">
            <p class="text-xs text-ink-red-4">{{ __('Failed') }}</p>
            <p class="text-xl font-semibold text-ink-red-4">{{ importResult?.failed_count ?? 0 }}</p>
          </div>
        </div>
        <div class="flex justify-end mt-5">
          <Button variant="solid" :label="__('Done')" @click="finishImportFlow" />
        </div>
      </div>
    </template>
  </Dialog>

  <!-- ── Import History Dialog ──────────────────────────────────────── -->
  <Dialog v-model="showHistoryModal" :options="{ size: '3xl' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Import History') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showHistoryModal = false" />
        </div>
        <div class="max-h-96 overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="bg-surface-gray-1 sticky top-0">
              <tr>
                <th class="text-left px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('File') }}</th>
                <th class="text-left px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('By') }}</th>
                <th class="text-left px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Date') }}</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Total') }}</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('OK') }}</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-ink-gray-5">{{ __('Failed') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-gray-1">
              <tr v-for="log in importLogs" :key="log.name">
                <td class="px-3 py-2 text-ink-gray-8">{{ log.file_name }}</td>
                <td class="px-3 py-2 text-ink-gray-6">{{ log.imported_by }}</td>
                <td class="px-3 py-2 text-ink-gray-6">{{ formatDateTime(log.import_datetime) }}</td>
                <td class="px-3 py-2 text-right text-ink-gray-7">{{ log.total_records }}</td>
                <td class="px-3 py-2 text-right text-ink-green-4">{{ log.success_count + log.updated_count }}</td>
                <td class="px-3 py-2 text-right" :class="log.failed_count > 0 ? 'text-ink-red-3 font-medium' : 'text-ink-gray-5'">{{ log.failed_count }}</td>
              </tr>
              <tr v-if="!importLogs.length">
                <td colspan="6" class="text-center py-6 text-ink-gray-4">{{ __('No imports yet') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </Dialog>

  <!-- ── Export Menu (popover triggered from parent) ─────────────────── -->
  <Dialog v-model="showExportModal" :options="{ size: 'sm' }">
    <template #body>
      <div class="bg-surface-modal px-6 pb-6 pt-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-ink-gray-9">{{ __('Export Trainers') }}</h3>
          <Button variant="ghost" class="w-7" icon="x" @click="showExportModal = false" />
        </div>
        <div class="space-y-3">
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1.5 block">{{ __('Which trainers?') }}</label>
            <select v-model="exportPreset" class="w-full rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none">
              <option value="all">{{ __('All Trainers') }}</option>
              <option value="active">{{ __('Active Trainers') }}</option>
              <option value="available">{{ __('Available Trainers') }}</option>
              <option value="filtered">{{ __('Current Filtered View') }}</option>
            </select>
          </div>
          <div class="flex gap-2">
            <Button class="flex-1" variant="outline" :label="__('Export Excel')" @click="doExport('xlsx')" />
            <Button class="flex-1" variant="outline" :label="__('Export CSV')" @click="doExport('csv')" />
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Dialog, Button, call, toast } from 'frappe-ui'
import { ref, computed } from 'vue'

// currentFilters lets the parent Trainers.vue pass its live status/availability
// filter state through, so "Current Filtered View" export matches exactly
// what the user is looking at on screen right now. currentSearch does the
// same for the universal name/phone/email search box, which is applied as
// an OR match server-side rather than living inside currentFilters.
const props = defineProps({
  currentFilters: { type: Object, default: () => ({}) },
  currentSearch: { type: String, default: '' },
})

// ── Import state ─────────────────────────────────────────────────────
const showImportModal = ref(false)
const showResultModal = ref(false)
const showHistoryModal = ref(false)
const showExportModal = ref(false)

const fileInput = ref(null)
const isDragging = ref(false)
const uploadError = ref(null)
const parsing = ref(false)
const preview = ref(null)
const uploadedFileName = ref('')
const uploadedFileUrl = ref('')

const importMode = ref('skip')
const importModeOptions = [
  { value: 'skip', label: __('Skip Existing') },
  { value: 'update', label: __('Update Existing') },
  { value: 'create', label: __('Create New Only') },
]

const importing = ref(false)
const importError = ref(null)
const importResult = ref(null)
const importLogs = ref([])

const exportPreset = ref('all')

const importableCount = computed(() => {
  if (!preview.value) return 0
  return preview.value.rows.filter((r) => !r.errors.length).length
})

function openImportModal() {
  resetUpload()
  showImportModal.value = true
}

function closeImportModal() {
  showImportModal.value = false
  resetUpload()
}

function resetUpload() {
  preview.value = null
  uploadError.value = null
  parsing.value = false
  uploadedFileName.value = ''
  uploadedFileUrl.value = ''
  importMode.value = 'skip'
  importError.value = null
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file) handleFile(file)
}

function onFileInput() {
  const file = fileInput.value.files?.[0]
  if (file) handleFile(file)
  fileInput.value.value = ''
}

async function handleFile(file) {
  uploadError.value = null
  const validExt = /\.(xlsx|xls|csv)$/i.test(file.name)
  if (!validExt) {
    uploadError.value = __('Only .xlsx and .csv files are supported')
    return
  }

  parsing.value = true
  uploadedFileName.value = file.name

  try {
    // Upload via Frappe's standard file upload endpoint (same one used
    // throughout this app's existing FilesUploaderArea component) so the
    // resulting file_url can be read server-side with frappe.get_doc("File", ...).
    const formData = new FormData()
    formData.append('file', file)
    formData.append('is_private', 1)

    const headers = {}
    if (window.csrf_token && window.csrf_token !== '{{ csrf_token }}') {
      headers['X-Frappe-CSRF-Token'] = window.csrf_token
    }

    const uploadRes = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers,
      body: formData,
    })
    const uploadJson = await uploadRes.json()
    const fileUrl = uploadJson?.message?.file_url
    if (!fileUrl) throw new Error('Upload failed')
    uploadedFileUrl.value = fileUrl

    const result = await call('crm.api.trainers_import.parse_and_validate', { file_url: fileUrl })
    preview.value = result
  } catch (err) {
    uploadError.value = err?.messages?.[0]?.message || err?.message || __('Failed to read file. Please check the format and try again.')
  } finally {
    parsing.value = false
  }
}

async function downloadTemplate() {
  window.open('/api/method/crm.api.trainers_import.download_template', '_blank')
}

async function runImport() {
  importError.value = null
  importing.value = true
  try {
    const rows = preview.value.rows.filter((r) => !r.errors.length)
    const result = await call('crm.api.trainers_import.commit_import', {
      rows: JSON.stringify(rows),
      mode: importMode.value,
      file_name: uploadedFileName.value,
    })
    importResult.value = result
    showImportModal.value = false
    showResultModal.value = true
  } catch (err) {
    importError.value = err?.messages?.[0]?.message || err?.message || __('Import failed')
  } finally {
    importing.value = false
  }
}

const emit = defineEmits(['imported'])

function finishImportFlow() {
  showResultModal.value = false
  resetUpload()
  toast.success(__('Import finished'))
  emit('imported') // parent Trainers.vue should call loadTrainers() on this
}

function rowClass(row) {
  if (row.errors.length) return 'bg-surface-red-1/30'
  if (row.duplicate_of || row.duplicate_in_file) return 'bg-surface-orange-1/30'
  return ''
}

async function openHistoryModal() {
  showHistoryModal.value = true
  try {
    importLogs.value = await call('crm.api.trainers_import.get_import_logs') || []
  } catch {
    importLogs.value = []
  }
}

async function openExportModal() {
  showExportModal.value = true
}

async function doExport(format) {
  let url = `/api/method/crm.api.trainers_import.export_trainers?format=${format}`
  if (exportPreset.value === 'filtered') {
    url += `&filters=${encodeURIComponent(JSON.stringify(props.currentFilters || {}))}`
    if (props.currentSearch) {
      url += `&search=${encodeURIComponent(props.currentSearch)}`
    }
  } else {
    url += `&preset=${exportPreset.value}`
  }
  window.open(url, '_blank')
  showExportModal.value = false
}

function formatDateTime(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

defineExpose({ openImportModal, openHistoryModal, openExportModal })
</script>
