#!/usr/bin/env python3
"""The one portal bundle in the journey whose text holds a specification table.

    python3 tests/e2e/pc01/journey/build_specification_bundle.py            # write the bundle
    python3 tests/e2e/pc01/journey/build_specification_bundle.py --check    # verify, write nothing
    python3 tests/e2e/pc01/journey/build_specification_bundle.py --install-recording

`BETA-LIVE-JOURNEY-01`. «Оптимизация» prices the rows of an AR set's specification table and
proposes cheaper analogs from a price list. The shipped baseline bundle
(`fixtures/synthetic/ar/bundles/ar_baseline.zip`) has no such table, so a pass over it honestly
holds no proposal and nothing can be decided or exported. This bundle is that baseline's eight
pages, byte for byte in text, plus one: a Form-7 style specification with three rows --

    1 Металлический щит МЩ-1   шт   2
    2 Дверь стальная ДС-1      шт   1
    3 Утеплитель минераловатный м3  12,5

-- which `tests/e2e/pc01/journey/fixtures/optimisation/prices.csv` prices (the first row has a
cheaper analog in the same list) and the journey's vendor lists admit.

**Why a recording has to be installed.** The run is the recorded one: the model reply is
replayed from `fixtures/recorded/text_analysis/<request checksum>.json`, and a different
document is a different checksum, so a run over this bundle is refused as
`recording_missing` until its recording exists. The reply is the baseline's own (eight pages
unchanged, so every quotation is still grounded; the ninth page raises no finding), filed
under this document's checksum. `--install-recording` computes that checksum with the same
code `fixtures/recorded/text_analysis/build_fixtures.py` uses for the baseline -- and
reproduces the baseline's own checksum first, as its control -- and writes the one file into
the lane's worktree. **It is an untracked file in a tracked directory**: `git status` shows
it, nothing commits it, and the journey's `start-specification-run` step is what says so
when it is absent. The full gate does not run this journey.

Exit status: 0 done, 1 a check failed, 2 a usage or environment error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BUNDLE_PATH = Path(__file__).resolve().parent / "fixtures" / "optimisation" / "ar_specification.zip"
STEM = "ar_specification"
BASELINE_KEY = "6c208358cfa9ae3a7591223084f87250084c9c6f8070f211d8e2fd9e278dbd1d"
RECORDINGS = REPO_ROOT / "fixtures" / "recorded" / "text_analysis"

SPEC_LINES = (
    ("Спецификация оборудования, изделий и материалов", {"size": 12, "center": True}),
    (
        "Поз. Наименование и техническая характеристика Тип, марка Код Ед. изм. Кол. Масса Примечание",
        {"size": 8.5, "space_before": 8},
    ),
    ("Изделия", {"size": 9.5, "space_before": 4}),
    ("1 Металлический щит МЩ-1 шт 2", {"size": 9.5}),
    ("2 Дверь стальная ДС-1 шт 1", {"size": 9.5}),
    ("Материалы", {"size": 9.5, "space_before": 4}),
    ("3 Утеплитель минераловатный м3 12,5", {"size": 9.5}),
    # The stamp line ends the table, so the page footer is not read as part of the last row.
    ("Изм. Кол.уч. Лист №док. Подпись Дата", {"size": 8.5, "space_before": 6}),
)


def _tools() -> tuple:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "fixtures"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    import build_ar_corpus  # noqa: E402
    from ar_corpus import content, document  # noqa: E402
    from portal_bundle import bundle  # noqa: E402

    return build_ar_corpus, content, document, bundle


def build_bundle() -> bytes:
    """The baseline's pages plus the specification page, as one portal bundle."""
    build_ar_corpus, content, document, bundle = _tools()
    original = content.PAGES
    page = content.Page(
        len(original) + 1,
        tuple(content.Line(text, **options) for text, options in SPEC_LINES),
    )
    content.PAGES = tuple(original) + (page,)
    try:
        pdf = document.build_baseline(build_ar_corpus.load_font())
    finally:
        content.PAGES = original
    return bundle.build_bundle(bundle.make_files(pdf, STEM)).data


