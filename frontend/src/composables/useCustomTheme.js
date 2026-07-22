import { ref } from 'vue'

// -----------------------------------------------------------------------
// Custom theme support
//
// frappe-ui's `useTheme()` only knows about 'light' | 'dark' | 'system'.
// We don't modify that package — instead we layer a 4th mode ('custom')
// on top of it at the app level:
//
//  - `setTheme('custom')` (still called from ThemeSwitcher.vue via
//     frappe-ui's own setTheme) sets `data-theme="custom"` on <html>.
//     Nothing in frappe-ui's CSS targets that attribute value, so the
//     light-mode CSS variables remain in effect as the base palette.
//  - We then override just the accent variables used for primary/solid
//     buttons (--surface-gray-7/6/5) with the user's chosen color, plus
//     derived hover/active shades.
// -----------------------------------------------------------------------

const STORAGE_KEY = 'crm-custom-accent-color'
const THEME_KEY = 'theme'
const DEFAULT_COLOR = '#2490EF' // Frappe blue

export const PRESET_COLORS = [
  '#2490EF', // blue
  '#7C3AED', // violet
  '#16A34A', // green
  '#DC2626', // red
  '#EA580C', // orange
  '#DB2777', // pink
  '#0D9488', // teal
  '#334155', // slate
]

export const customAccentColor = ref(
  localStorage.getItem(STORAGE_KEY) || DEFAULT_COLOR,
)

// Reactive flag so any component (ThemeSwitcher, PreferencesSettings, ...)
// can show/hide UI based on whether 'custom' is the active theme, without
// each one re-reading localStorage independently (which Vue can't track).
export const isCustomThemeActive = ref(localStorage.getItem(THEME_KEY) === 'custom')

function clamp(n) {
  return Math.max(0, Math.min(255, n))
}

// Lighten (positive percent) or darken (negative percent) a hex color.
function shade(hex, percent) {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = clamp((num >> 16) + Math.round(255 * percent))
  const g = clamp(((num >> 8) & 0x00ff) + Math.round(255 * percent))
  const b = clamp((num & 0x0000ff) + Math.round(255 * percent))
  return '#' + (0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1)
}

export function applyCustomAccentColor(color) {
  const root = document.documentElement
  root.style.setProperty('--surface-gray-7', color) // default/solid button bg
  root.style.setProperty('--surface-gray-6', shade(color, -0.08)) // hover
  root.style.setProperty('--surface-gray-5', shade(color, -0.16)) // active
  isCustomThemeActive.value = true
}

export function clearCustomAccentColor() {
  const root = document.documentElement
  root.style.removeProperty('--surface-gray-7')
  root.style.removeProperty('--surface-gray-6')
  root.style.removeProperty('--surface-gray-5')
  isCustomThemeActive.value = false
}

export function setCustomAccentColor(color) {
  customAccentColor.value = color
  localStorage.setItem(STORAGE_KEY, color)
  if (localStorage.getItem(THEME_KEY) === 'custom') {
    applyCustomAccentColor(color)
  }
}

// Call this once on app start (App.vue) so a saved custom color survives
// a page reload, the same way frappe-ui restores light/dark/system.
export function initializeCustomTheme() {
  if (localStorage.getItem(THEME_KEY) === 'custom') {
    applyCustomAccentColor(customAccentColor.value)
  } else {
    clearCustomAccentColor()
  }
}
