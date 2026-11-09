"""`AR-V3-OPT-IN` (`Q3`): the optimisation reads the version's newest published run of the STANDARD analysis.

A published AR v3 member is a run of the version and is listed, but it never takes the place of the standard run as the
text the specification is read from. Container-free: the reader is a fake, `_newest_published` is the function the
section specification and the proposals both call.
"""

from __future__ import annotations

import pytest

from auditmanager.optimisation.project_match import RunCandidate, _newest_published
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

VERSION = "ver_01M2545JSD15ETSNNV904XA001"


class _Reader:
    def __init__(self, runs: tuple[RunCandidate, ...]) -> None:
        self._runs = runs

    def runs_newest_first(self, session: object, *, version_uid: str) -> tuple[RunCandidate, ...]:
        return self._runs


def _id() -> str:
    return str(RunId.new())


def test_a_newer_published_v3_run_does_not_take_the_standard_one_s_place() -> None:
    v3, standard = _id(), _id()
    reader = _Reader((RunCandidate(v3, "published", False), RunCandidate(standard, "published")))
    assert _newest_published(reader, object(), VERSION) == standard  # type: ignore[arg-type]


def test_a_version_whose_only_published_run_is_v3_has_none() -> None:
    reader = _Reader((RunCandidate(_id(), "published", False), RunCandidate(_id(), "failed")))
    assert _newest_published(reader, object(), VERSION) is None  # type: ignore[arg-type]


def test_the_default_candidate_is_standard_so_a_reader_that_knows_one_analysis_is_unchanged() -> None:
    run = _id()
    assert RunCandidate(run, "published").standard_analysis is True
    assert _newest_published(_Reader((RunCandidate(run, "published"),)), object(), VERSION) == run  # type: ignore[arg-type]


def test_the_older_standard_run_is_picked_among_several() -> None:
    newest_v3, newer_standard, older_standard = _id(), _id(), _id()
    reader = _Reader((
        RunCandidate(newest_v3, "published", False),
        RunCandidate(newer_standard, "running"),
        RunCandidate(older_standard, "published"),
    ))
    assert _newest_published(reader, object(), VERSION) == older_standard  # type: ignore[arg-type]


def test_a_malformed_flag_is_an_integrity_error_not_a_guess() -> None:
    with pytest.raises(DomainError) as refused:
        _newest_published(_Reader((RunCandidate(_id(), "published", "no"),)), object(), VERSION)  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.INTERNAL_ERROR
