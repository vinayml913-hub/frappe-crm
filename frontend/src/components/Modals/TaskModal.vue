<template>
  <Dialog v-model="show" :options="{ size: 'xl' }">
    <template #body-title>
      <div class="flex items-center gap-3">
        <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
          {{ editMode ? __('Edit Task') : __('Create Task') }}
        </h3>
        <Button
          v-if="task?.reference_docname"
          size="sm"
          :label="
            task.reference_doctype == 'CRM Deal'
              ? __('Open Deal')
              : __('Open Lead')
          "
          :iconRight="ArrowUpRightIcon"
          @click="redirect()"
        />
      </div>
    </template>
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="space-y-1.5">
          <FormLabel :label="__('Title')" required />
          <TextInput
            ref="title"
            v-model="_task.title"
            :placeholder="__('Call with John Doe')"
            required
          />
        </div>
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">
            {{ __('Description') }}
          </div>
          <TextEditor
            ref="description"
            variant="outline"
            editor-class="!prose-sm overflow-auto min-h-[180px] max-h-80 py-1.5 px-2 rounded border border-[--surface-gray-2] bg-surface-gray-2 placeholder-ink-gray-4 hover:border-outline-gray-modals hover:bg-surface-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 text-ink-gray-8 transition-colors"
            :bubbleMenu="true"
            :content="_task.description"
            :placeholder="
              __('Took a call with John Doe and discussed the new project.')
            "
            @change="(val) => (_task.description = val)"
          />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Dropdown :options="taskStatusOptions(updateTaskStatus)">
            <Button :label="_task.status">
              <template #prefix>
                <TaskStatusIcon :status="_task.status" />
              </template>
            </Button>
          </Dropdown>
          <div class="w-36">
            <DateTimePicker
              v-model="_task.due_date"
              class="datepicker"
              :placeholder="__('01/04/2024 11:30 PM')"
              :format="getFormat('', '', true, true, false)"
              input-class="border-none"
            />
          </div>
          <Dropdown :options="taskPriorityOptions(updateTaskPriority)">
            <Button :label="_task.priority">
              <template #prefix>
                <TaskPriorityIcon :priority="_task.priority" />
              </template>
            </Button>
          </Dropdown>
        </div>
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">
            {{ __('Assigned Team') }}
            <span v-if="editMode && !canEditTeamMember" class="text-ink-gray-4">
              ({{ __('view only') }})
            </span>
          </div>
          <div
            class="w-full min-h-9 flex flex-wrap items-center gap-1.5 p-1.5 rounded-lg bg-surface-gray-2"
          >
            <div
              v-for="member in taskTeam"
              :key="member.name"
              class="flex items-center text-sm p-0.5 pl-1 text-ink-gray-6 border border-outline-gray-1 bg-surface-modal rounded-full"
            >
              <UserAvatar :user="member.name" size="sm" />
              <div class="ml-1">{{ member.full_name }}</div>
              <Button
                v-if="canEditTeamMember"
                variant="ghost"
                class="rounded-full !size-4 m-1"
                @click="removeTeamMember(member.name)"
              >
                <template #icon>
                  <FeatherIcon name="x" class="h-3 w-3 text-ink-gray-6" />
                </template>
              </Button>
            </div>
            <Link
              v-if="canEditTeamMember && taskTeam.length < maxTeamSize"
              class="form-control flex-1 min-w-[120px]"
              value=""
              doctype="User"
              :placeholder="__('Add people')"
              :filters="{
                name: ['in', users.data.crmUsers?.map((user) => user.name)],
                ignore_user_type: 1,
              }"
              :hideMe="false"
              @change="(option) => option && addTeamMember(option)"
            >
              <template #item-prefix="{ option }">
                <UserAvatar class="mr-2" :user="option.value" size="sm" />
              </template>
              <template #item-label="{ option }">
                <Tooltip :text="option.value">
                  <div class="cursor-pointer text-ink-gray-9">
                    {{ getUser(option.value).full_name }}
                  </div>
                </Tooltip>
              </template>
            </Link>
            <span
              v-else-if="canEditTeamMember && taskTeam.length >= maxTeamSize"
              class="text-xs text-ink-gray-4 px-1.5"
            >
              {{ __('Maximum of {0} people reached', [maxTeamSize]) }}
            </span>
            <span v-else-if="!taskTeam.length" class="text-xs text-ink-gray-4 px-1.5">
              {{ __('No one assigned yet') }}
            </span>
          </div>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button
          :label="editMode ? __('Update') : __('Create')"
          variant="solid"
          :loading="createTaskResource.loading || updateTaskResource.loading"
          @click="updateTask"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { taskStatusOptions, taskPriorityOptions, getFormat } from '@/utils'
