<template>
  <Dialog v-model="show" :options="{ size: 'lg', title: __('Set Revenue Target') }">
    <template #body-content>
      <div class="space-y-4">
        <div>
          <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Employee') }} *</label>
          <Link
            class="form-control"
            :value="form.employee && getUser(form.employee).full_name"
            doctype="User"
            :filters="{ name: ['in', crmUserNames], ignore_user_type: 1 }"
            :placeholder="__('Select employee')"
            :hideMe="false"
            @change="(v) => (form.employee = v)"
          />
        </div>

        <div>
          <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Target Type') }} *</label>
          <select v-model="form.target_type" class="form-control w-full">
            <option value="Monthly">{{ __('Monthly') }}</option>
            <option value="Quarterly">{{ __('Quarterly') }}</option>
            <option value="Yearly">{{ __('Yearly') }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div v-if="form.target_type === 'Monthly'">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Month') }} *</label>
            <select v-model="form.month" class="form-control w-full">
              <option value="">{{ __('Select') }}</option>
              <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div v-if="form.target_type === 'Quarterly'">
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Quarter') }} *</label>
            <select v-model="form.quarter" class="form-control w-full">
              <option value="">{{ __('Select') }}</option>
              <option v-for="q in ['Q1', 'Q2', 'Q3', 'Q4']" :key="q" :value="q">{{ q }}</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Year') }} *</label>
            <input v-model.number="form.year" type="number" class="form-control w-full" />
          </div>
        </div>

        <div>
          <label class="text-xs font-medium text-ink-gray-6 mb-1 block">{{ __('Revenue Target Amount (₹)') }} *</label>
          <input v-model.number="form.target_amount" type="number" min="0" class="form-control w-full" />
        </div>

        <ErrorMessage v-if="error" :message="error" />

        <div v-if="existingTargets.data?.length" class="border-t border-outline-gray-1 pt-4 mt-2">
          <p class="text-xs font-semibold text-ink-gray-5 uppercase mb-2">{{ __('Existing Targets') }}</p>
          <div class="space-y-1.5 max-h-48 overflow-y-auto">
            <div
              v-for="t in existingTargets.data"
              :key="t.name"
              class="flex items-center justify-between text-sm px-2 py-1.5 rounded hover:bg-surface-gray-1"
            >
              <span>{{ getUser(t.employee).full_name }} — {{ t.target_type }} {{ t.year }}{{ t.month ? ' ' + t.month : '' }}{{ t.quarter ? ' ' + t.quarter : '' }}: {{ formatCurrency(t.target_amount) }}</span>
              <div class="flex gap-1">
                <Button variant="ghost" icon="edit-2" @click="editTarget(t)" />
                <Button variant="ghost" icon="trash-2" @click="deleteTarget(t.name)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="editingName ? __('Update') : __('Create')" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { createResource, call, toast, Dialog } from 'frappe-ui'
import { ref, reactive, computed, onMounted } from 'vue'

const emit = defineEmits(['updated'])
const show = defineModel({ type: Boolean })

const { getUser, users } = usersStore()
const crmUserNames = computed(() => users.data?.crmUsers?.map((u) => u.name) || [])

const months = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const emptyForm = () => ({
  employee: '',
  target_type: 'Monthly',
  month: '',
  quarter: '',
  year: new Date().getFullYear(),
  target_amount: 0,
})

const form = reactive(emptyForm())
const error = ref(null)
const saving = ref(false)
const editingName = ref(null)

const existingTargets = createResource({
  url: 'crm.api.revenue_target.list_targets',
  auto: true,
  initialData: [],
})

function editTarget(t) {
  editingName.value = t.name
  Object.assign(form, {
    employee: t.employee,
    target_type: t.target_type,
    month: t.month || '',
    quarter: t.quarter || '',
    year: t.year,
    target_amount: t.target_amount,
  })
}

async function deleteTarget(name) {
  try {
    await call('crm.api.revenue_target.delete_target', { name })
    toast.success(__('Target deleted'))
    existingTargets.reload()
    emit('updated')
  } catch (err) {
    toast.error(err.messages?.[0] || __('Failed to delete target'))
  }
}

async function submit() {
  error.value = null
  if (!form.employee) { error.value = __('Employee is required'); return }
  if (!form.target_amount) { error.value = __('Target Amount is required'); return }
  if (form.target_type === 'Monthly' && !form.month) { error.value = __('Month is required'); return }
  if (form.target_type === 'Quarterly' && !form.quarter) { error.value = __('Quarter is required'); return }

  saving.value = true
  try {
    if (editingName.value) {
      await call('crm.api.revenue_target.update_target', {
        name: editingName.value,
        target: JSON.stringify(form),
      })
      toast.success(__('Target updated'))
    } else {
      await call('crm.api.revenue_target.create_target', {
        target: JSON.stringify(form),
      })
      toast.success(__('Target created'))
    }
    Object.assign(form, emptyForm())
    editingName.value = null
    existingTargets.reload()
    emit('updated')
  } catch (err) {
    error.value = err.messages?.join('\n') || err.message
  } finally {
    saving.value = false
  }
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)
}
</script>
