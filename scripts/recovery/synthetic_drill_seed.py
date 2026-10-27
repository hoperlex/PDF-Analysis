"""Opt-in operator CLI: fill a disposable SOURCE lane with a realistic dataset for a W58 drill.

`RECOVERY-REBASE-01`. The first real W58 drill restored a hand-written SQL seed: one Blob, one
version, one manifest entry. A restore drill that has never met a classification correction, a
finished run, a decision ledger, a price list or an optimisation pass proves little about the
schema it will be asked to restore. This module builds that dataset **through the owning
contexts' public surfaces** (``ingest``, ``sections``, ``runs``, ``decisions``,
``optimisation``) in recorded provider mode, so every row and every object is one the product
itself would have written: several projects, versions of one document, an expert's
classification and its correction, a published run with findings and expert decisions, price
and vendor lists, an optimisation pass with decisions, and the Blobs they bind.

It creates no database and no bucket and spends nothing: provider-selecting environment names
are removed before anything is imported, the run uses the checked-in recording, and the
endpoints must be loopback. It refuses a lane that already holds a project, because most of
what it writes can never be deleted (the tables are immutable by design).

One honest limit: the optimisation pass reads the run's saved text through the context's own
``SavedTextReader`` port. The AR baseline has no specification page, so the port is answered
with the same one-page Form-7 specification the optimisation suite uses, keyed to the real
published run. Everything the pass writes is real; the text it matched is a fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

for _name in ("AUDITMANAGER_PROVIDER_MODE", "AUDITMANAGER_MODEL_ID", "AUDITMANAGER_RUN_COST_CEILING_USD",
              "ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL"):
    os.environ.pop(_name, None)  # a drill seed must never be able to spend money

from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from auditmanager.access.public import AccountRepository, UserRepository  # noqa: E402
from auditmanager.analysis.text import (  # noqa: E402
    AR_TEXT_PROMPT_BUNDLE,
    CATEGORIES,
    STAGE_ID,
    AnalysisProfile,
    ProviderConfig,
    ProviderMode,
    RecordedAdapter,
)
from auditmanager.analysis.text.profile import ANALYSIS_PROFILE_ID  # noqa: E402
from auditmanager.decisions import record_decision  # noqa: E402
from auditmanager.dispatch.public import assign_work, transition_assignment  # noqa: E402
from auditmanager.findings import published_findings  # noqa: E402
from auditmanager.ingest import IngestService  # noqa: E402
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText  # noqa: E402
from auditmanager.optimisation.proposals.public import (  # noqa: E402
    decide_optimisation_proposal,
    list_optimisation_proposals,
    start_optimisation_pass,
)
from auditmanager.optimisation.public import (  # noqa: E402
    PriceListUploads,
    set_global_vendor_list,
    set_project_vendor_list,
)
from auditmanager.runs import execute_run, start_audit_run  # noqa: E402
from auditmanager.sections.public import (  # noqa: E402
    ORIGINAL_REVISION,
    classify_document_version,
    correct_document_version_classification,
)
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url  # noqa: E402
from auditmanager.shared.db.engine import create_database_engine  # noqa: E402
from auditmanager.shared.db.session import create_session_factory, session_scope  # noqa: E402
from auditmanager.shared.identity import IdempotencyKey  # noqa: E402
from auditmanager.storage import S3BlobStore, S3StorageSettings  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_CORPUS = _REPO / "fixtures" / "synthetic" / "ar"
_BUNDLES = _CORPUS / "bundles"
_RECORDINGS = _REPO / "fixtures" / "recorded" / "text_analysis"

#: `PROD-11-AR-V1-V2-REMOVAL-01`. АР is no longer a text profile of the product, so no served path
#: can start or execute a v1 АР run. The drill still wants a dataset shaped like the beta's data,
#: which holds finished v1 runs with findings and decisions, so the seed executes one under the
#: retired v1 profile, built here from the constants ``analysis.text`` keeps (the same objects the
#: removed ``AR_TEXT_PROFILE`` was made of) and passed to the executor explicitly.
_HISTORICAL_V1 = AnalysisProfile(
    analysis_profile_id=ANALYSIS_PROFILE_ID, profile_version="1.0.0", stage_id=STAGE_ID,
    discipline="AR", categories=CATEGORIES, prompt_bundle=AR_TEXT_PROMPT_BUNDLE,
)


def _resolve_historical_v1(analysis_profile_id: str, prompt_bundle_id: str) -> AnalysisProfile:
    if (str(analysis_profile_id), str(prompt_bundle_id)) != (
        str(_HISTORICAL_V1.analysis_profile_id), str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
    ):
        raise LookupError("the seed executes the historical v1 pair only")
    return _HISTORICAL_V1


_NAMES = frozenset({
    "FOUNDATION_INSTANCE", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT",
    "DATABASE_URL", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "S3_ENDPOINT_URL", "S3_API_PORT",
    "S3_CONSOLE_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
})
_PASSWORD = "a-long-enough-password"  # noqa: S105 - a synthetic lane's literal

_FORM7_PAGE = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5\n"
    "2 Окно ПВХ двухкамерное ОП В2 1460х1460 шт. 12\n"
    "3 Анкер химический HIT-HY 200 шт. 200\n"
    "4 Профиль направляющий ПН 50х40 п. м 120\n"
    "5 Пена монтажная шт. 3\n"
    "6 Монтажная лента компл. - по месту\n"
)
_PRICE_LIST = (
    "Код;Наименование;Марка;Ед. изм.;Цена;Валюта;Поставщик\n"
    ";Дверь противопожарная;ДПМ-01/60;шт;25000;RUB;ООО «Промет»\n"
    ";Дверь противопожарная;ДПМ-02/60;шт;21000;RUB;Кнауф Гипс\n"
    ";Дверь противопожарная металлическая;;шт;19500;RUB;Неизвестный завод\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460;;шт;18500,5;RUB;Промет\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460 эконом;;шт;16000;RUB;Кнауф Гипс\n"
    ";Анкер химический;HIT-HY 200;шт;12,75;EUR;Промет\n"
    ";Профиль направляющий ПН 50х40;;м;95;RUB;Промет\n"
    ";Профиль направляющий ПН 50х40 эконом;;м;60;RUB;Кнауф Гипс\n"
    ";Пена монтажная;;шт;700;RUB;Промет\n"
    ";Пена монтажная бытовая;;шт;300;RUB;Кнауф Гипс\n"
    ";Монтажная лента;;компл;450;RUB;Промет\n"
    ";Монтажная лента армированная;;компл;300;RUB;Кнауф Гипс\n"
).encode("utf-8")
_NEWER_PRICE_LIST = _PRICE_LIST.replace(b";21000;", b";20000;")
_VENDORS = ({"vendor": "Кнауф Гипс"}, {"vendor": "Промет"})


class SeedRefused(ValueError):
    """The lane is not a fresh, loopback, disposable source or a seeding step refused."""


class _Reader:
    """The optimisation context's runs-and-text port, answered for one published run."""

    def __init__(self, run_id: str, version_uid: str) -> None:
        self._run, self._version = run_id, version_uid
        self._layer = hashlib.sha256(_FORM7_PAGE.encode("utf-8")).hexdigest()

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        return (RunCandidate(self._run, "published"),) if version_uid == self._version else ()

    def saved_page_text(self, session: Session, *, run_id: str, version_uid: str,
                        page_count: int) -> SavedPageText | None:
        if run_id != self._run:
            return None
        pages = {number: "Общие данные" for number in range(1, page_count + 1)}
        pages[1] = _FORM7_PAGE
        return SavedPageText(run_id, self._layer, pages)


