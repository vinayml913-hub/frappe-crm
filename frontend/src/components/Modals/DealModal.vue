<template>
  <Dialog v-model="show" :options="{ size: '3xl' }">
    <template #body>
      <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
              {{ isEditMode ? __('Edit Deal') : __('Create Deal') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button
              v-if="isManager() && !isMobileView"
              variant="ghost"
              class="w-7"
              :tooltip="__('Edit Fields Layout')"
              :icon="EditIcon"
              @click="openQuickEntryModal"
            />
            <Button
              variant="ghost"
              class="w-7"
              icon="x"
              @click="show = false"
            />
          </div>
        </div>
        <div>
          <div
            v-if="!isEditMode && (hasOrganizationSections || hasContactSections)"
            class="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3"
          >
            <div
              v-if="hasOrganizationSections"
              class="flex items-center gap-3 text-sm text-ink-gray-5"
            >
              <div>{{ __('Choose Existing Organization') }}</div>
              <Switch v-model="chooseExistingOrganization" />
            </div>
            <div
              v-if="hasContactSections"
              class="flex items-center gap-3 text-sm text-ink-gray-5"
            >
              <div>{{ __('Choose Existing Contact') }}</div>
              <Switch v-model="chooseExistingContact" />
            </div>
          </div>
          <div
            v-if="!isEditMode && (hasOrganizationSections || hasContactSections)"
            class="h-px w-full border-t my-5"
          />
          <FieldLayout
            v-if="tabs.data?.length"
            :tabs="tabs.data"
            :data="deal.doc"
            doctype="CRM Deal"
          />

          <div v-if="!isEditMode" class="mt-4 pt-4 border-t border-outline-gray-modals">
            <div class="text-sm font-medium text-ink-gray-6 mb-2">
              {{ __('Assign To') }}
              <span class="text-ink-gray-4 font-normal">
                ({{ __('optional, up to {0} people', [maxTeamSize]) }})
              </span>
            </div>
            <div
              class="w-full min-h-11 flex flex-wrap items-center gap-1.5 p-1.5 rounded-lg bg-surface-gray-2"
            >
              <div
                v-for="member in assignToOnCreate"
                :key="member.name"
                class="flex items-center text-sm p-0.5 pl-1 text-ink-gray-6 border border-outline-gray-1 bg-surface-modal rounded-full"
              >
                <UserAvatar :user="member.name" size="sm" />
                <div class="ml-1">{{ member.full_name }}</div>
                <Button
                  variant="ghost"
                  class="rounded-full !size-4 m-1"
                  @click="removeAssignToOnCreate(member.name)"
                >
                  <template #icon>
                    <FeatherIcon name="x" class="h-3 w-3 text-ink-gray-6" />
                  </template>
                </Button>
              </div>
              <Link
                v-if="assignToOnCreate.length < maxTeamSize"
                class="form-control flex-1 min-w-[140px]"
                value=""
                doctype="User"
                :placeholder="__('Add people to notify')"
                :filters="{
                  name: ['in', crmUserNames],
                  ignore_user_type: 1,
                }"
                :hideMe="false"
                @change="(option) => option && addAssignToOnCreate(option)"
              >
                <template #item-prefix="{ option }">
                  <UserAvatar class="mr-2" :user="option.value" size="sm" />
                </template>
                <template #item-label="{ option }">
                  <span class="text-ink-gray-9">{{ getUser(option.value).full_name }}</span>
                </template>
              </Link>
            </div>
          </div>

          <ErrorMessage v-if="error" class="mt-4" :message="__(error)" />
        </div>
      </div>
      <div class="px-4 pb-7 pt-4 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button
            variant="solid"
            :label="isEditMode ? __('Update') : __('Create')"
            :loading="isDealCreating"
            @click="isEditMode ? updateDeal() : createDeal()"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import EditIcon from '@/components/Icons/EditIcon.vue'
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { statusesStore } from '@/stores/statuses'
import { isMobileView } from '@/composables/settings'
import { showQuickEntryModal, quickEntryProps } from '@/composables/modals'
import { useDocument } from '@/data/document'
import { useTelemetry } from 'frappe-ui/frappe'
import { Switch, createResource, call, toast, FeatherIcon } from 'frappe-ui'
import { computed, ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  defaults: { type: Object, default: () => ({}) },
  dealName: { type: String, default: null },
})

