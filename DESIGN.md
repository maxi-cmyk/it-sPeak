---
name: "it'sPEAK"
description: "A focused rehearsal control room for measurable speaking readiness and continuous improvement."
colors:
  canvas: "#f0e9dc"
  canvas-dark: "#09090b"
  surface-dark: "#18181b"
  surface-raised-dark: "#27272a"
  border-dark: "#27272a"
  border-strong-dark: "#3f3f46"
  text-primary-dark: "#fafafa"
  text-secondary-dark: "#d4d4d8"
  text-subtle-dark: "#a1a1aa"
  text-muted-dark: "#71717a"
  surface: "#fffdf8"
  surface-raised: "#e8dfd2"
  border: "#e8dfd2"
  border-strong: "#b5aa9b"
  text-primary: "#10243e"
  text-secondary: "#334155"
  text-subtle: "#475569"
  text-muted: "#5f6b7a"
  performance-cobalt: "#2563eb"
  performance-cobalt-hover: "#1d4ed8"
  performance-cobalt-soft: "#93c5fd"
  readiness-amber: "#92400e"
  progress-emerald: "#34d399"
  correction-red: "#b91c1c"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.18em"
rounded:
  md: "6px"
  lg: "8px"
  xl: "12px"
  2xl: "16px"
  full: "9999px"
spacing:
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  8: "32px"
  10: "40px"
components:
  button-primary:
    backgroundColor: "{colors.performance-cobalt}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.performance-cobalt-hover}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  input:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "10px 12px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.xl}"
    padding: "20px"
  chip:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
---

# Design System: it'sPEAK

## Overview

**Creative North Star: "The Rehearsal Control Room"**

it'sPEAK should feel like a dedicated place to prepare for a real speaking event: focused, precise, and quietly serious. The interface uses a deeper parchment off-white workspace by default and restores the original Zinc control-room palette in night mode. Both modes keep the same compact structure, restrained controls, and clear instrumentation so the speaker's recording, scores, and next action remain central.

The system is professional and performance-driven, but its feedback remains precise and encouraging. Improvement is treated as an ongoing rehearsal process rather than a game, competition, or corporate reporting exercise. Visual hierarchy comes from disciplined spacing, tonal layers, and a deliberately scarce cobalt accent—not from decorative effects.

**Key Characteristics:**

- User-selectable parchment workspace or original Zinc dark control room
- Compact information density with clear hierarchy
- Layered structural depth rather than decorative elevation
- Performance Cobalt reserved for focus and primary action
- Direct feedback expressed with supportive semantic color
- Restrained motion that clarifies state without creating spectacle

## Colors

The light palette combines a parchment canvas, cream surfaces, navy text, one clear cobalt accent, and tightly scoped semantic colors. Night mode restores the original Zinc hierarchy: `#09090b` canvas, `#18181b` surfaces, `#27272a` raised surfaces and borders, and light Zinc text. Performance Cobalt remains the action and focus accent in both modes.

### Primary

- **Performance Cobalt:** Marks the primary action, active selection, focus, and mid-range score state. Its saturation creates direction without turning the interface into a reward system.
- **Performance Cobalt Hover:** Deepens primary controls on interaction while preserving strong contrast with warm off-white text.
- **Performance Cobalt Soft:** Supports selected borders, labels, and restrained accent treatments where the solid primary would be too forceful.

### Secondary

- **Readiness Amber:** A deep burnt amber that keeps attention states legible on the warm canvas; it signals a metric that still needs attention or has not yet reached the target.
- **Progress Emerald:** Signals confirmed strengths, completed states, and scores that meet the proficiency threshold.
- **Correction Red:** Signals warnings, failures, blocked actions, and low-score states requiring direct intervention. A visible textual “warning” label is always red, never amber.

### Neutral

- **Control-Room Canvas:** Light mode uses deeper parchment to reduce glare and separate cream surfaces. Night mode restores the original near-black Zinc canvas with progressively lighter Zinc surfaces and borders, preserving the same structural depth without introducing gradients or decorative glow.
- **Instrument Surface:** The cream-white card, panel, and modal surface separates working regions from the canvas.
- **Raised Control Surface:** A warm beige used by inputs, subdued buttons, and secondary nested areas.
- **Quiet Border / Strong Border:** One-pixel divisions define structure without adding visual weight.
- **Primary Navy:** Reserved for headings, scores, input text, and decisive labels. Its depth anchors the warm workspace without making it feel severe.
- **Secondary Text:** Supports ordinary content and control labels.
- **Subtle Text / Muted Text:** Used for supporting explanations, timestamps, and low-priority metadata.

