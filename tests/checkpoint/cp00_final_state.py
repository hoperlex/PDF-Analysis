#!/usr/bin/env python3
"""The CP-00 final-state contour: what is true of a *terminal* checkpoint.

Run from the repository root::

    .venv/bootstrap/bin/python tests/checkpoint/cp00_final_state.py

Exit 0 means the tree's records describe the terminal state the tree is actually in.
Exit 1 names every place they do not, with the task that owns the disposition.

Why this module exists
----------------------
``artifacts/checkpoints/CP-00/check_state_records.py`` models the acceptance record as
"which round is owed". That model is correct while a round is open and *meaningless* once
the checkpoint is ratified: on the ratified tree it reports fourteen findings, and every
one of them is a true description of a ratified checkpoint rather than a defect. At the
same moment the 324-test contract suite passed without noticing that ``W0-INT-01``'s own
ratification assertion fails. A checkpoint therefore shipped with **no contour able to
tell a ratified checkpoint from an open round**, and that is what this module is.

The existing sweep is not replaced and not edited. Its round accounting is right for an
open round and is kept as history; this contour is additional.

The five checks
---------------
Each is a named function returning :class:`Finding` objects, each check has a positive
case, a negative case and a recorded mutation in
``tests/checkpoint/test_cp00_final_state_contour.py``, and each finding names the task
that owns the disposition rather than making one.

``terminal_state``
    A tree is exactly one of :data:`OPEN_ROUND`, :data:`CLOSED_ACCEPTED_ROUND`,
    :data:`TERMINAL_RATIFIED`. The state is *derived* from the manifest's data, never
    restated here. **A check that goes quiet at publication is worse than the one it
    replaces**, so the terminal state carries its own staleness obligations: the accepted
    round must be the last one, its two reports must bind to the same tree, its digests
    must be the ones the manifest publishes, and every checkpoint row in every live
    record must name that round and that state.

``live_vs_historical``
    A dated primary report may state a superseded fact; a live record may not. The
    distinction is **structural**: a record is historical when it declares a subject
    commit *in its own bytes*, or when the manifest binds it to an acceptance round as
    data. Nothing is excluded by path. And a historical record is **verified against the
    tree it names**, not skipped -- the exemption is turned into an obligation. The
    previous sweep's path skip list is the narrowing its own acceptance record warned
    against; see :data:`LIMITATIONS` for what this rule still does not reach.

``tag_integrity``
    The tag the records name exists, is an annotated tag object, peels to a commit, has
    not moved relative to the digest the records publish for it, and its **message** --
    which is bound to its own commit by construction -- states nothing false of that
    commit.

``file_and_hash_accounting``
    Every file the checkpoint claims exists; every aggregate hash enumerates the members
    it rolls over, with each member's own hash; and no two live bundle records give the
    same top-level field two different values.

``cross_gate_agreement``
    ``W0-INT-01``'s required-test command asserts on
    ``docs/architecture/CP00_ARCHITECTURE_REVIEW.json``. Those assertions are extracted
    from the task file and evaluated against the review. **This contour does not choose
    the value**: it fails while the two gates disagree and names both sides. The
    disposition is ``W0-INT-02``'s.

Structure over convention
-------------------------
Every Git subprocess goes through :func:`_git`, which builds its environment from an
allowlist and never reads :data:`os.environ`. ``E-06`` in
``artifacts/checkpoints/CP-00/known-risks.md`` is the measured reason: Git executes
configuration it reads from the ambient environment, and a seeded victim repository lost
its whole index under a hostile ``HOME`` while the suite reported success.
:class:`SpawnChokepointTests` keeps this the only door.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Subprocess environment. Never read os.environ; see E-06.
# ---------------------------------------------------------------------------

#: The only directories a program may be found in. There is deliberately no fall back
#: to the caller's PATH: "I could not find git in the system directories" is a failure a
#: human can read, and "I ran the git I was handed" is not a failure at all until later.
TRUSTED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

#: Every name the constructed environment may carry. The environment is built from this
#: list rather than filtered out of the inherited one: a denylist is correct only for the
#: names its author knew.
ENV_ALLOWLIST = (
    "PATH", "HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
    "GIT_CONFIG_NOSYSTEM", "GIT_TERMINAL_PROMPT", "LC_ALL", "LANG", "TZ",
)

_NEUTRAL_HOME: Path | None = None
_PROGRAM_CACHE: dict[str, str] = {}


def _program(name: str) -> str:
    resolved = _PROGRAM_CACHE.get(name)
    if resolved is None:
        resolved = shutil.which(name, path=TRUSTED_PATH)
        if resolved is None:
            raise AssertionError(
                f"{name!r} is not on the trusted path {TRUSTED_PATH!r}. This module "
                "refuses to fall back to the caller's PATH, because that is the "
                "shadowing vector it is closing."
            )
        _PROGRAM_CACHE[name] = resolved
    return resolved


def _neutral_home() -> Path:
    """A real, existing, empty directory every subprocess sees as ``HOME``.

    It has to exist: a ``HOME`` that does not makes some programs fall back to the passwd
    entry, which is the home this is supposed to replace.
    """
    global _NEUTRAL_HOME
    if _NEUTRAL_HOME is None or not _NEUTRAL_HOME.is_dir():
        home = Path(tempfile.mkdtemp(prefix="w0-qa-04-neutral-home-"))
        (home / "xdg").mkdir()
        atexit.register(shutil.rmtree, home, True)
        _NEUTRAL_HOME = home
    return _NEUTRAL_HOME


def _allowlisted_env() -> dict[str, str]:
    """The environment for every subprocess this module spawns, built from nothing."""
    home = _neutral_home()
    env = {
        "PATH": TRUSTED_PATH,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
    }
    if set(env) != set(ENV_ALLOWLIST):
        raise AssertionError(
            "the constructed environment and the allowlist that justifies it have "
            f"drifted: {sorted(set(env) ^ set(ENV_ALLOWLIST))}"
        )
    return env


def _git(*arguments: str, root: Path | None = None) -> subprocess.CompletedProcess:
    """**The one place this module spawns Git.** Reading only; nothing here writes."""
    prefix = () if root is None else ("-C", str(root))
    return subprocess.run(
        [_program("git"), *prefix, *arguments],
        capture_output=True,
        check=False,
        env=_allowlisted_env(),
    )


# ---------------------------------------------------------------------------
# Records the contour reads. Paths appear here because they are the *checkpoint's own*
# records, and every one of them is read for data rather than skipped: adding a name
# here can only add findings, never suppress one.
# ---------------------------------------------------------------------------

CHECKPOINT = "CP-00"
BUNDLE = f"artifacts/checkpoints/{CHECKPOINT}/"
MANIFEST = BUNDLE + "manifest.json"
CONTRACT_MANIFEST = BUNDLE + "contract-manifest.yaml"
BUILD_INFO = BUNDLE + "build-info.json"
ARCHITECTURE_REVIEW = "docs/architecture/CP00_ARCHITECTURE_REVIEW.json"

#: The three terminal states. Exactly one is true of a tree that has a manifest.
OPEN_ROUND = "open-round"
CLOSED_ACCEPTED_ROUND = "closed-accepted-round"
TERMINAL_RATIFIED = "terminal-ratified"
UNCLASSIFIED = "unclassified"
STATES = (OPEN_ROUND, CLOSED_ACCEPTED_ROUND, TERMINAL_RATIFIED)

#: A round carrying one of these statuses is closed. A round that has recorded a verdict
#: is closed too, whatever its status says.
CLOSED_STATUSES = frozenset({"failed", "spent", "void"})
#: The one status that closes a round *and* accepts it.
ACCEPTED_STATUS = "accepted"

CARDINALS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

#: How far into a record the contour looks for a subject declaration. A subject belongs
#: to a document's header; a commit named in the middle of a body is a mention, and
#: reading a mention as a binding is the proximity defect one level up.
HEADER_LINES = 26

#: **A subject declaration.** The shapes an evidence record uses to say, in its own
#: bytes, which tree its claims are about. This is the structural half of live-vs-
#: historical: a record that declares a subject is judged against *that* tree.
SUBJECT_DECLARATION = re.compile(
    r"^\s*[>|*\s]*`?(?:candidate_commit|subject_commit|frozen_at_commit|"
    r"candidate[ _]frozen[ _]at|subject[ _]commit)`?\s*[:\s]+`?([0-9a-f]{7,40})`?",
    re.IGNORECASE | re.MULTILINE,
)

#: A repository path shaped like an executable test artifact. A checkpoint that names a
#: test module as part of its blocking contour has to have it. The prefix narrows the
#: *claim shape*, not the files swept -- every live record is read -- so it can only add
#: findings, which is the same reason ``MUST_ACCOUNT`` is safe in the sweep this
#: contour sits beside.
CLAIMED_TEST_ARTIFACT = re.compile(r"`(tests/[A-Za-z0-9_./-]+\.py)`")

#: A string value that is shaped like a repository path.
PATH_SHAPED = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*\.[A-Za-z0-9]+$")

#: Everything this contour is known **not** to cover. Recorded rather than asserted away.
LIMITATIONS = (
    "A record that declares no subject commit and is nonetheless historical is read as "
    "live. The rule is a declaration rule, so an undeclared dated report is a finding "
    "against the record, not a silent pass -- but the contour cannot date it for itself.",
    "Historical verification reaches only the claims this contour can machine-check "
    "against a named tree: the tracked-path count and the reviewed-family digest. Prose "
    "findings inside a dated report are not re-derived.",
    "Round accounting in prose is left to check_state_records.py. This contour reads "
    "round claims only where they sit in a structural unit it can attribute: a typed "
    "manifest field, or a checkpoint table row whose first cell is the checkpoint id.",
    "The tag message is checked for the hash and byte-identity claims it makes in a "
    "machine-readable shape. Its test-count and stream claims are prose and are not "
    "re-measured here.",
    "'The tag has not moved' is checked against the digest the manifest publishes, not "
    "against a recorded target commit. A commit cannot name its own hash, and the tag "
    "sits on the commit that carries the manifest, so a recorded-target field is not "
    "available to this checkpoint by construction.",
    "parse_block_yaml covers the block-map subset the contract manifest actually uses. "
    "No YAML library exists in the hash-locked bootstrap environment and adding one "
    "would touch a frozen lock file. Sequences are dropped rather than misread, and an "
    "aggregate whose members cannot be enumerated fails, so the omission cannot pass "
    "silently as coverage.",
    "The mutation evidence proves the check *classes*, not every site inside them. A "
    "site-level narrowing within a check that is already red is invisible to it: "
    "measured, dropping one real path from claimed_paths takes the accounting findings "
    "from nine to seven while both suites keep their exact status, 46 tests and 0 red. "
    "Reading a narrowing of this contour is a review obligation, not something the "
    "contour can measure about itself.",
)


# ---------------------------------------------------------------------------
# Findings and tree access.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One thing that is not true of this tree. ``owner`` names who disposes of it."""

    check: str
    site: str
    message: str
    owner: str = "W0-INT-02"

    def __str__(self) -> str:
        return f"[{self.check}] {self.site}: {self.message}  (owner: {self.owner})"


