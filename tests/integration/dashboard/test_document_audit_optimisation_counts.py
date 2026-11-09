"""`D-463`: the optimisation counts of a document's audit equal what replaying every proposal's decision history says.

``DocumentAuditReadModel.audits`` reads, for each listed version, the proposals of its latest optimisation pass and how many of
them have no decision in force (none, or a withdrawn one). The first statement looked up the latest decision of every proposal of
the pass, one index probe each; measured on a stand (200 documents x ~530 proposals) that was ~0.8 s of a 1.3 s page. The statement
now aggregates the decisions of the pass's proposals once. This suite is the proof the answer did not move: passes whose
proposals carry every shape of history the table can hold (none, one verdict, withdrawn, withdrawn and decided again, a change of
mind, a lone withdrawal that the command would refuse but the table permits), read two ways --

* by an oracle that replays each history in Python (the latest decision decides; ``revoke`` and no decision are undecided), and
* by the statement the module used to run, kept here as the reference (a LATERAL "latest decision" per proposal).

Rows are written by plain SQL with every trigger on; a price list and a vendor list are the scaffolding the pass's scope trigger
asks for. The database is a fresh clone of the migrated template.
"""

from __future__ import annotations

import hashlib
import importlib
import random
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, bindparam, text
from sqlalchemy.orm import Session

from auditmanager.dashboard import DocumentAuditReadModel
from auditmanager.shared.identity import (
    AnalysisProfileId,
    BlobId,
    CommandId,
    OptimisationPassId,
    PriceListId,
    PromptBundleId,
    RunId,
    VendorListId,
)
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import Seeder

model = DocumentAuditReadModel()
module = importlib.import_module("auditmanager.dashboard.audit_state")

#: The decision history of one proposal, oldest first. Each shape the table can hold, and the answer it must give.
HISTORIES: tuple[tuple[tuple[str, ...], bool], ...] = (
    ((), True),  # never decided
    (("accept",), False),
    (("reject",), False),
    (("revise",), False),
    (("accept", "revoke"), True),  # withdrawn
    (("accept", "revoke", "accept"), False),  # withdrawn and decided again
    (("accept", "revoke", "revise"), False),
    (("reject", "revise"), False),  # a change of mind
    (("accept", "revoke", "accept", "revoke"), True),
    (("revoke",), True),  # the command refuses a withdrawal with nothing to withdraw; the table does not
    (("revise", "accept", "reject"), False),
)

#: The statement this module ran before `D-463`: the latest decision of every proposal by one index probe each.
_PER_PROPOSAL_REFERENCE = text(
    """
    WITH latest_pass AS (
        SELECT DISTINCT ON (p.version_uid) p.version_uid, p.optimisation_pass_id, p.proposal_count
        FROM optimisation_pass p
        WHERE p.version_uid IN :version_uids
        ORDER BY p.version_uid, p.started_at DESC, p.optimisation_pass_id DESC
    )
    SELECT lp.version_uid, lp.proposal_count,
           (SELECT count(*)
              FROM optimisation_proposal q
              LEFT JOIN LATERAL (
                  SELECT d.verdict FROM optimisation_proposal_decision d
                  WHERE d.optimisation_proposal_id = q.optimisation_proposal_id
                  ORDER BY d.seq DESC LIMIT 1
              ) cur ON TRUE
             WHERE q.optimisation_pass_id = lp.optimisation_pass_id
               AND (cur.verdict IS NULL OR cur.verdict = 'revoke'))
    FROM latest_pass lp
    """
).bindparams(bindparam("version_uids", expanding=True))


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


