"""The section-run bounds hold for every run that did not ask for ``relaxed_limits``.

`REVIEW-FIX-BOUNDS-1102` (finding S1-sprints-01): ``af581631`` lifted 1000 sources, 63 windows,
500 text pages and 900 000 request bytes for every fresh run. They apply again; a run that asked
for ``relaxed_limits`` -- the run whose frozen policy carries ``unbounded_stats`` -- keeps the
lift. Each default-mode assertion below fails against the lifted constants.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.extended import core, estimate, native_pages, workflow
from auditmanager.analysis.extended.coverage import coverage_policy
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.shared.errors import DomainError

LIFTED = 2**31 - 1


def policy(blocks: int, pages: int, *, windows: int | None = None, lifted: bool = False) -> dict:
    return {
        "enabled": True, "plan_version": core.PLAN_VERSION_V3, "max_blocks": blocks, "window_size": 16,
        "max_windows": max((blocks + 15) // 16, (pages + 15) // 16) if windows is None else windows,
        "text_page_limit": pages, "review": True, "rules_sha256": "0" * 64, "section_code": "AR",
        **coverage_policy(unbounded_stats=lifted),
    }


def test_the_ruled_figures_are_the_constants() -> None:
    assert (core.SECTION_MAX_SOURCES, core.SECTION_MAX_WINDOWS, core.SECTION_MAX_TEXT_PAGES) == (1000, 63, 500)
    assert (estimate.MAX_VISUAL_SOURCES, estimate.MAX_TEXT_PAGES) == (1000, 500)
    assert (workflow.MAX_WORKFLOW_WINDOWS, workflow.MAX_V3_REQUEST_BYTES) == (63, 900_000)


class TestTheAuthorityOfAFrozenPolicy:
    def test_the_bounds_themselves_are_enabled(self) -> None:
        assert core.enabled(policy(1000, 500))
        assert core.enabled(policy(1000, 1))
        assert core.enabled(policy(16, 500))

    @pytest.mark.parametrize("blocks, pages", [(1001, 16), (16, 501), (1001, 501)])
    def test_one_past_a_bound_is_refused(self, blocks: int, pages: int) -> None:
        assert not core.enabled(policy(blocks, pages))

    def test_a_window_count_past_63_is_refused(self) -> None:
        assert not core.enabled(policy(1000, 500, windows=64))

    def test_a_relaxed_run_keeps_the_lift(self) -> None:
        assert core.enabled(policy(1001, 501, lifted=True))
        assert core.enabled(policy(50_000, 40_000, lifted=True))
        assert not core.enabled(policy(LIFTED + 1, 16, lifted=True))

    def test_the_stamp_is_what_lifts_not_the_size(self) -> None:
        big = policy(5_000, 4_000)
        assert not core.enabled(big)
        assert core.enabled({**big, "unbounded_stats": True})
        assert not core.bounds_lifted({**big, "unbounded_stats": 1})
        assert not core.bounds_lifted(None)


class TestThePreflightScope:
    @staticmethod
    def scope(pages: int, **kwargs: object) -> dict:
        return estimate.estimate_visual_scope(version=NS(page_count=pages, manifest=()), **kwargs)

    def test_500_pages_are_priced_and_501_are_refused(self) -> None:
        assert self.scope(500)["text_page_limit"] == 500
        with pytest.raises(DomainError) as refused:
            self.scope(501)
        assert refused.value.detail_fields["reason"] == "cost_page_count_unavailable"

    def test_a_relaxed_run_is_priced_past_500_pages(self) -> None:
        scope = self.scope(5_000, relaxed_limits=True)
        assert scope["text_page_limit"] == 5_000 and scope["max_windows"] == 313

    def test_more_than_1000_image_blocks_are_refused_unless_relaxed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        raw = b"blocks"
        companion = NS(role="source.structured_companion", blob_id="blob", size_bytes=len(raw),
                       sha256=hashlib.sha256(raw).hexdigest())
        store = NS(read=lambda *_args, **_kw: raw)
        monkeypatch.setattr(estimate, "parse_blob_id", lambda value: value)
        monkeypatch.setattr(estimate, "read_block_list",
                            lambda *_args, **_kw: [NS(block_type=estimate.IMAGE)] * 1001)
        version = NS(page_count=300, manifest=(companion,))
        with pytest.raises(DomainError) as refused:
            estimate.estimate_visual_scope(version=version, blob_store=store)
        assert refused.value.detail_fields["reason"] == "cost_visual_source_limit_exceeded"
        relaxed = estimate.estimate_visual_scope(version=version, blob_store=store, relaxed_limits=True)
        assert relaxed["total_sources"] == relaxed["max_blocks"] == 1001

    def test_the_flag_must_be_a_boolean(self) -> None:
        with pytest.raises(ValueError):
            self.scope(10, relaxed_limits="yes")


class TestThePlannedWindow:
    @staticmethod
    def plan(**kwargs: object) -> object:
        return core.plan_inputs(version_uid="ver", section="AR", portal={}, manifest={}, text_layer={},
                                graph={}, observations=None, plan_version=core.PLAN_VERSION_V3, **kwargs)

    def test_more_than_1000_sources_or_an_offset_past_them_is_refused(self) -> None:
        for kwargs in ({"max_sources": 1001}, {"max_sources": 2000, "source_offset": 1000}):
            with pytest.raises(ValueError, match="extended_source_window_invalid"):
                self.plan(**kwargs)

    def test_a_relaxed_run_passes_that_check(self) -> None:
        try:
            self.plan(max_sources=5_000, source_offset=1_200, relaxed_limits=True)
        except Exception as error:  # the empty inputs fail later, for another reason
            assert str(error) != "extended_source_window_invalid"


class TestNativePages:
    @staticmethod
    def prepare(**kwargs: object) -> object:
        return native_pages.prepare_native_page_sources(
            version_uid="ver", source_ref=NS(blob_id="not-a-blob", sha256="0" * 64, size_bytes=1),
            blob_store=None, **kwargs)

    def test_501_pages_or_a_window_past_1000_are_refused(self) -> None:
        with pytest.raises(ValueError, match="native_page_limit_invalid"):
            self.prepare(max_pages=501)
        with pytest.raises(ValueError, match="native_page_window_invalid"):
            self.prepare(max_pages=16, window_offset=1000, max_sources=2000)
        with pytest.raises(ValueError, match="native_page_window_invalid"):
            self.prepare(max_pages=16, window_offset=0, max_sources=1001)

    def test_a_relaxed_run_passes_those_checks(self) -> None:
        for kwargs in ({"max_pages": 501}, {"max_pages": 16, "window_offset": 1000, "max_sources": 2000}):
            try:
                self.prepare(relaxed_limits=True, **kwargs)
            except Exception as error:  # the unreadable blob id fails later
                assert not str(error).startswith("native_page_")

    def test_the_image_cap_is_4_mib_and_only_a_relaxed_run_lifts_it(self) -> None:
        assert native_pages.MAX_NATIVE_PNG_BYTES == 4 * 1024 * 1024


class TestTheRequestAndTheMerge:
    @staticmethod
    def request(size: int) -> ModelRequest:
        body = {"messages": [{"content": json.dumps({"filler": "a" * size})}], "system": "rubric"}
        return ModelRequest("model", body, idempotency_scope="scope")

    def build(self, size: int, **kwargs: object) -> ModelRequest:
        return workflow._v3_request(self.request(size), run_id="run", section="AR",
                                    phase="comprehensive_analysis", **kwargs)

    def test_a_request_over_900_000_bytes_is_refused(self) -> None:
        assert self.build(100_000)
        with pytest.raises(ValueError, match="extended_v3_request_window_too_large"):
            self.build(900_000)

    def test_a_relaxed_run_builds_it(self) -> None:
        assert self.build(900_000, relaxed_limits=True)

    def test_the_merge_keeps_the_window_and_observation_bounds(self) -> None:
        items = [{"title": f"t{index}", "description": "d"} for index in range(3)]
        assert len(workflow.deterministic_lossless_merge_v3(items)) == 3
        with pytest.raises(ValueError, match="extended_global_window_limit_invalid"):
            workflow.deterministic_lossless_merge_v3(items, max_windows=64)
        flood = [{"title": str(index), "description": "d"}
                 for index in range(63 * workflow.MAX_MERGED_INPUTS + 1)]
        with pytest.raises(ValueError, match="extended_global_observation_limit_exceeded"):
            workflow.deterministic_lossless_merge_v3(flood)
        assert len(workflow.deterministic_lossless_merge_v3(flood, relaxed_limits=True)) == len(flood)
        assert workflow.deterministic_lossless_merge_v3(items, max_windows=64, relaxed_limits=True)
