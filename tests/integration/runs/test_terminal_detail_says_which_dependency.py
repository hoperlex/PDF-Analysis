"""`D-46` / `R-29`: a failed run says **which** dependency, and cannot say anything else.

`W29-SAY` made the screen explain what ``dependency_unavailable`` *means* and registered
`D-46` because the run reading still could not say **which** dependency: the catalog's
``safe_detail_keys`` live on the ``ErrorEnvelope``, and a ``200`` run reading is not an
error envelope. The information was not in the data, and inventing it was the one thing
that task forbade.

`RunStatus.terminal_detail` is the row's cheaper option, taken under `R-29`. This module
holds three separate claims about it, and the third is the one that decides whether the
property is safe to have at all:

1. **it carries the true sentence.** In ``recorded`` mode a document with no recording
   terminates ``analysis_input_invalid`` with ``reason: "recording_missing"``, which is
   *your document is fine, the provider is fine, this deployment has no recording for it*.
   `R-30` put the alpha stand in ``recorded`` mode, so that is the ordinary case now;
2. **it follows the reason and never leads it.** A detail from a stage whose code is not
   the code the run reports would read as an explanation of something else, which is worse
   than no detail;
3. **it is restricted to the reported code's own ``safe_detail_keys``, at three points in
   three different eras** -- when the terminal is chosen, when the row is written, and when
   a reader asks. Only the third covers a row this code did not write. An unrestricted
   detail object is how internals leak into a client, and the restriction is the point of
   the property rather than decoration.

The screen is :func:`auditmanager.shared.errors.screen_details`, which is the **same
function** the error envelope uses. The cases below prove it is actually called at each of
the three points, because "the same screen" is a claim about calls and not about intent.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.analysis.text import ProviderMode
from auditmanager.analysis.text.config import DEPENDENCY_NAME
from auditmanager.analysis.text.recorded import RecordedAdapter
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.findings.terminal import TerminalSelection, select_terminal
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode, UnsafeDetailKey
from auditmanager.shared.identity import IdempotencyKey

#: ``analysis_input_invalid``'s declared safe keys, written out rather than read from the
#: catalog. ``OPERATING_CONSTRAINTS.md`` §12: a test that derived its expectation from the
#: catalog would move both sides together and could not see the catalog being wrong.
RECORDING_MISS_KEYS = {"stage_id", "reason"}

#: ``dependency_unavailable``'s, likewise. One key, and it is the stable dependency class
#: name -- `W25-SEAL` §277: "never a host".
TRANSPORT_KEYS = {"dependency"}


def _start(session, seeded, tag: str) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w42-detail-{tag}-{uuid.uuid4()}"),
    )
    return str(started.run_id)


def _drive(session, seeded, blob_store, adapter, provider_config, tag: str) -> str:
    run_id = _start(session, seeded, tag)
    try:
        execute_run(
            session,
            run_id,
            blob_store=blob_store,
            adapter=adapter,
            provider_config=provider_config,
            sleep=lambda _seconds: None,
        )
    except DomainError:
        pass
    return run_id


def _row(session, run_id: str) -> dict:
    return dict(
        session.execute(
            text(
                "SELECT state, terminal_reason, terminal_detail "
                "FROM audit_run WHERE run_id = :r"
            ),
            {"r": run_id},
        )
        .mappings()
        .one()
    )


class _NeverReachable:
    """A provider that is unreachable for good, raising exactly as ``live.py`` maps it.

    Copied in shape from ``test_terminal_reason_names_the_cause.py``, which already proves
    this fixture really produces the transport case; what is new here is what travels
    *with* the code.
    """

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request):
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model provider did not return a usable response",
            dependency=DEPENDENCY_NAME,
        )


@pytest.fixture()
def empty_corpus_adapter(tmp_path):
    """A ``recorded`` adapter over a directory with nothing in it.

    This is `R-30`'s ordinary case, driven rather than described: the stand replays real
    recorded responses and a document with no recording says so. The adapter is the
    **shipped** one, not a stub -- a stub raising the right code would prove that the stub
    raises the right code.
    """
    return RecordedAdapter(tmp_path / "no-recordings-here")


# =======================================================================================
# 1. The true sentence, end to end.
# =======================================================================================


def test_a_document_with_no_recording_says_so_on_the_run(
    session, seeded, blob_store, provider_config, empty_corpus_adapter
) -> None:
    """`D-46`'s whole purpose, asserted on the row an operator reads.

    Before this property the run said ``analysis_input_invalid`` and stopped. A reader
    could not tell a corrupt fixture from an absent one, and `W29-SAY` could not write the
    sentence it had measured as true.
    """
    run_id = _drive(
        session, seeded, blob_store, empty_corpus_adapter, provider_config, "recording"
    )
    row = _row(session, run_id)
    assert row["state"] == "failed", row
    assert row["terminal_reason"] == "analysis_input_invalid", row
    assert row["terminal_detail"] is not None, (
        "the run reports a code and no detail, which is exactly `D-46`: it can say "
        "something went wrong with the input and not WHICH input"
    )
    assert row["terminal_detail"]["reason"] == "recording_missing", row
    assert row["terminal_detail"]["stage_id"] == "text_analysis", row
    assert set(row["terminal_detail"]) <= RECORDING_MISS_KEYS, row


def test_an_unreachable_provider_names_the_dependency_class_and_not_a_host(
    session, seeded, blob_store, provider_config
) -> None:
    """The other code that carries a detail, and the rule `W25-SEAL` wrote down for it.

    ``dependency_unavailable`` declares exactly one safe key and it is the **stable
    dependency class name, never a host**. A detail that named where the provider lives
    would be the internal leak this property has to be incapable of.
    """
    run_id = _drive(
        session, seeded, blob_store, _NeverReachable(), provider_config, "transport"
    )
    row = _row(session, run_id)
    assert row["terminal_reason"] == "dependency_unavailable", row
    assert row["terminal_detail"] == {"dependency": DEPENDENCY_NAME}, row
    assert set(row["terminal_detail"]) <= TRANSPORT_KEYS, row
    value = row["terminal_detail"]["dependency"]
    for leak in ("://", "http", "127.0.0.1", "localhost", "/"):
        assert leak not in value, (value, leak)


def test_a_published_run_carries_no_detail_at_all(
    session, seeded, blob_store, recorded_adapter, provider_config
) -> None:
    """The control. Without it the property could be filled for everything.

    A detail on a run that did not fail would be an explanation of nothing, and it would
    also be unscreenable: there is no ``terminal_reason`` whose allowlist could bound it.
    """
    run_id = _drive(
        session, seeded, blob_store, recorded_adapter, provider_config, "clean"
    )
    row = _row(session, run_id)
    assert row["state"] == "published", row
    assert row["terminal_reason"] is None
    assert row["terminal_detail"] is None


# =======================================================================================
# 2. The detail follows the reason.
# =======================================================================================


class TestTheDetailNeverLeadsTheReason:
    def test_stages_that_disagree_carry_no_detail(self) -> None:
        """One answer cannot represent two causes, and a union would be a third.

        ``_reason_for`` already keeps the generic ``analysis_failed`` when the failing
        stages report different codes. The detail follows it: with no single reason there
        is no allowlist to screen against, and merging two stages' classifiers would
        produce a sentence neither of them said.
        """
        selection = select_terminal(
            {"a": "failed", "b": "failed"},
            required_stages=["a", "b"],
            stage_errors={"a": "dependency_unavailable", "b": "analysis_input_invalid"},
            stage_details={
                "a": {"dependency": DEPENDENCY_NAME},
                "b": {"stage_id": "text_analysis", "reason": "recording_missing"},
            },
        )
        assert selection.terminal_reason == "analysis_failed"
        assert selection.terminal_detail is None

    def test_two_stages_with_one_code_and_different_details_carry_none(self) -> None:
        """Agreement on the code is not agreement on the classifier."""
        selection = select_terminal(
            {"a": "failed", "b": "failed"},
            required_stages=["a", "b"],
            stage_errors={"a": "analysis_input_invalid", "b": "analysis_input_invalid"},
            stage_details={
                "a": {"stage_id": "text_analysis", "reason": "recording_missing"},
                "b": {"stage_id": "text_analysis", "reason": "recording_malformed"},
            },
        )
        assert selection.terminal_reason == "analysis_input_invalid"
        assert selection.terminal_detail is None

    def test_a_detail_from_a_stage_the_run_does_not_report_is_not_carried(self) -> None:
        """The specific way a detail could become an explanation of something else."""
        selection = select_terminal(
            {"a": "failed", "b": "skipped"},
            required_stages=["a", "b"],
            stage_errors={"a": "analysis_failed", "b": "dependency_unavailable"},
            stage_details={"b": {"dependency": DEPENDENCY_NAME}},
        )
        assert selection.terminal_reason == "analysis_failed"
        assert selection.terminal_detail is None


# =======================================================================================
# 3. The restriction, at all three points.
# =======================================================================================


class TestTheRestrictionIsTheProperty:
    """`R-29` says *restricted to the reported code's own ``safe_detail_keys``*.

    Each case below drives one of the three screens **individually**, because a property
    that is screened once is a property that stops being screened the day one caller
    changes.
    """

    def test_the_first_screen_refuses_at_the_point_of_decision(self) -> None:
        with pytest.raises(UnsafeDetailKey) as refused:
            TerminalSelection(
                state="failed",
                degradation_set=("text_analysis",),
                terminal_reason="dependency_unavailable",
                # `stage_id` is safe for `analysis_input_invalid` and NOT for this code.
                # A key that is legal somewhere is the interesting case: a screen that
                # compared against the union of every code's keys would let it through.
                terminal_detail={"stage_id": "text_analysis"},
            )
        assert "dependency_unavailable declares safe_detail_keys" in str(refused.value)

    def test_a_detail_with_no_reason_is_refused_at_the_point_of_decision(self) -> None:
        """It is unscreenable, by anything, now or later."""
        with pytest.raises(ValueError) as refused:
            TerminalSelection(
                state="partial",
                degradation_set=("text_analysis",),
                terminal_detail={"dependency": DEPENDENCY_NAME},
            )
        assert "cannot be screened" in str(refused.value)

    def test_the_second_screen_refuses_on_the_way_into_the_row(
        self, session, seeded, blob_store, provider_config
    ) -> None:
        """The repository screens against the reason it is writing in the same statement."""
        from auditmanager.runs import RunRepository

        run_id = _start(session, seeded, "screen-2")
        repository = RunRepository()
        repository.advance(session, run_id=run_id, from_state="created", to_state="queued")
        repository.advance(session, run_id=run_id, from_state="queued", to_state="running")
        repository.advance(
            session, run_id=run_id, from_state="running", to_state="validating"
        )
        with pytest.raises(UnsafeDetailKey):
            repository.terminate(
                session,
                run_id=run_id,
                from_state="validating",
                to_state="failed",
                degradation_set=("text_analysis",),
                terminal_reason="dependency_unavailable",
                terminal_detail={"prompt": "the whole prompt, as it happens"},
            )
        session.rollback()

    def test_the_third_screen_refuses_a_row_this_code_did_not_write(self) -> None:
        """The only screen that covers a row written by an older process or by hand.

        This is not a hypothetical: the column is ``jsonb`` and the database's CHECK bounds
        its *shape*, not its keys -- deliberately, because encoding the frozen catalog's
        twenty-two key lists into a migration is how they drift. So the edge is where a
        row that got past the other two is stopped.
        """
        view = RunStatusView(
            run_id="run_01M2545JSD15ETSNNV904X991K",
            project_uid="prj_01M2545JSD15ETSNNV904X991F",
            version_uid="ver_01M2545JSD15ETSNNV904X991J",
            state="failed",
            provider_mode="recorded",
            created_at=__import__("datetime").datetime(
                2026, 9, 23, tzinfo=__import__("datetime").timezone.utc
            ),
            terminal_reason="dependency_unavailable",
            terminal_detail={"dependency": DEPENDENCY_NAME, "prompt": "leaked"},
        )
        with pytest.raises(UnsafeDetailKey):
            run_status_body(view)

    def test_the_third_screen_publishes_what_the_code_does_declare(self) -> None:
        """The other half: a screen that refused everything would also pass the case above."""
        view = RunStatusView(
            run_id="run_01M2545JSD15ETSNNV904X991K",
            project_uid="prj_01M2545JSD15ETSNNV904X991F",
            version_uid="ver_01M2545JSD15ETSNNV904X991J",
            state="failed",
            provider_mode="recorded",
            created_at=__import__("datetime").datetime(
                2026, 9, 23, tzinfo=__import__("datetime").timezone.utc
            ),
            terminal_reason="analysis_input_invalid",
            terminal_detail={"stage_id": "text_analysis", "reason": "recording_missing"},
        )
        body = run_status_body(view)
        assert body["terminal_detail"] == {
            "stage_id": "text_analysis",
            "reason": "recording_missing",
        }

    def test_a_detail_with_no_reason_is_not_published(self) -> None:
        """Belt to the database's own CHECK, at the layer a client reads."""
        view = RunStatusView(
            run_id="run_01M2545JSD15ETSNNV904X991K",
            project_uid="prj_01M2545JSD15ETSNNV904X991F",
            version_uid="ver_01M2545JSD15ETSNNV904X991J",
            state="partial",
            provider_mode="recorded",
            created_at=__import__("datetime").datetime(
                2026, 9, 23, tzinfo=__import__("datetime").timezone.utc
            ),
            terminal_detail={"dependency": DEPENDENCY_NAME},
        )
        assert "terminal_detail" not in run_status_body(view)


