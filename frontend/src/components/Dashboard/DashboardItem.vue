<template>
  <div class="h-full w-full">
    <div
      v-if="item.type == 'number_chart'"
      class="flex h-full w-full rounded shadow overflow-hidden"
      :class="isClickable ? 'cursor-pointer' : ''"
      @click="isClickable && handleCardClick()"
    >
      <Tooltip :text="__(item.data.tooltip)">
        <NumberChart
          v-if="item.data"
          :key="index"
          class="!items-start"
          :config="item.data"
        />
      </Tooltip>
    </div>
    <div
      v-else-if="item.type == 'spacer'"
      class="rounded bg-surface-white h-full overflow-hidden text-ink-gray-5 flex items-center justify-center"
      :class="editing ? 'border border-dashed border-outline-gray-2' : ''"
    >
      {{ editing ? __('Spacer') : '' }}
    </div>
    <div
      v-else-if="item.type == 'axis_chart'"
      class="h-full w-full rounded-md bg-surface-white shadow"
    >
      <AxisChart v-if="item.data" :config="item.data" />
    </div>
    <div
      v-else-if="item.type == 'donut_chart'"
      class="h-full w-full rounded-md bg-surface-white shadow overflow-hidden"
    >
      <DonutChart v-if="item.data" :config="item.data" />
    </div>
  </div>
</template>
<script setup>
import { AxisChart, DonutChart, NumberChart, Tooltip } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  index: { type: Number, required: true },
  item: { type: Object, required: true },
  editing: { type: Boolean, default: false },
  dateRange: { type: Object, default: null }, // { from, to }
  selectedUser: { type: String, default: null },
})

const router = useRouter()

// Cards that support click-through. Every other number_chart card
// (Avg. time to close, Avg. deal value, etc.) stays static.
const CLICKABLE_CARDS = {
  total_leads: { route: 'Leads', quickFilter: 'total' },
  ongoing_deals: { route: 'Deals', quickFilter: 'ongoing' },
  won_deals: { route: 'Deals', quickFilter: 'won' },
}

const isClickable = computed(
  () =>
    !props.editing &&
    props.item.type == 'number_chart' &&
    !!CLICKABLE_CARDS[props.item.name],
)

function handleCardClick() {
  const target = CLICKABLE_CARDS[props.item.name]
  if (!target) return

  router.push({
    name: target.route,
    query: {
      quick_filter: target.quickFilter,
      from: props.dateRange?.from || undefined,
      to: props.dateRange?.to || undefined,
      owner: props.selectedUser || undefined,
    },
  })
}
</script>
