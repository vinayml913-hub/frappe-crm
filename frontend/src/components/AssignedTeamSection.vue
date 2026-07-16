<template>
  <div class="flex flex-col gap-2 px-2 pt-5 pb-2.5">
    <!-- Current team members -->
    <div v-if="loading && !team.length" class="flex items-center gap-2 text-sm text-ink-gray-4 py-2">
      <LoadingIndicator class="h-4 w-4" />
      {{ __('Loading...') }}
    </div>

    <div v-else-if="!team.length" class="text-sm text-ink-gray-4 py-1">
      {{ __('No team members assigned yet') }}
    </div>

    <div v-else class="flex flex-col gap-1.5">
      <div
        v-for="member in team"
        :key="member.name"
        class="flex items-center justify-between gap-2 rounded-md px-1.5 py-1 hover:bg-surface-gray-1"
      >
        <div class="flex items-center gap-2 min-w-0">
          <UserAvatar :user="member.name" size="sm" />
          <Tooltip :text="member.name">
            <span class="text-sm text-ink-gray-8 truncate">{{ member.full_name }}</span>
          </Tooltip>
        </div>
        <Button
          v-if="canManage"
          variant="ghost"
          class="rounded-full !size-5 shrink-0"
          @click="removeMember(member.name)"
          :disabled="removingUser === member.name"
        >
          <template #icon>
            <FeatherIcon name="x" class="h-3 w-3 text-ink-gray-6" />
          </template>
        </Button>
      </div>
    </div>

    <!-- Add member — hidden entirely for users without manage permission -->
    <div v-if="canManage" class="mt-1">
      <div v-if="team.length >= maxSize" class="text-xs text-ink-gray-4 px-1.5">
        {{ __('Maximum of {0} team members reached', [maxSize]) }}
      </div>
      <Link
        v-else
        class="form-control"
        value=""
        doctype="User"
        :placeholder="__('Add team member')"
        :filters="{
          name: ['in', crmUserNames],
          ignore_user_type: 1,
        }"
        :hideMe="false"
        @change="(option) => option && addMember(option)"
      >
        <template #target="{ togglePopover }">
          <Button
            variant="ghost"
            class="w-full justify-start text-ink-gray-5"
            icon-left="plus"
            :label="__('Add team member')"
            @click="togglePopover"
          />
        </template>
        <template #item-prefix="{ option }">
          <UserAvatar class="mr-2" :user="option.value" size="sm" />
        </template>
        <template #item-label="{ option }">
          <span class="text-ink-gray-9">{{ getUser(option.value).full_name }}</span>
        </template>
      </Link>
    </div>

    <p v-if="errorMessage" class="text-xs text-ink-red-3 mt-1 px-1.5">{{ errorMessage }}</p>
  </div>
</template>

<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { Button, FeatherIcon, Tooltip, LoadingIndicator, call, toast } from 'frappe-ui'
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  dealName: { type: String, required: true },
})

const { users, getUser } = usersStore()
const crmUserNames = computed(() => users.data?.crmUsers?.map((u) => u.name) || [])

const team = ref([])
const canManage = ref(false)
const maxSize = ref(10)
const loading = ref(true)
const addingUser = ref(false)
const removingUser = ref(null)
const errorMessage = ref('')

async function loadTeam() {
  loading.value = true
  try {
    const result = await call('crm.api.deal_team.get_deal_team', { deal_name: props.dealName })
    team.value = result.team || []
    canManage.value = !!result.can_manage
    maxSize.value = result.max_size || 10
  } catch (err) {
    errorMessage.value = err?.messages?.[0]?.message || err?.message || __('Failed to load team')
  } finally {
    loading.value = false
  }
}

async function addMember(userEmail) {
  errorMessage.value = ''
  addingUser.value = true
  try {
    const result = await call('crm.api.deal_team.add_team_members', {
      deal_name: props.dealName,
      users: JSON.stringify([userEmail]),
    })
    team.value = result.team || []
    toast.success(__('Team member added'))
  } catch (err) {
    errorMessage.value = err?.messages?.[0]?.message || err?.message || __('Could not add team member')
    toast.error(errorMessage.value)
  } finally {
    addingUser.value = false
  }
}

async function removeMember(userEmail) {
  errorMessage.value = ''
  removingUser.value = userEmail
  try {
    const result = await call('crm.api.deal_team.remove_team_member', {
      deal_name: props.dealName,
      user: userEmail,
    })
    team.value = result.team || []
    toast.success(__('Team member removed'))
  } catch (err) {
    errorMessage.value = err?.messages?.[0]?.message || err?.message || __('Could not remove team member')
    toast.error(errorMessage.value)
  } finally {
    removingUser.value = null
  }
}

defineExpose({ reload: loadTeam })

onMounted(loadTeam)
</script>
