# Changes since `main`

This document covers the net changes on `frontend-iter-1`, which started from `main` at commit `9f1e06d6`. It is a file-by-file summary, not a chronological log.

## Repository and design documentation

| File | What changed |
| --- | --- |
| `.codex/hooks.json` | Added Impeccable checks after UI edits and at the end of a design task. |
| `.gitignore` | Ignored the local `.impeccable/` directory and `.agents/skills/impeccable/` installation. |
| `PRODUCT.md` | Added the product purpose, users, workflow, capabilities, constraints, and product principles. |
| `DESIGN.md` | Added the cream light theme, Zinc dark theme, blue accent system, typography, spacing, component guidance, and UI rules. |
| `nextSteps.md` | Removed the obsolete implementation checklist from the repository. |
| `changes.md` | Replaced the broad session summary with this file-by-file record and current verification results. |

## Backend

| File | What changed |
| --- | --- |
| `backend/itspeak/audio.py` | Aligned pacing, intonation, and filler-word proficiency with the `80/100` threshold; capped explicitly off-target results below that threshold; changed filler assessment to use the documented rate per 100 words; and stored up to three distinct filler-word examples. |
| `backend/itspeak/jobs.py` | Updated improvement guidance to use consistent metric names and threshold wording; removed recommendations for another priority from proficient feedback; included the exact eye-contact threshold; and added filler counts, rates, and up to three examples to filler feedback. |
| `backend/itspeak/pipeline.py` | Removed the repeated stationary-camera spatial-use warning from analysis results. |
| `backend/itspeak/quality.py` | Removed user-facing technical limitations about stationary-camera estimates and geometric smile proxies. |
| `backend/tests/test_audio_target_alignment.py` | Added regression tests for the calibrated pacing range, off-target score cap, documented filler-word rate, and three-example limit. |
| `backend/tests/test_improvement_focus.py` | Added coverage for the exact proficiency boundary, removal of extra priority recommendations, explicit eye-contact threshold, and limited filler-word examples. |

## Frontend routes and global styling

| File | What changed |
| --- | --- |
| `frontend/app/globals.css` | Added the complete theme token system and reusable UI classes; increased the default type and icon-control sizes; styled the date control for both themes; and corrected dark-mode theme-toggle contrast. |
| `frontend/app/layout.js` | Updated product metadata and added a pre-render theme initializer to prevent the wrong theme flashing during load. |
| `frontend/app/page.js` | Polished the Practice archive with stronger hierarchy, detailed loading placeholders, empty/error states, reliable create/edit/pin/delete states, and plain Session 1 baseline wording. |
| `frontend/app/project/[id]/page.js` | Added bordered project, session, latest-session, and progress sections; added a Selected archetype heading; grouped audio and visual improvement areas; added project editing; used the full width for projects without sessions; and simplified copy to explain only that Session 1 is the progress baseline. |
| `frontend/app/session/[id]/page.js` | Rebuilt the combined analysis hierarchy; added retry and transcript-save errors; moved the overall score and current ratings into one summary; separated Needs improvement from Done well; added observed low-scoring areas; bolded measured values; and clarified transcript, recording, and progress sections. |
| `frontend/app/sign-in/[[...sign-in]]/page.jsx` | Replaced control-room and retained-history jargon with plain speaking-practice copy. |
| `frontend/app/sign-up/[[...sign-up]]/page.jsx` | Replaced workspace and baseline jargon with plain account and progress copy. |

## Frontend components