@dataclass
class Verdict:
    state: str
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def by_check(self, check: str) -> list[Finding]:
        return [f for f in self.findings if f.check == check]


class Tree:
    """A read-only view of a tree, and of other revisions reachable from it.

    Two implementations exist so that every check can be exercised on a tree built for
    the purpose: :class:`RepositoryTree` over a real checkout, and :class:`MappingTree`
    over a dict. No check reads the filesystem or spawns Git for itself.
    """

    def paths(self) -> tuple[str, ...]:
        raise NotImplementedError

    def read(self, path: str) -> str | None:
        raise NotImplementedError

    def paths_at(self, rev: str) -> tuple[str, ...] | None:
        raise NotImplementedError

    def blob_at(self, rev: str, path: str) -> bytes | None:
        raise NotImplementedError

    def blob(self, path: str) -> bytes | None:
        raise NotImplementedError

    # -- shared helpers ----------------------------------------------------
    def json(self, path: str) -> object | None:
        text = self.read(path)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def exists(self, path: str) -> bool:
        return path in set(self.paths())


class RepositoryTree(Tree):
    """The working tree of a real checkout, read through ``git ls-files``."""

    def __init__(self, root: Path):
        self.root = Path(root)
        listing = _git("ls-files", "-z", root=self.root)
        if listing.returncode != 0:
            raise AssertionError(
                f"git ls-files failed in {self.root}: "
                f"{listing.stderr.decode('utf-8', 'replace')[:200]}"
            )
        self._paths = tuple(
            sorted(p for p in listing.stdout.decode("utf-8", "replace").split("\0") if p)
        )

    def paths(self) -> tuple[str, ...]:
        return self._paths

    def blob(self, path: str) -> bytes | None:
        try:
            return (self.root / path).read_bytes()
        except (OSError, ValueError):
            return None

    def read(self, path: str) -> str | None:
        raw = self.blob(path)
        if raw is None:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def paths_at(self, rev: str) -> tuple[str, ...] | None:
        listing = _git("ls-tree", "-r", "-z", "--name-only", rev, root=self.root)
        if listing.returncode != 0:
            return None
        return tuple(
            sorted(p for p in listing.stdout.decode("utf-8", "replace").split("\0") if p)
        )

    def blob_at(self, rev: str, path: str) -> bytes | None:
        blob = _git("--no-replace-objects", "show", f"{rev}:{path}", root=self.root)
        return blob.stdout if blob.returncode == 0 else None