class Scaffold:
    """What a pass needs around it: an expert, a price list of two positions, a global AR vendor list and runs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.seed = Seeder(session)
        self.expert = self.seed.expert
        self._serial = 0
        self.prices: dict[str, tuple[str, str]] = {}
        blob = str(BlobId.new())
        session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
        session.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob})
        session.execute(
            text("UPDATE blob SET state = 'available', sha256 = :s, size_bytes = 10, media_type = 'text/csv' WHERE blob_id = :b"),
            {"b": blob, "s": _digest("price list")},
        )
        self.blob = blob
        self.vendor_list = str(VendorListId.new())
        session.execute(
            text(
                "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, mode, revision_number, "
                "entry_count, set_by_user_uid) VALUES (:v, 'global', NULL, 'AR', 'list', 1, 1, :u)"
            ),
            {"v": self.vendor_list, "u": self.expert},
        )
        session.execute(
            text("INSERT INTO vendor_list_entry (vendor_list_id, ordinal, vendor) VALUES (:v, 1, 'Поставщик')"),
            {"v": self.vendor_list},
        )

    def price_list(self, project: str) -> tuple[str, str, str]:
        """A revision of two positions for ``project``: (revision, the matched position, the cheaper one)."""
        revision, matched, proposed = str(PriceListId.new()), "prp_" + "0" * 25 + "A", "prp_" + "0" * 25 + "B"
        matched, proposed = (f"prp_{_digest(revision + s)[:26].upper()}" for s in ("m", "p"))
        self.session.execute(
            text(
                "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, uploaded_by_user_uid, blob_id, "
                "sha256, size_bytes, media_type, source_format, source_filename, default_currency, parse_report, "
                "data_row_count, accepted_row_count, skipped_row_count) VALUES (:p, :pr, 1, :u, :b, :s, 10, 'text/csv', 'csv', "
                "'perf.csv', 'RUB', '{}'::jsonb, 2, 2, 0)"
            ),
            {"p": revision, "pr": project, "u": self.expert, "b": self.blob, "s": _digest("price list")},
        )
        for position, row, price in ((matched, 1, 100), (proposed, 2, 50)):
            self.session.execute(
                text(
                    "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, name, unit, unit_price, "
                    "currency, vendor, section_code) VALUES (:i, :p, :r, 'Материал', 'шт', :price, 'RUB', 'Поставщик', 'AR')"
                ),
                {"i": position, "p": revision, "r": row, "price": price},
            )
        return revision, matched, proposed

    def run(self, project: str, version: str) -> str:
        run_id = str(RunId.new())
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, "
                "provider_mode, frozen_input_digest) VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
            ),
            {"r": run_id, "p": project, "v": version, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()),
             "s": _digest(run_id)},
        )
        return run_id

    def pass_(
        self, project: str, document: str, version: str, run_id: str, histories: tuple[tuple[str, ...], ...], *,
        started: str, generator: str,
    ) -> str:
        """One pass over ``version`` holding one proposal per history, each with its decisions in order."""
        revision, matched, proposed = self.price_list_of(project)
        pass_id = str(OptimisationPassId.new())
        n = len(histories)
        self.session.execute(
            text(
                "INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, version_uid, run_id, text_layer_sha256, "
                "price_list_id, vendor_list_id, vendor_list_source, extraction_algorithm, match_algorithm, generator_version, "
                "specification_row_count, matched_row_count, proposed_row_count, proposal_count, started_by_user_uid, started_at) "
                "VALUES (:pass, :p, :d, :v, :r, :sha, :pl, :vl, 'global', 'ext-1', 'match-1', :g, :n, :n, :n, :n, :u, "
                "CAST(:t AS timestamptz))"
            ),
            {"pass": pass_id, "p": project, "d": document, "v": version, "r": run_id, "sha": _digest(pass_id), "pl": revision,
             "vl": self.vendor_list, "g": generator, "n": n, "u": self.expert, "t": started},
        )
        for ordinal, history in enumerate(histories, start=1):
            self._serial += 1
            proposal = f"opr_{_digest(f'proposal-{self._serial}')[:26].upper()}"
            self.session.execute(
                text(
                    "INSERT INTO optimisation_proposal (optimisation_proposal_id, optimisation_pass_id, ordinal, proposal_type, "
                    "spec_row_key, page_number, line_start, line_end, table_ordinal, row_text, matched_position_id, matched_basis, "
                    "proposed_position_id, analog_basis, name_similarity, proposed_vendor, unit, quantity, quantity_text, "
                    "current_unit_price, proposed_unit_price, currency, saving, rationale) "
                    "VALUES (:i, :pass, :o, 'cheaper_analog', :key, 1, :o, :o, 1, 'Позиция', :m, 'name', :pr, 'name_similarity', "
                    "0.8, 'Поставщик', 'шт', 2, '2', 100, 50, 'RUB', 100, 'Аналог дешевле')"
                ),
                {"i": proposal, "pass": pass_id, "o": ordinal, "key": "sr-" + _digest(proposal)[:32], "m": matched, "pr": proposed},
            )
            for seq, verdict in enumerate(history, start=1):
                command = str(CommandId.new())
                self.session.execute(
                    text(
                        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                        "VALUES (:c, 'decide_optimisation_proposal', :k, :f)"
                    ),
                    {"c": command, "k": command, "f": _digest(command)},
                )
                self.session.execute(
                    text(
                        "INSERT INTO optimisation_proposal_decision (proposal_decision_id, optimisation_proposal_id, seq, verdict, "
                        "comment, actor_user_uid, command_id) VALUES (:d, :q, :s, :v, :c, :u, :cmd)"
                    ),
                    {"d": f"opd_{_digest(command)[:26].upper()}", "q": proposal, "s": seq, "v": verdict,
                     "c": "Уточнить" if verdict == "revise" else None, "u": self.expert, "cmd": command},
                )
        return pass_id

    def price_list_of(self, project: str) -> tuple[str, str, str]:
        if project not in self.prices:
            self.prices[project] = self.price_list(project)[0:3]
        return self.prices[project]  # type: ignore[return-value]


def _expected_undecided(histories: tuple[tuple[str, ...], ...]) -> int:
    """The oracle: the latest decision decides; no decision and ``revoke`` are undecided."""
    return sum(1 for history in histories if not history or history[-1] == "revoke")


def test_every_history_shape_is_what_the_table_can_hold_and_is_decided_or_not_as_ruled() -> None:
    """The oracle's own table: a guard that the set is not vacuous (both answers, withdrawn and re-decided shapes)."""
    assert {answer for _, answer in HISTORIES} == {True, False}
    for history, undecided in HISTORIES:
        assert _expected_undecided((history,)) == int(undecided), history
    assert any("revoke" in h and h[-1] != "revoke" for h, _ in HISTORIES), "a withdrawn-then-decided history is covered"


