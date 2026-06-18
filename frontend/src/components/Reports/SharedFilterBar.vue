<template>
  <div class="px-5 pb-3 pt-3 flex items-center gap-3 flex-wrap border-b border-outline-gray-1">
    <Dropdown :options="presetOptions" :button="{
      label: presetLabel,
      class: '!w-44 justify-start [&>span]:mr-auto [&>svg]:text-ink-gray-5',
      variant: 'outline',
      iconRight: 'chevron-down',
      iconLeft: 'calendar',
    }" />

    <!-- Custom range inline controls — shown only when 'Custom Range' is the active preset -->
    <template v-if="showCustom">
      <input
        v-model="customFrom"
        type="date"
        class="rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none"
      />
      <span class="text-ink-gray-4 text-sm">{{ __('to') }}</span>
      <input
        v-model="customTo"
        type="date"
        class="rounded-md border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none"
      />
      <Button size="sm" variant="solid" :label="__('Apply')" :disabled="!customFrom || !customTo" @click="applyCustom" />
      <Button size="sm" variant="outline" :label="__('Reset')" @click="resetCustom" />
    </template>

    <!-- Employee filter — admins only. Server forces employees to their own data regardless. -->
    <Link
      v-if="isAdmin()"
      class="form-control w-56"
      variant="outline"
      :value="filters.user && getUser(filters.user).full_name"
      doctype="User"
      :filters="{ name: ['in', users.data?.crmUsers?.map((u) => u.name) || []], ignore_user_type: 1 }"
      :placeholder="__('All Employees')"
      @change="(v) => emit('update:user', v)"
    >
      <template #prefix>
        <UserAvatar v-if="filters.user" :user="filters.user" size="sm" class="mr-2" />
      </template>
    </Link>
    <Button v-if="isAdmin() && filters.user" variant="ghost" icon="x" @click="emit('update:user', null)" />
  </div>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { Dropdown, Button } from 'frappe-ui'
import { ref, computed } from 'vue'

const props = defineProps({
  filters: { type: Object, required: true },
  preset: { type: String, required: true },
})
const emit = defineEmits(['update:preset', 'update:customRange', 'update:user'])

const { users, getUser, isAdmin } = usersStore()

const PRESETS = [
  { key: 'last_7_days', label: 'Last 7 Days' },
  { key: 'last_30_days', label: 'Last 30 Days' },
  { key: 'last_60_days', label: 'Last 60 Days' },
  { key: 'last_90_days', label: 'Last 90 Days' },
  { key: 'last_180_days', label: 'Last 180 Days' },
  { key: 'last_360_days', label: 'Last 360 Days' },
  { key: 'ever', label: 'Ever' },
  { key: 'custom', label: 'Custom Range' },
]

const presetLabel = computed(() => PRESETS.find((p) => p.key === props.preset)?.label || __('Last 30 Days'))
const showCustom = computed(() => props.preset === 'custom')

const presetOptions = PRESETS.map((p) => ({
  label: __(p.label),
  onClick: () => emit('update:preset', p.key),
}))

const customFrom = ref(props.filters.customFrom || '')
const customTo = ref(props.filters.customTo || '')

function applyCustom() {
  if (!customFrom.value || !customTo.value) return
  emit('update:customRange', { from: customFrom.value, to: customTo.value })
}

function resetCustom() {
  customFrom.value = ''
  customTo.value = ''
  emit('update:preset', 'last_30_days')
}
</script>
