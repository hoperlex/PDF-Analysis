"""The optimisation reads the version's newest published run.

Container-free: the reader is a fake, `_newest_published` is the function the section specification and the proposals both
call.
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


def test_the_newest_published_run_is_the_one_read() -> None:
    newest, older = _id(), _id()
    reader = _Reader((RunCandidate(newest, "published"), RunCandidate(older, "published")))
    assert _newest_published(reader, object(), VERSION) == newest  # type: ignore[arg-type]


def test_a_version_with_no_published_run_has_none() -> None:
    reader = _Reader((RunCandidate(_id(), "running"), RunCandidate(_id(), "failed")))
    assert _newest_published(reader, object(), VERSION) is None  # type: ignore[arg-type]


def test_an_unfinished_newer_run_does_not_take_the_published_ones_place() -> None:
    newer, published = _id(), _id()
    reader = _Reader((RunCandidate(newer, "running"), RunCandidate(published, "published")))
    assert _newest_published(reader, object(), VERSION) == published  # type: ignore[arg-type]


def test_a_malformed_candidate_is_an_integrity_error_not_a_guess() -> None:
    with pytest.raises(DomainError) as refused:
        _newest_published(_Reader((RunCandidate(_id(), 7),)), object(), VERSION)  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.INTERNAL_ERROR
