#!/usr/bin/env python3
"""Check that no programme record presents a stale account of itself as current.

Run from the repository root:

    .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py

    # and, to run the same sweep against any historical tree, without a checkout:
    .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py --rev 5b70ee4

    # and, to prove the detectors can fire and that a label excuses only its own unit:
    .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py --selftest

Two axes, because CP-00 acceptance has failed on both.

**Axis one -- superseded evidence presented as current.** Exit 0 means every occurrence
of a superseded QA evidence commit in a tracked file is either committed acceptance
evidence -- which documents the defect it found, on purpose and dated -- or is labelled
as not-current **in the unit that contains the occurrence**.

**Axis two -- stale round accounting.** Rounds seven and eight failed on this and axis
one said nothing about it, which was recorded at the time as a limit rather than fixed:
"it covers one axis; it is not a general staleness check, and the round accounting it
says nothing about has failed twice on its own." Exit 0 now also means that every claim
about *which acceptance round is owed* and *how many acceptance rounds are in the
record* agrees with `artifacts/checkpoints/CP-00/manifest.json`, which is the record
that holds those two values as data rather than as prose.

Why the binding matters, and why this file exists at all. Rounds six, seven and eight of
CP-00 acceptance each failed on a stale state record, and each remediation declared an
exhaustive sweep without measuring one. The first automated form took any label within
three lines, which is proximity, not attribution: at one site a "superseded" attached to
854a682 licensed the very next line presenting e7f3989 as live, the exact defect it was
written to catch, and run against that tree it exited 0 while the commit message claimed
it would fail. So the unit here is structural, not a line window -- the enclosing JSON
object, the enclosing table row, or the enclosing sentence -- and the check is kept in
the checkpoint package so a reader can run it instead of taking a commit message's word.

Three properties of axis two are deliberate.

* **The truth is derived, never restated.** The owed round and the number of rounds come
  out of the manifest's `current_round` and `acceptance_rounds`. A sweep that carried its
  own copy of the round number would be one more record to go stale.
* **Nothing is skipped by path.** Round eight's blocking finding sat in the one state
  document the previous check was coded to skip. Every tracked file is swept except the
  dated primary acceptance reports, whose findings are quotations of the defect, and this
  file, which quotes what it searches for.
* **A record that says nothing cannot pass.** :data:`MUST_ACCOUNT` names the four records
  whose job is to state the round accounting; each has to carry both claims, and a
  missing claim is a failure. That list can only *add* failures -- the sweep itself is
  over every tracked file -- so it cannot hide a site the way a skip list can.
"""
from __future__ import annotations

import argparse
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
    # Independent review reports, for the same reason and one step further: their whole
    # purpose is to quote a stale claim verbatim next to the record that contradicts it.
    # Read as live prose, a table of findings reads as the findings themselves - this
    # sweep reported six of its own documented sites that way. Excluding review reports
    # cannot suppress a real defect, because a review report is not a record any consumer
    # reads for the current state; the manifest, the registry, the state document, the
    # wave plan and the task banners are, and none of them is excluded.
    "docs/program/reviews/",
)

#: This file quotes the SHAs and the claim shapes it searches for.
SELF = "artifacts/checkpoints/CP-00/check_state_records.py"

#: The record that holds the round accounting as data. Every claim on axis two is
#: compared against this file and against nothing else.
MANIFEST = "artifacts/checkpoints/CP-00/manifest.json"

#: The records whose job is to state the round accounting in prose or data. Each must
#: carry an owed-round claim and a round-count claim this check can read; a record that
#: states neither passes the sweep for the wrong reason. Adding a path here can only
#: produce a failure, never suppress one, which is why naming them is safe and naming a
#: skip list is not.
MUST_ACCOUNT = (
    MANIFEST,
    "artifacts/checkpoints/CP-00/acceptance.md",
    "docs/program/CURRENT_STATE.md",
    "docs/program/CHECKPOINT_REGISTRY.md",
)

#: A round whose entry carries one of these statuses can never be the owed round. A
#: round that has recorded a verdict is closed too, whatever its status says: the older
#: manifests in this history record rounds one and two with a verdict and no status at
#: all, and reading those as open would make every tree before round three compare
#: against a nonsense reference.
CLOSED_STATUSES = frozenset({"failed", "spent", "void"})

