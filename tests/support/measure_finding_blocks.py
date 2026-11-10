"""Measure the finding to portal block relation on real stored artifacts of a recorded run (D-353).

    flock <the host's run lock> timeout 1200 tools/measure/with_throwaway_stand.sh \\
        .venv/bin/python -m tests.support.measure_finding_blocks --out <dir> [--pz-pdf <PDF>] [--only NAME ...]

For each scenario a version is published from a portal bundle, the recorded adapter carries a run to ``published`` through the
real chain, and the shipped ``BlockAdapter.list_run_finding_blocks`` answers from the artifacts that run and that version
stored. Every linked (finding, block) pair is then held against the PDF's own glyphs and the block's recognised text
(``tests/support/finding_block_proof.py``), and the same artifacts are linked once more by the rule as it was before `D-353`'s
measurement (a cut of the line's box proportional to characters) so that the two are compared on one set of stored documents.

(``tail1`` is the last word of a line and ``w2`` every two neighbouring words at every offset of it, from 3 and 4 characters: what
a model quotes of a table row or a clause.)

Scenarios (each prints one JSON block and writes ``<out>/<name>.json`` plus ``<out>/report.md``):

* ``baseline`` -- ``ar_baseline.zip`` and the committed recording (three findings, five evidence items);
* ``ar_sweep`` -- the same bundle, one authored finding per unit of its text layer (every line, the head, middle and tail of a
  line, every pair of adjacent lines);
* ``pz_key_paragraphs`` / ``pz_sweep_paragraphs`` / ``pz_key_cells`` / ``pz_sweep_cells`` -- ``--pz-pdf`` (the synthetic
  «Пояснительная записка», 10 pages with tables and justified paragraphs) with portal blocks found on the page raster by an
  XY-cut at paragraph or at cell level (``tests/support/xy_cut_blocks.py``): the answer key's quotations that are unique on their
  page, and the same sweep.

**The second witness (`D-450`, `D-590`).** Each result also carries the relation as ``link_evidence`` computes it with the recognised text of the
portal's text blocks and the text layer's page texts (``figures_with_the_witness``; the witness is asked only when the quotation is unique on
its page and every block that touches the line has a reading, `JUDGE-N2` H1), over the same stored documents, with these sensitivity runs:
the widest unboxed stretch of a line tolerated (``gap_none``, ``gap_4``, ``gap_1`` heights of the line instead of the shipped two), the page-uniqueness
condition patched out (``no_unique_gate``, an ablation: what it keeps out), the shortest
quotation the witness is asked about set to 1 (``..._min1``), and the recognised text damaged the way a reading damages it (a word
in ten, in three, written with a look-alike Latin letter or a letter short; ``..._noise10`` and ``..._noise30``, each also without
the witness's abstention on a block whose reading carries a quality flag, ``..._without_the_doubtful_guard``; and the damage no flag
names, a letter short, ``..._dropped10`` and ``..._dropped30``; and the **naive witness**, with neither the abstention on a doubtful reading
nor the one on a near copy, on the exact and the damaged readings, ``..._naive_*``: an ablation that patches the rule's near-copy test
out for the call, to show what the two abstentions are worth). The shipped adapter hands the recognised text to the rule
(``bootstrap/adapters.py``, `D-590`), so its answer is the relation **with** the witness; this reproduction calls the rule
itself, **fails the scenario** unless the call with the blocks' text gives exactly the adapter's answer for every finding
(``reproduction_matches_the_adapter``), and reads the whole-width rule's figures (``figures``) from the call without the text.
The blocks' text of the ``pz_*`` and ``stress_*`` scenarios is what the PDF's own characters inside the block read as (an exact
reading); the quotations of the sweeps are unique on their page, so with an exact reading a wrong link needs overlapping
blocks and the noise runs of those sets show what a damaged reading costs in coverage, not in wrong links. ``repeat_sweep_cells``
is the set that can show the wrong link (`D-590`): a schedule whose rows repeat one phrase in two cells, quoted by an authored
finding whose evidence is the FIRST occurrence (what the chain's anchor resolution gives), with cell blocks.

**The scenarios that can fail (`D-649`).** ``witness_image``, ``witness_schedule``, ``witness_damage``, ``witness_a1`` and
``witness_gutter`` (``tests/support/witness_scenarios.py``) are PDFs with portal blocks and readings authored the way a portal fails
(an IMAGE block over the line with the phrase repeated, wrapped or bled into the notes; a schedule whose rows differ in two words of
four with damaged readings; Latin look-alikes, a letter O for a zero, a lost space, a dropped sign; the judge's A1; wide gutters, a cell
the portal did not box and A2b). Each result carries ``ablation``: the shipped rule and the rule with every subset of its guards (unique
quotation, reading of the touching blocks, quality flags, unboxed stretch, near copy) removed, and the rule with the pre-`D-626` unit of
the unboxed-stretch limit, each held against the PDF's glyphs by kind of case: a scenario is worth something only when some subset links
wrongly. ``ablation_offline`` is the same table computed from the PDF alone (no database) and ``ablation_offline_equals_the_stand`` says
whether the stored documents gave the same counts.

**What is authored.** The model's reply is never live: it is an authored recording (``recording_document``, token counts invented
and small, keyed by the request checksum the real chain computes), so a finding here is "a quotation somebody chose", not a
model's. The portal's blocks of the ``pz_*`` scenarios are an algorithm's, not a portal's. What is real is the chain from the
reply to the stored artifacts and the read under test.

Not product code; never run against a live provider (the recorded adapter has no client).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools" / "fixtures"))  # portal_bundle, ar_corpus

from sqlalchemy.orm import sessionmaker  # noqa: E402

from auditmanager.analysis.geometry import finding_blocks as rule_module  # noqa: E402
from auditmanager.analysis.geometry.finding_blocks import COVERAGE, WITNESS_MAX_GAP_LINE_HEIGHTS, WITNESS_MIN_CHARACTERS, Readings  # noqa: E402
from auditmanager.analysis.stages.extraction import NORMALIZATION_DESCRIPTION  # noqa: E402
from auditmanager.analysis.text import ProviderConfig, ProviderMode, RecordedAdapter  # noqa: E402
from auditmanager.analysis.text.adapter import build_request  # noqa: E402
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE  # noqa: E402
from auditmanager.analysis.text.recorded import recording_document  # noqa: E402
from auditmanager.analysis.text.textlayer import load_text_layer  # noqa: E402
from auditmanager.findings import group_published_findings, published_finding_evidence, published_findings  # noqa: E402
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url  # noqa: E402
from auditmanager.shared.db.engine import create_database_engine  # noqa: E402
from auditmanager.shared.identity import IdempotencyKey  # noqa: E402
from auditmanager.storage import S3BlobStore, S3StorageSettings  # noqa: E402
from tests.integration.analysis.geometry import reads_support as support  # noqa: E402
from tests.integration.analysis.recognised.recognised_support import BundleMembers, members  # noqa: E402
from tests.support.finding_block_proof import (  # noqa: E402
    NOISE_RATES,
    BlockFact,
    EvidenceFact,
    MemoOracle,
    PdfOracle,
    analyse,
    degrade,
    doubtful_blocks,
    figures,
    require_same_links,
    rule_links,
)
from tests.support import stress_layout_pdf, witness_scenarios  # noqa: E402
from tests.support.xy_cut_blocks import CELLS, PARAGRAPHS, Layout, block_text, page_blocks  # noqa: E402

MODEL_ID = "claude-opus-5"
RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"
#: Authored, not measured, and small enough to stay under the run's cost ceiling whatever the reply's length.
AUTHORED_USAGE = {"input_tokens": 3000, "output_tokens": 1500, "latency_ms": 9000}
MIN_UNIT_CHARACTERS = 12
SHORT_UNIT_CHARACTERS = 3


# -- authored replies --------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    kind: str
    page: int
    quote: str


def sweep_units(oracle: PdfOracle) -> tuple[list[Unit], Counter]:
    """Every line, the head / middle / tail of a line and every pair of adjacent lines whose text is unique on its page."""
    units: list[Unit] = []
    skipped: Counter = Counter()

    def offer(kind: str, page: int, text: str, page_text: str) -> None:
        if len(text) < MIN_UNIT_CHARACTERS:
            skipped["short"] += 1
        elif page_text.count(text) != 1:
            skipped["not unique on its page"] += 1
        else:
            units.append(Unit(kind, page, text))

    for entry in oracle.layer:
        lines = entry.text.split("\n")
        for index, line in enumerate(lines):
            offer("line", entry.page_number, line, entry.text)
            tokens = list(re.finditer(r"\S+", line))
            if tokens and len(line[tokens[-1].start():]) >= SHORT_UNIT_CHARACTERS and entry.text.count(tokens[-1].group()) == 1:
                units.append(Unit("tail1", entry.page_number, tokens[-1].group()))
            for first in range(len(tokens) - 1):
                # Every two neighbouring words, at every offset of the line: what a model quotes of a cell or a clause.
                text = line[tokens[first].start():tokens[first + 1].end()]
                if len(text) >= SHORT_UNIT_CHARACTERS + 1 and entry.text.count(text) == 1:
                    units.append(Unit("w2", entry.page_number, text))
            if len(tokens) >= 6:
                third = len(tokens) // 3
                for kind, first, last in (
                    ("head", 0, 2), ("middle", third, third + 2), ("tail", len(tokens) - 3, len(tokens) - 1),
                ):
                    offer(kind, entry.page_number, line[tokens[first].start():tokens[last].end()], entry.text)
            if index + 1 < len(lines):
                offer("pair", entry.page_number, line + "\n" + lines[index + 1], entry.text)
    return units, skipped


def sample(units: list[Unit], cap: int) -> list[Unit]:
    """Every k-th unit, k the least that keeps at most ``cap`` -- deterministic, and every kind keeps its share."""
    stride = -(-len(units) // cap) if cap and len(units) > cap else 1
    return units[::stride]


def key_units(oracle: PdfOracle, key_path: Path, name: str) -> tuple[list[list[Unit]], Counter]:
    """The answer key's findings whose every quotation is unique on its page, as stated."""
    key = json.loads(key_path.read_text(encoding="utf-8"))[name]["expected_findings"]
    findings: list[list[Unit]] = []
    skipped: Counter = Counter()
    for item in key:
        units = [
            Unit("key", int(location["pages"][0]), location["quote"]) for location in item["locations"]
        ]
        if all(oracle.layer[u.page - 1].text.count(u.quote) == 1 and len(u.quote) >= MIN_UNIT_CHARACTERS for u in units):
            findings.append(units)
        else:
            skipped["key finding with a quotation that is short or not unique on its page"] += 1
    return findings, skipped