def load_env(path: Path) -> dict[str, str]:
    """The lane's ``.env`` as data (never sourced); loopback endpoints only."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name not in _NAMES or name in values:
            raise SeedRefused("lane .env has an unknown or repeated assignment")
        values[name] = value
    if set(values) != _NAMES:
        raise SeedRefused("lane .env lacks a frozen foundation setting")
    url = parse_database_url(values["DATABASE_URL"])
    if url.host != "127.0.0.1" or not values["S3_ENDPOINT_URL"].startswith("http://127.0.0.1:"):
        raise SeedRefused("seeding is allowed only against loopback services")
    return values


def seed_source_lane(values: Mapping[str, str]) -> dict[str, Any]:
    """Write the dataset and return what it created (identities, never secrets)."""
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(values["DATABASE_URL"])))
    factory = create_session_factory(engine)
    store = S3BlobStore(S3StorageSettings(
        endpoint_url=values["S3_ENDPOINT_URL"], region=values["S3_REGION"],
        access_key_id=values["S3_ACCESS_KEY_ID"], secret_access_key=values["S3_SECRET_ACCESS_KEY"],
        bucket=values["S3_BUCKET"],
    ))
    store.check_access()
    users, accounts = UserRepository(), AccountRepository()
    ingest = IngestService(store, session_factory=factory)
    summary: dict[str, Any] = {}

    def unit(call: Any, /, **arguments: Any) -> Any:
        with session_scope(factory) as session:
            if "actor_uid" in arguments and "actor_roles" not in arguments:
                arguments["actor_roles"] = accounts.roles_of(session, arguments["actor_uid"])
            return call(session, **arguments)

    with Session(engine) as session:
        if session.execute(text("SELECT count(*) FROM project")).scalar_one():
            raise SeedRefused("the lane already holds a project; seed a fresh source")

    people: dict[str, str] = {}
    with session_scope(factory) as session:
        for label, email, roles in (
            ("admin", "admin.drill@example.com", ("admin",)),
            ("expert", "anna.drill@example.com", ("expert",)),
            ("second_expert", "boris.drill@example.com", ("expert",)),
        ):
            uid = str(users.create_user(session, email, _PASSWORD).user_uid)
            accounts.complete_profile(session, user_uid=uid, email=None,
                                      last_name="Петрова", first_name="Анна")
            for role in roles:
                accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
            people[label] = uid
    summary["accounts"] = len(people)

    def key(label: str) -> IdempotencyKey:
        return IdempotencyKey(f"drill-seed-{label}")

    # --- projects, documents, versions: portal bundles are the product's upload ------------
    school = ingest.create_project(name="Школа на 550 мест")
    kindergarten = ingest.create_project(name="Детский сад")
    warehouse = ingest.create_project(name="Склад (31 страница)")
    ingest.create_project(name="Пустой проект")
    first = ingest.upload_bundle(
        project_uid=school.project_uid, content=(_BUNDLES / "ar_baseline_minimal.zip").read_bytes(),
        source_filename="ar_baseline_minimal.zip", display_title="АР, раздел 1",
        idempotency_key=key("v1"))
    second = ingest.upload_bundle(
        project_uid=school.project_uid, content=(_BUNDLES / "ar_baseline.zip").read_bytes(),
        source_filename="ar_baseline.zip", display_title=None,
        idempotency_key=key("v2"), document_uid=first.version.document_uid)
    other = ingest.upload_bundle(
        project_uid=kindergarten.project_uid,
        content=(_BUNDLES / "ar_baseline_ocr_defects.zip").read_bytes(),
        source_filename="ar_baseline_ocr_defects.zip", display_title="АР с дефектами распознавания",
        idempotency_key=key("ocr"))
    large = ingest.upload_bundle(
        project_uid=warehouse.project_uid, content=(_BUNDLES / "pages_31.zip").read_bytes(),
        source_filename="pages_31.zip", display_title="АР, 31 страница", idempotency_key=key("p31"))
    project, document = str(school.project_uid), str(first.version.document_uid)
    version_1, version_2 = str(first.version.version_uid), str(second.version.version_uid)
    summary["versions"] = 4
    expert = people["expert"]

    # --- an expert's classification and its correction (append-only, revision 2) -----------
    # Version 1 is classified as a design-stage document and corrected to working
    # documentation; version 2 (the document's current one, the recorded run's and the
    # optimisation pass's subject) is classified once.
    unit(classify_document_version, project_uid=project, document_uid=document,
         version_uid=version_1, project_stage="P", section_code="AR", actor_uid=expert)
    unit(correct_document_version_classification, project_uid=project, document_uid=document,
         version_uid=version_1, project_stage="R", section_code="AR",
         reason="Стадия указана неверно: документ рабочей документации",
         expected_revision=ORIGINAL_REVISION, actor_uid=expert)
    unit(classify_document_version, project_uid=project, document_uid=document,
         version_uid=version_2, project_stage="R", section_code="AR", actor_uid=expert)
    unit(classify_document_version, project_uid=str(kindergarten.project_uid),
         document_uid=str(other.version.document_uid), version_uid=str(other.version.version_uid),
         project_stage="R", section_code="AR", actor_uid=people["second_expert"])

    # --- a finished recorded run with findings and expert decisions ------------------------
    config = ProviderConfig(mode=ProviderMode.RECORDED, model_id="claude-opus-5",
                            run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=False)
    with Session(engine) as session:
        started = start_audit_run(
            session, version_uid=version_2, analysis_profile_id=str(_HISTORICAL_V1.analysis_profile_id),
            prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id), provider_mode="recorded",
            idempotency_key=key("run"))
        session.commit()
        execute_run(session, started.run_id, blob_store=store, adapter=RecordedAdapter(_RECORDINGS),
                    provider_config=config, text_profiles=_resolve_historical_v1)
        session.commit()
        run_id = str(started.run_id)
        state = session.execute(text("SELECT state FROM audit_run WHERE run_id = :r"),
                                {"r": run_id}).scalar_one()
        findings = published_findings(session, run_id)
        if state != "published" or len(findings) < 2:
            raise SeedRefused(f"the recorded run did not publish findings (state {state})")
        for finding, event, comment in (
            (findings[0], "accept", "подтверждено по странице"),
            (findings[1], "reject", "другой объект"),
            (findings[0], "comment", "проверено повторно"),
        ):
            record_decision(session, finding_uid=str(finding.finding_uid),
                            finding_observation_id=str(finding.finding_observation_id),
                            event_type=event, comment=comment, author_label="Петрова А.",
                            author_user_uid=expert)
        session.commit()
    summary.update(run_id=run_id, run_state=state, findings=len(findings), decisions=3)

    # --- work assignments: an administrator hands work to experts; events are the history ---
    mine = unit(assign_work, project_uid=project, document_uid=document,
                assignee_user_uid=expert, note="Проверить раздел АР", actor_uid=people["admin"])
    unit(transition_assignment, assignment_uid=str(mine.assignment_uid), kind="started",
         actor_uid=expert)
    theirs = unit(assign_work, project_uid=str(kindergarten.project_uid), document_uid=None,
                  assignee_user_uid=people["second_expert"], note=None, actor_uid=people["admin"])
    for kind in ("started", "completed"):
        unit(transition_assignment, assignment_uid=str(theirs.assignment_uid), kind=kind,
             actor_uid=people["second_expert"])
    summary["work_assignments"] = 2

    # --- price lists, vendor lists, an optimisation pass and decisions on its proposals ------
    uploads = PriceListUploads(store, session_factory=factory)
    for label, content in (("prices-1", _PRICE_LIST), ("prices-2", _NEWER_PRICE_LIST)):
        uploads.upload(project_uid=project, content=content, source_filename=f"{label}.csv",
                       idempotency_key=label, actor_uid=expert)
    unit(set_global_vendor_list, section_code="AR", entries=list(_VENDORS), actor_uid=people["admin"])
    unit(set_project_vendor_list, project_uid=project, section_code="AR", mode="list",
         entries=list(_VENDORS[:1]), actor_uid=expert)
    started_pass = unit(start_optimisation_pass, project_uid=project, document_uid=document,
                        idempotency_key="pass-1", actor_uid=expert,
                        reader=_Reader(run_id, version_2)).optimisation_pass
    page = unit(list_optimisation_proposals,
                optimisation_pass_id=started_pass.optimisation_pass_id,
                actor_roles=frozenset({"expert"}))
    proposals = [item.optimisation_proposal_id for item in page.items]
    if len(proposals) < 2:
        raise SeedRefused("the optimisation pass produced fewer than two proposals")
    for index, (verdict, comment) in enumerate((("accept", None), ("revise", "уточнить марку"))):
        unit(decide_optimisation_proposal, proposal_id=proposals[index], verdict=verdict,
             comment=comment, idempotency_key=f"decision-{index}", actor_uid=expert)
    summary.update(price_lists=2, optimisation_proposals=len(proposals), optimisation_decisions=2)
    engine.dispose()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, required=True, help="the SOURCE lane's .env")
    args = parser.parse_args(argv)
    try:
        summary = seed_source_lane(load_env(args.env))
    except SeedRefused as exc:
        parser.exit(3, f"REFUSED: {exc}\n")
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
