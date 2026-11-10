"""Fill a throwaway PostgreSQL (at migration head) with a realistic volume for the optimisation counts of ``listDocuments`` (``D-463``,
``D-572``, ``D-574``) and the decision memory's read model (``D-494``).

Plain SQL, every trigger ON (no trigger is disabled; the immutability, state-machine, scope and count guards all answer). The database must be
disposable: the module creates a helper function (``perf_id``), scaffolding tables (dropped at the end of ``seed_d463``) and accounts.
IDs are ``<prefix>_`` + 26 upper-case hex characters of an md5 -- inside the ULID alphabet, which is all the CHECKs read.

Scale (environment, read at import): ``PERF_P1_DOCS`` (400), ``PERF_P2_DOCS`` (300), ``PERF_PASS_SIZES`` (``300,500,800``), ``PERF_OLD_PASS_SIZE`` (400),
``PERF_P2_PASS_SIZE`` (100). The defaults are the 700-document volume the figures in the README were taken on; ``scale()`` returns what is configured.

D-463 (the optimisation counts on listDocuments):
  project 1 ("the page"): P1_DOCS documents, every current version AR-classified with a published standard run holding
    10..109 findings (about two thirds decided, some revoked), a LATEST optimisation pass of 300 / 500 / 800 proposals
    (by hash), ~60 % of the proposals decided once, some revoked and re-decided; 40 % of the documents also have an OLDER
    pass on the same version; a fifth have a non-current V1 with its own pass; runs of other kinds beside the result run
    (older published, newer failed, newer running).
  project 2 ("background"): P2_DOCS documents with lighter data (passes of 100 proposals on half of the AR ones).
D-494 (decision memory): ``seed_memory(engine, ids, upto)`` grows the memory to ``upto`` cases (decisions 1..3, text, content,
  two evidence rows, withdraw / restore / forget status events); called once per scale point.
"""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository, UserRepository

P1_DOCS = int(os.environ.get("PERF_P1_DOCS", "400"))
P2_DOCS = int(os.environ.get("PERF_P2_DOCS", "300"))
PASS_SIZES = tuple(int(x) for x in os.environ.get("PERF_PASS_SIZES", "300,500,800").split(","))
OLD_PASS_SIZE = int(os.environ.get("PERF_OLD_PASS_SIZE", "400"))
P2_PASS_SIZE = int(os.environ.get("PERF_P2_PASS_SIZE", "100"))
PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal


def scale() -> dict[str, object]:
    """The volume ``seed_d463`` would build, from the configuration alone: no database is touched."""
    return {
        "p1_documents": P1_DOCS, "p2_documents": P2_DOCS, "pass_sizes": list(PASS_SIZES), "old_pass_size": OLD_PASS_SIZE,
        "p2_pass_size": P2_PASS_SIZE,
    }


