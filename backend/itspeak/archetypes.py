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
    ArchetypeDefinition("startup_pitch", "Startup Pitch", "enabled"),
    ArchetypeDefinition("academic_conference", "Academic / Conference", "enabled"),
    ArchetypeDefinition("informal_team", "Informal / Team", "enabled"),
    ArchetypeDefinition("job_interview", "Job Interview", "enabled"),
)


def list_archetypes() -> list[dict[str, str]]:
    return [asdict(item) for item in ARCHETYPE_REGISTRY]