def test_the_counts_of_the_latest_pass_equal_the_replayed_histories_and_the_old_statement(session: Session) -> None:
    scaffold = Scaffold(session)
    seed = scaffold.seed
    project = seed.project("Проект с оптимизацией")
    rng = random.Random(463)

    versions: dict[str, tuple[str, ...]] = {}  # version -> expected histories of its latest pass
    expected: dict[str, tuple[int, int] | None] = {}

    def add_version(title: str, *, latest: tuple[tuple[str, ...], ...] | None, older: tuple[tuple[str, ...], ...] | None = None) -> str:
        document = seed.document(project, title)
        version = seed.version(document, classified=("R", "AR"))
        run = scaffold.run(project, version)
        if older is not None:
            scaffold.pass_(project, document, version, run, older, started="2026-11-01T10:00:00+00", generator="gen-1")
        if latest is not None:
            scaffold.pass_(project, document, version, run, latest, started="2026-11-02T10:00:00+00", generator="gen-2")
            expected[version] = (len(latest), _expected_undecided(latest))
        else:
            expected[version] = None
        return version

    every_shape = tuple(history for history, _ in HISTORIES)
    add_version("Все формы историй", latest=every_shape)
    add_version("Ничего не решено", latest=((), (), ()))
    add_version("Всё решено", latest=(("accept",), ("reject",), ("accept", "revoke", "revise")))
    add_version("Всё снято", latest=(("accept", "revoke"), ("revoke",)))
    add_version("Пустой проход", latest=())
    add_version("Прохода нет", latest=None)
    # an older pass that disagrees with the latest one: only the latest counts
    add_version("Старый проход иной", latest=(("accept",), ("accept",)), older=((), (), (), ()))
    for index in range(8):  # random mixes, a fixed seed
        mix = tuple(rng.choice(HISTORIES)[0] for _ in range(rng.randint(1, 40)))
        older = tuple(rng.choice(HISTORIES)[0] for _ in range(rng.randint(1, 10))) if index % 2 else None
        add_version(f"Случайный набор {index}", latest=mix, older=older)
    session.commit()

    names = list(expected)
    audits = model.audits(session, version_uids=names)
    assert set(audits) == set(names)
    wrong = []
    for version, pair in expected.items():
        record = audits[version]
        got = (record.optimisation_proposal_count, record.optimisation_undecided_count)
        if pair is None:
            if got != (None, None):
                wrong.append(f"{version}: no pass, read {got}")
        elif got != pair:
            wrong.append(f"{version}: expected {pair} (replayed), read {got}")
    assert not wrong, "\n".join(wrong)

    # and the statement it replaced says the same, version by version
    reference = {str(row[0]): (int(row[1]), int(row[2])) for row in session.execute(_PER_PROPOSAL_REFERENCE, {"version_uids": names})}
    assert reference == {version: pair for version, pair in expected.items() if pair is not None}
    for version, pair in reference.items():
        record = audits[version]
        assert (record.optimisation_proposal_count, record.optimisation_undecided_count) == pair


