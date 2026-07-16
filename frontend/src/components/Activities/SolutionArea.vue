<template>
  <div
    class="activity group flex h-56 cursor-pointer flex-col justify-between gap-2 rounded-md bg-surface-gray-1 px-4 py-3 hover:bg-surface-gray-2"
  >
    <div class="flex items-center justify-between">
      <div class="truncate text-lg font-medium text-ink-gray-8">
        {{ solution.trainer_name }}
      </div>
      <Dropdown
        :options="[
          {
            label: __('Delete'),
            icon: 'trash-2',
            onClick: () => deleteSolution(solution.name),
          },
        ]"
        class="h-6 w-6"
        @click.stop
      >
        <Button
          icon="more-horizontal"
          variant="ghosted"
          class="!h-6 !w-6 hover:bg-surface-gray-2"
          @click.stop.prevent
        />
      </Dropdown>
    </div>
    <div class="flex-1 space-y-1.5 overflow-hidden text-p-sm text-ink-gray-6">
      <div v-if="solution.trainer_experience" class="truncate">
        {{ __('Experience') }}: {{ solution.trainer_experience }}
      </div>
      <div v-if="solution.location" class="truncate">
        {{ __('Location') }}: {{ solution.location }}
      </div>
      <div v-if="solution.duration" class="truncate">
        {{ __('Duration') }}: {{ solution.duration }}
      </div>
      <div v-if="solution.costing_for_training" class="truncate">
        {{ __('Costing') }}: {{ formatNumberIntoCurrency(solution.costing_for_training) }}
      </div>
      <div v-if="solution.lab_cost" class="truncate">
        {{ __('Lab Cost') }}: {{ formatNumberIntoCurrency(solution.lab_cost) }}
      </div>
      <div v-if="solution.attachments?.length" class="truncate">
        {{ solution.attachments.length }}
        {{ solution.attachments.length == 1 ? __('Attachment') : __('Attachments') }}
      </div>
    </div>
    <div class="mt-1 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 truncate">
        <UserAvatar :user="solution.owner" size="xs" />
        <div
          class="truncate text-sm text-ink-gray-8"
          :title="getUser(solution.owner).full_name"
        >
          {{ getUser(solution.owner).full_name }}
        </div>
      </div>
      <Tooltip :text="formatDate(solution.modified)">
        <div class="truncate text-sm text-ink-gray-7">
          {{ __(timeAgo(solution.modified)) }}
        </div>
      </Tooltip>
    </div>
  </div>
</template>
<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import { timeAgo, formatDate } from '@/utils'
import { Tooltip, Dropdown, call } from 'frappe-ui'
import { usersStore } from '@/stores/users'

defineProps({
  solution: { type: Object, default: () => ({}) },
})

const solutions = defineModel({ type: Object })

const { getUser } = usersStore()

function formatNumberIntoCurrency(value) {
  if (!value) return ''
  return '₹' + Number(value).toLocaleString('en-IN')
}

async function deleteSolution(name) {
  await call('frappe.client.delete', {
    doctype: 'CRM Solution',
    name,
  })
  solutions.value?.reload()
}
</script>