class MappingTree(Tree):
    """A tree built for a test. ``revisions`` maps a revision name to its own mapping."""

    def __init__(
        self,
        files: dict[str, str | bytes],
        revisions: dict[str, dict[str, str | bytes]] | None = None,
    ):
        self._files = dict(files)
        self._revisions = {k: dict(v) for k, v in (revisions or {}).items()}

    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._files))

    @staticmethod
    def _as_bytes(value: str | bytes) -> bytes:
        return value.encode("utf-8") if isinstance(value, str) else value

    def blob(self, path: str) -> bytes | None:
        value = self._files.get(path)
        return None if value is None else self._as_bytes(value)

    def read(self, path: str) -> str | None:
        raw = self.blob(path)
        if raw is None:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def paths_at(self, rev: str) -> tuple[str, ...] | None:
        revision = self._revisions.get(rev)
        return None if revision is None else tuple(sorted(revision))

    def blob_at(self, rev: str, path: str) -> bytes | None:
        revision = self._revisions.get(rev)
        if revision is None:
            return None
        value = revision.get(path)
        return None if value is None else self._as_bytes(value)


@dataclass(frozen=True)
class TagFacts:
    """What Git says about the checkpoint tag. Gathered once, injected into the check."""

    name: str
    exists: bool = False
    annotated: bool = False
    commit: str | None = None
    message: str = ""

    @classmethod
    def gather(cls, root: Path, name: str) -> "TagFacts":
        kind = _git("cat-file", "-t", name, root=root)
        if kind.returncode != 0:
            return cls(name=name, exists=False)
        annotated = kind.stdout.decode("utf-8", "replace").strip() == "tag"
        peeled = _git("rev-list", "-n1", name, root=root)
        commit = peeled.stdout.decode("utf-8", "replace").strip() or None
        message = ""
        if annotated:
            body = _git("cat-file", "-p", name, root=root)
            if body.returncode == 0:
                raw = body.stdout.decode("utf-8", "replace")
                # An annotated tag object is a header block, a blank line, then the
                # message. The message is the unit bound to this commit; the headers are
                # not claims.
                message = raw.split("\n\n", 1)[1] if "\n\n" in raw else ""
        return cls(
            name=name, exists=True, annotated=annotated, commit=commit, message=message
        )


# ---------------------------------------------------------------------------
# Small parsers. No PyYAML is available in the bootstrap environment, and adding one
# would touch a frozen lock file, so the contract manifest is read by a parser whose
# scope is exactly the shape that file has: two-space indented block maps of scalars.
# ---------------------------------------------------------------------------


