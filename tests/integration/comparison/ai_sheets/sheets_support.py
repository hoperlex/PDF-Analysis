"""The world and the helpers of the sheet-description database tests (`CMP-VC-AISHEET-01`).

Plain code, no pytest; ``conftest.py`` loads it by path and hands it to a test as ``h``. Everything is written through the connection
it is given, and with the ``db`` fixture that connection is rolled back at the end of the test (``document_version`` refuses DELETE
by trigger), so nothing of a test stays in the lane's database.

:func:`sheet_world` makes a project with a finished series of one transition and six sheet pairs::

    p1  different     the table sheet of the unit fixtures (a table, a place, a shift); a permit item is attached to it
    p2  needs_review  a result with no pointer but a service note: nothing to ask about
    p3  same          a sheet that did not change
    p4  added         a sheet that is in the newer version only
    p5  removed       a sheet that is in the older version only
    p6  different     another table sheet (its own result, its own content key)

and returns their ids. The model is :class:`~auditmanager.comparison.public.RecordedAnswers`: an answer is filed under the digest of
the exact request the handler will build, which the test gets by building the packet through the same code.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid

SHA = "a" * 64
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def new_id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def x(connection: Connection, sql: str, **values: Any) -> None:
    connection.execute(text(sql), values)


def digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


@dataclass
class Sheet:
    pair: str
    status: str
    page_a: str | None = None
    page_b: str | None = None
    result: str | None = None
    result_key: str | None = None


@dataclass
class World:
    project: str
    document: str
    versions: list[str]
    build: str
    series: str
    transition: str
    sheets: dict[str, Sheet] = field(default_factory=dict)
    profile_ids: list[str] = field(default_factory=list)

    def __getitem__(self, name: str) -> Sheet:
        return self.sheets[name]


def _page_profile(connection: Connection, version: str, number: int, key: str, *, sheet: str = "7", title: str = "План этажа") -> str:
    profile_id = new_id("cpr")
    x(connection, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                  "algo_version, status, profile) VALUES (:i, :v, :n, :k, 'cmp-profile/3', 'ready', CAST(:p AS jsonb))",
      i=profile_id, v=version, n=number, k=key,
      p=json.dumps({"scan": False, "stamp": {"sheet_number": sheet, "sheet_name": title, "designation": "ЭМ-12", "revision_number": "3"}}))
    return profile_id


def _result(connection: Connection, project: str, status: str, document: dict[str, Any], page_a: str, page_b: str, key: str) -> str:
    result_id = new_id("csp")
    x(connection, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, algo_version, "
                  "status, reasons, channels, result, page_a_profile_id, page_b_profile_id) VALUES (:i, :p, :k, 'cmp-engine/2', :s, "
                  "'[]'::jsonb, '{}'::jsonb, CAST(:r AS jsonb), :a, :b)",
      i=result_id, p=project, k=key, s=status, r=json.dumps(document), a=page_a, b=page_b)
    return result_id


def sheet_world(connection: Connection, fx: Any, *, transition_state: str = "completed") -> World:
    """The world of the module note. ``fx`` is the unit tests' ``sheet_fixtures`` (the pages and the engine's result)."""
    world = World(project=str(ProjectUid.new()), document=str(DocumentUid.new()), versions=[], build=new_id("cmx"),
                  series=new_id("cser"), transition=new_id("ctn"))
    x(connection, "INSERT INTO project (project_uid, name) VALUES (:p, 'ai-sheets')", p=world.project)
    x(connection, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Электроснабжение')",
      d=world.document, p=world.project)
    for number in (1, 2):
        version = str(VersionUid.new())
        world.versions.append(version)
        x(connection, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, "
                      "page_count) VALUES (:v, :d, :n, 'application/pdf', 1, :s, 10)", v=version, d=world.document, n=number, s=SHA)
    x(connection, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, "
                  "rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, :s, 'v1.2', 'm1', '[]')",
      m=world.build, p=world.project, d=world.document, s=SHA)
    command = new_id("cmd")
    x(connection, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) VALUES (:c, "
                  "'start_comparison_series', :k, :f)", c=command, k=new_id("k")[:20], f=SHA)
    x(connection, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, state, comparison_matrix_id, "
                  "matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) VALUES (:s, :p, :d, 'completed', :m, 0, "
                  ":sha, :a, 'A', :c)", s=world.series, p=world.project, d=world.document, m=world.build, sha=SHA, a=ACTOR, c=command)
    x(connection, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
                  "source_version_uid, target_version_uid, state, summary, verdict) VALUES (:t, :s, 1, :v1, :v2, :st, "
                  "CASE WHEN :st = 'completed' THEN '{}'::jsonb END, CASE WHEN :st = 'completed' THEN '[]'::jsonb END)",
      t=world.transition, s=world.series, v1=world.versions[0], v2=world.versions[1], st=transition_state)
    v1, v2 = world.versions
    plan = [
        ("p1", "different", 1, 1, "table"), ("p2", "needs_review", 2, 2, "quiet"), ("p3", "same", 3, 3, "quiet"),
        ("p4", "added", None, 4, None), ("p5", "removed", 5, None, None), ("p6", "different", 6, 5, "table"),
    ]
    for number, (name, status, page_a, page_b, shape) in enumerate(plan, 1):
        a = _page_profile(connection, v1, page_a, digest(name, "a")) if page_a else None
        b = _page_profile(connection, v2, page_b, digest(name, "b")) if page_b else None
        sheet = Sheet(pair=new_id("ctp"), status=status, page_a=a, page_b=b)
        world.profile_ids += [p for p in (a, b) if p]
        if shape is not None:
            document = fx.table_result() if shape == "table" else {
                "format": 1, "canvas": {"width_pt": fx.PAGE_W, "height_pt": fx.PAGE_H},
                "how_compared": {"algo_version": "cmp-engine/2", "dpi": 100, "tolerance_pt": 0.5, "transform": [1, 0, 0, 1, 0, 0]},
                "text_changes": [], "differences": [],
                "service_notes": [{"kind": "stamp", "change": "changed", "zone": "stamp", "field": "date", "before": "01.01", "after": "02.01"}],
                "aligned_blocks": [], "mask": None,
            }
            sheet.result_key = digest(name, "result")
            sheet.result = _result(connection, world.project, status, document, str(a), str(b), sheet.result_key)
        permit = ({"state": "declared_and_found", "items": [{"text": "Изм. 3: замена люка Лк-1", "state": "declared_and_found"}]}
                  if name == "p1" else None)
        x(connection, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, state, status, "
                      "page_a_profile_id, page_b_profile_id, result_id, permit) VALUES (:i, :t, :n, 'done', :s, :a, :b, :r, "
                      "CAST(:permit AS jsonb))",
          i=sheet.pair, t=world.transition, n=number, s=status, a=a, b=b, r=sheet.result,
          permit=None if permit is None else json.dumps(permit))
        world.sheets[name] = sheet
    return world


def material_for(fx: Any, world: World) -> Any:
    """A :class:`FakeMaterial` with the table pages for every sheet that has a result (the others get plain pages)."""
    pages: dict[str, Any] = {}
    for name in ("p1", "p6"):
        sheet = world[name]
        a, b = fx.table_pages(str(sheet.page_a), str(sheet.page_b), world.versions[0], world.versions[1])
        pages[str(sheet.page_a)], pages[str(sheet.page_b)] = a, b
    for name in ("p2", "p3"):
        sheet = world[name]
        for profile in (sheet.page_a, sheet.page_b):
            pages[str(profile)] = fx.page(str(profile), world.versions[0], 1, [(60, 60, 120, 72, "Щит ЩО-1")], [])
    pages[str(world["p4"].page_b)] = fx.page(str(world["p4"].page_b), world.versions[1], 4, [(60, 60, 140, 72, "Схема ЩО-2"), (60, 90, 100, 102, "ЩР-1")], [])
    pages[str(world["p5"].page_a)] = fx.page(str(world["p5"].page_a), world.versions[0], 5, [(60, 60, 140, 72, "Схема ЩО-3"), (60, 90, 100, 102, "ЩР-7")], [])
    return fx.FakeMaterial(pages)


def add_table_pair(connection: Connection, world: World, fx: Any, name: str, result: dict[str, Any], *, pair_no: int, pages: Any,
                   status: str = "different") -> Sheet:
    """A further sheet pair of the world with the result given. ``pages`` is the material's ``pages`` dict, which gets its two pages."""
    a = _page_profile(connection, world.versions[0], pair_no, digest(name, "a"))
    b = _page_profile(connection, world.versions[1], pair_no, digest(name, "b"))
    sheet = Sheet(pair=new_id("ctp"), status=status, page_a=a, page_b=b, result_key=digest(name, "result"))
    sheet.result = _result(connection, world.project, status, result, a, b, sheet.result_key)
    x(connection, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, state, status, "
                  "page_a_profile_id, page_b_profile_id, result_id) VALUES (:i, :t, :n, 'done', :s, :a, :b, :r)",
      i=sheet.pair, t=world.transition, n=pair_no, s=status, a=a, b=b, r=sheet.result)
    world.sheets[name] = sheet
    pa, pb = fx.table_pages(a, b, world.versions[0], world.versions[1])
    from dataclasses import replace

    pages[a], pages[b] = replace(pa, width_pt=3000.0, height_pt=2000.0), replace(pb, width_pt=3000.0, height_pt=2000.0)
    return sheet
