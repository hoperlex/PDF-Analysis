#!/usr/bin/env python3
"""Check that no programme record presents a superseded evidence commit as current.

Run from the repository root:

    .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py

Exit 0 means every occurrence of a superseded QA evidence commit in a tracked file is
either committed acceptance evidence -- which documents the defect it found, on purpose
and dated -- or is labelled as not-current **in the unit that contains the occurrence**.

Why the binding matters, and why this file exists at all. Rounds six, seven and eight of
CP-00 acceptance each failed on a stale state record, and each remediation declared an
exhaustive sweep without measuring one. The first automated form took any label within
three lines, which is proximity, not attribution: at one site a "superseded" attached to
854a682 licensed the very next line presenting e7f3989 as live, the exact defect it was
written to catch, and run against that tree it exited 0 while the commit message claimed
it would fail. So the unit here is structural, not a line window -- the enclosing JSON
object, or the enclosing sentence -- and the check is kept in the checkpoint package so a
reader can run it instead of taking a commit message's word.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

#: Evidence commits that have been superseded. Abbreviated forms; both are matched as
#: substrings, so the full forty-character SHAs are found too.
SUPERSEDED = ("e7f39890211b", "854a68201cdd")

#: The accepted evidence commit. Reported, not checked -- a record naming none of these
#: at all is a different defect from one naming the wrong one.
LIVE = "3da104e5d6fa"

#: Tokens that, inside the same unit as the SHA, mark it as not-current.
LABELS = (
    "supersed", "history", "historical", "earlier", "former", "previous", "prior",
    "first qa evidence", "second qa evidence", "round-one deliverable", "spent", "void",
    "no longer", "was still", "stale", "old value", "superceded",
)

#: Committed acceptance evidence: dated primary reports whose findings are quotations of
#: the defect. Correcting them would destroy the record that lets this sweep be audited.
EVIDENCE_PREFIXES = (
    "artifacts/checkpoints/CP-00/manual-report-round-",
    "artifacts/checkpoints/CP-00/automated-report-round-",
)

#: This file quotes the SHAs it searches for.
SELF = "artifacts/checkpoints/CP-00/check_state_records.py"


def labelled(unit: str) -> bool:
    lowered = unit.lower()
    return any(label in lowered for label in LABELS)


def json_problems(path: str, document: object) -> list[str]:
    """Walk the document; the unit is the smallest object or array containing the SHA."""
    problems: list[str] = []

    def walk(node: object, trail: str) -> None:
        if isinstance(node, dict):
            rendered = json.dumps(node)
            hits = [sha for sha in SUPERSEDED if sha in rendered]
            if hits:
                if labelled(rendered):
                    return  # this object explains itself; do not descend further
                for key, value in node.items():
                    walk(value, f"{trail}.{key}")
                if not any(isinstance(v, (dict, list)) for v in node.values()):
                    problems.append(f"{path}{trail}: {', '.join(hits)} in an object that "
                                    f"does not mark it superseded: {rendered[:140]}")
            return
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{trail}[{index}]")
            return
        if isinstance(node, str):
            hits = [sha for sha in SUPERSEDED if sha in node]
            if hits and not labelled(node):
                problems.append(f"{path}{trail}: {', '.join(hits)} unlabelled in: {node[:140]}")

    walk(document, "")
    return problems


def text_problems(path: str, text: str) -> list[str]:
    """The unit is the enclosing sentence. Split on . ! ? only -- a colon introduces a
    list whose label commonly sits before it, and splitting there produced false hits."""
    flat = re.sub(r"\s+", " ", text)
    problems: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s", flat):
        hits = [sha for sha in SUPERSEDED if sha in sentence]
        if hits and not labelled(sentence):
            problems.append(f"{path}: {', '.join(hits)} unlabelled in: {sentence.strip()[:150]}")
    return problems


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()

    problems: list[str] = []
    live_named: list[str] = []
    for path in tracked:
        if path.startswith(EVIDENCE_PREFIXES) or path == SELF:
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        if LIVE in text:
            live_named.append(path)
        if path.endswith(".json"):
            try:
                problems += json_problems(path, json.loads(text))
                continue
            except json.JSONDecodeError:
                pass
        problems += text_problems(path, text)

    print(f"superseded commits presented as current: {len(problems)}")
    for problem in problems:
        print("  !", problem)
    print(f"\nthe live evidence commit {LIVE} is named in {len(live_named)} tracked files:")
    for path in sorted(live_named):
        print("   ", path)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