def parse_block_yaml(text: str) -> dict:
    """Parse the block-map subset of YAML the checkpoint's contract manifest uses.

    Returns nested dicts of strings. Comments, blank lines and anything that is not a
    ``key:`` or ``key: value`` line are ignored. Sequences are not supported and the
    contract manifest has none; a sequence would be dropped rather than misread, and
    :func:`aggregate_problems` fails on a family whose members it cannot enumerate, so
    the omission cannot pass silently as coverage.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        match = re.match(r"^([A-Za-z0-9_.\-/]+):\s*(.*)$", line.strip())
        if not match:
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, root)]
        parent = stack[-1][1]
        key, value = match.group(1), match.group(2).strip()
        if value:
            parent[key] = value
        else:
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def top_level_scalars(document: object) -> dict[str, str]:
    """A record's own assertions: its top-level scalar fields, as strings.

    Nested fields are deliberately excluded. A value inside ``digest_model`` is prose
    *about* a field, qualified by its container; treating it as an assertion of the same
    name is the proximity defect that this whole checkpoint keeps re-learning.
    """
    if not isinstance(document, dict):
        return {}
    return {
        key: str(value)
        for key, value in document.items()
        if isinstance(value, (str, int, float, bool))
    }


def markdown_tables(text: str) -> list[list[tuple[int, list[str]]]]:
    """Every pipe table, as a list of ``(line number, cells)`` rows including its header.

    Tables are separated by any non-table line. The header matters: a row is only a
    *status* claim if the table it is in has a status column, and without that the rule
    reads a roadmap's "main result" column as a status and reports a checkpoint summary
    as a stale state record. That was measured, not supposed.
    """
    tables: list[list[tuple[int, list[str]]]] = []
    current: list[tuple[int, list[str]]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            if current:
                tables.append(current)
                current = []
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells if cell):
            continue  # the header separator is not a claim
        current.append((number, cells))
    if current:
        tables.append(current)
    return tables


#: A column header that makes the cell under it a claim about state. Small and closed:
#: widening it to "result" or "outcome" is what turned a roadmap row into a finding.
STATUS_HEADERS = ("status", "state", "статус", "состояние")


def status_column(header: list[str]) -> int | None:
    """The index of the status column in a table header, or ``None`` if it has none."""
    for index, cell in enumerate(header):
        if any(token in cell.strip().lower() for token in STATUS_HEADERS):
            return index
    return None


def _cardinal(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return CARDINALS.get(token)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# The reviewed-family digest, recomputed from the recipe the checkpoint publishes.
# ---------------------------------------------------------------------------


def reviewed_families(tree: Tree) -> tuple[str, ...]:
    """The four reviewed families, read out of the contract manifest as data.

    Never restated here: a contour that carried its own copy of the family list would be
    one more record to go stale.
    """
    parsed = parse_block_yaml(tree.read(CONTRACT_MANIFEST) or "")
    families = parsed.get("families")
    if isinstance(families, dict) and families:
        return tuple(sorted(families))
    return ()


def artifact_manifest_digest(
    families: tuple[str, ...],
    paths: tuple[str, ...],
    read_blob,
) -> tuple[str | None, int]:
    """The recipe ``contract-manifest.yaml`` publishes, executed.

    ``git ls-tree -r --name-only <commit> -- <families>``, sorted; for each path, the
    UTF-8 path bytes then the RAW 32-byte sha256 of the content, into one sha256.
    """
    if not families:
        return None, 0
    members = sorted(
        path for path in paths if any(path.startswith(f"{fam}/") for fam in families)
    )
    digest = hashlib.sha256()
    for path in members:
        blob = read_blob(path)
        if blob is None:
            return None, len(members)
        digest.update(path.encode("utf-8"))
        digest.update(hashlib.sha256(blob).digest())
    return digest.hexdigest(), len(members)


# ---------------------------------------------------------------------------
# Check one: terminal state.
# ---------------------------------------------------------------------------

CHECK_TERMINAL = "terminal-state"


def classify(manifest: object) -> tuple[str, list[str]]:
    """Derive the terminal state from the manifest's data. Never restate it.

    Returns ``(state, reasons)``. ``reasons`` is empty when exactly one state is true.
    """
    if not isinstance(manifest, dict):
        return UNCLASSIFIED, ["the manifest is not a JSON object"]
    rounds = manifest.get("acceptance_rounds")
    if not isinstance(rounds, list) or not rounds:
        return UNCLASSIFIED, ["acceptance_rounds is missing or empty"]

    entries: dict[int, dict] = {}
    for entry in rounds:
        if isinstance(entry, dict) and isinstance(entry.get("round"), int):
            entries[entry["round"]] = entry
    if not entries:
        return UNCLASSIFIED, ["acceptance_rounds carries no entry with an integer round"]

    current = manifest.get("current_round")
    reasons: list[str] = []
    if current not in entries:
        return UNCLASSIFIED, [
            f"current_round is {current!r} and acceptance_rounds carries no entry for it"
        ]
    entry = entries[current]
    status = entry.get("status")
    verdict = entry.get("verdict")
    closed = status in CLOSED_STATUSES or status == ACCEPTED_STATUS or verdict is not None
    accepted = status == ACCEPTED_STATUS and verdict == "PASS"
    ratified = manifest.get("ratified") is True
    declared = manifest.get("status")
    has_ratification = isinstance(manifest.get("ratification"), dict)

    satisfied: list[str] = []
    if not closed and not ratified:
        satisfied.append(OPEN_ROUND)
    if accepted and not ratified:
        satisfied.append(CLOSED_ACCEPTED_ROUND)
    if accepted and ratified and has_ratification:
        satisfied.append(TERMINAL_RATIFIED)

    if len(satisfied) != 1:
        reasons.append(
            f"round {current} has status {status!r} and verdict {verdict!r}, "
            f"manifest ratified={manifest.get('ratified')!r} status={declared!r}, "
            f"ratification record {'present' if has_ratification else 'absent'}: "
            f"the tree satisfies {satisfied or 'no'} terminal state, and exactly one "
            "must be true"
        )
        return UNCLASSIFIED, reasons
    state = satisfied[0]
    if state == TERMINAL_RATIFIED and declared != "ratified":
        reasons.append(
            f"the manifest classifies terminal-ratified but its own status field is "
            f"{declared!r}"
        )
    return state, reasons


def terminal_state_problems(tree: Tree, state: str, manifest: object) -> list[Finding]:
    """What must be true of the classified state, *including once it is terminal*.

    The obligations below are the answer to the failure mode this contour replaces: a
    check that goes quiet at the moment of publication. Each one stays live in the
    terminal state and each one catches a record going stale after ratification.
    """
    problems: list[Finding] = []
    if not isinstance(manifest, dict):
        return problems
    entries = {
        entry["round"]: entry
        for entry in manifest.get("acceptance_rounds", [])
        if isinstance(entry, dict) and isinstance(entry.get("round"), int)
    }
    current = manifest.get("current_round")

    if state == TERMINAL_RATIFIED:
        # (a) the accepted round is the last one. Opening a further round without
        # moving current_round leaves the manifest one round behind itself.
        highest = max(entries)
        if current != highest:
            problems.append(Finding(
                CHECK_TERMINAL, MANIFEST,
                f"current_round is {current!r} but acceptance_rounds reaches round "
                f"{highest}; a terminal checkpoint's accepted round is the last one",
            ))
        # (b) the accepted round's two reports bind to one tree. A report swapped for
        # another round's, or a re-freeze that moves one stream and not the other,
        # shows up here and nowhere else.
        entry = entries.get(current, {})
        subjects: dict[str, str] = {}
        for key in ("manual_report", "automated_report"):
            report = entry.get(key)
            if not isinstance(report, str):
                problems.append(Finding(
                    CHECK_TERMINAL, MANIFEST,
                    f"round {current} is accepted and records no {key}; a ratified "
                    "checkpoint carries both streams' primary reports",
                ))
                continue
            declared = declared_subject(tree, report)
            if declared is None:
                problems.append(Finding(
                    CHECK_TERMINAL, report,
                    f"round {current}'s {key} declares no subject commit in its own "
                    "bytes, so nothing binds the accepted result to a tree",
                ))
            else:
                subjects[key] = declared
        if len(set(_common_prefix_group(subjects.values()))) > 1:
            problems.append(Finding(
                CHECK_TERMINAL, MANIFEST,
                f"round {current}'s two primary reports declare different subject "
                f"commits {sorted(set(subjects.values()))}; the streams judged "
                "different trees",
            ))
        # (c) the digests the manifest publishes are the accepted round's own.
        for key in ("tested_candidate_digest", "evidence_bundle_digest"):
            published, scoped = manifest.get(key), entry.get(key)
            if not scoped:
                problems.append(Finding(
                    CHECK_TERMINAL, MANIFEST,
                    f"round {current} is accepted and its {key} is empty; the terminal "
                    "state publishes a digest no round carries",
                ))
            elif published != scoped:
                problems.append(Finding(
                    CHECK_TERMINAL, MANIFEST,
                    f"top-level {key} is {published!r} and round {current} carries "
                    f"{scoped!r}",
                ))
    problems.extend(_checkpoint_row_problems(tree, state, manifest))
    return problems


def _common_prefix_group(values) -> list[str]:
    """Group abbreviated SHAs that are prefixes of one another into one representative."""
    unique = sorted(set(values), key=len)
    groups: list[str] = []
    for value in unique:
        if not any(value.startswith(g) or g.startswith(value) for g in groups):
            groups.append(value)
    return groups


#: How a checkpoint row's status cell reads in each terminal state. The vocabulary is
#: small and closed on purpose: a prose sweep over every sentence that mentions the
#: checkpoint produced 36 hits on this tree of which most were about an ADR, a test
#: fixture or a quotation, which is the noise this programme keeps mistaking for rigour.
TERMINAL_TOKENS = ("ratified", "tagged")
NON_TERMINAL_TOKENS = ("blocked", "open", "owed", "not ratified", "pending", "planned")


def checkpoint_status_cells(tree: Tree) -> list[tuple[str, str, list[str]]]:
    """``(site, status cell, whole row)`` for every live checkpoint status claim.

    The attribution rule is entirely structural and has three parts, all read out of the
    document rather than out of a list here: the record must be **live**, the table must
    have a **status column**, and the row's **first cell** must be the checkpoint id.
    No line window, no proximity, no path list. A prose sweep for the same thing was
    measured on this tree and returned 36 hits, of which the great majority were about
    an ADR, a test fixture or a quotation; this returns the rows that are actually
    claims about the checkpoint's state.
    """
    found: list[tuple[str, str, list[str]]] = []
    for path in tree.paths():
        if not path.endswith(".md"):
            continue
        if subject_commit(tree, path) is not None:
            continue  # historical: judged against its own tree, not this one
        text = tree.read(path)
        if text is None:
            continue
        for table in markdown_tables(text):
            if not table:
                continue
            column = status_column(table[0][1])
            if column is None:
                continue
            for line, cells in table[1:]:
                head = cells[0].strip().strip("`*")
                if head != CHECKPOINT or len(cells) <= column:
                    continue
                found.append((f"{path}:{line}", cells[column], cells))
    return found


def _checkpoint_row_problems(tree: Tree, state: str, manifest: object) -> list[Finding]:
    """Every live checkpoint status row must state the state the manifest derives.

    **This is the obligation that survives publication.** In the terminal state the row
    must say so, and it must name the accepted round -- so a later round accepted without
    the registry being brought forward turns this red, which is exactly the staleness the
    check it sits beside can no longer see once no round is owed.
    """
    problems: list[Finding] = []
    current = manifest.get("current_round") if isinstance(manifest, dict) else None
    rows = checkpoint_status_cells(tree)
    if not rows:
        problems.append(Finding(
            CHECK_TERMINAL, "(status rows)",
            f"no live record carries a status row for {CHECKPOINT}, so the terminal "
            "state is asserted by the manifest and corroborated by nothing",
            owner="W0-INT-02",
        ))
    for site, cell, cells in rows:
        body = cell.lower()
        terminal_claim = any(token in body for token in TERMINAL_TOKENS)
        non_terminal = [t for t in NON_TERMINAL_TOKENS if t in body]
        if state == TERMINAL_RATIFIED:
            if non_terminal:
                problems.append(Finding(
                    CHECK_TERMINAL, site,
                    f"the manifest classifies {state} and this {CHECKPOINT} status cell "
                    f"states {non_terminal}: {' | '.join(cells)[:150]}",
                ))
            elif not terminal_claim:
                problems.append(Finding(
                    CHECK_TERMINAL, site,
                    f"the manifest classifies {state} and this {CHECKPOINT} status cell "
                    f"states nothing this check can read about it: "
                    f"{' | '.join(cells)[:150]}",
                ))
            for match in re.finditer(r"round[\s-]+([a-z]+|\d{1,2})", body):
                number = _cardinal(match.group(1))
                if number is not None and number != current:
                    problems.append(Finding(
                        CHECK_TERMINAL, site,
                        f"this {CHECKPOINT} status cell names acceptance round {number} "
                        f"and the manifest's accepted round is {current}",
                    ))
        elif terminal_claim and not non_terminal:
            problems.append(Finding(
                CHECK_TERMINAL, site,
                f"the manifest classifies {state} and this {CHECKPOINT} status cell "
                f"already states {[t for t in TERMINAL_TOKENS if t in body]}: "
                f"{' | '.join(cells)[:150]}",
            ))
    return problems


# ---------------------------------------------------------------------------
# Check two: live versus historical, structurally.
# ---------------------------------------------------------------------------

CHECK_LIVE = "live-vs-historical"


def declared_subject(tree: Tree, path: str) -> str | None:
    """The commit a record declares as its subject **in its own bytes**, or ``None``.

    Only the record's own header, matched by :data:`SUBJECT_DECLARATION`. Kept separate
    from the manifest's binding on purpose: a report whose header declares nothing is
    bound to a tree by somebody else's say-so, and a checkpoint's accepted result has to
    be legible from the report a reader is handed.
    """
    text = tree.read(path)
    if text is None:
        return None
    head = "\n".join(text.splitlines()[:HEADER_LINES])
    match = SUBJECT_DECLARATION.search(head)
    return match.group(1) if match else None


def bound_subject(tree: Tree, path: str) -> str | None:
    """The subject the **manifest** binds a report to: a commit, or ``round-N``.

    The manifest binds a report path to an acceptance round and that round to the commit
    its candidate was frozen at. ``round-N`` is returned when the round records no
    commit, so the caller can tell "bound to a tree" from "bound to a round number",
    which are not the same evidence and were once conflated here.
    """
    manifest = tree.json(MANIFEST)
    if not isinstance(manifest, dict):
        return None
    for entry in manifest.get("acceptance_rounds", []):
        if not isinstance(entry, dict):
            continue
        if path in (entry.get("manual_report"), entry.get("automated_report")):
            frozen = entry.get("candidate_frozen_at_commit")
            if isinstance(frozen, str) and frozen:
                return frozen
            return f"round-{entry.get('round')}"
    return None


def subject_commit(tree: Tree, path: str) -> str | None:
    """The subject a record is bound to, from either source, or ``None`` if it is live.

    Nothing else. There is no path list here, and a report the manifest does not bind
    and whose header declares nothing is **live** -- which is a finding against the
    record, not a silent pass.
    """
    return declared_subject(tree, path) or bound_subject(tree, path)


def classify_records(tree: Tree) -> tuple[list[str], list[tuple[str, str]]]:
    """``(live paths, [(historical path, declared subject)])`` over the whole tree."""
    live: list[str] = []
    historical: list[tuple[str, str]] = []
    for path in tree.paths():
        if tree.read(path) is None:
            continue
        subject = subject_commit(tree, path)
        if subject is None:
            live.append(path)
        else:
            historical.append((path, subject))
    return live, historical


#: A machine-checkable claim a dated report makes about the tree it names. The claim is
#: **verified against that tree**, which is what turns the exemption into an obligation:
#: the previous sweep skipped these files by path and its own acceptance record calls
#: that a narrowing it warned against.
TRACKED_PATH_CLAIM = re.compile(
    r"(?:tree swept:[^\n]*?|over\s+the\s+)(\d{1,5})\s+(?:tracked\s+)?paths", re.IGNORECASE
)


def live_vs_historical_problems(tree: Tree) -> list[Finding]:
    return live_vs_historical_report(tree)[0]


def live_vs_historical_report(tree: Tree) -> tuple[list[Finding], int]:
    """``(findings, claims actually verified against a named tree)``.

    The second value is the anti-vacuity measurement. "Historical records were not a
    problem" is worth nothing if no historical claim was ever checked; this counts the
    ones that were re-derived at the commit they name, and a caller that wants the
    exemption to have been paid for asserts it is not zero.
    """
    problems: list[Finding] = []
    verified = 0
    live, historical = classify_records(tree)

    # Anti-vacuity. A classifier that puts everything on one side is not a classifier,
    # and a contour whose exemption never applies proves nothing about the exemption.
    if not live:
        problems.append(Finding(
            CHECK_LIVE, "(classification)",
            "every readable record declares a subject commit; no record is live, so the "
            "live-record obligations below are vacuous", owner="W0-QA-04",
        ))
    if not historical:
        problems.append(Finding(
            CHECK_LIVE, "(classification)",
            "no record declares a subject commit; the historical class is empty, so the "
            "structural rule is untested on this tree", owner="W0-QA-04",
        ))

    for path, subject in historical:
        text = tree.read(path) or ""
        claims = [int(m.group(1)) for m in TRACKED_PATH_CLAIM.finditer(text)]
        if not claims:
            continue
        if subject.startswith("round-"):
            problems.append(Finding(
                CHECK_LIVE, path,
                f"this record is bound to {subject} and the manifest records no commit "
                f"for that round, so its claim of {claims[0]} tracked paths cannot be "
                "verified against the tree it describes",
            ))
            continue
        at_subject = tree.paths_at(subject)
        if at_subject is None:
            problems.append(Finding(
                CHECK_LIVE, path,
                f"this record declares subject commit {subject}, which this tree cannot "
                "resolve; its claims cannot be verified where they apply",
            ))
            continue
        for claimed in claims:
            verified += 1
            if claimed != len(at_subject):
                problems.append(Finding(
                    CHECK_LIVE, path,
                    f"claims {claimed} tracked paths of its own subject commit "
                    f"{subject}, which has {len(at_subject)}",
                ))
    return problems, verified


# ---------------------------------------------------------------------------
# Check three: tag integrity.
# ---------------------------------------------------------------------------

CHECK_TAG = "tag-integrity"

#: Claims the tag message makes in a machine-readable shape. The tag object binds its
#: message to its own commit by construction, so the message is the one record whose
#: subject needs no declaration -- and therefore the one record whose claims must be
#: true of the commit it points at.
TAG_DIGEST_CLAIM = re.compile(r"artifact_manifest_sha256\s+([0-9a-f]{64})")
TAG_COUNT_CLAIM = re.compile(r"over\s+(\d{1,4})\s+files")
TAG_IDENTITY_CLAIM = re.compile(
    r"byte\s+identical\s+to\s+\w+\s+`?([0-9a-f]{7,40})`?", re.IGNORECASE
)


def recorded_tag(tree: Tree) -> str:
    """The tag name the checkpoint's own records carry, or ``""`` if none do.

    ``tag`` first, then ``tag_planned``: a checkpoint that has been prepared and not yet
    published names its identity in the second before the first is meaningful.
    """
    manifest = tree.json(MANIFEST)
    if isinstance(manifest, dict):
        for key in ("tag", "tag_planned"):
            value = manifest.get(key)
            if isinstance(value, str) and value:
                return value
    contract = parse_block_yaml(tree.read(CONTRACT_MANIFEST) or "")
    return contract.get("tag", "") if isinstance(contract.get("tag"), str) else ""


def tag_integrity_problems(tree: Tree, tag: TagFacts) -> list[Finding]:
    problems: list[Finding] = []
    manifest = tree.json(MANIFEST)
    contract = parse_block_yaml(tree.read(CONTRACT_MANIFEST) or "")

    # The records must agree on which tag this checkpoint has.
    named: dict[str, str] = {}
    if isinstance(manifest, dict):
        for key in ("tag", "tag_planned"):
            if isinstance(manifest.get(key), str):
                named[f"{MANIFEST}:{key}"] = manifest[key]
    if isinstance(contract.get("tag"), str):
        named[f"{CONTRACT_MANIFEST}:tag"] = contract["tag"]
    if not named:
        problems.append(Finding(
            CHECK_TAG, MANIFEST,
            "no checkpoint record names a tag, so there is no published identity for "
            "this checkpoint and nothing for the checks below to verify",
        ))
        return problems
    if len(set(named.values())) > 1:
        problems.append(Finding(
            CHECK_TAG, MANIFEST,
            f"the checkpoint records name more than one tag: {named}",
        ))
    if tag.name not in set(named.values()):
        problems.append(Finding(
            CHECK_TAG, tag.name,
            f"the tag under test is {tag.name!r} and the records name {sorted(set(named.values()))}",
        ))

    # **Ref-side findings are owned by the task that publishes refs.** A record naming a
    # tag that does not exist yet is the normal state of a prepared-but-unpublished
    # checkpoint: the manifest is written in the commit that gets tagged, so between the
    # record change and the tagging the records are ahead of the refs by construction.
    # Reporting that as the record-owner's defect would make it a state no task can
    # leave, which is the shape this phase has now hit six times.
    if not tag.exists:
        problems.append(Finding(
            CHECK_TAG, tag.name,
            "the records name this tag and it does not exist in this repository. If the "
            "checkpoint is prepared and not yet published this is the expected state "
            "until the tag is created; if it is published, the tag is missing",
            owner="W0-INT-03",
        ))
        return problems
    if not tag.annotated:
        problems.append(Finding(
            CHECK_TAG, tag.name,
            "the tag exists but is not an annotated tag object; a checkpoint tag carries "
            "its own message and tagger, and a lightweight tag carries neither",
            owner="W0-INT-03",
        ))
    if not tag.commit:
        problems.append(Finding(
            CHECK_TAG, tag.name, "the tag does not peel to a commit", owner="W0-INT-03",
        ))
        return problems

    families = reviewed_families(tree)
    at_tag = tree.paths_at(tag.commit)
    if at_tag is None:
        problems.append(Finding(
            CHECK_TAG, tag.name,
            f"the tag points at {tag.commit}, which this tree cannot resolve; nothing "
            "about the tagged tree can be verified",
        ))
        return problems
    digest, count = artifact_manifest_digest(
        families, at_tag, lambda path: tree.blob_at(tag.commit, path)
    )

    # "Has not moved" -- against the digest the records publish, because the tag sits on
    # the commit that carries the manifest and a commit cannot name its own hash.
    published = manifest.get("artifact_manifest_sha256") if isinstance(manifest, dict) else None
    if isinstance(published, str) and digest is not None and published != digest:
        problems.append(Finding(
            CHECK_TAG, tag.name,
            f"{MANIFEST} publishes artifact_manifest_sha256 {published} and the recipe "
            f"recomputed at the tag's own commit {tag.commit[:12]} gives {digest}: "
            "either the tag has moved or the reviewed families have",
        ))

    # The tag message is bound to this commit by construction. Its claims are live.
    for match in TAG_DIGEST_CLAIM.finditer(tag.message):
        if digest is not None and match.group(1) != digest:
            problems.append(Finding(
                CHECK_TAG, f"{tag.name} (message)",
                f"the tag message states artifact_manifest_sha256 {match.group(1)} and "
                f"the recipe over its own commit gives {digest}",
            ))
    for match in TAG_COUNT_CLAIM.finditer(tag.message):
        if int(match.group(1)) != count:
            problems.append(Finding(
                CHECK_TAG, f"{tag.name} (message)",
                f"the tag message states {match.group(1)} files and the reviewed "
                f"families at its own commit hold {count}",
            ))
    for match in TAG_IDENTITY_CLAIM.finditer(tag.message):
        other = match.group(1)
        drifted = _family_drift(tree, families, tag.commit, other)
        if drifted is None:
            problems.append(Finding(
                CHECK_TAG, f"{tag.name} (message)",
                f"the tag message claims byte identity with {other}, which this tree "
                "cannot resolve",
            ))
        elif drifted:
            problems.append(Finding(
                CHECK_TAG, f"{tag.name} (message)",
                f"the tag message claims the reviewed families are byte identical to "
                f"{other}, and {len(drifted)} differ at the tag's own commit: {drifted}",
            ))
    return problems


def _family_drift(
    tree: Tree, families: tuple[str, ...], here: str, there: str
) -> list[str] | None:
    """Reviewed-family paths whose bytes differ between two commits, or ``None``."""
    left, right = tree.paths_at(here), tree.paths_at(there)
    if left is None or right is None:
        return None
    def members(paths):
        return {p for p in paths if any(p.startswith(f"{f}/") for f in families)}
    drifted: list[str] = []
    for path in sorted(members(left) | members(right)):
        if tree.blob_at(here, path) != tree.blob_at(there, path):
            drifted.append(path)
    return drifted


# ---------------------------------------------------------------------------
# Check four: file and hash accounting.
# ---------------------------------------------------------------------------

CHECK_ACCOUNTING = "file-and-hash-accounting"

#: A key whose value is an aggregate hash over a set of files. Each one must enumerate
#: its members with their own hashes: "no aggregate whose members are unlisted".
AGGREGATE_KEYS = ("sha256", "artifact_manifest_sha256", "reviewed_manifest_digest")
#: A key that states how many files an aggregate covers.
COUNT_KEYS = ("files", "artifact_count")
#: A value shaped like a sha256.
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def bundle_records(tree: Tree) -> dict[str, dict[str, str]]:
    """The checkpoint's live structured records and their top-level fields.

    The set is derived from the manifest's own ``checkpoint_deliverables`` plus the
    manifest itself, and then narrowed to the records that are structured and live.
    Nothing is skipped by name: a deliverable that declares a subject commit is
    historical and is judged against its own tree by :func:`live_vs_historical_problems`.
    """
    manifest = tree.json(MANIFEST)
    declared = [MANIFEST]
    if isinstance(manifest, dict):
        declared += [
            path
            for path in manifest.get("checkpoint_deliverables", [])
            if isinstance(path, str)
        ]
    records: dict[str, dict[str, str]] = {}
    for path in declared:
        if subject_commit(tree, path) is not None:
            continue
        if path.endswith(".json"):
            fields = top_level_scalars(tree.json(path))
        elif path.endswith((".yaml", ".yml")):
            parsed = parse_block_yaml(tree.read(path) or "")
            fields = {k: v for k, v in parsed.items() if isinstance(v, str)}
        else:
            continue
        if fields:
            records[path] = fields
    return records


def claimed_paths(tree: Tree) -> dict[str, list[str]]:
    """Every repository path the checkpoint's live records claim, by claiming record.

    Two claim shapes, both structural:

    * a **path-shaped string value** in a structured record -- airtight, no prose;
    * a backticked **executable test artifact** in any live record, matched by
      :data:`CLAIMED_TEST_ARTIFACT`. A checkpoint that names a test module as part of
      its blocking contour must have it.
    """
    claims: dict[str, list[str]] = {}

    def add(site: str, path: str) -> None:
        claims.setdefault(site, [])
        if path not in claims[site]:
            claims[site].append(path)

    def walk(site: str, node: object) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(site, value)
        elif isinstance(node, list):
            for value in node:
                walk(site, value)
        elif isinstance(node, str) and PATH_SHAPED.match(node):
            add(site, node)

    manifest = tree.json(MANIFEST)
    if manifest is not None:
        walk(MANIFEST, manifest)
    contract = parse_block_yaml(tree.read(CONTRACT_MANIFEST) or "")
    walk(CONTRACT_MANIFEST, contract)
    build = tree.json(BUILD_INFO)
    if build is not None:
        walk(BUILD_INFO, build)

    declared = []
    if isinstance(manifest, dict):
        declared = [
            path
            for path in manifest.get("checkpoint_deliverables", [])
            if isinstance(path, str)
        ]
    for path in [MANIFEST, *declared]:
        if subject_commit(tree, path) is not None:
            continue
        text = tree.read(path)
        if text is None:
            continue
        for match in CLAIMED_TEST_ARTIFACT.finditer(text):
            add(path, match.group(1))
    return claims


def accounting_problems(tree: Tree) -> list[Finding]:
    problems: list[Finding] = []
    present = set(tree.paths())

    # (a) every file the checkpoint claims exists.
    for site, paths in sorted(claimed_paths(tree).items()):
        for path in paths:
            if path not in present:
                problems.append(Finding(
                    CHECK_ACCOUNTING, site,
                    f"claims the repository path {path!r}, which this tree does not track",
                ))

    # (b) no two live bundle records give the same top-level field two values.
    fields: dict[str, dict[str, str]] = {}
    for record, values in bundle_records(tree).items():
        for key, value in values.items():
            fields.setdefault(key, {})[record] = value
    for key, holders in sorted(fields.items()):
        if len(holders) > 1 and len(set(holders.values())) > 1:
            problems.append(Finding(
                CHECK_ACCOUNTING, key,
                "two live checkpoint records give this top-level field different "
                f"values, and neither says which tree it describes: "
                + "; ".join(f"{r} = {v}" for r, v in sorted(holders.items())),
            ))

    # (c) no aggregate whose members are unlisted.
    problems.extend(aggregate_problems(tree))
    return problems


def aggregate_problems(tree: Tree) -> list[Finding]:
    """Every aggregate hash must enumerate the files it rolls over, with their hashes.

    An aggregate whose members are unlisted is a number a reader can neither reproduce
    nor audit: it certifies a set nobody can name. The rule is applied to the contract
    manifest, which is the record that publishes the checkpoint's aggregates.
    """
    problems: list[Finding] = []
    parsed = parse_block_yaml(tree.read(CONTRACT_MANIFEST) or "")
    if not parsed:
        return problems

    def member_hashes(block: dict) -> int:
        """Per-**file** hashes: a filename-shaped key holding a sha256.

        Keyed by filename on purpose. ``sha256:`` under ``dependency_lock`` is the hash
        of the lock file named by its sibling ``path``, and ``sha256:`` under a family is
        that family's aggregate; neither is a member of the set the aggregate rolls over,
        and counting them would let an aggregate over 100 files look part-enumerated by
        the presence of its own value.
        """
        return sum(
            1
            for key, value in block.items()
            if isinstance(value, str)
            and SHA256.match(value)
            and re.fullmatch(r"[A-Za-z0-9_.-]+\.[A-Za-z0-9]+", key)
        )

    families = parsed.get("families")
    if isinstance(families, dict):
        for name, body in sorted(families.items()):
            if not isinstance(body, dict):
                continue
            aggregate = next(
                (body[k] for k in AGGREGATE_KEYS if isinstance(body.get(k), str)), None
            )
            if aggregate is None:
                continue
            declared = next(
                (int(body[k]) for k in COUNT_KEYS
                 if isinstance(body.get(k), str) and body[k].isdigit()), None
            )
            listed = member_hashes(body)
            if declared is None:
                problems.append(Finding(
                    CHECK_ACCOUNTING, f"{CONTRACT_MANIFEST}:families.{name}",
                    f"declares the aggregate {aggregate[:16]}… over an unstated number "
                    "of files",
                ))
            elif listed < declared:
                problems.append(Finding(
                    CHECK_ACCOUNTING, f"{CONTRACT_MANIFEST}:families.{name}",
                    f"declares the aggregate {aggregate[:16]}… over {declared} files and "
                    f"lists {max(listed, 0)} member hashes; an aggregate whose members "
                    "are unlisted certifies a set nobody can name",
                ))

    aggregate = parsed.get("artifact_manifest_sha256")
    declared = parsed.get("artifact_count")
    if isinstance(aggregate, str) and isinstance(declared, str) and declared.isdigit():
        def listed_everywhere(block: dict) -> int:
            """Every per-file hash anywhere in the record, at any depth.

            One level deep is not enough and the difference is not cosmetic: the family
            blocks are nested under ``families``, so a manifest that *did* enumerate its
            members family by family would have read as enumerating none of them, and
            the check would have gone on reporting a fully accounted record as unlisted.
            """
            return member_hashes(block) + sum(
                listed_everywhere(value)
                for value in block.values()
                if isinstance(value, dict)
            )

        listed = listed_everywhere(parsed)
        if listed < int(declared):
            problems.append(Finding(
                CHECK_ACCOUNTING, f"{CONTRACT_MANIFEST}:artifact_manifest_sha256",
                f"declares an aggregate over {declared} files and the record lists "
                f"{max(listed, 0)} per-file hashes across all of its sections",
            ))
    return problems


# ---------------------------------------------------------------------------
# Check five: cross-gate agreement.
# ---------------------------------------------------------------------------

CHECK_GATES = "cross-gate-agreement"

#: An assertion inside a task file's required-test command, over the parsed review.
GATE_ASSERTION = re.compile(
    r"assert\s+r\[(['\"])(?P<key>[A-Za-z_][A-Za-z0-9_]*)\1\]\s*"
    r"(?P<op>==|is)\s*(?P<value>'[^']*'|\"[^\"]*\"|True|False|None)"
)
#: The file a gate assertion is about, as the task file names it.
GATE_SUBJECT = re.compile(r"Path\((['\"])(?P<path>[^'\"]+)\1\)\.read_text\(\)")


def gate_assertions(tree: Tree) -> list[tuple[str, str, str, str, object]]:
    """``(task file, subject path, key, op, expected)`` for every gate in every task.

    Discovered structurally: any task file whose required-test command reads a JSON
    document and asserts on its fields is a gate. The contour does not know which task
    or which value; it knows that two gates over one field must agree.
    """
    found: list[tuple[str, str, str, str, object]] = []
    for path in tree.paths():
        if not path.startswith("docs/program/tasks/") or not path.endswith(".md"):
            continue
        text = tree.read(path)
        if text is None:
            continue
        for line in text.splitlines():
            subject = GATE_SUBJECT.search(line)
            if not subject:
                continue
            for match in GATE_ASSERTION.finditer(line):
                raw = match.group("value")
                if raw in ("True", "False", "None"):
                    expected = {"True": True, "False": False, "None": None}[raw]
                else:
                    expected = raw[1:-1]
                found.append(
                    (path, subject.group("path"), match.group("key"), match.group("op"), expected)
                )
    return found


def cross_gate_problems(tree: Tree) -> list[Finding]:
    """Fail while two gates over one field disagree. **Choose neither value.**"""
    problems: list[Finding] = []
    assertions = gate_assertions(tree)
    if not assertions:
        problems.append(Finding(
            CHECK_GATES, "docs/program/tasks/",
            "no task file states a ratification gate this contour can read, so the "
            "cross-gate check is vacuous on this tree", owner="W0-QA-04",
        ))
        return problems
    documents: dict[str, object] = {}
    for task, subject, key, op, expected in assertions:
        if subject not in documents:
            documents[subject] = tree.json(subject)
        document = documents[subject]
        if not isinstance(document, dict):
            problems.append(Finding(
                CHECK_GATES, subject,
                f"{task} asserts on this document and it is missing or not a JSON object",
            ))
            continue
        if key not in document:
            problems.append(Finding(
                CHECK_GATES, subject,
                f"{task} requires the field {key!r} and the document does not carry it",
            ))
            continue
        actual = document[key]
        agrees = (actual is expected) if op == "is" else (actual == expected)
        if not agrees:
            problems.append(Finding(
                CHECK_GATES, subject,
                f"two gates of one checkpoint disagree on {key!r}: {task} requires "
                f"{expected!r} and {subject} carries {actual!r}. This contour tests the "
                "agreement, not the value; choosing the canonical value is the "
                "disposition, not the check",
            ))
    return problems


# ---------------------------------------------------------------------------
# The contour.
# ---------------------------------------------------------------------------


def run(tree: Tree, tag: TagFacts) -> Verdict:
    """Every check, over one tree. Re-runnable: nothing here writes or caches."""
    manifest = tree.json(MANIFEST)
    if manifest is None:
        return Verdict(UNCLASSIFIED, [Finding(
            CHECK_TERMINAL, MANIFEST,
            "the checkpoint manifest is missing or does not parse; no terminal state "
            "can be derived and every check below would be vacuous",
        )])
    state, reasons = classify(manifest)
    verdict = Verdict(state)
    for reason in reasons:
        verdict.findings.append(Finding(CHECK_TERMINAL, MANIFEST, reason))
    verdict.findings += terminal_state_problems(tree, state, manifest)
    live_findings, verified = live_vs_historical_report(tree)
    verdict.findings += live_findings
    verdict.findings += tag_integrity_problems(tree, tag)
    verdict.findings += accounting_problems(tree)
    verdict.findings += cross_gate_problems(tree)
    live, historical = classify_records(tree)
    verdict.notes.append(
        f"{len(tree.paths())} tracked paths; {len(live)} live records, "
        f"{len(historical)} historical by their own declaration or by the manifest's "
        "binding"
    )
    verdict.notes.append(
        f"{verified} historical claim(s) re-derived at the commit the record names; "
        f"{len(checkpoint_status_cells(tree))} live {CHECKPOINT} status row(s) read"
    )
    return verdict


CHECKS = (CHECK_TERMINAL, CHECK_LIVE, CHECK_TAG, CHECK_ACCOUNTING, CHECK_GATES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP-00 final-state contour")
    parser.add_argument(
        "--root", default=".", help="repository root to read (default: the current tree)"
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="the checkpoint tag to verify; by default the one the records name",
    )
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    tree = RepositoryTree(root)
    # Resolved from the records, never defaulted to a literal. A default here was the
    # fifth instance of one pin: on a tree whose records had moved to the successor it
    # made the contour verify the *superseded* tag and then report the disagreement it
    # had itself introduced.
    verdict = run(tree, TagFacts.gather(root, arguments.tag or recorded_tag(tree)))

    print(f"tree: {root}")
    for note in verdict.notes:
        print(f"  {note}")
    print(f"\nterminal state: {verdict.state}")
    for check in CHECKS:
        found = verdict.by_check(check)
        print(f"\n{check}: {len(found)} finding(s)")
        for finding in found:
            print(f"  ! {finding.site}: {finding.message}")
            print(f"    owner: {finding.owner}")
    print("\nrecorded limitations of this contour:")
    for limitation in LIMITATIONS:
        print(f"  - {limitation}")
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    sys.exit(main())
