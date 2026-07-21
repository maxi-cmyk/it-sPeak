"""LLM coaching layer.

This is the *execution* layer. It converts normalized scores + context into a
strict JSON array of ``CoachingCard`` objects using **zero-shot / few-shot
structured prompting** at a **low temperature** — no RAG, no external retrieval.

The prompt design does three jobs:

1. **Inject** the normalized Face/Body scores, the archetype's expectations, the
   user's raw audience context, and (optionally) baseline scores for progress.
2. **Constrain** the output shape: a JSON array, max 3 cards per module, each
   card with exactly ``module``/``problem``/``importance``/``actionable_fix``.
3. **Guard** against hallucination: forbid unverifiable statistics and restrict
   advice to physical, delivery-grounded techniques.

The OpenAI API is used with GPT-4o-mini by default. If the API is
unavailable the service degrades to a deterministic rule-based fallback so the
pipeline never hard-crashes.
"""

from __future__ import annotations

import json
import logging
import re

from .config import compute_progress, get_archetype_config
from .models import (
    Archetype,
    CoachingCard,
    ImprovementArea,
    Module,
    NormalizedScores,
    VideoAnalysisResult,
)
from .settings import get_settings

logger = logging.getLogger("itspeak.coaching")

MAX_CARDS_PER_MODULE = 3


# --------------------------------------------------------------------------- #
# Prompt templates
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = """\
You are it'sPEAK, an elite public-speaking delivery coach. You analyse a
speaker's *physical delivery* (face and body) and produce sharp, tactical
coaching.

You are given objective, camera-derived scores (0-100) for the speaker, the
target speaking archetype, and the audience/context the speaker is preparing
for. Your job is to translate those numbers into concrete coaching cards.

HARD RULES (never break these):
- Output ONLY a JSON array. No prose, no markdown, no code fences, no comments.
- Each element is an object with EXACTLY these keys, all string-valued:
  "module", "problem", "importance", "actionable_fix".
- "module" MUST be either "face" or "body".
- Return AT MOST {max_cards} cards for the "face" module and AT MOST {max_cards}
  for the "body" module. Prioritise the LOWEST-scoring behaviours. If a metric
  is already strong (>= 80), do NOT create a card criticising it.
- "problem": describe the specific tracked behaviour that needs work.
- "importance": explain why it hurts THIS speaker's presence for THIS audience
  and archetype. Reference the audience context explicitly.
- "actionable_fix": ONE tactical, physical exercise or trick they can rehearse
  and apply next time. It must be concrete and rehearsable (a drill, a cue, a
  body mechanic) — not a vague platitude.

SAFETY / ANTI-HALLUCINATION RULES:
- Do NOT cite statistics, studies, percentages, or "experts say" style claims.
  You have no verified sources; inventing them is forbidden.
- Do NOT diagnose medical, psychological, or personality traits.
- Restrict ALL advice to physical delivery and stagecraft mechanics that
  directly relate to the provided face/body scores (eye contact, expression,
  posture, gestures). Do not comment on voice, slides, or content — you cannot
  observe those.
- If the data is weak/low-confidence, prefer fewer, high-certainty cards.
"""

USER_PROMPT_TEMPLATE = """\
TARGET ARCHETYPE: {archetype_label}
ARCHETYPE EXPECTATIONS: {archetype_description}

AUDIENCE / CONTEXT (verbatim from the speaker):
\"\"\"{audience_context}\"\"\"

PROJECT IMPROVEMENT AREAS:
{improvement_focus}
Create coaching cards only for the selected face/body modules. Voice coaching
is handled separately by the audio pipeline.

NORMALIZED DELIVERY SCORES (0-100, calibrated to the archetype above):
  FACE MODULE
    - eye_contact_score : {eye_contact_score}
    - expression_score  : {expression_score}
  BODY MODULE
    - posture_score     : {posture_score}
    - gesture_score     : {gesture_score}
    - movement_purposefulness_score : {movement_purposefulness_score}
    - spatial_use_score              : {spatial_use_score}

Metrics shown as "insufficient_data" MUST be excluded from judgments and
coaching. Movement labels describe observable motion only; never infer intent,
emotion, anxiety, nervousness, or mental state.

{progress_block}
ANALYSIS NOTES (data-quality warnings, factor into your confidence):
{warnings_block}

Produce the JSON array of coaching cards now, focusing on the weakest areas for
this archetype and audience. Respect every HARD RULE and SAFETY RULE.
"""