class TestTheDatabaseHoldsTheCouplingItself:
    """``0010``'s two CHECKs, as the lane's live schema enforces them.

    **These two cases cannot redden for a change to the migration, and that is recorded
    rather than hidden.** This suite connects to the already-migrated lane database, so
    weakening a constraint in ``0010``'s source changes nothing it can see -- measured:
    ``CHECK (true)`` in a whole-worktree copy left this file at 14 passed.
    ``OPERATING_CONSTRAINTS.md`` §10.1 names the first half of that trap and not the
    second: a whole-worktree copy is still not enough unless the suite **re-migrates**.

    They are kept because what they assert is true and worth asserting -- the schema this
    lane actually runs against refuses both -- and the migration-sensitive version lives
    in ``tests/integration/db/test_run_terminal_detail_schema.py``, over the
    ``migrated_engine`` fixture, which applies the head to a throwaway database through the
    literal command and therefore does redden.

    The key allowlist is deliberately **not** in the database: it belongs to the frozen
    catalog and encoding it in a migration is how it drifts. What is structural is that a
    detail must be a flat object and cannot exist without a reason to screen it against.
    """

    def test_a_detail_with_no_reason_is_refused_by_the_table(
        self, session, seeded, blob_store, recorded_adapter, provider_config
    ) -> None:
        run_id = _drive(
            session, seeded, blob_store, recorded_adapter, provider_config, "check-1"
        )
        assert _row(session, run_id)["terminal_reason"] is None
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                    "WHERE run_id = :r"
                ),
                {"d": json.dumps({"dependency": DEPENDENCY_NAME}), "r": run_id},
            )
        session.rollback()

    def test_a_detail_that_is_not_an_object_is_refused_by_the_table(
        self, session, seeded, blob_store, provider_config
    ) -> None:
        run_id = _drive(
            session, seeded, blob_store, _NeverReachable(), provider_config, "check-2"
        )
        assert _row(session, run_id)["terminal_reason"] is not None
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                    "WHERE run_id = :r"
                ),
                {"d": json.dumps(["dependency", DEPENDENCY_NAME]), "r": run_id},
            )
        session.rollback()