import { usersStore } from '@/stores/users'
import { useTelemetry } from 'frappe-ui/frappe'
import {
  TextEditor,
  Dropdown,
  Tooltip,
  DateTimePicker,
  createResource,
  call,
  toast,
  TextInput,
  FormLabel,
  FeatherIcon,
} from 'frappe-ui'
import { useOnboarding } from 'frappe-ui/frappe'
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  task: { type: Object, default: () => ({}) },
  doctype: { type: String, default: 'CRM Lead' },
  doc: { type: String, default: '' },
})

const show = defineModel({ type: Boolean })
const tasks = defineModel('reloadTasks', { type: Object, default: () => ({}) })

const emit = defineEmits(['updateTask', 'after'])

const router = useRouter()
const { users, getUser } = usersStore()
const { updateOnboardingStep } = useOnboarding('frappecrm')
const { capture } = useTelemetry()

const title = ref(null)
const editMode = ref(false)
const _task = ref({
  title: '',
  description: '',
  due_date: '',
  status: 'Backlog',
  priority: 'Low',
  reference_doctype: props.doctype,
  reference_docname: null,
})

// ── Assigned Team (multi-person) ─────────────────────────────────────
//
// Replaces the old single `assigned_to` Link picker per requirement.
// `assigned_to` on the CRM Task doc itself is left untouched in the
// schema (still read by ~10 other places as a single value) - it is
// now kept in sync automatically, server-side, by crm.api.task_team as
// a mirror of the first-added ("primary") team member. The UI here
// never reads or writes _task.value.assigned_to directly any more.
//
// CREATE mode: picks are staged locally in taskTeam (no API calls yet -
// the task doesn't exist), then sent via assign_team_on_create right
// after the task is successfully inserted (same pattern as Deal's
// creation-time "Assign To" picker in DealModal.vue).
//
// EDIT mode: taskTeam reflects the REAL current team (loaded via
// get_task_team when the modal opens on an existing task), and
// add/remove act immediately against the live API, matching how the
// Deal's "Assigned Team" sidebar section already behaves - not batched
// with the Update button.
const maxTeamSize = 10
const taskTeam = ref([])
const canManageExistingTeam = ref(false)
const loadingTeam = ref(false)

// Anyone may set the initial team while creating a task (creator
// exception, mirrors Deal). Once a task exists, only users the backend
// says can manage the team (System Manager / Sales Manager / Solution
// Manager) may add or remove - reflected here via canManageExistingTeam,
// which is populated from get_task_team()'s `can_manage` flag.
const canEditTeamMember = ref(true)

function addTeamMember(userEmail) {
  if (taskTeam.value.find((m) => m.name === userEmail)) return
  if (taskTeam.value.length >= maxTeamSize) return

  if (!editMode.value) {
    taskTeam.value.push({ name: userEmail, full_name: getUser(userEmail).full_name })
    return
  }

  // Edit mode - existing task, hits the live manager-gated API.
  call('crm.api.task_team.add_team_members', {
    task_name: _task.value.name,
    users: JSON.stringify([userEmail]),
  })
    .then((result) => {
      taskTeam.value = result.team || []
      toast.success(__('Team member added'))
    })
    .catch((err) => {
      toast.error(err?.messages?.[0]?.message || err?.message || __('Could not add team member'))
    })
}