# One-shot example steers the model onto the exact schema (few-shot grounding).
FEWSHOT_EXAMPLE = """\
EXAMPLE OF THE EXACT OUTPUT FORMAT (structure only — do not reuse the content):
[
  {
    "module": "face",
    "problem": "Gaze repeatedly drifts down and to the side instead of holding the camera/audience line.",
    "importance": "For a board audience judging your command of the material, dropped eye contact reads as uncertainty and undercuts your authority.",
    "actionable_fix": "Rehearse the 'lighthouse' drill: pick 3 fixed points at eye level, hold each for one full sentence before moving, and never look down while speaking a key number."
  }
]
"""


# --------------------------------------------------------------------------- #
# Coaching service
# --------------------------------------------------------------------------- #
class CoachingService:
    """Assembles the prompt, calls the LLM, and validates the response.

    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ---- public API ---- #
    def generate_cards(
        self,
        scores: NormalizedScores,
        archetype: Archetype,
        audience_context: str,
        analysis: VideoAnalysisResult | None = None,
        baseline: NormalizedScores | None = None,
        improvement_areas: list[ImprovementArea] | None = None,
    ) -> list[CoachingCard]:
        """Return validated coaching cards (<= 3 per module).

        Never raises for LLM/transport problems: on any failure it logs and
        returns a deterministic rule-based fallback so the pipeline completes.
        """
        system_prompt, user_prompt = self.build_prompt(
            scores, archetype, audience_context, analysis, baseline, improvement_areas
        )
        selected_modules = _selected_visual_modules(improvement_areas)
        if not selected_modules:
            return []
        try:
            raw = self._call_llm(system_prompt, user_prompt)
            cards = [card for card in self._parse_and_validate(raw) if card.module in selected_modules]
            if cards:
                return cards
            logger.warning("LLM returned no valid cards; using rule-based fallback.")
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash
            logger.warning("LLM coaching failed (%s); using rule-based fallback.", exc)
        return self._fallback_cards(scores, archetype, improvement_areas)

    def build_prompt(
        self,
        scores: NormalizedScores,
        archetype: Archetype,
        audience_context: str,
        analysis: VideoAnalysisResult | None,
        baseline: NormalizedScores | None,
        improvement_areas: list[ImprovementArea] | None = None,
    ) -> tuple[str, str]:
        """Assemble (system_prompt, user_prompt)."""
        cfg = get_archetype_config(archetype)

        progress_block = ""
        delta = compute_progress(scores, baseline)
        if delta:
            lines = "\n".join(f"    - {k}: {v:+.1f}" for k, v in delta.items())
            progress_block = (
                "PROGRESS VS. PREVIOUS SESSION (positive = improvement):\n"
                f"{lines}\n"
                "Acknowledge genuine improvement briefly where relevant.\n\n"
            )

        warnings = (analysis.warnings if analysis else []) or ["(none)"]
        warnings_block = "\n".join(f"  - {w}" for w in warnings)

        system = SYSTEM_PROMPT.format(max_cards=MAX_CARDS_PER_MODULE) + "\n" + FEWSHOT_EXAMPLE
        user = USER_PROMPT_TEMPLATE.format(
            archetype_label=cfg.label,
            archetype_description=cfg.description,
            audience_context=(audience_context.strip() or "(no audience context provided)"),
            improvement_focus=", ".join(area.value for area in (improvement_areas or list(ImprovementArea))),
            eye_contact_score=scores.eye_contact_score,
            expression_score=scores.expression_score,
            posture_score=scores.posture_score,
            gesture_score=scores.gesture_score,
            movement_purposefulness_score=scores.movement_purposefulness_score if scores.movement_purposefulness_score is not None else "insufficient_data",
            spatial_use_score=scores.spatial_use_score if scores.spatial_use_score is not None else "insufficient_data",
            progress_block=progress_block,
            warnings_block=warnings_block,
        )
        return system, user

    # ---- OpenAI provider ---- #
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call GPT-4o-mini through the official OpenAI SDK."""
        from openai import OpenAI

        if not self._settings.openai_api_key:
            raise RuntimeError("ITSPEAK_OPENAI_API_KEY is not set.")

        client = OpenAI(api_key=self._settings.openai_api_key)
        response = client.chat.completions.create(
            model=self._settings.coaching_model,
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_output_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    # ---- validation ---- #
    def _parse_and_validate(self, raw: str) -> list[CoachingCard]:
        """Parse the LLM JSON and enforce the card contract + per-module caps."""
        payload = _extract_json_array(raw)
        if not isinstance(payload, list):
            raise ValueError("LLM output was not a JSON array.")

        per_module: dict[Module, int] = {module: 0 for module in Module}
        cards: list[CoachingCard] = []
        for item in payload:
            try:
                card = CoachingCard.model_validate(item)
            except Exception as exc:  # noqa: BLE001 - skip malformed cards
                logger.warning("Dropping malformed coaching card: %s", exc)
                continue
            if per_module[card.module] >= MAX_CARDS_PER_MODULE:
                continue  # enforce the hard cap even if the model over-produced
            per_module[card.module] += 1
            cards.append(card)
        return cards

    # ---- deterministic fallback ---- #
    def _fallback_cards(
        self,
        scores: NormalizedScores,
        archetype: Archetype,
        improvement_areas: list[ImprovementArea] | None = None,
    ) -> list[CoachingCard]:
        """Rule-based cards used when the LLM is unavailable.

        Targets the single weakest metric in each module so the user still gets
        grounded, safe guidance.
        """
        cfg = get_archetype_config(archetype)
        catalogue: dict[str, tuple[Module, str, str, str]] = {
            "eye_contact_score": (
                Module.FACE,
                "Eye contact with the camera/audience line is inconsistent.",
                f"For a {cfg.label} setting, wandering eyes read as low conviction and weaken your authority.",
                "Run the 'lighthouse' drill: fix on 3 eye-level points, hold each for a full sentence, and never look down on a key line.",
            ),
            "expression_score": (
                Module.FACE,
                "Facial expressiveness is off-target for this archetype.",
                f"A {cfg.label} audience calibrates trust to your face; a mismatch in animation makes the message feel off.",
                "Rehearse in a mirror marking 3 'expression beats' per minute (a raised brow or smile on key phrases) until they feel automatic.",
            ),
            "posture_score": (
                Module.BODY,
                "Posture drifts from an upright, grounded baseline.",
                f"Slumping or leaning undercuts the commanding presence a {cfg.label} audience expects.",
                "Set a pre-talk anchor: feet shoulder-width, weight centred, crown of the head 'lifted by a string'; reset to it between points.",
            ),
            "gesture_score": (
                Module.BODY,
                "Gesture level and range don't match the archetype's ideal.",
                f"For a {cfg.label} audience, mismatched gesturing distracts from your words instead of reinforcing them.",
                "Define a 'gesture box' at chest height and rehearse landing 2-3 deliberate gestures per point, returning hands to a neutral rest between them.",
            ),
            "movement_purposefulness_score": (
                Module.BODY,
                "Observable torso movement lacks a clear settle-and-translate pattern.",
                f"For a {cfg.label} audience, repeated weight shifts compete with deliberate stage movement.",
                "Use the move-plant-deliver drill: move only during a transition, plant both feet, then deliver the next complete point.",
            ),
            "spatial_use_score": (
                Module.BODY,
                "Use of the available frame or stage area is off-target for this archetype.",
                f"A {cfg.label} delivery benefits when space changes reinforce the structure of the talk.",
                "Mark three floor zones and assign one idea to each; move once between ideas and stay planted within each zone.",
            ),
        }
        ranked = sorted(
            (
                (metric, value)
                for metric, value in scores.available().items()
                if metric in catalogue
            ),
            key=lambda kv: kv[1],
        )
        selected_modules = _selected_visual_modules(improvement_areas)
        selected_areas = set(improvement_areas or list(ImprovementArea))
        area_by_metric = {
            "eye_contact_score": ImprovementArea.EYE_CONTACT,
            "expression_score": ImprovementArea.FACIAL_EXPRESSION,
            "posture_score": ImprovementArea.POSTURE,
            "gesture_score": ImprovementArea.GESTURES,
        }
        cards: list[CoachingCard] = []
        for metric, value in ranked:
            if value >= 80:
                continue  # don't nag about already-strong areas
            module, problem, importance, fix = catalogue[metric]
            if module not in selected_modules or area_by_metric.get(metric) not in selected_areas:
                continue
            cards.append(
                CoachingCard(
                    module=module, problem=problem, importance=importance, actionable_fix=fix
                )
            )
        return cards[:4]  # at most the 4 metrics; naturally <=2 per module


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _selected_visual_modules(improvement_areas: list[ImprovementArea] | None) -> set[Module]:
    selected = set(improvement_areas or list(ImprovementArea))
    modules: set[Module] = set()
    if selected & {ImprovementArea.EYE_CONTACT, ImprovementArea.FACIAL_EXPRESSION}:
        modules.add(Module.FACE)
    if selected & {ImprovementArea.POSTURE, ImprovementArea.GESTURES}:
        modules.add(Module.BODY)
    return modules


def _extract_json_array(raw: str):
    """Best-effort extraction of a JSON array from an LLM response.

    Handles clean JSON, accidental code fences, or leading/trailing prose.
    """
    text = raw.strip()
    if not text:
        raise ValueError("Empty LLM response.")

    # Strip ```json ... ``` fences if the model added them despite instructions.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the first '[' ... last ']' slice.
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not locate a JSON array in the LLM response.")