CARDINALS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
_NUMBER = r"(\d{1,2}|" + "|".join(CARDINALS) + r")"

#: **Owed-round claims.** Adjacency, not co-occurrence. "point both streams at round 6
#: with `status: \"owed\"`" is a description of a mechanism and names no owed round; a
#: marker-and-reference-in-the-same-unit rule reads it as one, which is proximity again.
#: Each pattern below is a claim shape whose capture group *is* the round being claimed.
OWED_CLAIMS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # "round eight is owed", "round 8 owed", "round nine remains owed"
        r"rounds?[\s-]" + _NUMBER + r"\s+(?:is\s+|remains\s+|still\s+)*owed\b",
        # "Order from here: freeze ... for round nine"
        r"order from here[^.]{0,160}?rounds?[\s-]" + _NUMBER,
        # the manifest's `remaining` field, and any prose that uses the word
        r"\bremaining\b\s*:[^.]{0,160}?rounds?[\s-]" + _NUMBER,
        # "waits for two acceptance-stream PASS on the round-eight candidate"
        r"wait(?:s|ing)?\s+(?:for|on)[^.]{0,160}?rounds?[\s-]" + _NUMBER,
        # "the next round is nine", "next acceptance round ten"
        r"next\s+(?:acceptance\s+)?round[\s-]?(?:is\s+)?" + _NUMBER,
    )
)

#: **Round-count claims.** A cardinal immediately before "round(s)", in a unit that is
#: talking about the acceptance record rather than about a quantity of rounds. Without
#: the scope marker the pattern also matches "the field went four rounds unchecked" and
#: "acceptance.md ... is three rounds stale", neither of which counts anything.
COUNT_CLAIM = re.compile(r"(?<![\w-])" + _NUMBER + r"\s+(?:acceptance\s+)?rounds?\b", re.IGNORECASE)
#: A count claim is a claim about the *whole* record. Without this the pattern also
#: matches "the same defect survived two acceptance rounds" and "two acceptance rounds
#: failed on the residue of these edits", which count a subset and are not stale when
#: the record grows. Both were raised by the first run of this axis and are the reason
#: the marker list is totality phrasing rather than the word "rounds".
COUNT_SCOPE = (
    "in the record", "were opened", "have been opened", "across all",
)

#: Tokens that mark an axis-two claim as a dated statement rather than a current one.
#: Deliberately narrower than :data:`LABELS`: "void" and "spent" are the vocabulary of
#: an accurate round enumeration, so accepting them here would let the registry row that
#: says "4-5 void ... round 8 owed" excuse its own stale half.
ROUND_HISTORY_LABELS = (
    "supersed", "superceded", "historical", "at the time", "point-in-time",
    "was true when written", "no longer current", "as recorded then",
)


def labelled(unit: str) -> bool:
    lowered = unit.lower()
    return any(label in lowered for label in LABELS)


def round_labelled(unit: str) -> bool:
    lowered = unit.lower()
    return any(label in lowered for label in ROUND_HISTORY_LABELS)


def _number(token: str) -> int:
    return int(token) if token.isdigit() else CARDINALS[token.lower()]


# ---------------------------------------------------------------------------
# Axis one: superseded evidence commits.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Axis two: round accounting.
# ---------------------------------------------------------------------------


