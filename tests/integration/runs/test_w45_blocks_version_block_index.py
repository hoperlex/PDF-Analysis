"""`W45-BLOCKS`. `BlockAdapter.get_block_index` after a real run, over the real corpus.

``docs/program/W45-BLOCKS.md`` records the three decisions this operation embodies:
keyed by version, ``status`` distinguishes *absent* from *empty*, and no crops. This
file proves the ``"produced"`` half against a real ``page_geometry_extraction`` output;
``tests/integration/composition/test_version_blocks_wire_shape.py`` proves the
``"not_produced"`` half and the ``404`` for an unknown version, at the wire.

The adapter is built on a ``sessionmaker`` bound to the already-open ``session``
fixture's own connection, with ``join_transaction_mode="create_savepoint"`` -- the same
technique ``tests/integration/api/conftest.py``'s ``session_factory`` fixture uses --
so it reads the run this test just wrote inside the same rolled-back transaction rather
than needing a second, separately committed connection.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import BlockAdapter
from auditmanager.runs import execute_run, start_audit_run


def _block_adapter(session: Session, blob_store) -> BlockAdapter:
    factory = sessionmaker(
        bind=session.connection(),
        expire_on_commit=False,
        future=True,
        join_transaction_mode="create_savepoint",
    )
    return BlockAdapter(factory, blob_store=blob_store)


def test_a_published_run_s_block_index_answers_produced_with_real_geometry(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("w45-blocks-produced"),
    )
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    assert result.terminal_state == "published", (
        f"the run did not reach the success terminal: {dict(result.stage_statuses)}"
    )

    view = _block_adapter(session, blob_store).get_block_index(
        version_uid=seeded.version_uid
    )

    assert view.status == "produced", view
    assert view.produced_by_run_id == str(started.run_id)
    assert view.text_layer_sha256 is not None and re.match(
        r"^[0-9a-f]{64}$", view.text_layer_sha256
    ), view.text_layer_sha256
    assert view.block_count == len(view.blocks) > 0, (
        "the corpus baseline has real text lines; a zero-block answer here would be "
        "vacuous and prove nothing about the produced/not_produced distinction"
    )

    seen_pages = set()
    for block in view.blocks:
        assert re.match(r"^b_[0-9]{6}$", block.block_id), block
        assert block.page_number >= 1
        assert block.block_ordinal >= 0
        assert block.bbox_unit == "pt"
        assert block.bbox_origin == "top_left"
        assert set(block.bbox) == {"x0", "y0", "x1", "y1"}
        assert block.char_end > block.char_start >= 0
        seen_pages.add(block.page_number)
    assert seen_pages, "no page produced a block"


def test_the_view_carries_no_crops_field_at_all(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """`R-23`'s addendum: crops is empty in this pipeline and is not restated here.

    ``VersionBlockIndexView`` has no ``crops`` attribute -- checked directly, so a field
    added back later by mistake (say, wiring ``ROLE_PAGE_CROPS`` in "for completeness")
    reddens here rather than silently shipping an always-``[]`` field with no explanation
    on the wire, which is exactly what the dispatch brief forbids.
    """
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("w45-blocks-no-crops"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    view = _block_adapter(session, blob_store).get_block_index(
        version_uid=seeded.version_uid
    )
    assert not hasattr(view, "crops")
    assert not hasattr(view, "page_crops")