def observations(groups: list[list[Unit]]) -> list[dict[str, Any]]:
    result = []
    for number, units in enumerate(groups, start=1):
        result.append({
            "category": "internal_contradiction",
            "finding_text": f"AUTHORED {units[0].kind} p{units[0].page} #{number}",
            "recommendation_text": "Authored for the measurement of the finding to block relation; not a recommendation.",
            "evidence": [{"page_number": u.page, "quote": u.quote} for u in units],
        })
    return result


def author_recording(oracle: PdfOracle, directory: Path, replies: list[dict[str, Any]], note: str) -> Path:
    """Write the recording the real chain will ask for: keyed by the request checksum over this PDF's text layer."""
    pages = [
        {"page_number": p.page_number, "char_start": p.char_start, "char_end": p.char_end, "text": p.text}
        for p in oracle.layer
    ]
    document = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": "ver_01M25P3TH0X4C5ZR8G4M2Q7WJH",
        "extractor": {"name": "pdfplumber", "version": "0.11.10", "options_sha256": ""},
        "normalization": {"id": "nfc_v1", "description": NORMALIZATION_DESCRIPTION},
        "total_char_count": oracle.layer[-1].char_end, "pages": pages,
    }
    request = build_request(
        model_id=MODEL_ID, bundle=AR_TEXT_PROMPT_BUNDLE, text_layer=load_text_layer(document)
    )
    recording = recording_document(
        request=request, output_text=json.dumps({"observations": replies}, ensure_ascii=False),
        stop_reason="end_turn", note=note, **AUTHORED_USAGE,
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{request.request_sha256}.json"
    path.write_text(json.dumps(recording, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# -- bundles -----------------------------------------------------------------------------------


def raster_bundle(pdf: bytes, stem: str, layout: Layout, oracle: PdfOracle) -> BundleMembers:
    """A portal bundle for ``pdf`` whose blocks are the XY-cut of its page rasters (TEXT blocks that read as something)."""
    from portal_bundle import bundle as portal_bundle  # noqa: PLC0415
    from portal_bundle import blocklist, portal_format  # noqa: PLC0415
    from portal_bundle.pdffacts import PageFacts  # noqa: PLC0415

    boxes = page_blocks(pdf, layout)
    texts = block_text(pdf, boxes)
    facts = [PageFacts(p.width_pt, p.height_pt, 0, p.text) for p in oracle.layer]
    blocks = [
        blocklist.Block(portal_format.KIND_TEXT, index, box, text=text)
        for index, (row, words) in enumerate(zip(boxes, texts))
        for box, text in zip(row, words)
        if text
    ]
    files = portal_bundle.make_files(pdf, stem, pages=facts, blocks=blocks)
    return BundleMembers(name=f"{stem}.zip", pdf=pdf, markdown=files.results_md, block_list=files.blocks_json)


def sheet_bundle(sheet: witness_scenarios.Sheet, stem: str, oracle: PdfOracle) -> BundleMembers:
    """A portal bundle for a sheet of ``tests/support/witness_scenarios.py``: its blocks as authored, over the PDF's own pages."""
    markdown, block_list = witness_scenarios.portal_files(sheet, stem, oracle.layer)
    return BundleMembers(name=f"{stem}.zip", pdf=sheet.pdf, markdown=markdown, block_list=block_list)


# -- the rule as it was before the measurement --------------------------------------------------


def legacy_links(
    evidence: list[EvidenceFact], lines: list[Any], sizes: dict[int, tuple[float, float]], blocks: list[BlockFact]
) -> set[str]:
    """`finding_blocks.link_evidence` at ``3492b2d0d``: the line's box cut at the evidence's fraction of its characters,
    a block holding the evidence when it covers at least half of the cut box's area. Restated here, for comparison only."""
    held: set[str] = set()
    for span in evidence:
        width, height = sizes[span.page_number]
        for line in lines:
            if line.page_number != span.page_number or line.char_end <= span.char_start or line.char_start >= span.char_end:
                continue
            length = line.char_end - line.char_start
            start, end = max(span.char_start, line.char_start), min(span.char_end, line.char_end)
            left = line.x0 + (start - line.char_start) / length * (line.x1 - line.x0)
            right = line.x0 + (end - line.char_start) / length * (line.x1 - line.x0)
            box = (left / width, line.y0 / height, right / width, line.y1 / height)
            if not (box[2] > box[0] and box[3] > box[1]):
                continue
            for block in blocks:
                if block.page_number != span.page_number:
                    continue
                across = min(box[2], block.bbox_norm[2]) - max(box[0], block.bbox_norm[0])
                down = min(box[3], block.bbox_norm[3]) - max(box[1], block.bbox_norm[1])
                if across > 0 and down > 0 and across * down / ((box[2] - box[0]) * (box[3] - box[1])) >= COVERAGE:
                    held.add(block.portal_block_id)
    return held


# -- the stand ----------------------------------------------------------------------------------


def open_stand() -> tuple[Any, Any, Any, Any]:
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    store = S3BlobStore(S3StorageSettings.from_env())
    store.check_access()
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False, future=True)()
    return engine, connection, transaction, (session, store)


@dataclass
class Scenario:
    name: str
    note: str
    bundle: BundleMembers
    recording_dir: Path
    skipped: Counter
    authored: int | None
    sheet: Any = None            # a ``witness_scenarios.Sheet``: the scenario's ablation table is computed (`D-649`)


def run(session: Any, store: Any, scenario: Scenario) -> dict[str, Any]:
    oracle = PdfOracle(scenario.bundle.pdf)
    try:
        version_uid = support.seed_bundle_version(
            session, store, bundle=scenario.bundle, page_count=len(oracle.layer),
            text_character_count=oracle.layer[-1].char_end,
        )
        config = ProviderConfig(
            mode=ProviderMode.RECORDED, model_id=MODEL_ID, run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True,
        )
        key = IdempotencyKey("b5-" + hashlib.sha256(f"measure-{scenario.name}".encode()).hexdigest()[:32])
        run_id = support.run_published(
            session, version_uid, key, store, RecordedAdapter(scenario.recording_dir), config
        )
        adapter = support.block_adapter(session, store)
        links = adapter.list_run_finding_blocks(run_id=run_id)
        portal = adapter.list_portal_blocks(version_uid=version_uid)
        index = adapter.get_block_index(version_uid=version_uid)
        groups = sorted(
            group_published_findings(published_findings(session, run_id)), key=lambda g: g.canonical.finding_uid
        )
        evidence: dict[str, list[EvidenceFact]] = {}
        by_observation: dict[str, list[Any]] = {}
        for row in published_finding_evidence(session, run_id):
            by_observation.setdefault(row.finding_observation_id, []).append(row)
        for group in groups:
            evidence[group.canonical.finding_uid] = [
                EvidenceFact(e.page_number, e.char_start, e.char_end, e.quote)
                for e in by_observation.get(group.canonical.finding_observation_id, ())
            ]
        labels = {g.canonical.finding_uid: g.canonical.finding_text for g in groups}
        blocks = [
            BlockFact(
                b.portal_block_id, b.page_number, b.block_type, tuple(b.bbox_norm),
                None if b.recognised_text is None else b.recognised_text.text,
            )
            for b in portal.blocks
        ]
        linked = {i.finding_uid: list(i.portal_block_ids) for i in links.items}      # the shipped answer: with the second witness

        # The rule as it was, over the same stored documents.
        from auditmanager.analysis.geometry.finding_blocks import TextLine  # noqa: PLC0415

        lines = [
            TextLine(b.page_number, b.char_start, b.char_end, b.bbox["x0"], b.bbox["y0"], b.bbox["x1"], b.bbox["y1"])
            for b in index.blocks
        ]
        sizes = {p.page_number: (p.width_pt, p.height_pt) for p in oracle.layer}
        layer = {p.page_number: p.text for p in oracle.layer}          # the text layer's page texts: what the witness asks about uniqueness
        usable = [f for f in evidence.items()]
        unlinked = set(links.unlinked_pages)
        # The whole-width rule alone (`D-353`): the rule called without the text, which is the adapter's answer before `D-590`.
        plain = {uid: rule_links(facts, lines, sizes, blocks, unlinked, None) for uid, facts in usable}
        now = analyse(
            items=[(uid, plain[uid], labels[uid]) for uid, _ in usable], evidence=evidence, blocks=blocks,
            unlinked_pages=links.unlinked_pages, oracle=oracle,
        )
        order = {b.portal_block_id: n for n, b in enumerate(blocks)}
        before_items = []
        for uid, facts in usable:
            held = legacy_links([f for f in facts if f.page_number not in links.unlinked_pages], lines, sizes, blocks)
            before_items.append((uid, sorted(held, key=order.__getitem__), labels[uid]))
        before = analyse(items=before_items, evidence=evidence, blocks=blocks, unlinked_pages=links.unlinked_pages, oracle=oracle)

        # The rule with the second witness, over the same stored documents. First the guard: the call with the blocks' text must be
        # the adapter's answer, finding by finding, or this reproduction is not the shipped rule and nothing below means anything.
        def kind(label: str) -> str:
            return label.split()[1] if label.startswith("AUTHORED") else "recorded"

        texts = {b.portal_block_id: b.text for b in blocks if b.text}
        shared = Readings(texts, doubtful_blocks(blocks, texts), layer)
        with_text = {
            uid: rule_links(facts, lines, sizes, blocks, unlinked, texts, WITNESS_MIN_CHARACTERS, readings=shared)
            for uid, facts in usable
        }
        require_same_links(with_text, linked)
        adapter_figures = figures(analyse(
            items=[(uid, linked[uid], labels[uid]) for uid, _ in usable], evidence=evidence, blocks=blocks,
            unlinked_pages=links.unlinked_pages, oracle=oracle,
        ), label_of=kind)
        memo = MemoOracle(oracle)

        def witnessed(
            texts_given: dict[str, str] | None, min_characters: int = WITNESS_MIN_CHARACTERS, *, guarded: bool = True,
            veto: bool = True, unique: bool = True, max_gap: float | None = WITNESS_MAX_GAP_LINE_HEIGHTS,
        ) -> dict[str, Any]:
            """The relation with the witness; ``guarded=False`` drops the doubtful-reading abstention, ``veto=False`` the near-copy
            one and ``unique=False`` the page-uniqueness condition (each patched out of the rule for this call: an ablation, to see
            what each is worth, never the shipped rule); ``max_gap`` is the widest unboxed stretch of a line tolerated (``None``: any)."""
            doubtful = doubtful_blocks(blocks, texts_given) if guarded and texts_given else set()
            variant = Readings(texts_given, doubtful, layer)          # folded once for the variant, not once per finding
            with contextlib.ExitStack() as patched:
                if not veto:
                    patched.enter_context(mock.patch.object(rule_module, "_near_copy", lambda *_a, **_k: False))
                if not unique:
                    patched.enter_context(mock.patch.object(rule_module.Readings, "occurrences", lambda *_a, **_k: 1))
                result = [
                    (uid, rule_links(facts, lines, sizes, blocks, unlinked, texts_given, min_characters, readings=variant,
                                     max_gap_line_heights=max_gap), labels[uid])
                    for uid, facts in usable
                ]
            return analyse(items=result, evidence=evidence, blocks=blocks, unlinked_pages=links.unlinked_pages, oracle=memo)

        with_witness = witnessed(texts)
        sensitivity = {"min1": witnessed(texts, 1)}
        # How much each condition of the rule costs in coverage (and, on the sets where an error is possible, what it keeps out):
        # the widest unboxed stretch of a line tolerated, and the page-uniqueness condition dropped.
        sensitivity["gap_none"] = witnessed(texts, max_gap=None)
        sensitivity["gap_4"] = witnessed(texts, max_gap=4.0)
        sensitivity["gap_1"] = witnessed(texts, max_gap=1.0)
        sensitivity["no_unique_gate"] = witnessed(texts, unique=False)
        for rate in NOISE_RATES if scenario.sheet is None else ():     # the scenarios of `D-649` carry their own damage and their ablation table
            damaged = {key: degrade(key, text, rate) for key, text in texts.items()}
            name = f"noise{round(rate * 100)}"
            sensitivity[name] = witnessed(damaged)
            sensitivity[f"{name}_without_the_doubtful_guard"] = witnessed(damaged, guarded=False)
            # Damage no quality flag names (a letter short): the guard cannot see it.
            unseen = {key: degrade(key, text, rate, flaggable=False) for key, text in texts.items()}
            sensitivity[f"dropped{round(rate * 100)}"] = witnessed(unseen)
            # The naive witness (neither abstention), on the damaged readings: what the two are worth.
            sensitivity[f"naive_noise{round(rate * 100)}"] = witnessed(damaged, guarded=False, veto=False)
            sensitivity[f"naive_dropped{round(rate * 100)}"] = witnessed(unseen, guarded=False, veto=False)
            sensitivity[f"no_unique_gate_dropped{round(rate * 100)}"] = witnessed(unseen, unique=False)
        sensitivity["naive_exact"] = witnessed(texts, guarded=False, veto=False)
        ablation: dict[str, Any] = {}
        if scenario.sheet is not None:
            # `D-649`: the rule once for every subset of its guards removed, over the stored documents, and the same table from the PDF
            # alone. The counts must agree: the stored readings are the authored ones, the evidence the first occurrence, the lines the same.
            stored = witness_scenarios.Inputs(
                evidence, labels, lines, sizes, layer, blocks, memo, unlinked=frozenset(unlinked),
            )
            ablation["ablation"] = witness_scenarios.matrix(stored)
            ablation["ablation_offline"] = witness_scenarios.evaluate(scenario.sheet)
            differences = witness_scenarios.table_differences(ablation["ablation"], ablation["ablation_offline"])
            ablation["ablation_offline_equals_the_stand"] = not differences
            ablation["ablation_differences"] = differences[:50]
        before_pairs = {(p["finding_uid"], p["portal_block_id"]) for p in now["pairs"]}
        added = Counter(p["geometry"] for p in with_witness["pairs"] if (p["finding_uid"], p["portal_block_id"]) not in before_pairs)
        lost = sorted(before_pairs - {(p["finding_uid"], p["portal_block_id"]) for p in with_witness["pairs"]})
        if lost:
            raise AssertionError(f"the second witness removed {len(lost)} links the geometry made, e.g. {lost[:3]}")

        return {
            "name": scenario.name, "note": scenario.note, "run_id": run_id, "version_uid": version_uid,
            "pages": len(oracle.layer), "portal_blocks": len(blocks), "text_layer_lines": len(lines),
            "authored_findings": scenario.authored, "published_findings": len(groups),
            "evidence_items": sum(len(v) for v in evidence.values()),
            "skipped_units": dict(scenario.skipped), "status": links.status, "unlinked_pages": links.unlinked_pages,
            "figures": figures(now, label_of=kind), "figures_before_the_fix": figures(before, label_of=kind),
            "figures_with_the_witness": figures(with_witness, label_of=kind),
            "figures_of_the_adapter": adapter_figures,
            "witness_pairs_added_by_geometry_verdict": dict(added),
            "figures_with_the_witness_sensitivity": {name: figures(report) for name, report in sensitivity.items()},
            "reproduction_matches_the_adapter": True, **ablation,
            "analysis": now, "analysis_before_the_fix": before, "analysis_with_the_witness": with_witness,
        }
    finally:
        oracle.close()


def excerpt(text: str | None, width: int = 160) -> str | None:
    return None if text is None else (text if len(text) <= width else text[: width - 1] + "…")


def render(results: list[dict[str, Any]]) -> str:
    lines = ["# Finding to portal block relation: measured figures", ""]
    lines += ["| scenario | findings | with a block | coverage | links | wrong | marginal | missed | precision by glyphs | precision by text (contains / most words) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in results:
        rows = [("fixed rule", r["figures"]), ("rule before", r["figures_before_the_fix"]),
                ("fixed rule + witness", r["figures_with_the_witness"])]
        rows += [(f"witness {name}", f) for name, f in r["figures_with_the_witness_sensitivity"].items()]
        for label, f in rows:
            lines.append(
                f"| {r['name']} ({label}) | {f['findings']} | {f['findings_with_a_block']} | {f['coverage']} | {f['links']} | "
                f"{f['wrong']} | {f['links_by_geometry'].get('marginal', 0)} | {f['missed_links']} | "
                f"{f['link_precision_by_glyphs']} | {f['precision_text_contains']} / {f['precision_text_most_words']} "
                f"(of {f['links_with_recognised_text']}) |"
            )
    ablated = [r for r in results if "ablation" in r]
    if ablated:
        lines += ["", "# Scenarios that can fail (`D-649`): the shipped rule and the rule with guards removed, by kind of case", "",
                  "A kind's `wrong` is a link to a block that does not touch the quotation's glyphs. The last column names the smallest sets "
                  "of guards whose removal makes the kind link wrongly (`SHIPPED`: no guard is left to remove).", ""]
        for r in ablated:
            lines.append(witness_scenarios.render_table(r["name"], r["ablation"]))
            lines.append(f"The same table from the PDF alone equals the stand's: {r['ablation_offline_equals_the_stand']} "
                         f"({len(r['ablation_differences'])} differences listed).")
            lines.append("")
    for r in results:
        lines += ["", f"## {r['name']}", "", r["note"], ""]
        lines.append(f"pages {r['pages']}, portal blocks {r['portal_blocks']}, text-layer lines {r['text_layer_lines']}, "
                     f"authored {r['authored_findings']}, published {r['published_findings']}, evidence items {r['evidence_items']}, "
                     f"unlinked pages {r['unlinked_pages']}, skipped units {r['skipped_units']}")
        lines.append(f"links the witness added, by the glyph verdict: {r['witness_pairs_added_by_geometry_verdict']}")
        for title, key in (("fixed rule", "figures"), ("rule before the fix", "figures_before_the_fix"),
                           ("fixed rule + second witness", "figures_with_the_witness")):
            lines += ["", f"### {title}", "", "```json", json.dumps(r[key], ensure_ascii=False, indent=1), "```"]
        for title, key in (("WRONG links, fixed rule", "analysis"), ("WRONG links, rule before the fix", "analysis_before_the_fix"),
                           ("WRONG links, fixed rule + second witness", "analysis_with_the_witness")):
            wrong = [p for p in r[key]["pairs"] if p["geometry"] == "WRONG"]
            lines += ["", f"### {title}: {len(wrong)}", ""]
            for p in wrong[:25]:
                lines.append(f"* page {p['page']} block `{p['portal_block_id']}` ({p['block_type']}) bbox {p['bbox_norm']}: "
                             f"quote «{excerpt(p['quote'])}» block text «{excerpt(p['block_text'])}»")
        text_misses = [p for p in r["analysis"]["pairs"] if p["block_type"] == "text" and p["text"] not in (None, "contains")]
        lines += ["", f"### Links whose TEXT block does not contain the quote, fixed rule: {len(text_misses)}", ""]
        for p in text_misses[:25]:
            lines.append(f"* page {p['page']} `{p['portal_block_id']}` bbox {p['bbox_norm']} geometry {p['geometry']} text {p['text']} "
                         f"share {p['word_share']}: «{excerpt(p['quote'])}» / «{excerpt(p['block_text'])}»")
        misses = r["analysis"]["misses"]
        lines += ["", f"### Missed links, fixed rule (the glyphs lie in a block that is not linked): {len(misses)}", ""]
        for m in misses[:25]:
            lines.append(f"* page {m['page']} `{m['portal_block_id']}` bbox {m['bbox_norm']}: {[excerpt(q, 80) for q in m['quotes']]}")
    return "\n".join(lines) + "\n"


def build_scenarios(pz_pdf: Path | None, work: Path, only: set[str], cap: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    baseline = members("ar_baseline.zip")
    if not only or "baseline" in only:
        scenarios.append(Scenario(
            "baseline", "ar_baseline.zip and the committed recording: 3 findings, 5 evidence items, one TEXT block per page, "
            "IMAGE and STAMP blocks that hold no text-layer line.", baseline, RECORDINGS, Counter(), None))
    if not only or "ar_sweep" in only:
        oracle = PdfOracle(baseline.pdf)
        units, skipped = sweep_units(oracle)
        skipped["dropped by the cap (stride sampling)"] = len(units) - len(sample(units, cap))
        units = sample(units, cap)
        directory = work / "ar_sweep"
        author_recording(oracle, directory, observations([[u] for u in units]), "authored sweep over ar_baseline")
        oracle.close()
        scenarios.append(Scenario(
            "ar_sweep", "ar_baseline.zip with an authored finding per unit of its text layer (line, head, middle, tail, pair).",
            baseline, directory, skipped, len(units)))
    if pz_pdf is not None:
        pdf = pz_pdf.read_bytes()
        key_path = pz_pdf.parent / "answer_key.json"
        for layout in (PARAGRAPHS, CELLS):
            oracle = PdfOracle(pdf)
            stem = f"PZ_{layout.name}"
            bundle = raster_bundle(pdf, stem, layout, oracle)
            sweep, sweep_skipped = sweep_units(oracle)
            sweep_skipped["dropped by the cap (stride sampling)"] = len(sweep) - len(sample(sweep, cap))
            sweep = sample(sweep, cap)
            keyed, key_skipped = key_units(oracle, key_path, pz_pdf.stem)
            for name, groups, skipped, note in (
                (f"pz_key_{layout.name}", keyed, key_skipped, "the answer key's findings with quotations unique on their page"),
                (f"pz_sweep_{layout.name}", [[u] for u in sweep], sweep_skipped, "an authored finding per unit of the text layer"),
            ):
                if only and name not in only:
                    continue
                directory = work / name
                author_recording(oracle, directory, observations(groups), note)
                scenarios.append(Scenario(
                    name, f"{pz_pdf.name}, blocks from an XY-cut of the page raster at {layout.name} level "
                    f"(gap {layout.gap_x_pt} pt across, {layout.gap_y_pt} pt down): {note}.",
                    bundle, directory, skipped, len(groups)))
            oracle.close()
    if not only or {"stress_sweep_paragraphs", "stress_sweep_cells"} & only:
        pdf = stress_layout_pdf.build()
        for layout in (PARAGRAPHS, CELLS):
            name = f"stress_sweep_{layout.name}"
            if only and name not in only:
                continue
            oracle = PdfOracle(pdf)
            sweep, skipped = sweep_units(oracle)
            skipped["dropped by the cap (stride sampling)"] = len(sweep) - len(sample(sweep, cap))
            sweep = sample(sweep, cap)
            directory = work / name
            author_recording(oracle, directory, observations([[u] for u in sweep]), "authored sweep over the stress PDF")
            bundle = raster_bundle(pdf, f"stress_{layout.name}", layout, oracle)
            oracle.close()
            scenarios.append(Scenario(
                name, "tests/support/stress_layout_pdf.py (a schedule, two columns of running text and label/value rows: every line "
                f"crosses a place a portal cuts), blocks from an XY-cut of the page raster at {layout.name} level "
                f"(gap {layout.gap_x_pt} pt across, {layout.gap_y_pt} pt down): an authored finding per unit of the text layer.",
                bundle, directory, skipped, len(sweep)))
    if not only or "repeat_sweep_cells" in only:
        pdf, phrases = stress_layout_pdf.build_repeated()
        oracle = PdfOracle(pdf)
        name = "repeat_sweep_cells"
        units = [Unit("rep", page, phrase) for page, phrase in phrases]
        directory = work / name
        author_recording(oracle, directory, observations([[u] for u in units]), "authored sweep over the repeated-phrase PDF")
        bundle = raster_bundle(pdf, "repeat_cells", CELLS, oracle)
        oracle.close()
        scenarios.append(Scenario(
            name, "tests/support/stress_layout_pdf.py build_repeated (a schedule whose every row repeats one phrase in two cells): an authored "
            f"finding per row quoting the phrase, whose evidence is its first occurrence; blocks from an XY-cut at {CELLS.name} level.",
            bundle, directory, Counter(), len(units)))
    for name, build in witness_scenarios.SCENARIOS.items():
        if only and name not in only:
            continue
        sheet = build()
        oracle = PdfOracle(sheet.pdf)
        directory = work / name
        units = [Unit(quote.kind, quote.page, quote.text) for quote in sheet.quotes]
        author_recording(oracle, directory, observations([[unit] for unit in units]), f"authored findings of {name}")
        bundle = sheet_bundle(sheet, name, oracle)
        oracle.close()
        scenarios.append(Scenario(name, f"tests/support/witness_scenarios.py: {sheet.note} (`D-649`).", bundle, directory, Counter(), len(units), sheet))
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pz-pdf", type=Path, default=None)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--cap", type=int, default=700, help="most authored findings of one sweep (stride sampling above it)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    scenarios = build_scenarios(args.pz_pdf, args.out / "recordings", set(args.only), args.cap)
    engine, connection, transaction, (session, store) = open_stand()
    results: list[dict[str, Any]] = []
    try:
        for scenario in scenarios:
            try:
                result = run(session, store, scenario)
            except Exception as failure:  # noqa: BLE001 -- a scenario that cannot run is a finding of its own; the others go on
                print(json.dumps({"name": scenario.name, "failed": f"{type(failure).__name__}: {failure}"}, ensure_ascii=False))
                (args.out / f"{scenario.name}.failed.txt").write_text(f"{type(failure).__name__}: {failure}\n", encoding="utf-8")
                continue
            results.append(result)
            (args.out / f"{scenario.name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print(json.dumps({
                "name": result["name"], "fixed": result["figures"], "before": result["figures_before_the_fix"],
                "witness": result["figures_with_the_witness"], "added": result["witness_pairs_added_by_geometry_verdict"],
                "sensitivity": {k: {n: v[n] for n in ("findings_with_a_block", "coverage", "links", "wrong", "missed_links")}
                                for k, v in result["figures_with_the_witness_sensitivity"].items()},
            }, ensure_ascii=False))
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
    (args.out / "report.md").write_text(render(results), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