def round_truth(manifest: object) -> tuple[dict, list[str]]:
    """The owed round and the number of rounds, read out of the manifest as data.

    Also reports the manifest's own internal inconsistencies, because a sweep that
    compares every document against a broken reference silently blesses the break: the
    tree that opened this task had `current_round: 9` on a round whose own entry said
    `void`, so no round was owed and every document that named one was wrong including
    the manifest.
    """
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return {}, [f"{MANIFEST} is not a JSON object; axis two cannot run"]
    rounds = manifest.get("acceptance_rounds")
    if not isinstance(rounds, list) or not rounds:
        return {}, [f"{MANIFEST}: acceptance_rounds is missing or empty; axis two cannot run"]
    statuses: dict[int, object] = {}
    closed: set[int] = set()
    for entry in rounds:
        if isinstance(entry, dict) and isinstance(entry.get("round"), int):
            statuses[entry["round"]] = entry.get("status")
            if entry.get("status") in CLOSED_STATUSES or entry.get("verdict") is not None:
                closed.add(entry["round"])
    current = manifest.get("current_round")
    openable = sorted(n for n in statuses if n not in closed)
    truth = {"opened": len(statuses), "current": current, "open_rounds": set(openable)}

    if not openable:
        problems.append(
            f"{MANIFEST}: no acceptance round is open -- every entry is failed, spent or "
            f"void -- so no document can truthfully name an owed round. current_round is "
            f"{current!r}. Open the next round in acceptance_rounds before reconciling "
            "any record against this manifest."
        )
    if current not in statuses:
        problems.append(
            f"{MANIFEST}: current_round is {current!r} and acceptance_rounds carries no "
            "entry for it"
        )
    elif current in closed:
        problems.append(
            f"{MANIFEST}: current_round is {current!r} and that round's own status is "
            f"{statuses[current]!r}. A closed round cannot be the current one; the record "
            "is one round behind itself."
        )
    for stream in ("manual_acceptance", "automated_acceptance"):
        record = manifest.get(stream)
        if isinstance(record, dict) and record.get("round") != current:
            problems.append(
                f"{MANIFEST}: {stream}.round is {record.get('round')!r} and current_round "
                f"is {current!r}"
            )
    return truth, problems


def _owed_problems(site: str, unit: str, truth: dict) -> list[str]:
    problems: list[str] = []
    for pattern in OWED_CLAIMS:
        for match in pattern.finditer(unit):
            named = _number(match.group(1))
            if named in truth["open_rounds"]:
                continue
            problems.append(
                f"{site}: names round {named} as the round that is owed or next, and "
                f"{MANIFEST} says the open round(s) are "
                f"{sorted(truth['open_rounds']) or 'none'}: {unit.strip()[:170]}"
            )
    return problems


def _count_problems(site: str, unit: str, truth: dict) -> list[str]:
    lowered = unit.lower()
    if not any(marker in lowered for marker in COUNT_SCOPE):
        return []
    problems: list[str] = []
    for match in COUNT_CLAIM.finditer(unit):
        named = _number(match.group(1))
        if named == truth["opened"]:
            continue
        problems.append(
            f"{site}: counts {named} acceptance rounds and {MANIFEST} carries "
            f"{truth['opened']} entries in acceptance_rounds: {unit.strip()[:170]}"
        )
    return problems


def _round_unit_problems(site: str, unit: str, truth: dict,
                         path: str | None = None) -> tuple[list[tuple[str, str]], set[str]]:
    """Both axis-two detectors over one structural unit, plus which claims it made.

    Findings carry their file separately from their message so the summary can group by
    path without parsing its own output -- an earlier form split the message on ":" and
    reported prose as a filename.
    """
    if round_labelled(unit):
        return [], set()
    owner = path if path is not None else site
    problems = [(owner, message) for message in _owed_problems(site, unit, truth)]
    made: set[str] = set()
    if any(pattern.search(unit) for pattern in OWED_CLAIMS):
        made.add("owed")
    counts = [(owner, message) for message in _count_problems(site, unit, truth)]
    lowered = unit.lower()
    if any(marker in lowered for marker in COUNT_SCOPE) and COUNT_CLAIM.search(unit):
        made.add("count")
    return problems + counts, made


def prose_units(text: str) -> list[tuple[int, str]]:
    """`(line number, unit)` for a Markdown or plain-text document.

    A table row is its own unit and a paragraph is its own unit, split into sentences.
    Flattening a whole document and splitting on sentence ends -- what axis one does,
    and what is right for a SHA, which never spans a row -- merges a table row with the
    rows around it whenever no full stop separates them, and the CP-00 registry row is
    exactly that shape. Attribution has to survive to the row, or the report names a
    file and leaves a reader to find the claim.
    """
    units: list[tuple[int, str]] = []
    paragraph: list[str] = []
    start = 0

    def flush() -> None:
        nonlocal paragraph, start
        if paragraph:
            flat = re.sub(r"\s+", " ", " ".join(paragraph)).strip()
            for sentence in re.split(r"(?<=[.!?])\s", flat):
                if sentence.strip():
                    units.append((start, sentence.strip()))
        paragraph = []

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("|"):
            flush()
            units.append((number, re.sub(r"\s+", " ", stripped)))
            continue
        if not stripped:
            flush()
            continue
        if not paragraph:
            start = number
        paragraph.append(stripped.lstrip("> "))
    flush()
    return units


