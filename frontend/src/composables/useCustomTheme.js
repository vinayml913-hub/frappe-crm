import { ref } from 'vue'

// -----------------------------------------------------------------------
// Custom theme support
//
// frappe-ui's `useTheme()` only knows about 'light' | 'dark' | 'system'.
// We don't modify that package — instead we layer a 4th mode ('custom')
// on top of it at the app level:
//
//  - Selecting "Custom" calls frappe-ui's own `setTheme('dark')` so the
//    WHOLE page (backgrounds, text, sidebar, everything) switches to the
//    dark-mode base, exactly like the Dark option.
//  - We separately remember that the *user's* selection is "custom" (in
//    its own localStorage key, since frappe-ui's own 'theme' key now
//    holds 'dark').
//  - On top of that dark base we override the accent CSS variables used
//    for buttons, links, selected/active states, and focus rings with
//    the user's chosen color. Inline styles set via `element.style` beat
//    any stylesheet rule (including `[data-theme="dark"]` ones), so this
//    works regardless of the underlying base theme.
// -----------------------------------------------------------------------

const MODE_KEY = 'crm-theme-mode' // 'light' | 'dark' | 'system' | 'custom'
const COLOR_KEY = 'crm-custom-accent-color'
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
  localStorage.getItem(COLOR_KEY) || DEFAULT_COLOR,
)

// Reactive flag so any component can show/hide UI based on whether
// 'custom' is the active mode, without re-reading localStorage (which
// Vue can't track reactively).
export const isCustomThemeActive = ref(localStorage.getItem(MODE_KEY) === 'custom')

function clamp(n) {
  return Math.max(0, Math.min(255, n))
}

function hexToRgb(hex) {
  const num = parseInt(hex.replace('#', ''), 16)
  return { r: (num >> 16) & 0xff, g: (num >> 8) & 0xff, b: num & 0xff }
}

// Lighten (positive percent) or darken (negative percent) a hex color.
function shade(hex, percent) {
  const { r, g, b } = hexToRgb(hex)
  const nr = clamp(r + Math.round(255 * percent))
  const ng = clamp(g + Math.round(255 * percent))
  const nb = clamp(b + Math.round(255 * percent))
  return '#' + (0x1000000 + nr * 0x10000 + ng * 0x100 + nb).toString(16).slice(1)
}

function rgba(hex, alpha) {
  const { r, g, b } = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function hexToHsl(hex) {
  const { r, g, b } = hexToRgb(hex)
  const rn = r / 255,
    gn = g / 255,
    bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  let h = 0,
    s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case rn:
        h = (gn - bn) / d + (gn < bn ? 6 : 0)
        break
      case gn:
        h = (bn - rn) / d + 2
        break
      default:
        h = (rn - gn) / d + 4
    }
    h /= 6
  }
  return { h: h * 360, s: s * 100, l: l * 100 }
}

function hslToHex(h, s, l) {
  s /= 100
  l /= 100
  const k = (n) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n) =>
    l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  const toHex = (n) =>
    Math.round(255 * f(n))
      .toString(16)
      .padStart(2, '0')
  return `#${toHex(0)}${toHex(8)}${toHex(4)}`
}

// The neutral dark-mode gray ladder used for the app's big background
// surfaces (frappe-ui's darkMode/gray/*), so we can re-tint each step
// toward the custom color while keeping the same lightness (and
// therefore the same contrast against the untouched white/gray text).
const DARK_SURFACE_LADDER = {
  '--surface-white': '#0F0F0F', // darkMode/gray/900 - main page background
  '--surface-gray-1': '#232323', // darkMode/gray/700
  '--surface-gray-2': '#2B2B2B', // darkMode/gray/650
  '--surface-gray-3': '#343434', // darkMode/gray/600
  '--surface-gray-4': '#424242', // darkMode/gray/500
  '--surface-menu-bar': '#0F0F0F', // sidebar background
  '--surface-cards': '#1C1C1C', // darkMode/gray/800
  '--surface-modal': '#232323', // darkMode/gray/700
}

const DARK_OUTLINE_LADDER = {
  '--outline-gray-1': '#232323', // darkMode/gray/700
  '--outline-gray-2': '#343434', // darkMode/gray/600
  '--outline-gray-3': '#424242', // darkMode/gray/500
  '--outline-gray-4': '#808080', // darkMode/gray/300
  '--outline-gray-modals': '#343434', // darkMode/gray/600
}

// Tint one neutral gray step toward `hue` at a given saturation. Near-black
// steps (L close to 0) barely show any hue no matter the saturation, so we
// also nudge the lightness up slightly and enforce a floor — this keeps the
// tint clearly visible on the darkest surfaces without making the app look
// "light mode dark". Text/ink variables are untouched, so contrast is fine.
function tintStep(baseHex, hue, saturationPercent, lightnessBoost = 5, minLightness = 10) {
  const { l } = hexToHsl(baseHex)
  const boostedL = Math.max(l + lightnessBoost, minLightness)
  return hslToHex(hue, saturationPercent, boostedL)
}