def test_the_counts_are_a_fact_beside_the_audit_state(session: Session) -> None:
    """`R-150u`: a pass moves none of the four words (a version with a pass and no run of findings is still ``clean`` or ``not_run``)."""
    scaffold = Scaffold(session)
    project = scaffold.seed.project("Проект")
    document = scaffold.seed.document(project, "АР")
    version = scaffold.seed.version(document, classified=("R", "AR"))
    run = scaffold.run(project, version)
    scaffold.pass_(project, document, version, run, ((), ("accept",)), started="2026-11-02T10:00:00+00", generator="gen-2")
    session.commit()
    record = model.audits(session, version_uids=[version])[version]
    assert (record.optimisation_proposal_count, record.optimisation_undecided_count) == (2, 1)
    assert (record.state, record.partial) == ("not_run", False)  # the run was never walked to a result


def test_the_comparison_can_fail(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """A guard needs a way to fail: the shipped statement with its one rule bent -- a withdrawal counted as a decision in force --
    answers differently from the replayed histories, so the comparison above is not satisfied by any statement that merely runs."""
    scaffold = Scaffold(session)
    project = scaffold.seed.project("Проект")
    document = scaffold.seed.document(project, "АР")
    version = scaffold.seed.version(document, classified=("R", "AR"))
    run = scaffold.run(project, version)
    histories = ((), ("accept",), ("accept", "revoke"), ("accept", "revoke", "accept"), ("revoke",))
    scaffold.pass_(project, document, version, run, histories, started="2026-11-02T10:00:00+00", generator="gen-2")
    session.commit()

    honest = model.audits(session, version_uids=[version])[version]
    assert (honest.optimisation_proposal_count, honest.optimisation_undecided_count) == (5, _expected_undecided(histories)) == (5, 3)

    original = str(module._DOCUMENT_AUDITS)
    assert "cur.verdict <> 'revoke'" in original
    bent = original.replace("cur.verdict <> 'revoke'", "cur.verdict IS NOT NULL")  # any decision, a withdrawal included, is "decided"
    monkeypatch.setattr(module, "_DOCUMENT_AUDITS", text(bent).bindparams(bindparam("version_uids", expanding=True)))
    wrong = model.audits(session, version_uids=[version])[version]
    assert wrong.optimisation_undecided_count == 1  # only the never-decided proposal: the two withdrawn ones are miscounted
    assert wrong.optimisation_undecided_count != honest.optimisation_undecided_count