def round_problems_json(path: str, document: object,
                        truth: dict) -> tuple[list[tuple[str, str]], set[str]]:
    """Walk the document; the unit is one sentence of one string value, named by its key
    trail, and a subtree that is structurally a dated record is not swept.

    A per-round entry (`round` plus `status`) and any object carrying `superseded_by`
    are the record's own history. They are the *source* of the truth this axis compares
    against, and a history entry describing the round it belongs to is not a claim about
    the present.
    """
    problems: list[tuple[str, str]] = []
    made: set[str] = set()

    def historical(node: dict) -> bool:
        return "superseded_by" in node or ("round" in node and "status" in node)

    def walk(node: object, trail: str) -> None:
        if isinstance(node, dict):
            if historical(node):
                return
            for key, value in node.items():
                walk(value, f"{trail}.{key}")
            return
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{trail}[{index}]")
            return
        if isinstance(node, str):
            # The unit is the whole string value under its key trail, not a sentence of
            # it. The key is the structural container, so a marker the key supplies --
            # `remaining` -- belongs to the value as a whole; prefixing the trail to each
            # sentence separately made the key excuse or accuse sentences it does not
            # govern, which is the proximity defect one level down.
            unit = f"{trail}: " + re.sub(r"\s+", " ", node).strip()
            found, claims = _round_unit_problems(f"{path}{trail}", unit, truth, path)
            problems.extend(found)
            made.update(claims)

    walk(document, "")
    return problems, made


def round_problems_text(path: str, text: str,
                        truth: dict) -> tuple[list[tuple[str, str]], set[str]]:
    problems: list[tuple[str, str]] = []
    made: set[str] = set()
    for line, unit in prose_units(text):
        found, claims = _round_unit_problems(f"{path}:{line}", unit, truth, path)
        problems += found
        made |= claims
    return problems, made


# ---------------------------------------------------------------------------
# Tree access. `--rev` reads a commit's objects, so the historical measurements this
# check's record claims can be reproduced without a checkout, on a dirty working tree,
# and by a reader who may not create branches here.
# ---------------------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, check=True)


def tree(rev: str | None):
    if rev is None:
        listing = _run("git", "ls-files").stdout.decode("utf-8")

        def read(path: str) -> str | None:
            try:
                with open(path, encoding="utf-8") as handle:
                    return handle.read()
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                return None
    else:
        listing = _run("git", "ls-tree", "-r", "--name-only", rev).stdout.decode("utf-8")

        def read(path: str) -> str | None:
            blob = subprocess.run(
                ["git", "--no-replace-objects", "show", f"{rev}:{path}"],
                capture_output=True,
            )
            if blob.returncode != 0:
                return None
            try:
                return blob.stdout.decode("utf-8")
            except UnicodeDecodeError:
                return None

    return sorted(path for path in listing.split("\n") if path), read


