# Changes since `main`

This summary covers the current `frontend-iter-1` workspace, which started from `main` at commit `9f1e06d6`. It records the net result rather than a chronological development log.

## Added

- A documented product and visual system in `PRODUCT.md`, `DESIGN.md`, and `.impeccable/design.json`.
- The Impeccable frontend workflow, project configuration, and design checks under `.agents/skills/impeccable`, `.impeccable`, and `.codex/hooks.json`.
- Shared frontend design tokens and reusable component styles for page structure, cards, controls, fields, chips, status panels, typography, semantic feedback, and responsive layouts.
- A persistent light/night mode switch in the navigation:
  - light mode uses the cream and parchment workspace;
  - night mode restores the original Zinc dark design;
  - both modes retain the blue action and focus accents.
- Project editing from inside a project folder, including the project details, deadline, speaking archetype, and selected audio/visual improvement areas.
- Retained-session count and capacity information on project cards and project folders.
- Analysis progress presentation, including a progress bar above recording warnings while analysis is running.
- A separate “Other areas observed” feedback section for low-scoring metrics that were not selected as project focuses.
- Safe formatting that bolds measured values and score phrases inside analysis feedback.
- Theme-aware charts, score rings, Clerk authentication forms, controls, and semantic status colors.
- Frontend helpers for analysis presentation, theme persistence, feedback adaptation, and technical-warning filtering.
- Regression coverage for project-folder UI, feedback prioritisation, exact threshold behaviour, metric naming, analysis progress, technical-warning filtering, and theme persistence.
- A backend regression test confirming that a score of exactly 80 is proficient and generates no coaching cards.

## Changed

- Reworked the frontend into the “Rehearsal Control Room” design with larger readable type, stronger hierarchy, restrained blue accents, darker amber attention states, and red warning/error treatment.
- Improved dashboard loading, empty, and error states and made the primary project action clearer.
- Consolidated the first-session flow so an empty project shows one `Add first session` action in the retained-sessions area.
- Made project folders show the names of selected priorities instead of only a priority count.
- Updated project and session layouts for clearer responsive behaviour on smaller screens.
- Updated the results page to:
  - state the `80/100` coaching threshold explicitly;
  - rank selected focus areas from lowest score upward;
  - separate areas needing improvement from areas done well;
  - label the ratings section `Current rating`;
  - keep coaching cards aligned with selected focus modules;
  - recommend consideration of other unselected areas that score below the threshold.
- Standardised user-facing `Face` and `Facial expression` labels to `Facial expressions`, including project focuses, ratings, progress data, backend guidance, and the radar chart.
- Changed the coaching boundary so scores below 80 receive coaching while scores of 80 or above are proficient and receive no coaching feedback.
- Normalised saved analysis guidance in the frontend so reports created with the old 80-point boundary do not display stale coaching.
- Changed observed-area wording to: `We observed that [area] scored [score]/100, which is below the 80/100 coaching threshold.`
- Updated the backend improvement-focus filter and fallback copy to use the same threshold and terminology as the frontend.
- Preserved the existing score-priority behaviour: proficient selected areas redirect attention to the lowest-scoring other selected area.
- Made analysis charts, tooltips, score tracks, authentication surfaces, and supporting controls follow the selected light/night palette.

## Removed

- The dashboard introduction headings `Your rehearsal projects` and `Track each...`.
- The generic `Project` heading/prefix inside project folders.
- The duplicate `Start session 1` action.
- The `Current rating vs target` label.
- User-facing technical caveats about stationary-camera spatial-use assumptions and geometric smile proxies.
- The redundant spatial-use warning emitted by the backend pipeline.
- The `Smile proxy` entry from the results radar chart.
- Violet as the primary frontend accent; blue now consistently represents actions, focus, selection, and developing scores.
- The old `at or below 80` coaching rule and wording.

## Verification completed

- Frontend test suite: 23 tests passing.
- Targeted backend improvement-focus tests: 3 tests passing.
- Next.js production build passing.
- Impeccable design sidecar parses as valid JSON.
- `git diff --check` passing.
