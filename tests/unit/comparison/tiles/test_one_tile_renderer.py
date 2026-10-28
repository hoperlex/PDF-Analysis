"""One tile renderer for the API process (`CMP-C1-FIX-A` item 5, `CMP-VIEWER-01` section 12 item 2).

``VersionPageAdapter`` and ``ComparisonPairTileAdapter`` each built their own ``TileRenderer`` (two children at a time each), so
the host-level bound was four tile children, not two. The composition root builds one and hands it to both.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.adapters import ComparisonPairTileAdapter, VersionPageAdapter
from auditmanager.comparison.profile.tiles import TILE_SLOTS, TileRenderer


def renderer_of_page_adapter(adapter: VersionPageAdapter) -> TileRenderer:
    return adapter._reader._renderer()


def renderer_of_pair_adapter(adapter: ComparisonPairTileAdapter) -> TileRenderer:
    return adapter._reader._profiles._renderer()


def test_the_two_adapters_use_the_renderer_they_are_given() -> None:
    shared = TileRenderer()
    page = VersionPageAdapter(None, blob_store=None, tiles=shared)  # type: ignore[arg-type]
    pair = ComparisonPairTileAdapter(None, blob_store=None, tiles=shared)  # type: ignore[arg-type]
    assert renderer_of_page_adapter(page) is shared and renderer_of_pair_adapter(pair) is shared


def test_the_pair_tile_reader_reads_its_page_tiles_through_the_same_profile_reader() -> None:
    """The renderer is used by the profile reader the pair reader's tile source is built on, not by another one."""
    pair = ComparisonPairTileAdapter(None, blob_store=None, tiles=TileRenderer())  # type: ignore[arg-type]
    assert pair._reader.tiles._reader is pair._reader._profiles


def test_without_one_each_adapter_builds_its_own_which_is_what_the_composition_root_no_longer_allows() -> None:
    page = VersionPageAdapter(None, blob_store=None)  # type: ignore[arg-type]
    pair = ComparisonPairTileAdapter(None, blob_store=None)  # type: ignore[arg-type]
    assert renderer_of_page_adapter(page) is not renderer_of_pair_adapter(pair)


def test_an_explicit_reader_is_used_as_it_is() -> None:
    sentinel: Any = object()
    assert ComparisonPairTileAdapter(None, blob_store=None, reader=sentinel)._reader is sentinel  # type: ignore[arg-type]


class _Recorder:
    """Stands in for an adapter class of the composition root and keeps what it was built with."""

    built: list[dict[str, Any]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).built.append(kwargs)

    def __getattr__(self, name: str) -> Any:  # a port the router asks for something of: never reached by construction
        raise AttributeError(name)


def test_the_composition_root_hands_one_renderer_to_both_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    environ = {
        "DATABASE_URL": "postgresql+psycopg://user:password@127.0.0.1:9/nothing",
        "S3_ENDPOINT_URL": "http://127.0.0.1:9", "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "an-access-key", "S3_SECRET_ACCESS_KEY": "a-secret-key", "S3_BUCKET": "a-bucket",
        "AUDITMANAGER_API_TOKEN": "a-token-of-the-unit-test",
    }
    seen: dict[str, dict[str, Any]] = {}

    def spy(name: str, real: type) -> type:
        class Spy(real):  # type: ignore[valid-type, misc]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                seen[name] = kwargs
                super().__init__(*args, **kwargs)

        return Spy

    monkeypatch.setattr(composition, "VersionPageAdapter", spy("pages", composition.VersionPageAdapter))
    monkeypatch.setattr(composition, "ComparisonPairTileAdapter", spy("pairs", composition.ComparisonPairTileAdapter))
    composition.build_application(environ=environ)
    assert isinstance(seen["pages"]["tiles"], TileRenderer)
    assert seen["pages"]["tiles"] is seen["pairs"]["tiles"], "the page tiles and the pair tiles share one renderer"
    assert TILE_SLOTS == 2