const emit = defineEmits(['updated'])

const isEditMode = computed(() => !!props.dealName)

const { getUser, isManager, users } = usersStore()
const { getDealStatus, statusOptions } = statusesStore()

const crmUserNames = computed(() => users.data?.crmUsers?.map((u) => u.name) || [])

// "Assign To" at creation time - deliberately NOT bound to deal.doc /
// FieldLayout. The Assigned Team lives in Frappe's ToDo-based assignment
// system (same one crm.api.deal_team.py and the Deal page's "Assigned
// Team" sidebar section both use), not a stored field on CRM Deal, so
// there's a single source of truth whether the team was set here at
// creation or edited later on the Deal page.
const maxTeamSize = 10
const assignToOnCreate = ref([])

function addAssignToOnCreate(userEmail) {
  if (assignToOnCreate.value.find((m) => m.name === userEmail)) return
  if (assignToOnCreate.value.length >= maxTeamSize) return
  assignToOnCreate.value.push({
    name: userEmail,
    full_name: getUser(userEmail).full_name,
  })
}

function removeAssignToOnCreate(userEmail) {
  assignToOnCreate.value = assignToOnCreate.value.filter((m) => m.name !== userEmail)
}

const show = defineModel({ type: Boolean })
const router = useRouter()
const error = ref(null)

const { document: deal, triggerOnBeforeCreate } = useDocument('CRM Deal', props.dealName)

const hasOrganizationSections = ref(true)
const hasContactSections = ref(true)

const isDealCreating = ref(false)
const chooseExistingContact = ref(false)
const chooseExistingOrganization = ref(false)
const { capture } = useTelemetry()

// Shared so it can be triggered from multiple places (toggle change,
// tabs.data finishing its async load, or deal.doc finishing its async
// load) - whichever of tabs/deal resolves last is guaranteed to end up
// with the correct section visibility instead of a stale/no-op run.
function applySectionVisibility() {
  if (!tabs.data?.length) return

  tabs.data.forEach((tab) => {
    tab.sections.forEach((section) => {
      if (section.name === 'organization_section') {
        section.hidden = !chooseExistingOrganization.value
      } else if (section.name === 'organization_details_section') {
        section.hidden = chooseExistingOrganization.value
      } else if (section.name === 'contact_section') {
        section.hidden = !chooseExistingContact.value
      } else if (section.name === 'contact_details_section') {
        section.hidden = chooseExistingContact.value
      }
    })
  })
}

watch([chooseExistingOrganization, chooseExistingContact], applySectionVisibility)
watch(() => tabs.data, applySectionVisibility)

const tabs = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_fields_layout',
  cache: ['QuickEntry', 'CRM Deal'],
  params: { doctype: 'CRM Deal', type: 'Quick Entry' },
  auto: true,
  transform: (_tabs) => {
    hasOrganizationSections.value = false
    return _tabs.forEach((tab) => {
      tab.sections.forEach((section) => {
        section.columns.forEach((column) => {
          if (
            ['organization_section', 'organization_details_section'].includes(
              section.name,
            )
          ) {
            hasOrganizationSections.value = true
          } else if (
            ['contact_section', 'contact_details_section'].includes(
              section.name,
            )
          ) {
            hasContactSections.value = true
          }
          column.fields.forEach((field) => {
            if (field.fieldname == 'status') {
              field.fieldtype = 'Select'
              field.options = dealStatuses.value
              field.prefix = getDealStatus(deal.doc.status).color
            }

            if (field.fieldtype === 'Table') {
              deal.doc[field.fieldname] = []
            }
          })
        })
      })
    })
  },
})

const dealStatuses = computed(() => statusOptions('deal'))