def log(message: str) -> None:
    print(f"[seed {time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def run(conn, sql: str, **params):
    return conn.execute(text(sql), params)


def count(conn, table: str) -> int:
    return int(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def prepare(engine) -> dict[str, str]:
    """The id helper function and the accounts every row needs. Returns the ids the other steps use."""
    with engine.begin() as conn:
        run(
            conn,
            "CREATE OR REPLACE FUNCTION perf_id(prefix text, key text) RETURNS text LANGUAGE sql IMMUTABLE AS "
            "$$ SELECT prefix || '_' || substr(upper(md5(key)), 1, 26) $$",
        )
    ids: dict[str, str] = {}
    with Session(engine) as session:
        users, accounts = UserRepository(), AccountRepository()
        for label, email, first in (("expert_a", "perf-a@example.com", "Анна"), ("expert_b", "perf-b@example.com", "Борис")):
            uid = str(users.create_user(session, email, PASSWORD).user_uid)
            accounts.complete_profile(session, user_uid=uid, email=None, last_name="Перфов", first_name=first)
            accounts.grant_role(session, user_uid=uid, role="expert", granted_by=None)
            ids[label] = uid
        session.commit()
    with engine.connect() as conn:
        for key in ("prj:1", "prj:2", "prl:1", "prl:2", "vnl:1"):
            prefix = key.split(":")[0]
            ids[key] = conn.execute(text("SELECT perf_id(:p, :k)"), {"p": prefix, "k": "main:" + key}).scalar_one()
    log(f"accounts and helper ready: {ids}")
    return ids


def seed_documents(engine, ids: dict[str, str]) -> None:
    with engine.begin() as conn:
        run(
            conn,
            "INSERT INTO project (project_uid, name) VALUES (:p1, 'PERF проект 1 (страница)'), (:p2, 'PERF проект 2 (фон)')",
            p1=ids["prj:1"], p2=ids["prj:2"],
        )
        run(
            conn,
            """
            CREATE TABLE perf_ver AS
            SELECT t.pn, g,
                   CASE t.pn WHEN 1 THEN :p1 ELSE :p2 END AS project_uid,
                   perf_id('doc', 'd:' || t.pn || ':' || g) AS doc_uid,
                   perf_id('ver', 'cur:' || t.pn || ':' || g) AS ver_uid,
                   CASE WHEN g % 5 = 0 THEN perf_id('ver', 'old:' || t.pn || ':' || g) END AS old_ver_uid
            FROM (VALUES (1, CAST(:n1 AS int)), (2, CAST(:n2 AS int))) AS t(pn, n)
            CROSS JOIN LATERAL generate_series(1, t.n) AS g
            """,
            p1=ids["prj:1"], p2=ids["prj:2"], n1=P1_DOCS, n2=P2_DOCS,
        )
        run(
            conn,
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "SELECT doc_uid, project_uid, 'АР-' || g || ' Рабочая документация, лист ' || (g % 17) FROM perf_ver",
        )
        run(
            conn,
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
            "SELECT old_ver_uid, doc_uid, 1, 'application/pdf', 1024, md5(old_ver_uid) || md5(old_ver_uid || 'x'), 3 "
            "FROM perf_ver WHERE old_ver_uid IS NOT NULL",
        )
        run(
            conn,
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
            "SELECT ver_uid, doc_uid, CASE WHEN old_ver_uid IS NULL THEN 1 ELSE 2 END, 'application/pdf', 1024, "
            "md5(ver_uid) || md5(ver_uid || 'x'), 3 FROM perf_ver",
        )
        run(
            conn,
            "UPDATE document d SET current_version_uid = v.ver_uid FROM perf_ver v WHERE d.document_uid = v.doc_uid",
        )
        run(
            conn,
            """
            INSERT INTO document_version_classification (version_uid, project_stage, section_code, confirmed_by_user_uid)
            SELECT ver_uid, 'R',
                   CASE WHEN pn = 1 OR g % 2 = 0 THEN 'AR' ELSE (ARRAY['KM', 'OV', 'EOM', 'VK'])[1 + g % 4] END,
                   :u
            FROM perf_ver
            UNION ALL
            SELECT old_ver_uid, 'R', 'AR', :u FROM perf_ver WHERE old_ver_uid IS NOT NULL
            """,
            u=ids["expert_a"],
        )
    log("documents and versions done")


def seed_runs_and_findings(engine, ids: dict[str, str]) -> None:
    with engine.begin() as conn:
        # One row per run to create. P2 versions with g % 7 = 0 are never run.
        run(
            conn,
            """
            CREATE TABLE perf_run_plan AS
            SELECT perf_id('run', kind || ':' || ver) AS run_id, ver AS version_uid, project_uid, kind, g, ts, n_find,
                   perf_id('ap', 'ap:' || kind || ':' || ver) AS ap,
                   perf_id('pb', 'pb:' || kind || ':' || ver) AS pb
            FROM (
                SELECT 'pub' AS kind, ver_uid AS ver, project_uid, g,
                       now() - interval '20 days' + g * interval '1 second' AS ts,
                       CASE WHEN pn = 1 THEN 10 + abs(hashtext(ver_uid)) % 100 ELSE 5 + abs(hashtext(ver_uid)) % 30 END AS n_find
                  FROM perf_ver WHERE pn = 1 OR g % 7 <> 0
                UNION ALL
                SELECT 'pub_older', ver_uid, project_uid, g, now() - interval '25 days', 10
                  FROM perf_ver WHERE g % 5 = 1 AND (pn = 1 OR g % 7 <> 0)
                UNION ALL
                SELECT 'failed_new', ver_uid, project_uid, g, now() - interval '5 days', 0
                  FROM perf_ver WHERE g % 10 = 2 AND (pn = 1 OR g % 7 <> 0)
                UNION ALL
                SELECT 'running_new', ver_uid, project_uid, g, now() - interval '1 hour', 0
                  FROM perf_ver WHERE g % 4 = 3 AND (pn = 1 OR g % 7 <> 0)
                UNION ALL
                SELECT 'pub_oldver', old_ver_uid, project_uid, g, now() - interval '40 days', 15
                  FROM perf_ver WHERE old_ver_uid IS NOT NULL
            ) s
            """,
        )
        run(
            conn,
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "frozen_input_digest, created_at) "
            "SELECT run_id, project_uid, version_uid, 'created', ap, pb, 'recorded', md5(run_id) || md5(run_id || 'x'), ts FROM perf_run_plan",
        )
        walk = (
            ("queued", "kind IN ('pub','pub_older','pub_oldver','running_new','failed_new')", False, ""),
            ("running", "kind IN ('pub','pub_older','pub_oldver','running_new')", False, ""),
            ("validating", "kind IN ('pub','pub_older','pub_oldver')", False, ""),
        )
        for state, where, terminal, extra in walk:
            run(
                conn,
                f"UPDATE audit_run r SET state = '{state}' FROM perf_run_plan p WHERE r.run_id = p.run_id AND p.{where}",
            )
        run(
            conn,
            "UPDATE audit_run r SET state = 'published', terminal_at = now(), degradation_set = '[]'::jsonb "
            "FROM perf_run_plan p WHERE r.run_id = p.run_id AND p.kind IN ('pub','pub_older','pub_oldver')",
        )
        run(
            conn,
            "UPDATE audit_run r SET state = 'failed', terminal_at = now(), terminal_reason = 'analysis_failed' "
            "FROM perf_run_plan p WHERE r.run_id = p.run_id AND p.kind = 'failed_new'",
        )
        log(f"runs: {count(conn, 'audit_run')}")
        run(
            conn,
            """
            CREATE TABLE perf_find AS
            SELECT perf_id('fnd', 'f:' || p.run_id || ':' || s.k) AS fuid, perf_id('fobs', 'o:' || p.run_id || ':' || s.k) AS obs,
                   p.run_id, p.version_uid, p.project_uid, p.ap, p.pb, s.k AS g,
                   abs(hashtext(perf_id('fnd', 'f:' || p.run_id || ':' || s.k))) % 100 AS h
            FROM perf_run_plan p CROSS JOIN LATERAL generate_series(1, p.n_find) AS s(k) WHERE p.n_find > 0
            """,
        )
        run(
            conn,
            "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
            "SELECT fuid, project_uid, version_uid, run_id, 'internal_contradiction' FROM perf_find",
        )
        run(
            conn,
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
            "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
            "SELECT obs, run_id, fuid, 'text_analysis', 'internal_contradiction', "
            "'Замечание ' || g || ': размеры на листе не совпадают с экспликацией помещений', "
            "'Привести размеры в соответствие с экспликацией', true, ap, pb, 'recorded' FROM perf_find",
        )
        log(f"findings: {count(conn, 'finding')} observations: {count(conn, 'finding_observation')}")
        # Expert events, in four statements so that sequence_no orders them as the history would.
        for label, where, event_type, verdict, comment in (
            ("e1", "h < 65", "CASE WHEN h < 35 THEN 'accept' ELSE 'reject' END",
             "CASE WHEN h < 35 THEN 'accepted' ELSE 'rejected' END", "NULL"),
            ("e2", "h < 15", "'revoke'", "'pending'", "NULL"),
            ("e3", "h < 6", "'accept'", "'accepted'", "NULL"),
            ("e4", "h BETWEEN 60 AND 75", "'comment'", "NULL", "'Комментарий эксперта'"),
        ):
            run(
                conn,
                "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, "
                "author_label, author_user_uid) "
                f"SELECT perf_id('dec', '{label}:' || fuid), fuid, obs, {event_type}, {verdict}, {comment}, 'perf', :u "
                f"FROM perf_find WHERE {where}",
                u=ids["expert_a"],
            )
        log(f"expert events: {count(conn, 'expert_decision_event')}")


def seed_optimisation(engine, ids: dict[str, str]) -> None:
    pl = (ids["prl:1"], ids["prl:2"])
    with engine.begin() as conn:
        for index, project in ((0, ids["prj:1"]), (1, ids["prj:2"])):
            blob = f"blob_{pl[index][4:]}"
            run(conn, "INSERT INTO blob (blob_id) VALUES (:b)", b=blob)
            run(conn, "UPDATE blob SET state = 'verifying' WHERE blob_id = :b", b=blob)
            run(
                conn,
                "UPDATE blob SET state = 'available', sha256 = :s, size_bytes = 1000, media_type = 'text/csv' WHERE blob_id = :b",
                b=blob, s=("a" if index == 0 else "b") * 64,
            )
            run(
                conn,
                "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, uploaded_by_user_uid, blob_id, sha256, "
                "size_bytes, media_type, source_format, source_filename, default_currency, parse_report, data_row_count, "
                "accepted_row_count, skipped_row_count) "
                "VALUES (:pl, :p, 1, :u, :b, :s, 1000, 'text/csv', 'csv', 'perf.csv', 'RUB', '{}'::jsonb, 2000, 2000, 0)",
                pl=pl[index], p=project, u=ids["expert_a"], b=blob, s=("a" if index == 0 else "b") * 64,
            )
            run(
                conn,
                "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, name, unit, unit_price, currency, "
                "vendor, section_code) "
                "SELECT perf_id('prp', :pl || ':' || r), :pl, r, 'Материал ' || ((r + 1) / 2) || CASE WHEN r % 2 = 1 THEN '' ELSE ' аналог' END, "
                "'шт', CASE WHEN r % 2 = 1 THEN 1000 + (r + 1) / 2 ELSE 500 + (r + 1) / 2 END::numeric, 'RUB', "
                "'Поставщик ' || (((r + 1) / 2) % 50), 'AR' FROM generate_series(1, 2000) r",
                pl=pl[index],
            )
        run(
            conn,
            "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, mode, revision_number, entry_count, set_by_user_uid) "
            "VALUES (:v, 'global', NULL, 'AR', 'list', 1, 1, :u)",
            v=ids["vnl:1"], u=ids["expert_a"],
        )
        run(conn, "INSERT INTO vendor_list_entry (vendor_list_id, ordinal, vendor) VALUES (:v, 1, 'Поставщик 1')", v=ids["vnl:1"])
    log("price lists and vendor list done")

    with engine.begin() as conn:
        run(
            conn,
            f"""
            CREATE TABLE perf_pass_plan AS
            SELECT perf_id('opp', 'latest:' || v.ver_uid) AS pass_id, v.ver_uid AS version_uid, v.doc_uid AS document_uid,
                   v.project_uid, r.run_id, :pl1 AS price_list_id,
                   (ARRAY[{",".join(str(s) for s in PASS_SIZES)}])[1 + abs(hashtext(v.ver_uid)) % {len(PASS_SIZES)}] AS n,
                   'gen-2' AS gen, now() - interval '1 day' AS started_at
              FROM perf_ver v JOIN perf_run_plan r ON r.version_uid = v.ver_uid AND r.kind = 'pub' WHERE v.pn = 1
            UNION ALL
            SELECT perf_id('opp', 'older:' || v.ver_uid), v.ver_uid, v.doc_uid, v.project_uid, r.run_id, :pl1,
                   {OLD_PASS_SIZE}, 'gen-1', now() - interval '10 days'
              FROM perf_ver v JOIN perf_run_plan r ON r.version_uid = v.ver_uid AND r.kind = 'pub'
             WHERE v.pn = 1 AND v.g % 5 IN (0, 1)
            UNION ALL
            SELECT perf_id('opp', 'oldver:' || v.old_ver_uid), v.old_ver_uid, v.doc_uid, v.project_uid, r.run_id, :pl1,
                   {OLD_PASS_SIZE}, 'gen-2', now() - interval '30 days'
              FROM perf_ver v JOIN perf_run_plan r ON r.version_uid = v.old_ver_uid AND r.kind = 'pub_oldver' WHERE v.pn = 1
            UNION ALL
            SELECT perf_id('opp', 'bg:' || v.ver_uid), v.ver_uid, v.doc_uid, v.project_uid, r.run_id, :pl2,
                   {P2_PASS_SIZE}, 'gen-2', now() - interval '3 days'
              FROM perf_ver v JOIN perf_run_plan r ON r.version_uid = v.ver_uid AND r.kind = 'pub'
             WHERE v.pn = 2 AND v.g % 2 = 0
            """,
            pl1=ids["prl:1"], pl2=ids["prl:2"],
        )
        n_pass = count(conn, "perf_pass_plan")
        log(f"pass plan: {n_pass} passes, {conn.execute(text('SELECT sum(n) FROM perf_pass_plan')).scalar_one()} proposals")
        run(
            conn,
            "INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, version_uid, run_id, text_layer_sha256, "
            "price_list_id, vendor_list_id, vendor_list_source, extraction_algorithm, match_algorithm, generator_version, "
            "specification_row_count, matched_row_count, proposed_row_count, proposal_count, started_by_user_uid, started_at) "
            "SELECT pass_id, project_uid, document_uid, version_uid, run_id, md5(pass_id) || md5(pass_id || 'x'), price_list_id, :v, 'global', "
            "'ext-1', 'match-1', gen, n + 10, n, n, n, :u, started_at FROM perf_pass_plan",
            v=ids["vnl:1"], u=ids["expert_a"],
        )
        run(
            conn,
            """
            INSERT INTO optimisation_proposal (optimisation_proposal_id, optimisation_pass_id, ordinal, proposal_type, spec_row_key,
                page_number, sheet_label, line_start, line_end, table_ordinal, row_position, row_text, matched_position_id,
                matched_basis, proposed_position_id, analog_basis, name_similarity, proposed_vendor, unit, quantity, quantity_text,
                current_unit_price, proposed_unit_price, currency, saving, rationale)
            SELECT perf_id('opr', pp.pass_id || ':' || g), pp.pass_id, g, 'cheaper_analog', 'sr-' || md5(pp.pass_id || ':sr:' || g),
                   1 + g / 40, NULL, g, g, 1, g::text,
                   'Позиция спецификации ' || g || ': материал ' || (g % 1000) || ', поставка по проекту',
                   m.price_list_position_id, 'name', p.price_list_position_id, 'name_similarity', 0.8, p.vendor, 'шт',
                   (1 + g % 20)::numeric, (1 + g % 20)::text, m.unit_price, p.unit_price, 'RUB',
                   (m.unit_price - p.unit_price) * (1 + g % 20)::numeric,
                   'Аналог из прайс-листа дешевле выбранной позиции при тех же характеристиках'
              FROM perf_pass_plan pp
              CROSS JOIN LATERAL generate_series(1, pp.n) g
              JOIN price_list_position m ON m.price_list_id = pp.price_list_id AND m.row_number = 2 * (g % 1000) + 1
              JOIN price_list_position p ON p.price_list_id = pp.price_list_id AND p.row_number = 2 * (g % 1000) + 2
            """,
        )
        log(f"passes: {count(conn, 'optimisation_pass')} proposals: {count(conn, 'optimisation_proposal')}")

    with engine.begin() as conn:
        run(
            conn,
            "CREATE TABLE perf_dec AS SELECT q.optimisation_proposal_id AS pid, abs(hashtext(q.optimisation_proposal_id)) % 100 AS h "
            "FROM optimisation_proposal q",
        )
        run(
            conn,
            "CREATE TABLE perf_dec_rows (pid text, seq int, verdict text, comment text, opd text, cmd text, decided_at timestamptz)",
        )
        stages = (
            (1, "h < 60", "CASE WHEN h < 30 THEN 'accept' WHEN h < 48 THEN 'reject' ELSE 'revise' END",
             "CASE WHEN h >= 48 THEN 'Уточнить марку и поставщика' END", "3 days"),
            (2, "(h < 15) OR (h BETWEEN 30 AND 35)", "CASE WHEN h < 15 THEN 'revoke' ELSE 'revise' END",
             "CASE WHEN h >= 30 THEN 'Передумал: нужна доработка' END", "2 days"),
            (3, "h < 6", "'accept'", "NULL", "1 day"),
        )
        for seq, where, verdict, comment, age in stages:
            run(
                conn,
                f"INSERT INTO perf_dec_rows SELECT pid, {seq}, {verdict}, {comment}, perf_id('opd', 's{seq}:' || pid), "
                f"perf_id('cmd', 's{seq}:' || pid), now() - interval '{age}' FROM perf_dec WHERE {where}",
            )
        log(f"decision plan rows: {count(conn, 'perf_dec_rows')}")
        run(
            conn,
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "SELECT cmd, 'decide_optimisation_proposal', 'perf-' || opd, md5(opd) || md5(cmd) FROM perf_dec_rows",
        )
        run(
            conn,
            "INSERT INTO optimisation_proposal_decision (proposal_decision_id, optimisation_proposal_id, seq, verdict, comment, "
            "actor_user_uid, command_id, decided_at) "
            "SELECT opd, pid, seq, verdict, comment, :u, cmd, decided_at FROM perf_dec_rows ORDER BY pid, seq",
            u=ids["expert_b"],
        )
        log(f"decisions: {count(conn, 'optimisation_proposal_decision')}")


def analyse(engine, label: str) -> None:
    started = time.time()
    raw = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    raw.execute(text("VACUUM (ANALYZE)"))
    raw.close()
    log(f"vacuum analyze ({label}) {time.time() - started:.1f}s")


def seed_d463(engine, ids: dict[str, str]) -> None:
    started = time.time()
    seed_documents(engine, ids)
    seed_runs_and_findings(engine, ids)
    seed_optimisation(engine, ids)
    # The plan tables are scaffolding; the measurement must not see them.
    with engine.begin() as conn:
        for table in ("perf_dec_rows", "perf_dec", "perf_find", "perf_pass_plan"):
            run(conn, f"DROP TABLE {table}")
    analyse(engine, "d463")
    log(f"D-463 seed done in {time.time() - started:.1f}s")


# ---------------------------------------------------------------------------------------------------------------------
# D-494: the decision memory


def seed_memory(engine, ids: dict[str, str], upto: int) -> None:
    """Grow the memory to ``upto`` cases. Case numbers continue from what is there, so a second call adds the difference."""
    with engine.connect() as conn:
        have = count(conn, "decision_memory_case")
    if upto <= have:
        return
    started = time.time()
    lo, hi = have + 1, upto
    u = ids["expert_a"]
    with engine.begin() as conn:
        run(
            conn,
            """
            CREATE TEMP TABLE perf_cases ON COMMIT DROP AS
            SELECT g, perf_id('dmc', 'c:' || g) AS case_id FROM generate_series(CAST(:lo AS int), CAST(:hi AS int)) g
            """,
            lo=lo, hi=hi,
        )
        run(
            conn,
            """
            INSERT INTO decision_memory_case (case_id, origin_observation_id, origin_finding_uid, origin_project_uid,
                origin_document_uid, origin_version_uid, origin_run_id, category, section_code, data_class, crop_state,
                capture_version, content_sha256, captured_at)
            SELECT case_id, perf_id('fobs', 'mo:' || g), perf_id('fnd', 'mf:' || g), perf_id('prj', 'mp:' || (g % 20)),
                   perf_id('doc', 'md:' || g), perf_id('ver', 'mv:' || g), perf_id('run', 'mr:' || g),
                   (ARRAY['internal_contradiction', 'explicit_placeholder', 'dimensions', 'layout', 'facade', 'roof',
                          'documentation', 'evacuation'])[1 + g % 8],
                   CASE WHEN g % 11 = 0 THEN NULL ELSE (ARRAY['AR', 'KM', 'OV', 'EOM', 'VK', 'PT', 'PB', 'SS', 'ITP', 'GP',
                          'TX', 'AI', 'KJ', 'POS', 'PS'])[1 + g % 15] END,
                   CASE WHEN g % 5 < 3 THEN 'test' ELSE 'real' END,
                   CASE WHEN g % 3 = 0 THEN 'none_available' ELSE 'referenced' END,
                   'dm-capture/1', md5(case_id) || md5(case_id || 'x'),
                   now() - (CAST(:hi AS int) - g) * interval '3 minutes'
              FROM perf_cases
            """,
            hi=hi,
        )
        # decisions: 1 for 60 %, 2 for 30 %, 3 for 10 %
        run(
            conn,
            """
            INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, severity,
                author_user_uid, origin_kind, decided_at)
            SELECT perf_id('dmd', 'd:' || g || ':' || k), case_id, perf_id('dec', 'ms:' || g || ':' || k),
                   CASE WHEN (g + k) % 3 = 0 THEN 'reject' ELSE 'accept' END,
                   CASE WHEN (g + k) % 3 = 0 THEN 'rejected' ELSE 'accepted' END,
                   CASE WHEN (g + k) % 3 = 0 THEN NULL ELSE (ARRAY['critical', 'economic', 'operational', 'recommendation',
                        'check_adjacent'])[1 + (g + k) % 5] END,
                   :u, (ARRAY['direct', 'direct', 'carried', 'imported'])[1 + (g + k) % 4],
                   now() - (CAST(:hi AS int) - g) * interval '3 minutes' + k * interval '1 minute'
              FROM perf_cases
              CROSS JOIN LATERAL generate_series(1, CASE WHEN g % 10 = 0 THEN 3 WHEN g % 10 < 4 THEN 2 ELSE 1 END) k
            """,
            u=u, hi=hi,
        )
        run(
            conn,
            "INSERT INTO decision_memory_decision_text (memory_decision_id, comment) "
            "SELECT memory_decision_id, CASE WHEN abs(hashtext(memory_decision_id)) % 10 < 3 "
            "THEN 'Комментарий эксперта: размеры согласованы с заказчиком, замечание снято' END "
            "FROM decision_memory_decision d JOIN perf_cases c ON c.case_id = d.case_id",
        )
        run(
            conn,
            "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, proposed_severity, stage_id, "
            "analysis_profile_id, prompt_bundle_id, provider_mode) "
            "SELECT case_id, 1, repeat('Размеры на листе не совпадают с экспликацией помещений. ', 5), "
            "repeat('Привести размеры в соответствие. ', 4), 'operational', 'text_analysis', "
            "perf_id('ap', 'map:' || g), perf_id('pb', 'mpb:' || g), 'live' FROM perf_cases",
        )
        run(
            conn,
            "INSERT INTO decision_memory_evidence (case_id, revision, ordinal, page_number, quote, char_start, char_end) "
            "SELECT case_id, 1, o, 1 + g % 30, repeat('Цитата из листа проекта. ', 8), 0, 200 FROM perf_cases CROSS JOIN generate_series(0, 1) o",
        )
    log(f"memory cases {lo}..{hi} inserted in {time.time() - started:.1f}s")

    # Status events in chunks: the status guard takes one advisory lock per case inside the transaction.
    chunk = 1000
    for a in range(lo, hi + 1, chunk):
        b = min(a + chunk - 1, hi)
        with engine.begin() as conn:
            run(
                conn,
                "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid) "
                "SELECT perf_id('dmw', 'w1:' || g), perf_id('dmc', 'c:' || g), 'withdraw', 'wrong_decision', :u "
                "FROM generate_series(CAST(:a AS int), CAST(:b AS int)) g WHERE g % 100 < 12",
                u=u, a=a, b=b,
            )
        with engine.begin() as conn:
            run(
                conn,
                "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid) "
                "SELECT perf_id('dmw', 'r1:' || g), perf_id('dmc', 'c:' || g), 'restore', 'other', :u "
                "FROM generate_series(CAST(:a AS int), CAST(:b AS int)) g WHERE g % 100 < 4",
                u=u, a=a, b=b,
            )
        with engine.begin() as conn:
            # the second withdraw of some restored cases, so a case can carry three events
            run(
                conn,
                "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid) "
                "SELECT perf_id('dmw', 'w2:' || g), perf_id('dmc', 'c:' || g), 'withdraw', 'test_data', :u "
                "FROM generate_series(CAST(:a AS int), CAST(:b AS int)) g WHERE g % 100 < 1",
                u=u, a=a, b=b,
            )
        with engine.begin() as conn:
            # forget: the tombstone and the deletes of the content side in ONE transaction (the guard reads xmin)
            run(
                conn,
                "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, "
                "owner_permission_ref, forgotten_content_sha256) "
                "SELECT perf_id('dmw', 'f1:' || g), perf_id('dmc', 'c:' || g), 'forget', 'client_request', :u, 'perf-permission', "
                "md5('f' || g) || md5('g' || g) FROM generate_series(CAST(:a AS int), CAST(:b AS int)) g WHERE g % 100 BETWEEN 50 AND 52",
                u=u, a=a, b=b,
            )
            run(
                conn,
                "DELETE FROM decision_memory_decision_text t USING decision_memory_decision d, decision_memory_status_event e "
                "WHERE t.memory_decision_id = d.memory_decision_id AND e.case_id = d.case_id AND e.kind = 'forget' "
                "AND e.xmin = pg_current_xact_id()::xid",
            )
            run(
                conn,
                "DELETE FROM decision_memory_evidence t USING decision_memory_status_event e "
                "WHERE e.case_id = t.case_id AND e.kind = 'forget' AND e.xmin = pg_current_xact_id()::xid",
            )
            run(
                conn,
                "DELETE FROM decision_memory_content t USING decision_memory_status_event e "
                "WHERE e.case_id = t.case_id AND e.kind = 'forget' AND e.xmin = pg_current_xact_id()::xid",
            )
    with engine.connect() as conn:
        log(
            "memory: cases %s decisions %s status events %s" % (
                count(conn, "decision_memory_case"), count(conn, "decision_memory_decision"),
                count(conn, "decision_memory_status_event"),
            )
        )
    analyse(engine, f"memory {hi}")
    log(f"memory seed to {hi} done in {time.time() - started:.1f}s")