**The Controlled Signal Rule.** Performance Cobalt should identify focus, selection, or the primary next action; it must not wash entire screens or decorate passive content.

**The Semantic Evidence Rule.** Amber marks attention metrics, emerald marks progress, and red marks warnings or errors. Never use them merely to make the interface more colorful.

**The Night Neutral Rule.** Night mode remaps the neutral surface and text hierarchy to the original Zinc palette while retaining blue actions and accents. Semantic colors may brighten only enough to retain contrast on dark surfaces.

## Typography

**Display Font:** System sans (`ui-sans-serif`, `system-ui`, `sans-serif`)

**Body Font:** System sans (`ui-sans-serif`, `system-ui`, `sans-serif`)

**Character:** A single native sans-serif stack keeps the product fast, neutral, and instrument-like. Dark navy text anchors the warm off-white environment; weight, size, spacing, and case establish hierarchy instead of font pairing or editorial ornament.

### Hierarchy

- **Display** (700, 28px, 1.2): Page titles and the strongest result summaries.
- **Title** (600, 20px, 1.4): Card headings, modal titles, and prominent metric labels.
- **Body** (400, 16px, 1.5): Instructions, analysis, feedback, and normal controls; explanatory text may open to a 1.75 line height.
- **Label** (600, 14px, 0.18em, uppercase when sectional): Eyebrows, status headings, chart labels, and compact metadata. Legacy compact annotations are raised to this same 14px floor at the utility layer.
- **Score** (700, 28–32px, compact line height): Numeric performance readouts; use only where the number is the primary evidence.

**The Instrument Label Rule.** Uppercase tracked labels identify compact sections and measurements; they are not a substitute for readable body copy and never render below the 14px label floor.

## Layout

Content sits in a centered container with a maximum width of 1024px and 24px horizontal gutters. Primary pages use 40px vertical padding, with 24–32px between major sections and 12–24px within cards. The spacing rhythm follows 4px increments and favors compact, legible groupings.

Dashboards begin as one column, become two columns from 640px, and use three columns where appropriate from 1024px. Project and results pages move from one column to asymmetric two-column arrangements at the large breakpoint, keeping the recording or primary analysis wider than supporting controls. Navigation remains a shallow sticky bar with a bottom border; mobile layouts preserve the same hierarchy by wrapping or stacking content rather than shrinking controls below comfortable sizes.

**The One Working Plane Rule.** Each view should have one visually dominant working region; supporting cards stay quieter and must not compete through equal accent, size, or contrast.

## Elevation & Depth

Depth is layered and structural. The canvas, card surface, and raised control surface form a three-level tonal system reinforced by one-pixel borders. Cards remain flat at rest. Strong shadows belong primarily to blocking overlays and modals, where they clarify interruption and spatial priority; interactive cards may gain a restrained shadow alongside a border-color change.

### Shadow Vocabulary

- **Modal Lift** (`0 25px 50px -12px rgb(0 0 0 / 0.25)`): Reserved for dialogs over a darkened, softly blurred backdrop.
- **Interactive Lift** (`0 20px 25px -5px rgb(0 0 0 / 0.10), 0 8px 10px -6px rgb(0 0 0 / 0.10)`): Optional for a hovered project card when border contrast alone is insufficient.
- **Selected Inset** (`inset 0 0 0 1px rgb(147 197 253 / 0.18)`): Reinforces selected improvement areas without producing a glow effect.

**The Structural Depth Rule.** Use tonal separation and borders first. A shadow must communicate overlay, interaction, or selection—not decoration.

## Shapes

The form language is gently geometric. Inputs and buttons use 8px corners, cards use 12px corners, and dialogs use 16px corners. Small badges may use 6px corners, while chips, statuses, and circular score markers use full rounding. Borders are consistently thin and quiet. Video remains rectangular within its containing surface so the recorded performance retains visual authority.