async function createDeal() {
  if (deal.doc.website && !deal.doc.website.startsWith('http')) {
    deal.doc.website = 'https://' + deal.doc.website
  }
  if (chooseExistingContact.value) {
    deal.doc['first_name'] = null
    deal.doc['last_name'] = null
    deal.doc['email'] = null
    deal.doc['mobile_no'] = null
  } else deal.doc['contact'] = null

  await triggerOnBeforeCreate?.()

  createResource({
    url: 'crm.fcrm.doctype.crm_deal.crm_deal.create_deal',
    params: { doc: deal.doc },
    auto: true,
    validate() {
      error.value = null
      if (deal.doc.annual_revenue) {
        if (typeof deal.doc.annual_revenue === 'string') {
          deal.doc.annual_revenue = deal.doc.annual_revenue.replace(/,/g, '')
        } else if (isNaN(deal.doc.annual_revenue)) {
          error.value = __('Annual Revenue should be a number')
          return error.value
        }
      }
      if (
        deal.doc.mobile_no &&
        isNaN(deal.doc.mobile_no.replace(/[-+() ]/g, ''))
      ) {
        error.value = __('Mobile No. should be a number')
        return error.value
      }
      if (deal.doc.email && !deal.doc.email.includes('@')) {
        error.value = __('Invalid email address')
        return error.value
      }
      if (!deal.doc.status) {
        error.value = __('Status is required')
        return error.value
      }
      isDealCreating.value = true
    },
    onSuccess(name) {
      capture('deal_created')
      isDealCreating.value = false
      show.value = false

      if (assignToOnCreate.value.length) {
        call('crm.api.deal_team.assign_team_on_create', {
          deal_name: name,
          users: JSON.stringify(assignToOnCreate.value.map((m) => m.name)),
        })
          .then(() => {
            toast.success(__('Deal created and team notified'))
          })
          .catch((err) => {
            // Deal itself was created successfully - only the team
            // assignment failed, so this is a toast, not a blocking error.
            const msg = err?.messages?.[0]?.message || err?.message || __('Could not assign team')
            toast.error(msg)
          })
      }

      router.push({ name: 'Deal', params: { dealId: name } })
    },
    onError(err) {
      isDealCreating.value = false
      if (!err.messages) {
        error.value = err.message
        return
      }
      error.value = err.messages.join('\n')
    },
  })
}

async function updateDeal() {
  error.value = null

  if (deal.doc.website && !deal.doc.website.startsWith('http')) {
    deal.doc.website = 'https://' + deal.doc.website
  }
  if (deal.doc.annual_revenue && typeof deal.doc.annual_revenue === 'string') {
    deal.doc.annual_revenue = deal.doc.annual_revenue.replace(/,/g, '')
  }
  if (deal.doc.mobile_no && isNaN(deal.doc.mobile_no.replace(/[-+() ]/g, ''))) {
    error.value = __('Mobile No. should be a number')
    return
  }
  if (deal.doc.email && !deal.doc.email.includes('@')) {
    error.value = __('Invalid email address')
    return
  }
  if (!deal.doc.status) {
    error.value = __('Status is required')
    return
  }

  isDealCreating.value = true
  deal.save.submit(null, {
    onSuccess: () => {
      isDealCreating.value = false
      show.value = false
      toast.success(__('Deal updated successfully'))
      emit('updated')
    },
    onError: (err) => {
      isDealCreating.value = false
      error.value = err.messages?.join('\n') || err.message
    },
  })
}

function openQuickEntryModal() {
  showQuickEntryModal.value = true
  quickEntryProps.value = { doctype: 'CRM Deal' }
  nextTick(() => (show.value = false))
}

watch(show, (isOpen) => {
  if (isOpen) assignToOnCreate.value = []
})

// In edit mode, decide up front whether to show the "existing
// organization/contact" Link section or the "type a new one" details
// section, based on what the deal already has - instead of always
// defaulting to the typed-entry section (which writes to
// organization_name/first_name/etc, NOT the real organization/contact
// Link fields the rest of the CRM reads from). Waiting on deal.doc.name
// here because useDocument() loads the existing record asynchronously.
// applySectionVisibility() is called explicitly here too, in case
// deal.doc finishes loading AFTER tabs.data already has - the
// watch(() => tabs.data, ...) above only fires once, on that initial
// load, and won't re-run just because chooseExistingOrganization/
// chooseExistingContact get set a moment later here.
watch(
  () => deal.doc?.name,
  (name) => {
    if (!name) return

    if (isEditMode.value) {
      chooseExistingOrganization.value = !!deal.doc.organization
      chooseExistingContact.value = !!deal.doc.contact
      applySectionVisibility()
      return
    }

    deal.doc.no_of_employees = '1-10'
    Object.assign(deal.doc, props.defaults)

    if (!deal.doc.deal_owner) {
      deal.doc.deal_owner = getUser().name
    }
    if (!deal.doc.status && dealStatuses.value[0].value) {
      deal.doc.status = dealStatuses.value[0].value
    }
  },
  { immediate: true },
)
</script>