def selftest() -> int:
    """Prove each detector fires, and that a label excuses only the unit it is in.

    A guard nobody has made fail is a guard nobody has tested; that sentence is the
    reason this checkpoint has re-run nine acceptance rounds.
    """
    truth = {"opened": 10, "current": 10, "open_rounds": {10}}
    cases = (
        ("owed fires on a stale round", "Round eight is owed.", True),
        ("owed passes on the open round", "Round ten is owed.", False),
        ("owed fires on an order-from-here", "Order from here: freeze the digest for round nine.", True),
        ("owed ignores a mechanism description",
         "point both streams at round 6 with `status: \"owed\"` and report_path null", False),
        ("count fires on a stale total", "Eight rounds are now in the record.", True),
        ("count passes on the true total", "Ten rounds are now in the record.", False),
        ("count ignores a quantity", "the field went four rounds unchecked", False),
        ("count ignores review rounds", "accepted after twelve review rounds", False),
        ("a history label excuses its own unit",
         "Historically, round eight is owed.", False),
        ("a history label does not reach the next unit",
         "Round eight is owed.", True),
    )
    failures = []
    for name, unit, should_fire in cases:
        found, _ = _round_unit_problems("selftest", unit, truth)
        if bool(found) != should_fire:
            failures.append(f"{name}: expected fire={should_fire}, got {found}")
    row = prose_units("| CP-00 | frozen; 4-5 void; round 8 owed |\n\nA sentence about round 10.\n")
    if len(row) != 2 or "round 8 owed" not in row[0][1]:
        failures.append(f"a table row must be its own unit; got {row}")
    print(f"selftest cases: {len(cases) + 1}, failures: {len(failures)}")
    for failure in failures:
        print("  !", failure)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rev", help="sweep this commit's tree instead of the working tree")
    parser.add_argument("--selftest", action="store_true",
                        help="prove the axis-two detectors can fire, and exit")
    arguments = parser.parse_args(argv)
    if arguments.selftest:
        return selftest()

    paths, read = tree(arguments.rev)
    where = arguments.rev or "the working tree"

    manifest_text = read(MANIFEST)
    truth: dict = {}
    round_problems: list[tuple[str, str]] = []
    if manifest_text is None:
        round_problems.append((MANIFEST, f"{MANIFEST} is unreadable at {where}; axis two "
                                         "cannot run"))
    else:
        try:
            truth, manifest_problems = round_truth(json.loads(manifest_text))
        except json.JSONDecodeError as error:
            truth, manifest_problems = {}, [f"{MANIFEST} does not parse: {error}"]
        round_problems += [(MANIFEST, message) for message in manifest_problems]

    problems: list[str] = []
    live_named: list[str] = []
    claims: dict[str, set[str]] = {}
    for path in paths:
        if path.startswith(EVIDENCE_PREFIXES) or path == SELF:
            continue
        text = read(path)
        if text is None:
            continue
        if LIVE in text:
            live_named.append(path)
        document = None
        if path.endswith(".json"):
            try:
                document = json.loads(text)
            except json.JSONDecodeError:
                document = None
        if document is not None:
            problems += json_problems(path, document)
        else:
            problems += text_problems(path, text)
        if truth:
            if document is not None:
                found, made = round_problems_json(path, document, truth)
            else:
                found, made = round_problems_text(path, text, truth)
            round_problems += found
            claims[path] = made

    if truth:
        for path in MUST_ACCOUNT:
            made = claims.get(path)
            if made is None:
                round_problems.append((
                    path,
                    f"{path} is missing at {where}; it is one of the records that must "
                    "state the round accounting",
                ))
                continue
            for claim, description in (
                ("owed", "which acceptance round is owed"),
                ("count", "how many acceptance rounds are in the record"),
            ):
                if claim not in made:
                    round_problems.append((
                        path,
                        f"{path} states nothing this check can read about {description}. "
                        "A record that says nothing passes the sweep without being "
                        "current; state it so it can be checked.",
                    ))

    print(f"tree swept: {where}, {len(paths)} tracked paths")
    print(f"\naxis one - superseded commits presented as current: {len(problems)}")
    for problem in problems:
        print("  !", problem)
    if truth:
        print(
            f"\naxis two - stale round accounting: {len(round_problems)} "
            f"(manifest says current_round={truth.get('current')!r}, "
            f"{truth.get('opened')} rounds opened, "
            f"open round(s) {sorted(truth.get('open_rounds', ())) or 'none'})"
        )
    else:
        print(f"\naxis two - stale round accounting: {len(round_problems)} (truth unavailable)")
    for _path, problem in round_problems:
        print("  !", problem)

    owned = sorted({path for path, _ in round_problems})
    if owned:
        print("\naxis two names these files:")
        for path in owned:
            print("   ", path)
    print(f"\nthe live evidence commit {LIVE} is named in {len(live_named)} tracked files:")
    for path in sorted(live_named):
        print("   ", path)
    return 1 if problems or round_problems else 0


if __name__ == "__main__":
    sys.exit(main())