**The Nested Radius Rule.** A nested control uses an equal or smaller radius than its containing surface: 8px controls inside 12px cards, and 12px cards inside 16px dialogs.

## Components

Components should feel precise and encouraging: clear enough to operate under rehearsal pressure, with feedback that guides rather than judges.

### Buttons

- **Shape:** Gently curved rectangle (8px radius), normally 10px vertical and 16px horizontal padding.
- **Primary:** Performance Cobalt with primary text and semibold labeling; use once per action group for the clearest next step.
- **Hover / Focus:** Deepen to the hover cobalt over the standard 150ms state transition. Keyboard focus receives a visible soft-cobalt outline with offset from the control edge.
- **Active:** Darken or compress subtly; do not bounce, celebrate, or add gradient effects.
- **Secondary:** Raised neutral surface with a strong neutral border and secondary text.
- **Disabled:** Muted neutral fill and text with no hover response.

### Chips

- **Style:** Compact full-radius control with a raised neutral fill, thin border, and concise label.
- **State:** Selected improvement areas use a transparent cobalt tint, soft cobalt text and border, plus the selected inset treatment. Multi-selection must remain visually obvious without resembling collectible badges.

### Cards / Containers

- **Corner Style:** 12px for normal cards and 16px for blocking dialogs.
- **Background:** Instrument Surface over the Control-Room Canvas; nested controls may use the Raised Control Surface.
- **Shadow Strategy:** Flat by default; follow the Structural Depth Rule.
- **Border:** One-pixel Quiet Border, strengthening or shifting to soft cobalt only for interaction or selection.
- **Internal Padding:** 16px for compact cards and 20–24px for primary content panels.

### Inputs / Fields

- **Style:** Raised neutral background, strong neutral border, 8px radius, primary input text, and muted placeholder text.
- **Focus:** Border changes to Performance Cobalt and receives a visible focus outline. Focus must not rely on color alone where an outline can provide stronger keyboard affordance.
- **Error / Disabled:** Correction Red is reserved for actionable validation errors; disabled fields use lowered neutral contrast and a non-interactive cursor.

### Navigation

Navigation uses the active canvas color, a quiet bottom border, and a sticky position. The product name is bold and compact; links use subtle neutral text and become primary text or Performance Cobalt on interaction. A persistent day/night switch sits beside authentication controls and swaps the complete neutral workspace palette while retaining blue accents. Authentication controls stay visually subordinate to the current page task.

### Theme Toggle

The theme toggle is a compact full-radius switch with a moving circular thumb and explicit sun/moon symbols. It uses `role="switch"`, exposes its checked state, supports keyboard focus, and stores the user's choice locally. The movement is brief and functional; reduced-motion preferences remove the transition.

### Score Ring

The circular score is the system's principal instrument display. A thin neutral track holds one semantic stroke: emerald at or above proficiency, cobalt through the developing middle range, and red for a clearly low result. The score remains a direct readout rather than a medal, badge, streak, or celebratory animation.

### Feedback Panel

Feedback pairs a metric label, measured score, target state, and concise next action. When a selected metric scores 80 or above, use Progress Emerald to acknowledge proficiency, then redirect attention toward the lowest-scoring selected area. The tone is confident and constructive, never punitive.

## Do's and Don'ts

### Do:

- **Do** make the next rehearsal action visually unambiguous with one primary cobalt control per action group.
- **Do** use the original Zinc canvas, surfaces, borders, and light text in night mode while retaining cobalt actions and accents.
- **Do** connect semantic color to measured evidence, completion, or actionable system state.
- **Do** keep feedback direct and encouraging, especially when redirecting a proficient user toward a weaker metric.
- **Do** preserve visible keyboard focus and readable contrast across interactive elements.

### Don't:

- **Don't** introduce points, streaks, trophies, confetti, collectible badges, or other gamification patterns.
- **Don't** make the product resemble a corporate analytics suite with dense KPI walls, executive charts, or ornamental dashboards.
- **Don't** use flashy gradients, neon glows, decorative glass effects, or attention-seeking motion.
- **Don't** apply Performance Cobalt to passive content or large background areas; its restraint gives it meaning.
- **Don't** add shadows when tonal layering or a border already communicates the hierarchy.
