<template>
  <Dialog v-model="show" :options="{ title: __('Link Existing Contact') }">
    <template #body-content>
      <div class="flex gap-1 rounded border p-2 text-ink-gray-5 mb-4">
        <FeatherIcon name="info" class="size-3.5 mt-0.5" />
        <p class="text-p-sm">
          {{
            __(
              'Search for an existing contact and link it to this client.',
            )
          }}
        </p>
      </div>
      <div>
        <label class="mb-1.5 block text-xs text-ink-gray-5">
          {{ __('Contact') }}
        </label>
        <Link
          class="form-control"
          size="md"
          :value="contact"
          doctype="Contact"
          :filters="[['company_name', '!=', organization]]"
          :placeholder="__('Search for a contact')"
          @change="(data) => (contact = data)"
        />
      </div>
      <ErrorMessage class="mt-3" :message="error" />
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button
          variant="solid"
          :label="__('Link Contact')"
          :disabled="!contact"
          :loading="linkContact.loading"
          @click="submit"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { Dialog, ErrorMessage, FeatherIcon, createResource, toast } from 'frappe-ui'
import { ref } from 'vue'

const props = defineProps({
  organization: { type: String, required: true },
  options: {
    type: Object,
    default: () => ({ afterLink: () => {} }),
  },
})

const show = defineModel({ type: Boolean })

const contact = ref('')
const error = ref('')

const linkContact = createResource({
  url: 'crm.fcrm.doctype.crm_organization.api.link_contact',
  onSuccess() {
    toast.success(__('Contact Linked'))
    props.options.afterLink?.()
    show.value = false
    contact.value = ''
    error.value = ''
  },
  onError(err) {
    error.value = err.messages?.[0] || err.message
  },
})

function submit() {
  error.value = ''
  if (!contact.value) {
    error.value = __('Please select a contact')
    return
  }
  linkContact.submit({
    organization: props.organization,
    contact: contact.value,
  })
}
</script>