def _build_fixtures_module():
    path = RECORDINGS / "build_fixtures.py"
    spec = importlib.util.spec_from_file_location("journey_build_fixtures", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request_key(pdf_path: Path) -> tuple[str, object]:
    """The checksum the recorded adapter looks the reply up by, and the request itself."""
    module = _build_fixtures_module()
    from auditmanager.analysis.text.adapter import build_request
    from auditmanager.analysis.text.profile import AR_TEXT_PROFILE
    from auditmanager.analysis.text.textlayer import load_text_layer

    module.CORPUS_PDF = pdf_path
    request = build_request(
        model_id=module.MODEL_ID,
        bundle=AR_TEXT_PROFILE.prompt_bundle,
        text_layer=load_text_layer(module.build_text_layer_document()),
    )
    return request.request_sha256, request


def recording_for(bundle_bytes: bytes) -> tuple[str, dict]:
    module = _build_fixtures_module()
    from auditmanager.analysis.text.recorded import recording_document

    with tempfile.TemporaryDirectory(prefix="journey-spec-") as scratch:
        pdf_path = Path(scratch) / f"{STEM}.pdf"
        bundle_path = Path(scratch) / f"{STEM}.zip"
        bundle_path.write_bytes(bundle_bytes)
        with zipfile.ZipFile(bundle_path) as archive:
            pdf_path.write_bytes(archive.read(f"{STEM}.pdf"))
        # The control: the same code on the baseline must reproduce the baseline's checksum.
        control, _ = request_key(REPO_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf")
        if control != BASELINE_KEY:
            raise SystemExit(
                f"the control failed: the baseline's request checksum is {control}, not "
                f"{BASELINE_KEY}. The prompt or the text-layer code moved; the baseline's own "
                "recording is stale too, and this tool would file a reply under a wrong key."
            )
        key, request = request_key(pdf_path)
    document = recording_document(
        request=request,
        output_text=module._payload(module.OBSERVATIONS_COMPLETE),
        stop_reason="end_turn",
        input_tokens=2300,
        output_tokens=940,
        latency_ms=12100,
        note=(
            "AR baseline reply for the journey's specification bundle: the baseline's eight "
            "pages unchanged plus one specification page that raises no finding. Synthetic, "
            "authored; no model produced it. Written by "
            "tests/e2e/pc01/journey/build_specification_bundle.py --install-recording."
        ),
    )
    return key, document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="verify the committed bundle, write nothing")
    parser.add_argument("--install-recording", action="store_true",
                        help="write the recording this bundle's run needs into the lane's worktree")
    args = parser.parse_args(argv)

    fresh = build_bundle()
    if args.check:
        if not BUNDLE_PATH.is_file():
            print(f"missing: {BUNDLE_PATH}", file=sys.stderr)
            return 1
        if BUNDLE_PATH.read_bytes() != fresh:
            print(f"{BUNDLE_PATH.name} differs from what this tool builds; rebuild it", file=sys.stderr)
            return 1
        key, _ = recording_for(fresh)
        print(f"specification bundle OK: {len(fresh)} bytes; request checksum {key}")
        return 0
    if args.install_recording:
        committed = BUNDLE_PATH.read_bytes() if BUNDLE_PATH.is_file() else fresh
        key, document = recording_for(committed)
        target = RECORDINGS / f"{key}.json"
        rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if target.exists():
            if target.read_text(encoding="utf-8") != rendered:
                print(f"{target} exists and differs; refusing to overwrite it", file=sys.stderr)
                return 1
            print(f"recording already installed: {target.relative_to(REPO_ROOT)}")
            return 0
        target.write_text(rendered, encoding="utf-8")
        print(f"wrote {target.relative_to(REPO_ROOT)} (untracked)")
        return 0
    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_PATH.write_bytes(fresh)
    print(f"wrote {BUNDLE_PATH.relative_to(REPO_ROOT)} ({len(fresh)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
