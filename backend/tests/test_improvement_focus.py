from __future__ import annotations

import unittest

from itspeak.jobs import _apply_improvement_focus
from itspeak.models import (
    Archetype,
    AudioAnalysisResult,
    BodyMetrics,
    CoachingCard,
    CoachingReport,
    FaceMetrics,
    ImprovementArea,
    Module,
    NormalizedScores,
    VideoAnalysisResult,
)


def make_report(areas: list[ImprovementArea]) -> CoachingReport:
    return CoachingReport(
        archetype=Archetype.CORPORATE_BOARD,
        scores=NormalizedScores(
            eye_contact_score=85,
            expression_score=85,
            posture_score=70,
            gesture_score=70,
            archetype=Archetype.CORPORATE_BOARD,
        ),
        raw_analysis=VideoAnalysisResult(face=FaceMetrics(), body=BodyMetrics()),
        audio=AudioAnalysisResult(
            summary={},
            performance_scores={"aggregate_vocal_rating": 65, "pacing_alignment": 55, "vocal_intonation_variety": 75, "word_choice_efficiency": 65},
            readable_metrics={},
            transcript={"text": ""},
            actionable_coaching_cards=["Slow the rushed phrases."],
        ),
        cards=[
            CoachingCard(module=Module.FACE, problem="Face", importance="Face", actionable_fix="Face"),
            CoachingCard(module=Module.BODY, problem="Body", importance="Body", actionable_fix="Body"),
        ],
        improvement_areas=areas,
    )


class ImprovementFocusTest(unittest.TestCase):
    def test_lowest_selected_score_is_first_and_proficient_cards_are_removed(self):
        report = _apply_improvement_focus(
            make_report([ImprovementArea.PACING, ImprovementArea.EYE_CONTACT, ImprovementArea.POSTURE]),
            {"vocal_score": 55, "face_score": 85, "body_score": 70},
        )

        self.assertEqual([item.area for item in report.improvement_guidance], [ImprovementArea.PACING, ImprovementArea.POSTURE, ImprovementArea.EYE_CONTACT])
        self.assertEqual([item.priority for item in report.improvement_guidance], [1, 2, 3])
        self.assertTrue(report.improvement_guidance[-1].proficient)
        self.assertIn("Prioritise Pacing", report.improvement_guidance[-1].message)
        self.assertEqual([card.module for card in report.cards], [Module.BODY])
        self.assertEqual(len(report.audio.actionable_coaching_cards), 1)

    def test_single_proficient_area_gets_maintenance_message_without_criticism(self):
        report = _apply_improvement_focus(
            make_report([ImprovementArea.EYE_CONTACT]),
            {"vocal_score": 55, "face_score": 85, "body_score": 70},
        )

        self.assertEqual(report.cards, [])
        self.assertEqual(report.audio.actionable_coaching_cards, [])
        self.assertIn("select another area", report.improvement_guidance[0].message)

    def test_threshold_score_is_proficient_and_gets_no_coaching(self):
        source = make_report([ImprovementArea.PACING])
        source.audio.performance_scores["pacing_alignment"] = 80

        report = _apply_improvement_focus(source)

        self.assertTrue(report.improvement_guidance[0].proficient)
        self.assertEqual(report.audio.actionable_coaching_cards, [])
        self.assertEqual(report.cards, [])


if __name__ == "__main__":
    unittest.main()
