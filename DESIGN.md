# DESIGN.md — Phone Marketplace & Price Intelligence Platform

## 1. Visual Direction & Aesthetic Identity
- **Character**: Precision Industrial Commerce & Editorial Hardware Catalog.
- **Inspiration**: High-precision engineering instruments, Swiss typography, refined Japanese hardware directories, tactile physical materiality.
- **Distinctiveness**: Avoids generic "AI SaaS" templates (no generic purple blur gradients, no ubiquitous #F4F1EA cream + #D97757 terracotta combo, no over-rounded cards with vague drop shadows). Instead, uses crisp architectural structure, clear visual density tiers, and purposeful contrast.

---

## 2. Design Philosophy
1. **Utility & Precision First**: Every pixel and token communicates hardware data, price deltas, condition grades, or market trends.
2. **Tactile Feedback**: Interactive elements respond with mechanical certainty (scale changes, tactile border illumination, unambiguous focus rings).
3. **No Decorative Filler**: Structural lines, dividers, and tags carry meaning (e.g. storage capacities, SIM locks, battery health, price movements).
4. **Taste as Leverage**: Polish invisible details — easing curves, line-height proportions, optical kerning, and micro-press states.

---

## 3. Color System

### Base Neutral Palette
- **Canvas Base (Dark/Charcoal Mode)**: `#0F1115` (Deep slate-graphite, not muddy pure black)
- **Surface Elevation 1 (Card/Panel)**: `#171A21`
- **Surface Elevation 2 (Elevated/Hover)**: `#212631`
- **Border Subtle**: `rgba(255, 255, 255, 0.08)`
- **Border Strong / Active**: `rgba(255, 255, 255, 0.18)`

### Typography & Content
- **Text Primary**: `#F1F3F7` (High contrast, crisp legibility)
- **Text Secondary**: `#9CA3B5` (Muted technical notes, specs)
- **Text Tertiary**: `#616B7E` (Metadata, timestamps, subtle labels)

### Semantic & Market Accents
- **Hardware Primary Brand**: `#3B82F6` (Electric Cobalt — used strictly for primary actions)
- **Price Up / Bullish / Premium**: `#10B981` (Emerald / Mint — indicates price drops for buyers or positive margins)
- **Price Down / Warning**: `#F43F5E` (Rose Coral — critical alerts, out of stock)
- **Market Caution / Neutral**: `#F59E0B` (Warm Amber — fluctuating rate, verification pending)

---

## 4. Typography System
- **Display / Headings**: Instrument Sans / Space Grotesk (technical geometric clarity with distinct personality)
- **Body & Interface**: Plus Jakarta Sans / Inter Variable with strict optical tracking
- **Data & Numbers**: JetBrains Mono or Fira Code for prices, storage (GB/TB), IMEI, and serial numbers with tabular lining figures (`font-variant-numeric: tabular-nums`).

### Scale
- **Display 1 (Hero)**: `36px` / `1.1` (Tracking: `-0.02em`, Weight: `700`)
- **Heading 1**: `28px` / `1.2` (Tracking: `-0.015em`, Weight: `600`)
- **Heading 2**: `20px` / `1.3` (Tracking: `-0.01em`, Weight: `600`)
- **Body Regular**: `15px` / `1.5` (Tracking: `0`, Weight: `400`)
- **Body Medium / Caption**: `13px` / `1.4` (Tracking: `0.005em`, Weight: `500`)
- **Mono Technical Tag**: `12px` / `1.2` (Weight: `500`, Tabular numbers)

---

## 5. Spacing System
Based on a strict 4px / 8px incremental scale:
- `space-1`: `4px` (Tight padding within tags, icons)
- `space-2`: `8px` (Gaps between badge chips, micro-elements)
- `space-3`: `12px` (Internal card header padding, form input vertical padding)
- `space-4`: `16px` (Default container padding, standard gap)
- `space-6`: `24px` (Section padding within panels, card group spacing)
- `space-8`: `32px` (Major block separation)
- `space-12`: `48px` (Page section break)

---

## 6. Border Radius
- **Micro (Badges, Tags, Tooltips)**: `4px`
- **Interactive Inputs & Buttons**: `6px`
- **Product Cards & Panels**: `10px`
- **Modals / Sheets**: `14px`
*Rule*: Avoid pill-shapes (`rounded-full`) for standard rectangles; preserve crisp, engineered geometry.

---

## 7. Shadows & Depth
- **Level 0 (Flat/Subtle)**: `none`, separated purely by `1px solid var(--border-subtle)`
- **Level 1 (Card/Hover)**: `0 1px 3px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2)`
- **Level 2 (Popovers, Dropdowns)**: `0 8px 24px -4px rgba(0, 0, 0, 0.6)`
- **Level 3 (Modals/Dialogs)**: `0 20px 48px -8px rgba(0, 0, 0, 0.75)`

---

## 8. Grid & Layout
- **Container Max Width**: `1280px` (desktop viewport)
- **Columns**: 12-column grid on desktop, 6-column on tablet, 2 or 1 column on mobile.
- **Alignment**: Strict left-alignment for text and values; right-alignment for pricing, percentages, and metrics.
- **No Orphan Elements**: Use `text-wrap: balance` on headings.

---

## 9. Responsive Breakpoints
- **Mobile (`sm`)**: `< 640px` (single column cards, compact sticky bottom bar)
- **Tablet (`md`)**: `640px – 1023px` (2 column grid, collapsible filters drawer)
- **Desktop (`lg`)**: `1024px – 1279px` (3 column grid, split-pane view)
- **Wide (`xl`)**: `≥ 1280px` (4 column grid or full analytics sidebar + catalog)

---

## 10. Component Rules

### Buttons
- **Primary**: Solid Cobalt background, sharp text, `:hover` darkens by 6% with instant response, `:active` scales to `0.98`.
- **Secondary / Ghost**: Semi-transparent slate with border, hover brings border opacity to 35%.
- **Icon Buttons**: Must always specify `aria-label`, min target size `44x44px` on touch devices.

### Product Cards
- Explicit image ratio (`4:3` or `1:1`) with reserved layout space (`aspect-ratio` to avoid Cumulative Layout Shift).
- Prominent price display with tabular numerals.
- Status indicator for condition (Brand New / Open Box / Grade A+ / Grade B).
- Hover effect: Subtle border brighten and slight elevation; do NOT scale up the entire card heavily.

### Forms & Filtering
- Visible labels above fields at all times (no placeholder-only labels).
- Real-time inline validation with descriptive, actionable error copy placed directly beneath the input.
- Filter chips should indicate active count and have instant clear triggers.

### Navigation
- Compact header with instant search (`Cmd+K` shortcut).
- Persistent breadcrumbs on deep product detail pages.
- Mobile bottom navigation bar for high-frequency actions (Search, Watchlist, Alerts, Account).

---

## 11. Interaction States
- **Hover**: 150ms `ease-out`, subtle property transition (opacity, border-color, background).
- **Active / Pressed**: Immediate (`0ms` delay), scale `0.97 - 0.98`.
- **Focus Visible**: Unambiguous 2px ring with `2px` offset (`outline: 2px solid #3B82F6`, `outline-offset: 2px`). Never remove focus outlines without custom replacement.
- **Disabled**: `opacity: 0.45`, `cursor: not-allowed`, remove hover/active responses.

---

## 12. Animation Rules (Emil Kowalski Framework)
- **High Frequency (< 100x/day)**: Instant (`0ms`). No animation for keyboard shortcuts, fast filter clicks, or closing modals with Escape.
- **Medium Frequency (Toasts, Drawers, Dropdowns)**: `150ms – 220ms` using `cubic-bezier(0.16, 1, 0.3, 1)` (snappy ease-out).
- **Entering Elements**: Start fast, settle gently (`ease-out`). Scale from `0.96` to `1.0` and opacity from `0` to `1`.
- **Exiting Elements**: Fast exit without bounce (`ease-in`, `120ms`).
- **Never animate `width` or `height`**: Always prefer `transform` and `opacity` to avoid layout reflows.
- **Honor Reduced Motion**: `@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }`.

---

## 13. Accessibility Rules (WCAG 2.1 AA+)
- Contrast ratio ≥ 4.5:1 for normal body text, ≥ 3:1 for large display text and key UI borders.
- Touch targets strictly ≥ 44×44px.
- All SVG icons have `aria-hidden="true"` or a meaningful `<title>` / `aria-label`.
- Full keyboard navigation loop: Tab, Shift+Tab, Enter, Space, Escape on all overlays.

---

## 14. Do & Don't Checklist

### Do:
- Use tabular figures for price lists and market deltas.
- Build clean, data-dense tables and cards with readable hierarchy.
- Use explicit CSS properties in transitions (`transition: transform 180ms ease-out, opacity 180ms ease-out`).
- Verify responsive layout with `agent-browser` on mobile and desktop viewports.

### Don't:
- Don't use `transition: all`.
- Don't use purple-to-pink gradients or pastel amorphous blobs.
- Don't use ALL-CAPS tracked eyebrows above every single title.
- Don't make buttons or interactive items smaller than 44px on touch devices.
- Don't use emoji as system icons.
