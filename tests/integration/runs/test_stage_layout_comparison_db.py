"""`HOSTS-CMP-01` on real PostgreSQL (migration ``0062``, no new migration): the comparison cells live in the revision's ``cells`` array.

The cell key pattern and the array bound (1 to 32) of ``0062`` admit ``<kind>:main`` beside the six rows, so no column and no head move. What is shown:

* a revision appended with the four comparison cells reads back as its analysis rows (the cells a run's plan is made of) and its comparison cells, apart;
* a revision appended without them reads back with none stored, and follows the table of its kit (``custom`` has none);
* the latest revision is the one in force, and the database holds the whole array of a ``blocks`` ensemble, the other five rows and the four kinds (at most
  twelve cells, under the bound of 32).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from auditmanager.access.public import UserRepository
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.stage_layout_store import SqlStageLayoutStore

KINDS = layout.COMPARISON_KINDS


def user(session) -> str:  # type: ignore[no-untyped-def]
    return str(UserRepository().create_user(session, "cmp-layout-" + uuid4().hex, "layout-test-password").user_uid)


def test_the_comparison_cells_are_stored_with_the_rows_and_read_back_apart(session) -> None:  # type: ignore[no-untyped-def]
    store, by = SqlStageLayoutStore(), user(session)
    written = store.append_revision(
        session, kit="codex_only", cells=layout.preset_cells("codex_only"), created_by=by,
        comparison_cells=layout.comparison_preset_cells("codex_only"))
    read = store.current_revision(session)
    assert read is not None and read.layout_revision_id == written.layout_revision_id
    assert read.cells == layout.preset_cells("codex_only"), "the rows of a run's plan are the six rows and nothing else"
    assert read.comparison_cells == layout.comparison_preset_cells("codex_only")
    assert [c.row for c in read.comparison_cells] == list(KINDS)
    stored = session.execute(text(
        "SELECT jsonb_array_length(cells) FROM stage_layout_revision WHERE layout_revision_id = :i"), {"i": read.layout_revision_id}).scalar_one()
    assert stored == len(layout.preset_cells("codex_only")) + 4 <= 32


def test_a_revision_without_them_stores_none_and_follows_its_kit(session) -> None:  # type: ignore[no-untyped-def]
    store, by = SqlStageLayoutStore(), user(session)
    store.append_revision(session, kit="claude_only", cells=layout.preset_cells("claude_only"), created_by=by)
    named = store.current_revision(session)
    assert named.comparison_cells is None and named.comparison_cells_in_force == layout.comparison_preset_cells("claude_only")
    assert named.comparison_cell("comparison_report").model_id == "claude-sonnet-5-5"
    store.append_revision(session, kit="custom", cells=layout.preset_cells("claude_only"), created_by=by)
    custom = store.current_revision(session)
    assert custom.comparison_cells is None and custom.comparison_cells_in_force is None and custom.comparison_cell("comparison_spec") is None
    assert [r.revision_no for r in store.history(session, limit=10)] == [2, 1]


def test_the_latest_revision_is_the_one_whose_comparison_cells_are_in_force(session) -> None:  # type: ignore[no-untyped-def]
    store, by = SqlStageLayoutStore(), user(session)
    store.append_revision(session, kit="codex_only", cells=layout.preset_cells("codex_only"), created_by=by,
                          comparison_cells=layout.comparison_preset_cells("codex_only"))
    other = tuple(c.__class__(c.cell_key, c.model_id, "medium") for c in layout.comparison_preset_cells("codex_only"))
    store.append_revision(session, kit="codex_only", cells=layout.preset_cells("codex_only"), created_by=by, comparison_cells=other)
    assert {c.effort for c in store.current_revision(session).comparison_cells} == {"medium"}
    assert {c.effort for c in store.history(session, limit=10)[1].comparison_cells} == {"high"}
