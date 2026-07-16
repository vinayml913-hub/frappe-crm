<template>
  <Dropdown :options="exportOptions" :button="{ label: __('Export'), iconLeft: 'download', variant: 'outline' }" />
</template>

<script setup>
import { Dropdown } from 'frappe-ui'

const props = defineProps({
  fromDate: { type: String, default: null },
  toDate: { type: String, default: null },
  userId: { type: String, default: null },
  quickRange: { type: String, default: null },
  source: { type: String, default: 'leaderboard' },
})

// Direct browser navigation to the whitelisted method, exactly mirroring
// the existing export pattern already used in this app for list-view
// exports (frappe.desk.reportview.export_query via window.open — see
// ViewControls.vue). frappe.response['type'] = 'download' on the backend
// triggers the file download.
function buildUrl(format) {
  const params = new URLSearchParams()
  if (props.fromDate) params.set('fromDate', props.fromDate)
  if (props.toDate) params.set('toDate', props.toDate)
  if (props.userId) params.set('userId', props.userId)
  if (props.quickRange) params.set('quickRange', props.quickRange)
  params.set('format', format)
  params.set('source', props.source)
  return `/api/method/crm.api.reports.export_report?${params.toString()}`
}

const exportOptions = [
  { label: __('Export Excel'), onClick: () => window.open(buildUrl('xlsx'), '_blank') },
  { label: __('Export CSV'), onClick: () => window.open(buildUrl('csv'), '_blank') },
]
</script>
