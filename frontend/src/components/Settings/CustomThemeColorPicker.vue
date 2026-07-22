<template>
  <div class="flex flex-col gap-3 mt-1">
    <div class="flex items-center gap-2 flex-wrap">
      <button
        v-for="preset in PRESET_COLORS"
        :key="preset"
        type="button"
        class="size-6 rounded-full border transition-transform"
        :class="
          preset.toLowerCase() === customAccentColor.toLowerCase()
            ? 'ring-2 ring-offset-2 ring-outline-gray-5 scale-105'
            : 'border-outline-gray-2'
        "
        :style="{ backgroundColor: preset }"
        :aria-label="preset"
        @click="choose(preset)"
      />

      <!-- Custom / pick-your-own swatch -->
      <label
        class="relative flex items-center justify-center size-6 rounded-full border border-outline-gray-2 cursor-pointer overflow-hidden"
        :style="{ backgroundColor: customAccentColor }"
      >
        <input
          type="color"
          class="absolute inset-0 opacity-0 cursor-pointer"
          :value="customAccentColor"
          @input="choose($event.target.value)"
        />
      </label>
    </div>

    <div class="flex items-center gap-2">
      <span class="text-p-sm text-ink-gray-6">{{ __('Selected color') }}</span>
      <span class="text-p-sm font-mono text-ink-gray-8">{{
        customAccentColor
      }}</span>
    </div>
  </div>
</template>

<script setup>
import {
  customAccentColor,
  setCustomAccentColor,
  PRESET_COLORS,
} from '@/composables/useCustomTheme'

function choose(color) {
  setCustomAccentColor(color)
}
</script>
