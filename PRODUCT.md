# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

it'sPEAK serves university students and early-career professionals preparing
for consequential spoken communication: presentations, pitches, interviews,
conferences, and keynote-style talks. They use the product while rehearsing and
need specific feedback they can apply before the real event.

## Product Purpose

it'sPEAK helps a user become ready for a specific speaking event. It analyses a
short rehearsal, turns observable delivery signals into concrete actions, and
makes improvement across repeated rehearsals visible and encouraging. Readiness
is the primary outcome; measurable progress is the mechanism and motivation.

## Positioning

The product combines multimodal analysis of the user's own rehearsal with a
project-based improvement loop. Instead of teaching generic presentation
principles, it evaluates selected vocal and visual improvement areas, preserves
a baseline, and helps the user focus each subsequent rehearsal on the weakest
relevant areas.

## Operating Context

Users create a project for an upcoming speaking event, choose one or more areas
of improvement, and upload an English-language presentation video. The product
checks recording quality before analysis, processes the recording
asynchronously, and returns scores, confidence information, a transcript,
prioritised coaching actions, and synchronised visual review. Users can retain
up to five successful sessions in a project and use the first as a protected
baseline while preparing for the event.

## Capabilities and Constraints

- Recordings are English-language videos with a permanent maximum duration of
  three minutes.
- The seven permanent selectable improvement metrics are pacing, intonation,
  filler words, eye contact, facial expression, posture, and gestures.
- A project permanently retains at most five successful sessions. Session 1 is
  the protected baseline and cannot be replaced.
- Recordings, reports, and project history remain private and require an
  authenticated account.
- Clerk owns authentication. The web client sends authenticated requests to
  FastAPI, while Supabase persistence and private Storage access remain
  backend-owned.
- Quality and confidence limitations must remain visible. Geometric signals
  describe observable delivery and must not be presented as emotion,
  personality, intent, anxiety, or clinical inference.
- A selected metric above 80 is treated as proficient; the product redirects
  attention toward the lowest-scoring other selected area.

## Brand Commitments

The product name is `it'sPEAK`. Product language is direct, encouraging, and
specific about what the analysis observed. It does not shame the user, inflate
measurement certainty, or imply psychological diagnosis.

## Evidence on Hand

- The implemented product workflow and technical boundaries are documented in
  `README.md`.
- Current dashboard, project, upload, processing, and session-result surfaces
  are implemented under `frontend/app` and `frontend/components`.
- Metric scoring, quality gates, coaching, persistence, and authentication are
  implemented under `backend/itspeak` with tests under `backend/tests`.
- Supabase migrations and schema snapshots live under `supabase/migrations` and
  `backend/persistence`.
- No approved testimonials, customer logos, deployment claims, or independent
  outcome studies are currently present. Future interface work must not invent
  them.

## Product Principles

1. Optimise every workflow for readiness for the user's real speaking event.
2. Make improvement visible, specific, and motivating across rehearsals.
3. Turn each weak metric into one concrete action the user can practise next.
4. Preserve trust through private data handling and honest measurement limits.
5. Prioritise the user's weakest relevant area without obscuring demonstrated
   proficiency.