| File | What changed |
| --- | --- |
| `frontend/components/AddProjectModal.js` | Polished the create/edit form; added larger archetype radio indicators and metric selection controls; renamed `Rehearsal goal` to `Project description`; enlarged and themed the calendar control; added save/error states; and simplified the selection instructions. |
| `frontend/components/ImprovementAreaIcon.js` | Added a consistent SVG icon set for all seven audio and visual improvement areas. |
| `frontend/components/AddSessionModal.js` | Added dialog semantics, clearer upload instructions, file constraints, consistent controls, and blue theme styling. |
| `frontend/components/AllSessionsModal.js` | Simplified the dialog to `Sessions`, removed retained-session jargon, and improved close-button accessibility. |
| `frontend/components/Navbar.js` | Standardised the product name, removed the unused notification action, added the accessible theme switch, and aligned navigation spacing and controls. |
| `frontend/components/ProcessingModal.js` | Added determinate analysis progress above warnings, clearer processing and replacement states, and plain replacement copy explaining the Session 1 baseline. |
| `frontend/components/ProjectCard.js` | Reworked card hierarchy; showed selected improvement areas and session capacity; added deadline states including `Due today`; and made the project action menu keyboard-accessible with pending states. |
| `frontend/components/RatingBar.js` | Normalised invalid or out-of-range values, improved score contrast, and added complete accessible meter values. |
| `frontend/components/ScoreRing.js` | Normalised score input, switched to theme-aware semantic colours, and improved the accessible score description. |
| `frontend/components/SessionCard.js` | Added semantic score colours, replaced arrow-only progress with `Improved` or `Lower`, standardised `Facial expressions`, and improved responsive wrapping. |
| `frontend/components/SkillRadar.js` | Increased chart and label sizes, added a screen-reader summary, and made chart colours theme-aware. |
| `frontend/components/ThemeToggle.js` | Added the persistent accessible light/dark switch with sun and moon states. |
| `frontend/components/TimelineChart.js` | Standardised `Facial expressions` naming and made axes, grid, tooltip, and series colours theme-aware. |
| `frontend/components/VideoAnalysisPlayer.js` | Improved recording loading and overlay errors, made the eye-contact timeline accessible, raised metric readability, limited visible warnings, and presented warnings in red. |

## Frontend helpers and configuration

| File | What changed |
| --- | --- |
| `frontend/lib/analysisPresentation.mjs` | Added analysis-stage progress calculation, filtering of technical camera/proxy caveats, and safe splitting of measurable phrases for bold display. |
| `frontend/lib/improvementAreas.mjs` | Standardised the seven metric labels, including `Facial expressions`, and removed the inconsistent Unicode icon data now replaced by SVGs. |
| `frontend/lib/reportAdapter.js` | Normalised legacy guidance; prevented off-target audio metrics from appearing proficient; ranked corrected scores; generated observed-area feedback; removed other-priority recommendations from Done well; stated the `80/100` threshold explicitly; and displayed up to three distinct filler-word examples. |
| `frontend/lib/theme.mjs` | Added supported theme constants, safe theme normalisation, local-storage persistence, and the initial theme script. |
| `frontend/tailwind.config.js` | Connected Tailwind colours and typography to the theme variables and raised the minimum readable text sizes. |

## Tests

| File | What changed |
| --- | --- |
| `frontend/tests/analysisPresentation.test.mjs` | Added coverage for analysis progress, measurable-value formatting, warning filtering, and combined-analysis presentation. |
| `frontend/tests/improvementFocus.test.mjs` | Added coverage for threshold behaviour, legacy off-target pacing, explicit eye-contact threshold, observed-area wording, removal of extra recommendations, and the three-example filler limit. |
| `frontend/tests/persistenceUi.test.mjs` | Added coverage for project/session capacity, the single first-session action, project editing, simplified project copy, accessible selection icons, and the themed date control. |
| `frontend/tests/theme.test.mjs` | Added coverage for safe theme restoration, the accessible switch, Zinc dark-mode tokens, and the corrected dark-toggle contrast styles. |

## Removed

- Duplicate first-session actions and the generic project heading.
- Dashboard introduction copy that repeated the page purpose.
- Violet as the primary UI accent.
- User-facing stationary-camera and geometric-proxy caveats.
- `Smile proxy` from the score radar.
- `Current rating vs target` wording.
- Other-priority recommendations from the Done well section.
- Internal UI jargon including `retained`, `protected`, `coaching focus`, `scoring profile`, and `pillar progress`.

## Verification completed

- Backend suite: 55 tests passing.
- Frontend suite: 28 tests passing.
- Next.js production build passing.
- Dark theme-toggle contrast checked against the active Zinc palette.
- `git diff --check` passing.