function removeTeamMember(userEmail) {
  if (!editMode.value) {
    taskTeam.value = taskTeam.value.filter((m) => m.name !== userEmail)
    return
  }

  call('crm.api.task_team.remove_team_member', {
    task_name: _task.value.name,
    user: userEmail,
  })
    .then((result) => {
      taskTeam.value = result.team || []
      toast.success(__('Team member removed'))
    })
    .catch((err) => {
      toast.error(err?.messages?.[0]?.message || err?.message || __('Could not remove team member'))
    })
}

async function loadExistingTeam() {
  if (!_task.value.name) return
  loadingTeam.value = true
  try {
    const result = await call('crm.api.task_team.get_task_team', { task_name: _task.value.name })
    taskTeam.value = result.team || []
    canManageExistingTeam.value = !!result.can_manage
    canEditTeamMember.value = canManageExistingTeam.value
  } catch (err) {
    taskTeam.value = []
    canEditTeamMember.value = false
  } finally {
    loadingTeam.value = false
  }
}

const validateTask = () => {
  if (!_task.value.title) {
    toast.error(__('Title is required'))
    return false
  }
  return true
}

const createTaskResource = createResource({
  url: 'frappe.client.insert',
  makeParams() {
    return {
      doc: {
        doctype: 'CRM Task',
        reference_doctype: props.doctype,
        reference_docname: props.doc || null,
        ..._task.value,
      },
    }
  },
  validate: validateTask,
  onSuccess(d) {
    if (d.name) {
      updateOnboardingStep('create_first_task')
      capture('task_created')

      // Team was staged locally during creation (or defaulted to just
      // the creator, below) - assign it now that the task actually
      // exists, via the one-time creator exception.
      const pickedUsers = taskTeam.value.length
        ? taskTeam.value.map((m) => m.name)
        : [getUser().name]

      call('crm.api.task_team.assign_team_on_create', {
        task_name: d.name,
        users: JSON.stringify(pickedUsers),
      }).catch((err) => {
        // Task itself was created successfully - only the team
        // assignment failed, so this is a toast, not a blocking error.
        toast.error(err?.messages?.[0]?.message || err?.message || __('Could not assign team'))
      })

      tasks.value?.reload?.()
      emit('after', d, true)
      show.value = false
      toast.success(__('Task created'))
    }
  },
})

const updateTaskResource = createResource({
  url: 'frappe.client.set_value',
  makeParams() {
    return {
      doctype: 'CRM Task',
      name: _task.value.name,
      fieldname: _task.value,
    }
  },
  validate: validateTask,
  onSuccess(d) {
    if (d.name) {
      tasks.value?.reload?.()
      emit('after', d)
      show.value = false
    }
  },
})

function updateTaskStatus(status) {
  _task.value.status = status
}

function updateTaskPriority(priority) {
  _task.value.priority = priority
}

function redirect() {
  if (!props.task?.reference_docname) return
  let name = props.task.reference_doctype == 'CRM Deal' ? 'Deal' : 'Lead'
  let params = { leadId: props.task.reference_docname }
  if (name == 'Deal') {
    params = { dealId: props.task.reference_docname }
  }
  router.push({ name: name, params: params })
}

async function updateTask() {
  if (_task.value.name) {
    updateTaskResource.submit()
  } else {
    createTaskResource.submit()
  }
}

function render() {
  editMode.value = false
  taskTeam.value = []
  canEditTeamMember.value = true
  setTimeout(() => title.value?.el?.focus?.(), 100)
  nextTick(() => {
    _task.value = { ...props.task }
    if (_task.value.title) {
      editMode.value = true
      loadExistingTeam()
    }
  })
}

onMounted(() => show.value && render())

watch(show, (value) => {
  if (!value) return
  render()
})
</script>

<style scoped>
:deep(.datepicker svg) {
  width: 0.875rem;
  height: 0.875rem;
}
</style>
