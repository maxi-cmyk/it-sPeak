"""Archetype registry scaffold; scoring definitions will be expanded later."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ArchetypeDefinition:
    key: str
    label: str
    status: str


ARCHETYPE_REGISTRY = (
    ArchetypeDefinition("corporate_board", "Corporate / Board", "enabled"),
    ArchetypeDefinition("motivational_keynote", "Motivational / Keynote", "enabled"),
    ArchetypeDefinition("startup_pitch", "Startup Pitch", "planned"),
    ArchetypeDefinition("academic_conference", "Academic / Conference", "planned"),
    ArchetypeDefinition("informal_team", "Informal / Team", "planned"),
    ArchetypeDefinition("job_interview", "Job Interview", "planned"),
    ArchetypeDefinition("custom", "Custom", "planned"),
)


def list_archetypes() -> list[dict[str, str]]:
    return [asdict(item) for item in ARCHETYPE_REGISTRY]
