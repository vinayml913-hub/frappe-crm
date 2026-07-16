<template>
  <Dialog v-model="show" :options="{ size: '3xl' }">
    <template #body-title>
      <div class="flex items-center gap-3">
        <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
          {{ editMode ? __('Edit Solution') : __('Add Solution') }}
        </h3>
        <Button
          v-if="_solution?.reference_docname"
          size="sm"
          :label="
            _solution.reference_doctype == 'CRM Deal'
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
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            ref="trainerName"
            v-model="_solution.trainer_name"
            :label="__('Trainer Name')"
            :placeholder="__('John Doe')"
            required
          />
          <FormControl
            v-model="_solution.trainer_experience"
            :label="__('Trainer Experience')"
            :placeholder="__('5 years')"
          />
          <FormControl
            v-model="_solution.location"
            :label="__('Location')"
            :placeholder="__('Bengaluru')"
          />
          <FormControl
            v-model="_solution.duration"
            :label="__('Duration (in days/hour)')"
            :placeholder="__('3 days')"
          />
          <FormControl
            v-model="_solution.costing_for_training"
            type="number"
            :label="__('Costing for Training (in days/hour)')"
            :placeholder="__('0.00')"
          />
          <FormControl
            v-model="_solution.lab_cost"
            type="number"
            :label="__('Lab Cost')"
            :placeholder="__('0.00')"
          />
          <FormControl
            v-model="_solution.availability_for_training"
            :label="__('Availability for Training')"
            :placeholder="__('e.g. 20th Aug onwards')"
          />
          <FormControl
            v-model="_solution.availability_for_discussion_call"
            :label="__('Availability for Discussion Call')"
            :placeholder="__('e.g. Weekdays after 5 PM')"
          />
          <div>
            <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('SM') }}</div>
            <Link
              v-model="_solution.sm"
              class="form-control"
              doctype="User"
              :placeholder="__('Solution Manager')"
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
          </div>
        </div>
        <div>
          <div class="mb-1.5 flex items-center justify-between text-xs text-ink-gray-5">
            <span>{{ __('Documents') }}</span>
            <FileUploader
              v-if="_solution.name"
              :upload-args="{
                doctype: 'CRM Solution',
                docname: _solution.name,
                private: true,
              }"
              @success="(f) => attachments.push(f)"
            >
              <template #default="{ openFileSelector }">
                <Button
                  size="sm"
                  :label="__('Attach File')"
                  @click="openFileSelector()"
                >
                  <template #prefix>
                    <AttachmentIcon class="h-4 w-4" />
                  </template>
                </Button>
              </template>
            </FileUploader>
            <div v-else class="text-ink-gray-4">
              {{ __('Save to attach PDF, Word, or other files') }}
            </div>
          </div>
          <div
            v-if="attachments.length"
            class="flex flex-wrap gap-2 rounded border border-outline-gray-modals p-2"
          >
            <AttachmentItem
              v-for="a in attachments"
              :key="a.file_url"
              :label="a.file_name"
            >
              <template #suffix>
                <FeatherIcon
                  class="h-3.5"
                  name="x"
                  @click.stop="removeAttachment(a)"
                />
              </template>
            </AttachmentItem>
          </div>
          <div v-else class="text-p-sm text-ink-gray-4">
            {{ __('No documents attached yet') }}
          </div>
        </div>
        <ErrorMessage v-if="error" class="mt-1" :message="__(error)" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button
          :label="editMode ? __('Done') : __('Create')"
          variant="solid"
          :loading="loading"
          @click="updateSolution"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import AttachmentItem from '@/components/AttachmentItem.vue'
import Link from '@/components/Controls/Link.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'
import { FileUploader, Tooltip, FeatherIcon, call } from 'frappe-ui'
import { ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  solution: { type: Object, default: () => ({}) },
  doctype: { type: String, default: 'CRM Deal' },
  doc: { type: String, default: '' },
})

const show = defineModel({ type: Boolean })
const solutions = defineModel('reloadSolutions', {
  type: Object,
  default: () => ({}),
})

const emit = defineEmits(['after'])

const router = useRouter()
const { getUser } = usersStore()

const error = ref(null)
const loading = ref(false)
const trainerName = ref(null)
const editMode = ref(false)
let _solution = ref({})
const attachments = ref([])

function removeAttachment(attachment) {
  attachments.value = attachments.value.filter((a) => a !== attachment)
}

async function updateSolution() {
  if (!_solution.value.trainer_name) {
    error.value = 'Trainer Name is mandatory'
    return
  }
  error.value = null
  loading.value = true
  try {
    if (_solution.value.name) {
      await call('frappe.client.set_value', {
        doctype: 'CRM Solution',
        name: _solution.value.name,
        fieldname: _solution.value,
      })
      solutions.value?.reload?.()
      emit('after', _solution.value)
      show.value = false
    } else {
      const d = await call('frappe.client.insert', {
        doc: {
          doctype: 'CRM Solution',
          ..._solution.value,
          reference_doctype: props.doctype,
          reference_docname: props.doc || '',
        },
      })
      if (d.name) {
        _solution.value = { ..._solution.value, name: d.name }
        editMode.value = true
        solutions.value?.reload?.()
        emit('after', d, true)
      }
    }
  } catch (err) {
    error.value =
      err?.messages?.[0] || err?.message || 'Could not save solution'
  } finally {
    loading.value = false
  }
}

function redirect() {
  if (!props.solution?.reference_docname) return
  let name = props.solution.reference_doctype == 'CRM Deal' ? 'Deal' : 'Lead'
  let params = { leadId: props.solution.reference_docname }
  if (name == 'Deal') {
    params = { dealId: props.solution.reference_docname }
  }
  router.push({ name: name, params: params })
}

watch(
  () => show.value,
  (value) => {
    if (!value) return
    editMode.value = false
    attachments.value = props.solution?.attachments || []
    nextTick(() => {
      trainerName.value?.el?.focus()
      _solution.value = { ...props.solution }
      if (_solution.value.name) {
        editMode.value = true
      }
    })
  },
)
</script>
