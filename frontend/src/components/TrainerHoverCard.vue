<template>
  <div
    class="relative"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <slot />

    <div
      v-if="show"
      class="absolute z-20 mt-1 w-72 rounded-lg border border-outline-gray-1 bg-surface-white p-4 shadow-lg text-sm"
      :class="placementClass"
      @mouseenter="cancelHide"
      @mouseleave="onLeave"
    >
      <div v-if="details.loading" class="flex items-center justify-center py-4">
        <LoadingIndicator class="h-4 w-4 text-ink-gray-4" />
      </div>

      <div v-else-if="details.error" class="text-ink-red-3">
        {{ __('Could not load trainer details') }}
      </div>

      <div v-else-if="details.data" class="space-y-3">
        <div>
          <p class="font-semibold text-ink-gray-9">{{ details.data.trainer_name || trainerId }}</p>
          <p class="text-xs text-ink-gray-4">{{ trainerId }}</p>
        </div>

        <div class="space-y-1.5">
          <div v-for="row in rows" :key="row.label" class="flex items-start gap-2">
            <span class="text-xs text-ink-gray-4 w-24 flex-shrink-0 pt-0.5">{{ row.label }}</span>
            <span class="text-xs text-ink-gray-7 break-words">{{ row.value || '—' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  trainerId: { type: String, default: '' },
  placement: { type: String, default: 'bottom' }, // 'bottom' | 'top'
})

const show = ref(false)
let showTimer = null
let hideTimer = null

const details = createResource({
  url: 'crm.api.trainers.get_trainer_details',
  cache: ['TrainerHoverDetails', props.trainerId],
  makeParams: () => ({ trainer: props.trainerId }),
  auto: false,
})

function onEnter() {
  if (!props.trainerId) return
  cancelHide()
  showTimer = setTimeout(() => {
    show.value = true
    if (!details.data && !details.loading) {
      details.fetch()
    }
  }, 300)
}

function onLeave() {
  if (showTimer) {
    clearTimeout(showTimer)
    showTimer = null
  }
  hideTimer = setTimeout(() => {
    show.value = false
  }, 150)
}

function cancelHide() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

const placementClass = computed(() =>
  props.placement === 'top' ? 'bottom-full mb-1' : 'top-full',
)

const rows = computed(() => {
  const d = details.data || {}
  return [
    { label: __('Phone'), value: d.phone },
    { label: __('Email'), value: d.email },
    { label: __('Location'), value: d.location },
    { label: __('Skill'), value: d.technology_expert_in },
    { label: __('Level'), value: d.skill_level },
    { label: __('Experience'), value: d.experience },
    { label: __('Availability'), value: d.availability },
    { label: __('Status'), value: d.status },
    { label: __('Commercial'), value: d.commercial ? `${d.commercial} (${d.commercial_type || ''})`.trim() : null },
    { label: __('Company'), value: d.company },
  ]
})
</script>
