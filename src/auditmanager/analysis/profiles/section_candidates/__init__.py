"""Read-only legacy vocabulary for section profile authors."""

from auditmanager.analysis.profiles.section_candidates.metadata import (
    ProfileCandidate,
    SheetTypeCandidate,
    load_candidates,
)

__all__ = ["ProfileCandidate", "SheetTypeCandidate", "load_candidates"]
