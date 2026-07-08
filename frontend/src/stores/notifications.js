import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

export const visible = ref(false)

export const notifications = createResource({
  url: 'crm.api.notifications.get_notifications',
  initialData: [],
  auto: true,
})

export const unreadNotificationsCount = computed(
  () => notifications.data?.filter((n) => !n.read).length || 0,
)

// Polling fallback: refresh every 60s in case the websocket
// connection silently dropped and stopped delivering
// real-time 'crm_notification' events.
let pollInterval = null
export function startNotificationPolling() {
  if (pollInterval) return
  pollInterval = setInterval(() => {
    notifications.reload()
  }, 60000)
}
export function stopNotificationPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

export const notificationsStore = defineStore('crm-notifications', () => {
  const mark_as_read = createResource({
    url: 'crm.api.notifications.mark_as_read',
    onSuccess: () => {
      mark_as_read.params = {}
      notifications.reload()
    },
  })

  function toggle() {
    visible.value = !visible.value
  }

  function mark_doc_as_read(doc) {
    mark_as_read.params = { doc: doc }
    mark_as_read.reload()
    toggle()
  }

  return {
    unreadNotificationsCount,
    mark_as_read,
    mark_doc_as_read,
    toggle,
  }
})
