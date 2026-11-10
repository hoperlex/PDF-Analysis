"""Passes with proposals that carry every decision history the table can hold, written by plain SQL with every trigger on.

Shared by the suites that prove a read of the optimisation tables equal to a replay of the histories
(``tests/integration/dashboard/test_document_audit_optimisation_counts.py``, `D-463`;
``tests/integration/optimisation/proposals/test_decision_counts_one_pass.py``, `D-574`). A price list and a vendor list are the
scaffolding the pass's scope trigger asks for. The caller holds a session on a fresh clone of the migrated template.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session

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
from tests.integration.documents.seeding import Seeder

__all__ = ["HISTORIES", "Scaffold", "expected_counts", "expected_undecided"]

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


def expected_undecided(histories: tuple[tuple[str, ...], ...]) -> int:
    """The oracle: the latest decision decides; no decision and ``revoke`` are undecided."""
    return sum(1 for history in histories if not history or history[-1] == "revoke")


def expected_counts(histories: tuple[tuple[str, ...], ...]) -> dict[str, int]:
    """The oracle of a pass's ``decision_counts``: the latest decision decides, ``revoke`` and no decision are ``pending``.

    Only the states somebody holds are keys, as the statement answers; the repository reader fills the rest with zero.
    """
    counted: dict[str, int] = {}
    for history in histories:
        state = "pending" if not history or history[-1] == "revoke" else history[-1]
        counted[state] = counted.get(state, 0) + 1
    return counted
