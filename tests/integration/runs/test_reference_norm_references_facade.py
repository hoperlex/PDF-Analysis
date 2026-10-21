"""`NORM-REFS-RUN-01`: the Runs public facade exports the listing use case and its port."""

from __future__ import annotations

from types import SimpleNamespace

from auditmanager.runs import public as runs_public
from auditmanager.runs import reference_pipeline as chain


def test_the_use_case_and_its_port_are_the_runs_public_surface() -> None:
    assert runs_public.read_run_norm_references is chain.read_run_norm_references
    assert runs_public.RunNormReferences is chain.RunNormReferences
    assert runs_public.SavedRunPageText is chain.SavedRunPageText
    assert runs_public.SavedRunTextReader is chain.SavedRunTextReader
    assert runs_public.NORM_REFERENCES_STATES == chain.STATES
    assert (
        runs_public.NORM_REFERENCES_READY,
        runs_public.NORM_REFERENCES_SNAPSHOT_NOT_PINNED,
        runs_public.NORM_REFERENCES_TEXT_UNAVAILABLE,
        runs_public.NORM_REFERENCES_TOO_MANY_CITATIONS,
    ) == chain.STATES


def test_a_reader_with_the_port_method_satisfies_the_runtime_protocol() -> None:
    reader = SimpleNamespace(saved_page_text=lambda session, **keywords: None)

    assert isinstance(reader, runs_public.SavedRunTextReader)
