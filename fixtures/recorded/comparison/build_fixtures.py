"""Rebuild the synthetic recording of the comparison summary (`COMPARE-PERSISTED-SUMMARY-01`, B2).

Run with ``PYTHONPATH=src``. ``--check`` writes nothing and exits non-zero when the committed file is
stale or when a file here is not a recording of the request the builder makes.

**Every file here is synthetic.** The reply was authored by hand to prove that the command replays a
recording keyed by the digest of the exact request: no model produced it and no provider call was made.
It is not field evidence for anything, and every statement opens with «Синтетический ответ, не
результат вызова модели» so a summary stored from it cannot pass for a model's.

The request is built exactly as the command builds it -- two published versions, one approved sheet
pair, the raw differences of ``raw_text`` sealed by ``raw_evidence_seal``, the bounded input of
``summary_input``, the prompt of ``summary_prompt`` -- over a pair of four-page versions whose page 2 is
redrawn (a dimension changes from 30 to 35) and whose other pages are the same. The identities are
fixed constants, so the request, its digest and the file name are the same on every run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auditmanager.comparison.approved_evidence import raw_artifact
from auditmanager.comparison.summary_input import prepare_version_summary_input
from auditmanager.comparison.summary_model import recording_document
from auditmanager.comparison.summary_prompt import SummaryRequest, build_request
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

HERE = Path(__file__).resolve().parent
PROJECT = "prj_01M2545JSD15ETSNNV904XJ001"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XJ001"
V1 = "ver_01M2545JSD15ETSNNV904XJ001"
V2 = "ver_01M2545JSD15ETSNNV904XJ002"
COMPARISON = "cmp_01M2545JSD15ETSNNV904XJ001"
LINK = "sln_01M2545JSD15ETSNNV904XJ001"
MARKER = "Синтетический ответ, не результат вызова модели"

SOURCE_PAGES = {
    1: "ОБЩИЕ ДАННЫЕ\nЛист 1 изм. 1\n",
    2: "ПЛАН ЭТАЖА\nЛист 2 изм. 1\nОси А-Б, 1-4\nДлина стены 30\nВысота проёма 21\n",
    3: "РАЗРЕЗ 1-1\nЛист 3 изм. 1\n",
    4: "СПЕЦИФИКАЦИЯ\nЛист 4 изм. 1\n",
}
TARGET_PAGES = {
    1: "ОБЩИЕ ДАННЫЕ\nЛист 1 изм. 1\n",
    2: "ПЛАН ЭТАЖА\nЛист 2 изм. 2\nОси А-Б, 1-4\nДлина стены 35\nВысота проёма 21\n",
    3: "РАЗРЕЗ 1-1\nЛист 3 изм. 1\n",
    4: "СПЕЦИФИКАЦИЯ\nЛист 4 изм. 1\n",
}


def synthetic_request() -> SummaryRequest:
    """The request the command makes over the synthetic pair."""
    def facts(uid: str, ordinal: int, sha: str) -> VersionFacts:
        return VersionFacts(uid, DOCUMENT, PROJECT, ordinal, sha, 4096, 4, "application/pdf")

    pair = OrderedVersionPair(PROJECT, DOCUMENT, facts(V1, 1, "a" * 64), facts(V2, 2, "b" * 64))
    diffs, seal = raw_artifact(
        pair=pair, comparison_id=COMPARISON, link_revision=1, links=[(LINK, 2, 2)],
        source_pages=SOURCE_PAGES, target_pages=TARGET_PAGES,
    )
    return build_request(prepare_version_summary_input(version_pair=pair, raw_diffs=diffs, raw_seal=seal))


def synthetic_reply(request: SummaryRequest) -> str:
    ids = list(request.hunk_ids)
    assert len(ids) == 2, ids  # the revision mark and the wall length
    return json.dumps({"statements": [
        {"text": f"{MARKER}: на листе 2 изменена отметка изменения (с 1 на 2).", "hunk_ids": [ids[0]]},
        {"text": f"{MARKER}: на листе 2 длина стены изменена с 30 на 35.", "hunk_ids": [ids[1]]},
    ]}, ensure_ascii=False)


def built() -> dict[str, str]:
    request = synthetic_request()
    document = recording_document(
        request=request, output_text=synthetic_reply(request), input_tokens=310, output_tokens=96,
        note="Hand-authored reply for the synthetic two-version pair of fixtures/recorded/comparison/build_fixtures.py.",
        origin={"kind": "synthetic", "task_id": "COMPARE-PERSISTED-SUMMARY-01",
                "statement": "Authored by hand; no model produced it and no provider call was made."},
    )
    return {f"{request.request_sha256}.json": json.dumps(document, ensure_ascii=False, indent=2) + "\n"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 on drift")
    args = parser.parse_args(argv)
    wanted = built()
    present = {path.name: path.read_text(encoding="utf-8") for path in HERE.glob("*.json")}
    problems = [f"missing or stale: {name}" for name, body in wanted.items() if present.get(name) != body]
    problems += [f"not a recording of the synthetic request: {name}" for name in present if name not in wanted]
    if args.check:
        for line in problems:
            print(line)
        return 1 if problems else 0
    for name in present:
        if name not in wanted:
            (HERE / name).unlink()
    for name, body in wanted.items():
        (HERE / name).write_text(body, encoding="utf-8")
    print("wrote", ", ".join(sorted(wanted)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