function applyTintedBackground(color) {
  const { h } = hexToHsl(color)
  const root = document.documentElement.style

  Object.entries(DARK_SURFACE_LADDER).forEach(([varName, baseHex]) => {
    root.setProperty(varName, tintStep(baseHex, h, 55))
  })
  Object.entries(DARK_OUTLINE_LADDER).forEach(([varName, baseHex]) => {
    root.setProperty(varName, tintStep(baseHex, h, 60, 6, 14))
  })
}

function clearTintedBackground() {
  const root = document.documentElement.style
  Object.keys(DARK_SURFACE_LADDER).forEach((varName) =>
    root.removeProperty(varName),
  )
  Object.keys(DARK_OUTLINE_LADDER).forEach((varName) =>
    root.removeProperty(varName),
  )
}

// frappe-ui's dialog backdrop (`.dialog-overlay`, using its
// `bg-black-overlay-200` / `dark:bg-black-overlay-700` classes) is a flat,
// literal black color baked in at build time — NOT a CSS variable — so it
// can't be reached with `element.style.setProperty` like everything else
// here. Any open dialog (including this Settings panel) dims whatever is
// behind it with that black scrim, which is what makes a tinted page look
// like "color painted over black". We inject a small stylesheet to
// override just that class with a tinted version instead.
const OVERLAY_STYLE_ID = 'crm-custom-theme-overlay-style'

function applyOverlayTint(color) {
  let styleEl = document.getElementById(OVERLAY_STYLE_ID)
  if (!styleEl) {
    styleEl = document.createElement('style')
    styleEl.id = OVERLAY_STYLE_ID
    document.head.appendChild(styleEl)
  }
  styleEl.textContent = `.dialog-overlay { background-color: ${rgba(color, 0.72)} !important; }`
}

function clearOverlayTint() {
  const styleEl = document.getElementById(OVERLAY_STYLE_ID)
  if (styleEl) styleEl.textContent = ''
}

export function applyCustomAccentColor(color) {
  const root = document.documentElement.style

  // Whole-page background: tint the dark-mode surface/border ladder
  // toward the custom color. Text/ink variables are left untouched, so
  // white/light text stays exactly as it is in normal dark mode.
  applyTintedBackground(color)

  // Tint the dialog backdrop scrim too, so an open panel (like this
  // Settings page) doesn't look like it's floating on plain black.
  applyOverlayTint(color)

  // Solid/primary buttons
  root.setProperty('--surface-gray-7', color)
  root.setProperty('--surface-gray-6', shade(color, -0.08)) // hover
  root.setProperty('--surface-gray-5', shade(color, -0.16)) // active

  // Links
  root.setProperty('--ink-blue-3', color)
  root.setProperty('--blue-link', color)

  // Selected / active states (e.g. active sidebar item, selected row)
  root.setProperty('--surface-blue-1', rgba(color, 0.08))
  root.setProperty('--surface-blue-2', rgba(color, 0.16))
  root.setProperty('--surface-blue-3', color)
  root.setProperty('--ink-blue-2', color)

  // Focus rings / outlines
  root.setProperty('--outline-blue-1', color)

  isCustomThemeActive.value = true
}

export function clearCustomAccentColor() {
  const root = document.documentElement.style
  clearTintedBackground()
  clearOverlayTint()
  ;[
    '--surface-gray-7',
    '--surface-gray-6',
    '--surface-gray-5',
    '--ink-blue-3',
    '--blue-link',
    '--surface-blue-1',
    '--surface-blue-2',
    '--surface-blue-3',
    '--ink-blue-2',
    '--outline-blue-1',
  ].forEach((prop) => root.removeProperty(prop))

  isCustomThemeActive.value = false
}

export function setCustomAccentColor(color) {
  customAccentColor.value = color
  localStorage.setItem(COLOR_KEY, color)
  if (localStorage.getItem(MODE_KEY) === 'custom') {
    applyCustomAccentColor(color)
  }
}

// Central place to change the theme mode. `setTheme` is frappe-ui's own
// setter, passed in from the component so this file has no direct
// dependency on frappe-ui.
export function setThemeMode(mode, setTheme) {
  if (mode === 'custom') {
    setTheme('dark') // whole page switches to the dark base
    localStorage.setItem(MODE_KEY, 'custom')
    applyCustomAccentColor(customAccentColor.value)
  } else {
    clearCustomAccentColor()
    localStorage.setItem(MODE_KEY, mode)
    setTheme(mode)
  }
}

// What tile should show as selected. Falls back to frappe-ui's own
// currentTheme if we've never explicitly picked "custom".
export function getThemeMode(currentTheme) {
  const stored = localStorage.getItem(MODE_KEY)
  if (stored === 'custom') return 'custom'
  return currentTheme
}

// Call this once on app start (App.vue) so a saved custom color/mode
// survives a page reload, the same way frappe-ui restores light/dark/system.
export function initializeCustomTheme(setTheme) {
  if (localStorage.getItem(MODE_KEY) === 'custom') {
    setTheme('dark')
    applyCustomAccentColor(customAccentColor.value)
  } else {
    clearCustomAccentColor()
  }
}
