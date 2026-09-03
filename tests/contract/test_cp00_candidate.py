"""Independent consumer-side verification of the CP-00 candidate (`W0-QA-01`).

This module is written by an agent that authored none of the reviewed artifacts. It
asserts cross-family invariants over repository data, invokes the documented analysis
Gates A-D verbatim, and proves each invariant by mutating exactly the thing it claims
to protect inside a throwaway copy.

Reviewed candidate: `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` (`W0-CLN-01`
integration). Every assertion here is a statement about that tree. The evidence commit
that carries this file is a different, later commit and certifies nothing.

Two rules the module holds itself to:

* Nothing under `contracts/**`, `fixtures/**`, `docs/architecture/**` or `scripts/**`
  is written. Mutations happen in `tempfile.mkdtemp()` copies and are removed again.
* A documented gate is executed as written, through a shell, from the repository root.
  A gate that cannot run as documented is a failing test, not a skipped one.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

REVIEWED_CANDIDATE_COMMIT = "92e13fa496a723ed6e4c3adbf138c4f4e1d7c368"

BOOTSTRAP_PYTHON = REPOSITORY_ROOT / ".venv/bootstrap/bin/python"

ANALYSIS = "contracts/analysis/v1"
DOMAIN = "contracts/domain/v1"
EVENTS = "contracts/events/v1"
GOLDEN = "fixtures/golden"

ANALYSIS_README = f"{ANALYSIS}/README.md"
DOMAIN_README = f"{DOMAIN}/README.md"
EVENTS_README = f"{EVENTS}/README.md"
LINT_RULES_MD = "docs/architecture/ARCHITECTURE_LINT_RULES.md"
LINT_RULES_JSON = "docs/architecture/ARCHITECTURE_LINT_RULES.json"
SELECTION_MD = f"{GOLDEN}/SELECTION.md"

CANONICAL_VERSION_KEY = "contract_version"
CANDIDATE_CONTRACT_VERSION = "1.0.0-draft.1"

#: Version keys that no machine contract under ``contracts/**`` may declare (`ID-01`,
#: `ALR-24`). The one deliberate exception is the negative fixture whose whole purpose
#: is to carry the rejected key.
FORBIDDEN_VERSION_KEYS = frozenset({"version", "schema_version"})
LEGACY_KEY_FIXTURE = f"{EVENTS}/examples/event-envelope.legacy-schema-version.invalid.json"

#: Attempt-authority field names that `ALR-25` and the domain identifier catalog forbid
#: as *field names*. All three legitimately occur as string values (forbidden-detail-key
#: lists, legacy evidence names), so only object keys are checked.
FORBIDDEN_AUTHORITY_KEYS = frozenset({"authority_token", "fencing_token", "fence_token"})

#: Every reviewed family. Byte identity with the candidate is asserted over all of them,
#: except for the narrow, externally declared ratification delta defined below.
REVIEWED_PREFIXES = ("contracts/", "fixtures/", "docs/architecture/", "scripts/")

#: Three of the four reviewed families are touched by nothing, ever. Ratification does
#: not reach them, so no record can license a byte of change here.
IMMUTABLE_REVIEWED_PREFIXES = ("contracts/", "fixtures/", "scripts/")

#: The one family ratification does reach, and then only inside the declared set.
RATIFIABLE_REVIEWED_PREFIX = "docs/architecture/"

#: The external record. It is outside every reviewed family on purpose: a record that
#: lived inside the tree it authorises could licence its own drift.
CHECKPOINT_MANIFEST = "artifacts/checkpoints/CP-00/manifest.json"
CHECKPOINT_REGISTRY = "docs/program/CHECKPOINT_REGISTRY.md"

#: **The registry's state vocabulary, closed and machine-readable.** The CP-00 row of
#: `CHECKPOINT_REGISTRY.md` states its state by citing, in a code span, the manifest key
#: that holds it. These are identifiers, not English words, so a sentence that negates
#: one cannot be mistaken for one that asserts it — the failure the first form of this
#: check had, where `\bratified\b` matched inside "not ratified" and a row denying
#: ratification read as a row confirming it.
RATIFIED_STATE_TOKEN = "ratification"
UNRATIFIED_STATE_TOKEN = "ratification_blocked"
REGISTRY_STATE_TOKENS = frozenset({RATIFIED_STATE_TOKEN, UNRATIFIED_STATE_TOKEN})

#: Only this task may ratify CP-00. `W0.3_ratification_integration.md` assigns the
#: ratification act, the CP-00 review and the checkpoint evidence to it alone.
RATIFYING_TASK = "W0-INT-01"

#: **The ceiling on any ratification delta, and the reason it cannot be widened
#: silently.** A ratification record names the files it changes, but a record that could
#: name anything would be no control at all — the integrator would only have to add a
#: path to the record it writes itself. So the record may name *fewer* paths than this
#: set and never one outside it. Widening the ceiling means editing this module, which
#: only `W0-QA-01` owns, which means reopening this task and passing another independent
#: review.
#:
#: The five entries are exactly the artifacts CP-00 ratification is recorded as needing:
#: the review document whose `ratified` flag is the ratification act, in both its forms,
#: and the three point-in-time statements listed under `known_pre_ratification_items` in
#: the checkpoint manifest — the `PD-02` precondition text in two documents, the stale
#: `GATE-E` prose in the lint specification, and the owner-decision count in the ADR
#: index. Nothing else in `docs/architecture/**` is reconciled by ratification.
RATIFICATION_DELTA_CEILING = frozenset(
    {
        "docs/architecture/ADR_INDEX.md",
        "docs/architecture/ARCHITECTURE_LINT_RULES.md",
        "docs/architecture/CP00_ARCHITECTURE_REVIEW.json",
        "docs/architecture/CP00_ARCHITECTURE_REVIEW.md",
        "docs/architecture/CP00_OWNER_DECISIONS.md",
    }
)

#: The two acceptance digests of the current manifest form. One identifies the immutable
#: input the acceptance streams judged, frozen before they run; the other identifies the
#: tree that carries their results. They are necessarily different, because writing the
#: results changes the tree — which is why the single retired `candidate_digest` was
#: wrong: computed last, it certified a tree the streams never saw.
ACCEPTANCE_DIGEST_FIELDS = ("tested_candidate_digest", "evidence_bundle_digest")

#: Provenance a ratification record must carry. A delta authorised by a bare boolean
#: would be an accident with a flag on it.
RATIFICATION_REQUIRED_FIELDS = ("task", "decided_on", "decided_by", "reason")

GATE_MARKERS = {
    "A": "name-map gate PASS",
    "B": "evidence gate PASS",
    "C": "reviewer gate PASS",
    "D": "decision-transfer gate PASS",
}

#: Gate C resolves the accepted inventory out of this repository's object database. A
#: mutated copy is not a Git work tree, so the object database is named explicitly for
#: that gate only. Gate B addresses the legacy repository with its own ``git -C`` and
#: must not inherit a ``GIT_DIR``.
GATE_NEEDS_OBJECT_STORE = frozenset({"C"})


def _read(relative: str) -> str:
    return (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def _load(relative: str) -> object:
    return json.loads(_read(relative))


def _repository_json_files(prefix: str) -> list[str]:
    root = REPOSITORY_ROOT / prefix
    return sorted(
        path.relative_to(REPOSITORY_ROOT).as_posix() for path in root.rglob("*.json")
    )


def _object_keys(document: object):
    """Yield every object key of a JSON document, at any depth."""
    if isinstance(document, dict):
        for key, value in document.items():
            yield key
            yield from _object_keys(value)
    elif isinstance(document, list):
        for value in document:
            yield from _object_keys(value)


def _declared_properties(document: object):
    """Yield every name declared as a JSON Schema ``properties`` member or ``required``
    entry, at any depth."""
    if isinstance(document, dict):
        for key, value in document.items():
            if key == "properties" and isinstance(value, dict):
                yield from value
            if key == "required" and isinstance(value, list):
                yield from (item for item in value if isinstance(item, str))
            yield from _declared_properties(value)
    elif isinstance(document, list):
        for value in document:
            yield from _declared_properties(value)


def _values_for_key(document: object, wanted: str):
    if isinstance(document, dict):
        for key, value in document.items():
            if key == wanted and isinstance(value, str):
                yield value
            else:
                yield from _values_for_key(value, wanted)
    elif isinstance(document, list):
        for value in document:
            yield from _values_for_key(value, wanted)


def _fenced_blocks(relative: str) -> list[tuple[str | None, str]]:
    """Return ``(heading, body)`` for every fenced block of a Markdown document."""
    blocks: list[tuple[str | None, str]] = []
    heading: str | None = None
    lines = _read(relative).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            heading = line.strip()
        if line.startswith("```"):
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            blocks.append((heading, "\n".join(body) + "\n"))
        index += 1
    return blocks


def _documented_analysis_gate(letter: str) -> str:
    """The executable body of one documented analysis gate, taken from the contract.

    The command is not restated here: it is read out of the artifact under review, so a
    gate that is edited, renamed or removed changes what this module runs.
    """
    wanted = f"### Gate {letter} "
    matches = [
        body
        for heading, body in _fenced_blocks(ANALYSIS_README)
        if heading is not None and heading.startswith(wanted)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Gate {letter} is not recorded exactly once as an executable block in "
            f"{ANALYSIS_README}; found {len(matches)}. A gate that cannot be located "
            "cannot be executed as documented."
        )
    return matches[0]


def _documented_blocks(relative: str, language: str = "bash") -> list[str]:
    """Every fenced block of one document, in source order."""
    lines = _read(relative).splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("```" + language):
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            blocks.append("\n".join(body) + "\n")
        index += 1
    return blocks


def _run_shell(script: str, cwd: Path, env_overrides: dict[str, str] | None = None):
    """Execute a documented block through a shell, exactly as it is written.

    The shell is deliberate. Three W0.3 gates were found to be one-directional, one of
    them because a ``$`` inside a double-quoted ``python -c`` string was expanded by the
    shell before Python ever saw it. Running the recorded text through ``bash`` is what
    exposes that class of defect; re-typing the body into Python would hide it.
    """
    import os

    env = dict(os.environ)
    env.pop("GIT_DIR", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", "-c", script],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _candidate_reviewed_paths(root: Path) -> list[str]:
    """Every reviewed-family path recorded in the candidate commit."""
    listing = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "--no-replace-objects",
            "ls-tree",
            "-r",
            "--name-only",
            REVIEWED_CANDIDATE_COMMIT,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        raise AssertionError(
            "the reviewed candidate commit is not readable from this checkout: "
            + listing.stderr.strip()
        )
    return [path for path in listing.stdout.split("\n") if path.startswith(REVIEWED_PREFIXES)]


def _present_reviewed_paths(root: Path) -> list[str]:
    """Every reviewed-family path present in the checkout now.

    Tracked plus untracked-not-ignored, which is the set the checkpoint manifest's own
    digest recipe describes. Globbing the working tree instead would pick up a
    gitignored ``scripts/__pycache__`` byte-code file and make the answer depend on
    whether anyone had run the validator; the manifest records that exact mistake.
    """
    listing = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "contracts",
            "fixtures",
            "docs/architecture",
            "scripts",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        raise AssertionError("git could not enumerate the reviewed families")
    return sorted(path for path in listing.stdout.split("\n") if path)


def _candidate_blob(root: Path, relative: str) -> bytes | None:
    blob = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "--no-replace-objects",
            "show",
            f"{REVIEWED_CANDIDATE_COMMIT}:{relative}",
        ],
        capture_output=True,
        check=False,
    )
    return blob.stdout if blob.returncode == 0 else None


def _drifted_reviewed_paths(root: Path) -> list[str]:
    """Reviewed paths that are not byte-identical to the candidate commit.

    Three ways a path drifts, and all three are reported: its bytes changed, it was
    deleted, or it did not exist at the candidate and exists now. The third was a blind
    spot in the first form of this check — it only walked the candidate's own file list,
    so a *new* architecture document could have been added without the check noticing.

    The comparison is byte-for-byte on purpose. A parsed-JSON comparison is blind to
    re-indentation and key reordering — the domain scope gate of `W0-DOM-02` had exactly
    that hole — and the hashes this review records are hashes of bytes, so anything
    weaker would certify a document nobody hashed.
    """
    at_candidate = set(_candidate_reviewed_paths(root))
    present = set(_present_reviewed_paths(root))
    drifted: set[str] = set()
    for relative in at_candidate:
        blob = _candidate_blob(root, relative)
        on_disk = root / relative
        if blob is None or not on_disk.is_file() or blob != on_disk.read_bytes():
            drifted.add(relative)
    drifted |= present - at_candidate
    return sorted(drifted)


def _checkpoint_manifest(root: Path) -> dict | None:
    """The external checkpoint record, or ``None`` when there is not one."""
    path = root / CHECKPOINT_MANIFEST
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return document if isinstance(document, dict) else None


def _ratification_record(root: Path) -> tuple[bool, frozenset[str], list[str]]:
    """Read the declared ratification from the external record.

    Returns ``(externally_ratified, declared_delta, problems)``. ``problems`` is empty
    only when the record is admissible; an inadmissible record licenses **nothing**, so
    the caller treats it exactly like a missing one and reports why.

    The policy this implements, in full:

    * No record, or ``ratified`` false — no delta at all. Every reviewed family stays
      byte-identical to the candidate. A record cannot pre-authorise an edit before the
      ratification it authorises has actually been taken.
    * ``ratified`` true — a delta is admissible only if the record names the paths
      explicitly, every named path lies under ``docs/architecture/``, every named path
      is inside :data:`RATIFICATION_DELTA_CEILING`, and every named path already existed
      at the candidate. A path that did not exist at the candidate is a **new** reviewed
      artifact; that needs review, not ratification.
    * The record must name the task that took the act, when, on whose authority, and
      why. A delta authorised by a bare boolean would be an accident with a flag on it.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return False, frozenset(), []

    problems: list[str] = []
    ratified = manifest.get("ratified")
    if not isinstance(ratified, bool):
        return False, frozenset(), [
            f"{CHECKPOINT_MANIFEST}: 'ratified' must be a boolean, got {ratified!r}"
        ]
    if not ratified:
        return False, frozenset(), []

    record = manifest.get("ratification")
    if not isinstance(record, dict):
        return True, frozenset(), [
            f"{CHECKPOINT_MANIFEST} declares ratified true but carries no 'ratification' "
            "object. Ratification may change the reviewed architecture family only "
            "through a record that names, explicitly: 'allowed_delta_paths' (a list of "
            "repository-relative paths under docs/architecture/), plus "
            + ", ".join(f"'{field}'" for field in RATIFICATION_REQUIRED_FIELDS)
            + "."
        ]

    for field in RATIFICATION_REQUIRED_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(
                f"{CHECKPOINT_MANIFEST}: ratification.{field} must be a non-empty string"
            )
    task = record.get("task")
    if isinstance(task, str) and task != RATIFYING_TASK:
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.task is {task!r}; only "
            f"{RATIFYING_TASK} may ratify CP-00"
        )

    declared = record.get("allowed_delta_paths")
    if not isinstance(declared, list) or not declared:
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths must be a "
            "non-empty list of repository-relative paths"
        )
        return True, frozenset(), problems
    if not all(isinstance(item, str) and item for item in declared):
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths must hold strings"
        )
        return True, frozenset(), problems
    if len(declared) != len(set(declared)):
        problems.append(
            f"{CHECKPOINT_MANIFEST}: ratification.allowed_delta_paths repeats a path"
        )

    outside_family = sorted(
        item for item in declared if not item.startswith(RATIFIABLE_REVIEWED_PREFIX)
    )
    if outside_family:
        problems.append(
            "ratification may not reach outside "
            f"{RATIFIABLE_REVIEWED_PREFIX}: {outside_family}"
        )
    above_ceiling = sorted(set(declared) - RATIFICATION_DELTA_CEILING - set(outside_family))
    if above_ceiling:
        problems.append(
            "these paths are outside the ratification ceiling this module pins, so the "
            "record cannot authorise them: "
            f"{above_ceiling}. Widening the ceiling means reopening W0-QA-01."
        )
    absent_at_candidate = sorted(
        item
        for item in declared
        if item.startswith(RATIFIABLE_REVIEWED_PREFIX)
        and _candidate_blob(root, item) is None
    )
    if absent_at_candidate:
        problems.append(
            "these paths did not exist at the reviewed candidate, so they are new "
            f"reviewed artifacts and need review rather than ratification: "
            f"{absent_at_candidate}"
        )
    # The ceiling is not only an upper bound. For CP-00 the five files are not a menu:
    # each one is a reconciliation ratification is obliged to perform — the flag, the
    # `PD-02` precondition in two documents, the stale `GATE-E` sentence, the ADR-index
    # decision count. An earlier form of this check said "the record may name fewer
    # paths than the ceiling", which let a record declare the work and skip it.
    understated = sorted(RATIFICATION_DELTA_CEILING - set(declared))
    if understated:
        problems.append(
            "the record does not declare every reconciliation CP-00 ratification owes; "
            f"missing: {understated}. For this checkpoint the declared set is the whole "
            "ceiling, not a subset of it."
        )

    if problems:
        return True, frozenset(), problems
    return True, frozenset(declared), []


def _registry_state_problem(root: Path) -> str | None:
    """Compare the two external records by structure. ``None`` means they agree.

    The CP-00 row of the checkpoint registry states its state by citing, in a code span,
    the manifest key that holds it — `ratification_blocked` while blocked,
    `ratification` once ratified. Identifiers, not English: a row reading "not ratified"
    cannot be mistaken for one reading "ratified", which is exactly what the first form
    of this check got wrong.
    """
    manifest = _checkpoint_manifest(root)
    if manifest is None:
        return f"{CHECKPOINT_MANIFEST} is missing"
    external = manifest.get("ratified") is True
    rows = [
        line
        for line in (root / CHECKPOINT_REGISTRY).read_text(encoding="utf-8").splitlines()
        if line.startswith("| CP-00 ")
    ]
    if len(rows) != 1:
        return f"{CHECKPOINT_REGISTRY} does not carry exactly one CP-00 row"
    cited = {
        span for span in re.findall(r"`([^`]+)`", rows[0]) if span in REGISTRY_STATE_TOKENS
    }
    if len(cited) != 1:
        return (
            "the CP-00 registry row must cite exactly one manifest state key in a code "
            f"span, one of {sorted(REGISTRY_STATE_TOKENS)}; the row's prose is not read "
            f"and cannot carry the state. Row: {rows[0]}"
        )
    token = cited.pop()
    # Deliberately *not* also requiring the manifest to still carry a key of that name.
    # An unratified manifest has no `ratification` object and a ratified one may drop
    # `ratification_blocked` as spent history, so tying the comparison to key presence
    # would make it depend on whether history was kept — the ambient-state coupling this
    # module has had to remove twice already. The token is a state name from a closed
    # vocabulary; the comparison is between two states.
    if (token == RATIFIED_STATE_TOKEN) != external:
        return (
            f"{CHECKPOINT_REGISTRY} cites `{token}` for CP-00 while "
            f"{CHECKPOINT_MANIFEST} declares ratified={external}. A ratified checkpoint "
            f"cites `{RATIFIED_STATE_TOKEN}`; an unratified one cites "
            f"`{UNRATIFIED_STATE_TOKEN}`."
        )
    return None


def _undeclared_drift(root: Path) -> list[str]:
    """Reviewed-family drift that no admissible ratification record accounts for.

    One direction only — what changed without being declared. On its own this is not
    the policy: see :func:`_ratification_delta_problems`, which also requires the other
    direction, because a record that declares five reconciliations and performs one
    leaves nothing undeclared and would otherwise pass.
    """
    _, declared, problems = _ratification_record(root)
    licensed = frozenset() if problems else declared
    return sorted(set(_drifted_reviewed_paths(root)) - licensed)


def _unperformed_declarations(root: Path) -> list[str]:
    """Paths a valid record declares that are byte-identical to the candidate anyway.

    The other direction, and the one an independent negative probe found missing. A
    ratification record is a statement that these reconciliations were made; a declared
    path that never changed means the statement is false, whether by oversight or
    because the work was skipped and the record written anyway.
    """
    _, declared, problems = _ratification_record(root)
    if problems:
        return []
    return sorted(declared - set(_drifted_reviewed_paths(root)))


def _ratification_delta_problems(root: Path) -> list[str]:
    """The whole reviewed-family delta policy, both directions, in one answer.

    * every reviewed family byte-identical to the candidate, **except**
    * exactly the paths an admissible record declares — no more (undeclared drift) and
      no fewer (declared but not performed),
    * with `contracts/**`, `fixtures/**` and `scripts/**` untouchable regardless.
    """
    problems: list[str] = []
    _, declared, record_problems = _ratification_record(root)
    problems.extend(record_problems)

    immutable = _immutable_family_drift(root)
    if immutable:
        problems.append(
            "ratification does not reach these families and no record can license a "
            f"byte of them: {immutable}"
        )
    undeclared = _undeclared_drift(root)
    if undeclared:
        problems.append(
            "these reviewed artifacts differ from the candidate and no ratification "
            f"record accounts for them: {undeclared}"
        )
    unperformed = _unperformed_declarations(root)
    if unperformed:
        problems.append(
            "the ratification record declares these reconciliations and they were not "
            f"made — the files are byte-identical to the candidate: {unperformed}. "
            "Declaring the work is not doing it."
        )
    return problems


def _immutable_family_drift(root: Path) -> list[str]:
    """Drift in the three families ratification never reaches.

    Redundant with :func:`_undeclared_drift` while the ceiling holds, and stated
    separately anyway: the guarantee that `contracts/**`, `fixtures/**` and `scripts/**`
    are untouchable should not depend on reading the ceiling correctly.
    """
    return [
        path
        for path in _drifted_reviewed_paths(root)
        if path.startswith(IMMUTABLE_REVIEWED_PREFIXES)
    ]


def _reviewed_manifest_digest(root: Path) -> tuple[str, int]:
    """The checkpoint manifest's own `artifact_manifest_sha256` recipe, recomputed.

    For each tracked reviewed path in sorted order: the UTF-8 path bytes, then the raw
    32-byte SHA-256 of the file content — not its hex text.
    """
    tracked = sorted(
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-tree",
                "-r",
                "--name-only",
                "HEAD",
                "--",
                "contracts",
                "fixtures",
                "docs/architecture",
                "scripts",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
    )
    tracked = [path for path in tracked if path]
    running = hashlib.sha256()
    for relative in tracked:
        running.update(relative.encode("utf-8"))
        running.update(hashlib.sha256((root / relative).read_bytes()).digest())
    return running.hexdigest(), len(tracked)


class _CheckpointSandbox:
    """A throwaway working copy of the whole repository, object database included.

    Ratification probes have to answer questions about `git status`, about blobs at the
    candidate commit and about the external record all at once, so a partial copy will
    not do. Nothing here touches the repository under review: the object database is
    copied, never shared, and no Git command that writes is ever run — the sandbox is
    reset by rewriting bytes, not by asking Git to restore them.
    """

    #: Never copied: the live virtual environment, which is symlinked instead, and the
    #: object database, which is copied separately.
    NOT_COPIED = frozenset({".git", ".venv"})

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="w0-qa-01-checkpoint-"))
        shutil.copytree(REPOSITORY_ROOT / ".git", self.root / ".git")
        # The whole tree, not a hand-listed subset. The candidate digest enumerates
        # every tracked path, so a sandbox that carried only the interesting
        # directories would make the recipe unrunnable rather than make the probe
        # meaningful — and a hand-listed subset silently rots as the repository grows.
        for entry in sorted(REPOSITORY_ROOT.iterdir()):
            if entry.name in self.NOT_COPIED:
                continue
            if entry.is_dir():
                shutil.copytree(entry, self.root / entry.name, symlinks=True)
            elif entry.is_file():
                shutil.copy2(entry, self.root / entry.name)
        (self.root / ".venv").symlink_to(REPOSITORY_ROOT / ".venv")
        # `.gitignore` ignores `.venv/` as a directory; here it is a symlink, which that
        # pattern does not match, so the sandbox would enumerate it as an untracked file
        # and the digest recipe would try to read a directory. Excluded in the sandbox's
        # own copied metadata — a plain file write, not a Git command — so the sandbox
        # enumerates exactly what the repository does.
        exclude = self.root / ".git/info/exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write("\n.venv\n")
        self._pristine: dict[str, bytes] = {}

    def normalise_to_candidate(self) -> None:
        """Put the sandbox into the pre-ratification state, whatever the host tree is.

        These probes are about the policy, not about today's repository. Without this
        the whole class would silently change meaning the moment `W0-INT-01` ratifies —
        half of it passing for the wrong reason and half failing for the wrong reason —
        which is exactly the ambient-state dependence that made the original
        `ratified is False` pin a trap. Reviewed files are rewritten from the candidate
        blob, anything added since is removed, and the external record is returned to
        `ratified: false` with no `ratification` object.
        """
        at_candidate = set(_candidate_reviewed_paths(self.root))
        for relative in sorted(set(_present_reviewed_paths(self.root)) - at_candidate):
            (self.root / relative).unlink(missing_ok=True)
        for relative in sorted(at_candidate):
            blob = _candidate_blob(self.root, relative)
            if blob is None:
                raise AssertionError(f"candidate blob unavailable for {relative}")
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or target.read_bytes() != blob:
                target.write_bytes(blob)
        manifest_path = self.root / CHECKPOINT_MANIFEST
        if manifest_path.is_file():
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["ratified"] = False
            document.pop("ratification", None)
            manifest_path.write_text(
                json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    def __enter__(self) -> "_CheckpointSandbox":
        return self

    def __exit__(self, *_exc: object) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _remember(self, relative: str) -> None:
        if relative not in self._pristine:
            path = self.root / relative
            self._pristine[relative] = path.read_bytes() if path.is_file() else b""

    def edit(self, relative: str, marker: str = "\n<!-- ratification edit -->\n") -> None:
        """Append a visible marker, so the file drifts without becoming nonsense."""
        self._remember(relative)
        path = self.root / relative
        path.write_bytes(path.read_bytes() + marker.encode("utf-8"))

    def patch_json(self, relative: str, **fields: object) -> None:
        self._remember(relative)
        path = self.root / relative
        document = json.loads(path.read_text(encoding="utf-8"))
        document.update(fields)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def drop_json_key(self, relative: str, key: str) -> None:
        self._remember(relative)
        path = self.root / relative
        document = json.loads(path.read_text(encoding="utf-8"))
        document.pop(key, None)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def declare_ratification(
        self,
        paths: list[str],
        *,
        ratified: bool = True,
        task: str = RATIFYING_TASK,
        omit: tuple[str, ...] = (),
    ) -> None:
        """Write the external record the way `W0-INT-01` is expected to write it."""
        record: dict[str, object] = {
            "task": task,
            "decided_on": "2026-09-02",
            "decided_by": "repository owner, recorded by the program integrator",
            "reason": (
                "CP-00 ratification: set review.ratified and reconcile the three "
                "recorded point-in-time statements."
            ),
            "allowed_delta_paths": paths,
        }
        for field in omit:
            record.pop(field, None)
        self.patch_json(CHECKPOINT_MANIFEST, ratified=ratified, ratification=record)

    def set_registry_state(self, token: str | None, prose: str) -> None:
        """Rewrite the CP-00 registry row: a state token plus deliberate prose.

        `prose` exists so the probes can prove the English is never consulted — the
        combinations below pair a confirming token with denying prose and vice versa.
        """
        self._remember(CHECKPOINT_REGISTRY)
        path = self.root / CHECKPOINT_REGISTRY
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.startswith("| CP-00 "):
                cells = line.split("|")
                citation = f" see manifest `{token}`;" if token else ""
                cells[-2] = f" {prose};{citation} "
                lines[index] = "|".join(cells)
                break
        else:  # pragma: no cover - the registry always carries the row
            raise AssertionError("no CP-00 row to rewrite")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def restore_one(self, relative: str) -> None:
        """Put a single remembered path back, leaving the rest of the mutation alone."""
        payload = self._pristine.pop(relative)
        path = self.root / relative
        if payload:
            path.write_bytes(payload)
        elif path.is_file():
            path.unlink()

    def restore(self) -> None:
        for relative, payload in self._pristine.items():
            path = self.root / relative
            if payload:
                path.write_bytes(payload)
            elif path.is_file():
                path.unlink()
        self._pristine.clear()


class _MutableCopy:
    """A throwaway copy of the reviewed trees, for one mutation.

    The candidate is never written. Everything happens under ``tempfile.mkdtemp()`` and
    is removed in ``close()``. ``.venv`` is symlinked so a documented command's
    ``.venv/bootstrap/bin/python`` prefix resolves from the copy's own root.
    """

    def __init__(self, subtrees: tuple[str, ...] = ("contracts",)) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="w0-qa-01-mutation-"))
        for subtree in subtrees:
            shutil.copytree(REPOSITORY_ROOT / subtree, self.root / subtree)
        (self.root / ".venv").symlink_to(REPOSITORY_ROOT / ".venv")

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def load(self, relative: str) -> object:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def store(self, relative: str, document: object) -> None:
        (self.root / relative).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def run_gate(self, letter: str):
        overrides = (
            {"GIT_DIR": str(REPOSITORY_ROOT / ".git")}
            if letter in GATE_NEEDS_OBJECT_STORE
            else None
        )
        return _run_shell(_documented_analysis_gate(letter), self.root, overrides)

    def run_block(self, script: str):
        return _run_shell(script, self.root)


class ACandidateIntegrityTests(unittest.TestCase):
    """The tree under test is the commit the report certifies, byte for byte.

    Named to sort first: if this fails, every other result in this module describes some
    other tree and the review report is void.

    One narrow exception exists, and it is the whole subject of
    :class:`RatificationRecordTests`. Ratification is recorded *in* the artifact it
    ratifies, so `W0-INT-01` cannot do its job without changing files inside
    `docs/architecture/**`. That is a declared act, not drift — but only when an external
    record says so, names the files, and stays inside the ceiling this module pins.
    Everything else, in every family, is still drift and still a failure.
    """

    def test_the_candidate_file_set_is_the_one_this_report_describes(self) -> None:
        reviewed = _candidate_reviewed_paths(REPOSITORY_ROOT)
        # The candidate is immutable, so its reviewed file count is a fixed number. A
        # different count means a different tree, not a looser check.
        self.assertEqual(
            len(reviewed),
            100,
            "the candidate's reviewed file set is not the one this report describes",
        )

    def test_the_three_untouchable_families_are_byte_identical(self) -> None:
        """`contracts/**`, `fixtures/**`, `scripts/**` — no record can license a byte."""
        self.assertEqual(
            _immutable_family_drift(REPOSITORY_ROOT),
            [],
            "ratification does not reach these families; any difference from the "
            "candidate voids the report",
        )

    def test_the_reviewed_delta_is_exactly_what_is_declared(self) -> None:
        """Both directions: nothing undeclared changed, and nothing declared was skipped."""
        external_ratified, declared, _ = _ratification_record(REPOSITORY_ROOT)
        self.assertEqual(
            _ratification_delta_problems(REPOSITORY_ROOT),
            [],
            f"record ratified={external_ratified}, declared={sorted(declared)}, "
            f"observed drift={_drifted_reviewed_paths(REPOSITORY_ROOT)}",
        )

    def test_recorded_analysis_hashes_are_reproducible(self) -> None:
        """The two artifacts the report names by hash still hash to those values."""
        expected = {
            f"{ANALYSIS}/stage-registry.json": (
                "2c7f952bd7e21d2f6b1015d759476d38126d2ed3b021202a4065a6384dfed1a5"
            ),
            f"{ANALYSIS}/legacy-stage-name-map.json": (
                "df999f88b445c0b6ed096b157841da4787cac397b4f4c05a75628f84f9eba3a3"
            ),
            f"{ANALYSIS}/legacy-stage-map.json": (
                "7ba0c9c8febeabac4d1da4b7e2ff417e9f534c93976c8690b8fee44e65f29b07"
            ),
        }
        actual = {
            relative: hashlib.sha256(
                (REPOSITORY_ROOT / relative).read_bytes()
            ).hexdigest()
            for relative in expected
        }
        self.assertEqual(actual, expected)


class DocumentedAnalysisGateTests(unittest.TestCase):
    """Gates A-D are invoked as written. A gate that cannot run is a failed review."""

    def test_all_four_gates_are_recorded_as_executable_blocks(self) -> None:
        for letter in "ABCD":
            with self.subTest(gate=letter):
                body = _documented_analysis_gate(letter)
                self.assertIn(
                    ".venv/bootstrap/bin/python",
                    body,
                    "the gate no longer names the provisioned validator interpreter",
                )

    def test_bootstrap_interpreter_the_gates_name_is_present(self) -> None:
        self.assertTrue(
            BOOTSTRAP_PYTHON.is_file(),
            f"{BOOTSTRAP_PYTHON} is missing; every documented gate names it, so none of "
            "them can be executed as documented",
        )

    def _assert_gate_passes(self, letter: str) -> str:
        overrides = (
            {"GIT_DIR": str(REPOSITORY_ROOT / ".git")}
            if letter in GATE_NEEDS_OBJECT_STORE
            else None
        )
        result = _run_shell(
            _documented_analysis_gate(letter), REPOSITORY_ROOT, overrides
        )
        self.assertEqual(
            result.returncode,
            0,
            f"documented Gate {letter} did not execute as written.\n"
            f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}",
        )
        self.assertIn(GATE_MARKERS[letter], result.stdout)
        return result.stdout

    def test_gate_a_name_level_alias_map_structure(self) -> None:
        stdout = self._assert_gate_passes("A")
        self.assertIn("62 unique names", stdout)
        self.assertIn("293 observations", stdout)
        self.assertIn("31/31 alias-bearing sites", stdout)

    def test_gate_b_every_evidence_locator_resolves(self) -> None:
        stdout = self._assert_gate_passes("B")
        self.assertIn("293/293 locators resolve", stdout)

    def test_gate_c_independent_reviewer_checks(self) -> None:
        stdout = self._assert_gate_passes("C")
        self.assertIn("9/9 stages", stdout)
        self.assertIn("11/11 exclusion ids", stdout)

    def test_gate_d_owner_decisions_transferred(self) -> None:
        stdout = self._assert_gate_passes("D")
        self.assertIn("all 9 creation triggers", stdout)
        self.assertIn("RC-02 beats RC-05", stdout)

    def test_documented_analysis_command_block_runs_clean(self) -> None:
        """The `## Gates` command list, including the standalone validator run."""
        blocks = [
            body
            for heading, body in _fenced_blocks(ANALYSIS_README)
            if heading == "## Gates"
        ]
        self.assertEqual(len(blocks), 1)
        result = _run_shell(blocks[0], REPOSITORY_ROOT)
        self.assertEqual(
            result.returncode,
            0,
            f"the documented analysis command block failed: {result.stderr.strip()}",
        )
        self.assertIn("PASS", result.stdout)

    def test_documented_negative_examples_are_rejected(self) -> None:
        """The README's prose claim about the three `*.invalid.json` fixtures."""
        from jsonschema import Draft202012Validator

        pairs = {
            "result-package.missing-attempt-authority.invalid.json": (
                "result-package.schema.json"
            ),
            "stage-result.failed-missing-error.invalid.json": "stage-result.schema.json",
            "stage-result.succeeded-with-error.invalid.json": "stage-result.schema.json",
        }
        present = sorted(
            path.name
            for path in (REPOSITORY_ROOT / ANALYSIS / "examples").glob("*.invalid.json")
        )
        self.assertEqual(present, sorted(pairs))
        for example, schema in pairs.items():
            with self.subTest(example=example):
                validator = Draft202012Validator(_load(f"{ANALYSIS}/{schema}"))
                errors = list(
                    validator.iter_errors(_load(f"{ANALYSIS}/examples/{example}"))
                )
                self.assertTrue(errors, f"{example} was accepted by {schema}")


class DocumentedNeighbourGateTests(unittest.TestCase):
    """The domain, event and golden families document their own gates. Run those too."""

    def test_domain_documented_blocks(self) -> None:
        for index, block in enumerate(_documented_blocks(DOMAIN_README)):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"domain block {index} failed: {result.stderr.strip()}",
                )

    def test_event_documented_blocks_including_the_declared_residue(self) -> None:
        blocks = _documented_blocks(EVENTS_README)
        self.assertEqual(len(blocks), 6, "the event README's gate list changed shape")
        expected_exit = {index: 0 for index in range(len(blocks))}
        # The fifth block is documented as exiting 1 and reporting exactly the negative
        # fixture. It is a declared residue, not a defect, and is asserted as such.
        expected_exit[4] = 1
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    expected_exit[index],
                    f"event block {index}: {result.stdout.strip()} "
                    f"{result.stderr.strip()}",
                )
                if index == 4:
                    self.assertIn("legacy-schema-version.invalid.json", result.stderr)
                    self.assertEqual(
                        1,
                        result.stderr.count("contracts/"),
                        "the un-excluded sweep must report exactly one file",
                    )

    def test_golden_documented_blocks(self) -> None:
        blocks = _documented_blocks(SELECTION_MD)
        self.assertEqual(len(blocks), 2)
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"golden block {index} failed: {result.stderr.strip()}",
                )
                self.assertNotIn("False", result.stdout)
        self.assertIn("U-05 PASS", _run_shell(blocks[1], REPOSITORY_ROOT).stdout)

    def test_architecture_documented_gates(self) -> None:
        lines = _read(LINT_RULES_MD).splitlines()
        blocks: list[tuple[str, str]] = []
        label = None
        index = 0
        while index < len(lines):
            match = re.match(r"\*\*(GATE-[A-F])\*\*", lines[index])
            if match:
                label = match.group(1)
            if lines[index].startswith("```bash"):
                body: list[str] = []
                index += 1
                while index < len(lines) and not lines[index].startswith("```"):
                    body.append(lines[index])
                    index += 1
                if label is not None:
                    blocks.append((label, "\n".join(body) + "\n"))
            index += 1
        self.assertEqual(
            sorted({label for label, _ in blocks}),
            ["GATE-A", "GATE-B", "GATE-C", "GATE-D", "GATE-E", "GATE-F"],
            "the architecture specification no longer records all six gates",
        )
        declared = _ratification_record(REPOSITORY_ROOT)[1]
        for position, (label, block) in enumerate(blocks):
            with self.subTest(gate=label, position=position):
                result = _run_shell(block, REPOSITORY_ROOT)
                if result.returncode == 0:
                    continue
                # The one admissible failure. GATE-F's strict form asserts that nothing
                # under docs/architecture is dirty except the two lint-rule files that
                # `W0-ARC-02` owned; it is a claim about *that* task's write boundary,
                # made against the working tree. A ratification edit in progress dirties
                # other files in the same directory and trips it. The gate is not
                # skipped and not weakened: it must still fail for no reason other than
                # the declared ratification delta, and the reported paths must be a
                # subset of it.
                reported = {
                    line.strip().strip("'\"")
                    for line in re.findall(r"'docs/architecture/[^']+'", result.stderr)
                }
                self.assertTrue(
                    reported and reported <= set(declared),
                    f"{label} block {position} failed for something other than the "
                    f"declared ratification delta.\nreported: {sorted(reported)}\n"
                    f"declared: {sorted(declared)}\nstderr: {result.stderr.strip()}",
                )


class ContractVersionKeyTests(unittest.TestCase):
    """`ID-01`: exactly one version key across the three contract families."""

    def test_no_contract_declares_a_forbidden_version_key(self) -> None:
        offenders: dict[str, list[str]] = {}
        for relative in _repository_json_files("contracts"):
            if relative == LEGACY_KEY_FIXTURE:
                continue
            document = _load(relative)
            hits = sorted(
                {
                    key
                    for key in _object_keys(document)
                    if key in FORBIDDEN_VERSION_KEYS
                }
                | {
                    name
                    for name in _declared_properties(document)
                    if name in FORBIDDEN_VERSION_KEYS
                }
            )
            if hits:
                offenders[relative] = hits
        self.assertEqual(offenders, {})

    def test_the_single_negative_fixture_is_the_only_declared_exception(self) -> None:
        document = _load(LEGACY_KEY_FIXTURE)
        self.assertIn("schema_version", document)
        self.assertEqual(document[CANONICAL_VERSION_KEY], CANDIDATE_CONTRACT_VERSION)
        notes = " ".join(
            rule["false_positive_notes"]
            for rule in _load(LINT_RULES_JSON)["rules"]
            if rule["rule_id"] == "ALR-24"
            for rule["false_positive_notes"] in [" ".join(rule["false_positive_notes"])]
        )
        self.assertIn(
            "legacy-schema-version.invalid.json",
            notes,
            "the exception this test relies on is not recorded in ALR-24",
        )

    def test_every_family_declares_the_same_candidate_version(self) -> None:
        declared: dict[str, str] = {}
        for relative in _repository_json_files("contracts"):
            document = _load(relative)
            if isinstance(document, dict) and CANONICAL_VERSION_KEY in document:
                value = document[CANONICAL_VERSION_KEY]
                if isinstance(value, str):
                    declared[relative] = value
        self.assertTrue(declared)
        self.assertEqual(
            sorted(set(declared.values())),
            [CANDIDATE_CONTRACT_VERSION],
            f"contract families disagree on the candidate version: {declared}",
        )

    def test_domain_and_event_schemas_pin_the_key_by_const(self) -> None:
        for relative in (
            f"{DOMAIN}/error-envelope.schema.json",
            f"{EVENTS}/event-envelope.schema.json",
        ):
            with self.subTest(schema=relative):
                schema = _load(relative)
                self.assertIn(CANONICAL_VERSION_KEY, schema["required"])
                self.assertEqual(
                    schema["properties"][CANONICAL_VERSION_KEY].get("const"),
                    CANDIDATE_CONTRACT_VERSION,
                )
                self.assertIs(schema.get("additionalProperties"), False)

    def test_golden_versions_itself_under_a_different_key(self) -> None:
        """A recorded cross-family fact, asserted rather than left to prose.

        `ID-01` and `ALR-24` are scoped to `contracts/**`. The golden baseline is
        fixture-local and keeps `schema_version`. This test pins that difference so it
        stays a deliberate boundary rather than drifting into an accident.
        """
        self.assertEqual(
            _load(LINT_RULES_JSON)["rules"][
                [rule["rule_id"] for rule in _load(LINT_RULES_JSON)["rules"]].index(
                    "ALR-24"
                )
            ]["scope"],
            ["contracts/**/*.json"],
            "ALR-24 changed scope; the golden exemption below rests on that scope",
        )
        carriers = sorted(
            relative
            for relative in _repository_json_files(GOLDEN)
            if "schema_version" in set(_object_keys(_load(relative)))
            | set(_declared_properties(_load(relative)))
        )
        self.assertEqual(
            carriers,
            [
                f"{GOLDEN}/GJ-01/manifest.json",
                f"{GOLDEN}/GJ-02/manifest.json",
                f"{GOLDEN}/GJ-03/manifest.json",
                f"{GOLDEN}/GJ-04/manifest.json",
                f"{GOLDEN}/GJ-05/manifest.json",
                f"{GOLDEN}/journey-manifest.schema.json",
                f"{GOLDEN}/selection.json",
                f"{GOLDEN}/selection.schema.json",
            ],
            "the golden family's use of schema_version moved; re-record the "
            "cross-family version-key statement in the review report",
        )


class ForbiddenAuthorityFieldNameTests(unittest.TestCase):
    """`ALR-25`: the attempt-authority capability is named `execution_token`."""

    def test_no_contract_declares_a_forbidden_authority_field_name(self) -> None:
        offenders: dict[str, list[str]] = {}
        for relative in _repository_json_files("contracts"):
            document = _load(relative)
            hits = sorted(
                {
                    key
                    for key in _object_keys(document)
                    if key in FORBIDDEN_AUTHORITY_KEYS
                }
                | {
                    name
                    for name in _declared_properties(document)
                    if name in FORBIDDEN_AUTHORITY_KEYS
                }
            )
            if hits:
                offenders[relative] = hits
        self.assertEqual(offenders, {})

    def test_the_legacy_names_survive_only_as_recorded_evidence_values(self) -> None:
        capability = _load(f"{DOMAIN}/identifiers.json")["authority_capabilities"][
            "execution_token"
        ]
        self.assertEqual(capability["canonical_field_name"], "execution_token")
        self.assertEqual(
            sorted(item["name"] for item in capability["legacy_evidence_names"]),
            ["authority_token", "fencing_token"],
        )
        for item in capability["legacy_evidence_names"]:
            self.assertEqual(item["status"], "legacy_evidence_only")

    def test_the_authority_bearing_packages_use_the_canonical_name(self) -> None:
        for relative in (
            f"{ANALYSIS}/job-package.schema.json",
            f"{ANALYSIS}/result-package.schema.json",
        ):
            with self.subTest(schema=relative):
                schema = _load(relative)
                authority = schema["$defs"]["attempt_authority"]
                self.assertIn("execution_token", authority["properties"])
                self.assertIn("execution_token", authority["required"])


class SchemaAndExampleValidityTests(unittest.TestCase):
    """Every owned schema is valid Draft 2020-12; every example behaves as declared."""

    def test_every_contract_schema_is_a_valid_draft_2020_12_schema(self) -> None:
        from jsonschema import Draft202012Validator

        schemas = [
            relative
            for relative in _repository_json_files("contracts")
            if relative.endswith(".schema.json")
        ]
        self.assertEqual(len(schemas), 11, "the owned schema set changed shape")
        for relative in schemas:
            with self.subTest(schema=relative):
                document = _load(relative)
                self.assertEqual(
                    document.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )
                Draft202012Validator.check_schema(document)

    def test_every_positive_example_validates_against_its_schema(self) -> None:
        from jsonschema import Draft202012Validator

        pairs = (
            (f"{ANALYSIS}/job-package.schema.json", f"{ANALYSIS}/examples/job-package.example.json"),
            (f"{ANALYSIS}/stage-result.schema.json", f"{ANALYSIS}/examples/stage-result.example.json"),
            (f"{ANALYSIS}/result-package.schema.json", f"{ANALYSIS}/examples/result-package.example.json"),
            (f"{DOMAIN}/error-envelope.schema.json", f"{DOMAIN}/examples/error-envelope.example.json"),
            (f"{EVENTS}/event-envelope.schema.json", f"{EVENTS}/examples/event-envelope.example.json"),
            (f"{DOMAIN}/identifiers.schema.json", f"{DOMAIN}/identifiers.json"),
            (f"{DOMAIN}/state-machines.schema.json", f"{DOMAIN}/state-machines.json"),
            (f"{DOMAIN}/error-codes.schema.json", f"{DOMAIN}/error-codes.json"),
            (f"{ANALYSIS}/stage-registry.schema.json", f"{ANALYSIS}/stage-registry.json"),
            (f"{ANALYSIS}/legacy-stage-map.schema.json", f"{ANALYSIS}/legacy-stage-map.json"),
            (f"{ANALYSIS}/legacy-stage-name-map.schema.json", f"{ANALYSIS}/legacy-stage-name-map.json"),
            (f"{GOLDEN}/selection.schema.json", f"{GOLDEN}/selection.json"),
        )
        for schema_relative, instance_relative in pairs:
            with self.subTest(instance=instance_relative):
                validator = Draft202012Validator(_load(schema_relative))
                errors = list(validator.iter_errors(_load(instance_relative)))
                self.assertEqual(
                    [error.message for error in errors],
                    [],
                    f"{instance_relative} does not validate against {schema_relative}",
                )

    def test_every_journey_manifest_validates(self) -> None:
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(_load(f"{GOLDEN}/journey-manifest.schema.json"))
        for journey in ("GJ-01", "GJ-02", "GJ-03", "GJ-04", "GJ-05"):
            with self.subTest(journey=journey):
                errors = list(
                    validator.iter_errors(_load(f"{GOLDEN}/{journey}/manifest.json"))
                )
                self.assertEqual([error.message for error in errors], [])

    def test_every_negative_example_is_rejected_for_its_own_reason(self) -> None:
        from jsonschema import Draft202012Validator

        cases = (
            (
                f"{DOMAIN}/error-envelope.schema.json",
                f"{DOMAIN}/examples/error-envelope.unknown-code.invalid.json",
                "error_code",
            ),
            (
                f"{EVENTS}/event-envelope.schema.json",
                LEGACY_KEY_FIXTURE,
                "schema_version",
            ),
        )
        for schema_relative, example_relative, blamed in cases:
            with self.subTest(example=example_relative):
                validator = Draft202012Validator(_load(schema_relative))
                errors = list(validator.iter_errors(_load(example_relative)))
                self.assertTrue(errors, f"{example_relative} was accepted")
                self.assertTrue(
                    any(
                        blamed in error.message or list(error.path)[:1] == [blamed]
                        for error in errors
                    ),
                    f"{example_relative} is not rejected for {blamed}: "
                    f"{[error.message for error in errors]}",
                )


class DomainErrorEnumParityTests(unittest.TestCase):
    """The envelope enum is exactly the catalog key set, and the family agrees on itself."""

    def test_envelope_enum_equals_the_catalog_exactly(self) -> None:
        catalog = _load(f"{DOMAIN}/error-codes.json")
        envelope = _load(f"{DOMAIN}/error-envelope.schema.json")
        enum = envelope["properties"]["error_code"]["enum"]
        self.assertEqual(len(enum), len(set(enum)), "the envelope enum repeats a code")
        self.assertEqual(sorted(enum), sorted(catalog["codes"]))
        self.assertEqual(len(catalog["codes"]), 20)

    def test_every_declared_code_carries_a_status_and_a_retry_flag(self) -> None:
        catalog = _load(f"{DOMAIN}/error-codes.json")
        for code, definition in sorted(catalog["codes"].items()):
            with self.subTest(code=code):
                self.assertRegex(code, r"^[a-z][a-z0-9_]*$")
                self.assertIsInstance(definition["http"], int)
                self.assertNotIsInstance(definition["http"], bool)
                self.assertTrue(400 <= definition["http"] <= 599)
                self.assertIsInstance(definition["retryable"], bool)
                self.assertIn(definition["category"], catalog["categories"])

    def test_state_machine_and_identifier_references_resolve(self) -> None:
        machines = _load(f"{DOMAIN}/state-machines.json")
        codes = set(_load(f"{DOMAIN}/error-codes.json")["codes"])
        identifiers = set(_load(f"{DOMAIN}/identifiers.json")["identifiers"])
        referenced = {machines["default_violation"]}
        for machine in machines["machines"].values():
            referenced |= {
                guard["on_violation"]
                for guard in machine["guards"]
                if "on_violation" in guard
            }
            for case in machine.get("run_creation", {}).get("cases", []):
                if "error_code" in case:
                    referenced.add(case["error_code"])
        self.assertLessEqual(referenced, codes, sorted(referenced - codes))
        used = {machine["identifier"] for machine in machines["machines"].values()} | {
            aggregate["identifier"]
            for aggregate in machines["non_state_machine_aggregates"].values()
        }
        self.assertLessEqual(used, identifiers, sorted(used - identifiers))

    def test_one_candidate_revision_across_the_family(self) -> None:
        revisions = {
            relative: _load(f"{DOMAIN}/{relative}")["candidate_revision"]
            for relative in ("identifiers.json", "state-machines.json", "error-codes.json")
        }
        self.assertEqual(len(set(revisions.values())), 1, revisions)


class AnalysisReferentialIntegrityTests(unittest.TestCase):
    """Reference resolution recomputed independently of the family's own gate text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = _load(f"{ANALYSIS}/stage-registry.json")
        cls.sites = _load(f"{ANALYSIS}/legacy-stage-map.json")
        cls.names = _load(f"{ANALYSIS}/legacy-stage-name-map.json")
        cls.stage_ids = {stage["stage_id"] for stage in cls.registry["stages"]}
        cls.exclusion_ids = {
            item["excluded_scope_id"] for item in cls.registry["excluded_scope"]
        }
        cls.site_ids = {
            declaration["source_declaration_id"]
            for declaration in cls.sites["declarations"]
        }

    def test_declared_counts_are_the_recomputed_counts(self) -> None:
        self.assertEqual(len(self.stage_ids), 9)
        self.assertEqual(len(self.exclusion_ids), 11)
        self.assertEqual(len(self.site_ids), 31)
        self.assertEqual(len(self.sites["declarations"]), 31)
        self.assertEqual(len(self.names["names"]), self.names["name_count"])
        self.assertEqual(self.names["name_count"], 62)

    def test_every_stage_and_exclusion_reference_resolves(self) -> None:
        for entry in self.names["names"]:
            with self.subTest(name=entry["legacy_stage_name"]):
                if entry["resolution"] == "canonical_stage":
                    self.assertIn(entry["canonical_stage_id"], self.stage_ids)
                    self.assertNotIn("excluded_scope_id", entry)
                else:
                    self.assertIn(entry["excluded_scope_id"], self.exclusion_ids)
                    self.assertNotIn("canonical_stage_id", entry)
                for covered in entry.get("also_covers_stage_ids", []):
                    self.assertIn(covered, self.stage_ids)

    def test_every_declaration_site_reference_resolves(self) -> None:
        for entry in self.names["names"]:
            observations = [entry] + entry.get("additional_observations", [])
            for observation in observations:
                self.assertIn(observation["source_declaration_id"], self.site_ids)
        for stage in self.registry["stages"]:
            self.assertLessEqual(
                set(stage["evidence"]["legacy_declaration_ids"]), self.site_ids
            )
        for exclusion in self.registry["excluded_scope"]:
            self.assertLessEqual(
                set(exclusion.get("legacy_declaration_ids", [])), self.site_ids
            )

    def test_every_dependency_edge_resolves(self) -> None:
        for stage in self.registry["stages"]:
            for dependency in stage["depends_on"]:
                self.assertIn(dependency, self.stage_ids)

    def test_every_example_stage_id_resolves(self) -> None:
        referenced: list[str] = []
        for path in sorted(
            (REPOSITORY_ROOT / ANALYSIS / "examples").glob("*.example.json")
        ):
            document = json.loads(path.read_text(encoding="utf-8"))
            referenced += list(_values_for_key(document, "stage_id"))
        self.assertTrue(referenced)
        self.assertLessEqual(set(referenced), self.stage_ids)

    def test_run_lifecycle_rule_ids_are_unique_and_complete(self) -> None:
        triggers = self.registry["run_lifecycle"]["triggers"]
        rule_ids = [trigger["rule_id"] for trigger in triggers]
        self.assertEqual(len(rule_ids), 9)
        self.assertEqual(sorted(rule_ids), [f"RC-{n:02d}" for n in range(1, 10)])
        precedence = self.registry["run_lifecycle"]["trigger_precedence"]
        self.assertEqual(len(precedence), 1)
        ruling = precedence[0]
        by_id = {trigger["rule_id"]: trigger for trigger in triggers}
        for reference in (
            [ruling["winning_rule_id"], ruling["losing_rule_id"]]
            + list(ruling["competing_rule_ids"])
        ):
            self.assertIn(reference, by_id)
        self.assertEqual(
            by_id[ruling["winning_rule_id"]]["trigger"],
            "idempotent_replay_same_key_and_payload",
        )
        self.assertEqual(
            by_id[ruling["losing_rule_id"]]["trigger"], "repeat_of_terminal_run"
        )

    def test_package_schemas_bind_the_registry_contract_by_const(self) -> None:
        for relative in (
            f"{ANALYSIS}/job-package.schema.json",
            f"{ANALYSIS}/result-package.schema.json",
        ):
            with self.subTest(schema=relative):
                block = _load(relative)["$defs"]["stage_registry_ref"]
                self.assertEqual(
                    block["properties"]["contract"]["const"],
                    self.registry["contract"],
                )
                self.assertEqual(
                    block["properties"][CANONICAL_VERSION_KEY]["const"],
                    CANDIDATE_CONTRACT_VERSION,
                )

    def test_alias_resolution_names_the_two_map_contracts(self) -> None:
        alias = self.registry["alias_resolution"]
        self.assertEqual(alias["name_map_contract"], self.names["contract"])
        self.assertEqual(alias["site_map_contract"], self.sites["contract"])

    def test_the_bundled_stage_result_equals_the_standalone_contract(self) -> None:
        bundled = _load(f"{ANALYSIS}/result-package.schema.json")["$defs"]["stage_result"]
        self.assertEqual(bundled, _load(f"{ANALYSIS}/stage-result.schema.json"))

    def test_remapping_a_name_to_another_existing_stage_stays_resolvable(self) -> None:
        """Recorded deliberately: this is the one thing the gates cannot decide.

        Re-pointing a legacy name from one existing stage to another existing stage
        leaves every reference valid. It is a semantic change, caught by review of the
        62 recorded `rationale` strings and by the product authority, never by
        referential integrity. This test asserts the residue exists rather than
        pretending it is closed.
        """
        remapped = json.loads(json.dumps(self.names))
        holders = Counter(
            item["canonical_stage_id"]
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
        )
        entry = next(
            item
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
            and item["canonical_stage_id"] != "norm_verification"
            and holders[item["canonical_stage_id"]] > 1
        )
        entry["canonical_stage_id"] = "norm_verification"
        for item in remapped["names"]:
            if item["resolution"] == "canonical_stage":
                self.assertIn(item["canonical_stage_id"], self.stage_ids)
        covered = {
            item["canonical_stage_id"]
            for item in remapped["names"]
            if item["resolution"] == "canonical_stage"
        }
        self.assertEqual(
            covered,
            self.stage_ids,
            "the chosen probe accidentally orphaned a stage; pick a name whose stage "
            "keeps other evidence, so the remap really is invisible to the gates",
        )


class GoldenBaselineInvariantTests(unittest.TestCase):
    """Selection shape, assertion totals and every declared checksum."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = _load(f"{GOLDEN}/selection.json")
        cls.journeys = [journey["journey_id"] for journey in cls.selection["journeys"]]
        cls.manifests = {
            journey: _load(f"{GOLDEN}/{journey}/manifest.json") for journey in cls.journeys
        }

    def test_the_selected_set_is_five_stable_journeys(self) -> None:
        self.assertEqual(self.journeys, ["GJ-01", "GJ-02", "GJ-03", "GJ-04", "GJ-05"])

    def test_manifest_checksums_match_the_declared_values(self) -> None:
        for journey in self.selection["journeys"]:
            with self.subTest(journey=journey["journey_id"]):
                digest = hashlib.sha256(
                    (
                        REPOSITORY_ROOT / GOLDEN / journey["journey_id"] / "manifest.json"
                    ).read_bytes()
                ).hexdigest()
                self.assertEqual(digest, journey["manifest_sha256"])

    def test_every_input_artifact_checksum_and_size_matches(self) -> None:
        checked = 0
        for journey, manifest in self.manifests.items():
            for artifact in manifest["input_manifest"]["artifacts"]:
                with self.subTest(journey=journey, path=artifact["path"]):
                    payload = (REPOSITORY_ROOT / artifact["path"]).read_bytes()
                    self.assertEqual(
                        hashlib.sha256(payload).hexdigest(), artifact["sha256"]
                    )
                    self.assertEqual(len(payload), artifact["size_bytes"])
                    checked += 1
        self.assertEqual(checked, 19, "the declared input artifact count moved")

    def test_assertion_invariants_recompute_from_the_manifests(self) -> None:
        invariants = self.selection["assertion_invariants"]
        declared = {
            journey: {item["id"] for item in manifest["expected_outputs"]}
            | {item["id"] for item in manifest["failure_cases"]}
            for journey, manifest in self.manifests.items()
        }
        per_journey = {journey: len(ids) for journey, ids in declared.items()}
        self.assertEqual(invariants["per_journey_assertions"], per_journey)
        mapped = [
            identifier
            for row in self.selection["inventory_assertion_coverage"]
            for identifier in row["assertion_ids"]
        ]
        annotated = [
            identifier
            for row in self.selection["target_scope_annotations"]
            for identifier in row["assertion_ids"]
        ]
        self.assertEqual(invariants["inventory_mapped_assertions"], len(mapped))
        self.assertEqual(invariants["target_scope_annotation_assertions"], len(annotated))
        self.assertEqual(invariants["total_assertions"], len(mapped) + len(annotated))
        self.assertEqual(invariants["total_assertions"], 95)
        every = mapped + annotated
        self.assertEqual(len(every), len(set(every)), "an assertion is mapped twice")
        self.assertEqual(set(every), set().union(*declared.values()))

    def test_the_inventory_fan_in_map_is_complete_and_injective(self) -> None:
        fan_in = [
            candidate
            for journey in self.selection["journeys"]
            for candidate in journey["inventory_candidates"]
        ]
        self.assertEqual(
            sorted(fan_in), [f"GJ-{n:02d}" for n in range(1, 12)], "fan-in changed"
        )
        self.assertEqual(len(fan_in), len(set(fan_in)))

    def test_parity_evidence_is_only_ever_a_legacy_observation(self) -> None:
        legacy_commit = None
        for journey, manifest in self.manifests.items():
            for item in manifest["expected_outputs"] + manifest["failure_cases"]:
                with self.subTest(journey=journey, assertion=item["id"]):
                    if item.get("parity_oracle"):
                        self.assertEqual(item["provenance_class"], "legacy_observed")
                    self.assertIn(
                        item["provenance_class"],
                        {"legacy_observed", "greenfield_target", "pending_owner_decision"},
                    )
                    if item["provenance_class"] == "legacy_observed":
                        self.assertTrue(
                            item["legacy_evidence_refs"],
                            "a legacy observation carries no locator",
                        )
                    else:
                        self.assertFalse(
                            item.get("parity_oracle"),
                            "a target divergence is presented as parity evidence",
                        )
            commit = manifest["provenance"]["legacy_source_commit"]
            self.assertRegex(commit, r"^[0-9a-f]{40}$")
            legacy_commit = legacy_commit or commit
            self.assertEqual(commit, legacy_commit, "manifests name two legacy commits")

    def test_the_golden_legacy_commit_is_the_analysis_evidence_commit(self) -> None:
        analysis_commit = _load(f"{ANALYSIS}/legacy-stage-name-map.json")[
            "legacy_source_commit"
        ]
        for journey, manifest in self.manifests.items():
            with self.subTest(journey=journey):
                self.assertEqual(
                    manifest["provenance"]["legacy_source_commit"], analysis_commit
                )


class ArchitectureCoverageTests(unittest.TestCase):
    """ADR coverage and lint-rule coverage, recomputed from the artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = _load(LINT_RULES_JSON)
        cls.rules = cls.spec["rules"]
        cls.rule_ids = {rule["rule_id"] for rule in cls.rules}
        cls.review = _load("docs/architecture/CP00_ARCHITECTURE_REVIEW.json")

    def test_adr_files_index_and_review_agree(self) -> None:
        files = sorted(
            path.name[:8]
            for path in (REPOSITORY_ROOT / "docs/architecture/adr").glob("ADR-*.md")
        )
        self.assertEqual(files, [f"ADR-{n:04d}" for n in range(1, 19)])
        indexed = sorted(set(re.findall(r"ADR-\d{4}", _read("docs/architecture/ADR_INDEX.md"))))
        self.assertEqual(indexed, files)
        reviewed = sorted(entry["adr_id"] for entry in self.review["adrs"])
        self.assertEqual(reviewed, files)
        self.assertEqual(self.review["coverage"]["adrs_total"], len(files))

    def test_markdown_table_and_json_declare_the_same_rule_set(self) -> None:
        table_ids = re.findall(r"^\|\s*(ALR-\d{2})\s*\|", _read(LINT_RULES_MD), re.M)
        self.assertEqual(len(table_ids), len(set(table_ids)))
        self.assertEqual(sorted(table_ids), sorted(self.rule_ids))
        self.assertEqual(len(self.rule_ids), len(self.rules))

    def test_every_rule_identity_is_pinned(self) -> None:
        pin = self.spec["rule_identity_pin"]
        self.assertEqual(sorted(pin), sorted(self.rule_ids))
        for rule in self.rules:
            with self.subTest(rule=rule["rule_id"]):
                self.assertEqual(
                    pin[rule["rule_id"]],
                    {
                        "slug": rule["slug"],
                        "enforcement": rule["enforcement"],
                        "severity": rule["severity"],
                    },
                )
        self.assertEqual(len({rule["slug"] for rule in self.rules}), len(self.rules))

    def test_declared_counts_recompute(self) -> None:
        counts = self.spec["counts"]
        self.assertEqual(counts["rules_total"], len(self.rules))
        self.assertEqual(
            counts["by_enforcement"],
            dict(Counter(rule["enforcement"] for rule in self.rules)),
        )
        self.assertEqual(
            counts["by_severity"], dict(Counter(rule["severity"] for rule in self.rules))
        )
        self.assertEqual(
            counts["static_error_subset"],
            sum(
                1
                for rule in self.rules
                if rule["enforcement"] == "static" and rule["severity"] == "error"
            ),
        )
        self.assertEqual(counts["escalations"], len(self.spec["escalations"]))

    def test_every_agents_md_prohibition_is_covered_exactly_once_over(self) -> None:
        declared = set(self.spec["agents_md_prohibitions"])
        covered = {
            item for rule in self.rules for item in rule.get("covers_prohibitions", [])
        }
        self.assertEqual(declared, covered)
        self.assertEqual(len(declared), self.spec["counts"]["prohibitions_declared"])

    def test_every_alr_reference_in_the_specification_resolves(self) -> None:
        for field in (
            "review_only_subset",
            "handoff_w1_arc_01",
            "open_items",
            "escalations",
            "conflicts_checked_not_escalated",
        ):
            with self.subTest(field=field):
                referenced = set(
                    re.findall(r"ALR-\d{2}", json.dumps(self.spec[field]))
                )
                self.assertLessEqual(referenced, self.rule_ids)

    def test_every_anchor_file_is_a_repository_path(self) -> None:
        anchors = sorted(
            {anchor for rule in self.rules for anchor in rule["anchor_files"]}
        )
        missing = [
            anchor for anchor in anchors if not (REPOSITORY_ROOT / anchor).is_file()
        ]
        self.assertEqual(missing, [])

    def test_ratified_agrees_with_the_external_record(self) -> None:
        """The review may not decide its own ratification.

        This replaces a flat `assertIs(ratified, False)`. That pin was correct about the
        danger and wrong about the mechanism: it made ratification impossible rather than
        making self-ratification impossible, and `W0-INT-01` could not do its declared
        job without turning the suite red. The danger is unchanged and so is the answer
        to it — the flag is compared against a record kept outside the artifact.
        """
        external_ratified, _, problems = _ratification_record(REPOSITORY_ROOT)
        declared_here = self.review["ratified"]
        self.assertIsInstance(declared_here, bool)
        if declared_here:
            self.assertEqual(
                problems,
                [],
                "the review declares itself ratified and the external record does not "
                "admissibly say so",
            )
        self.assertEqual(
            declared_here,
            external_ratified,
            f"{LINT_RULES_JSON.rsplit('/', 1)[0]}/CP00_ARCHITECTURE_REVIEW.json says "
            f"ratified={declared_here} while {CHECKPOINT_MANIFEST} says "
            f"ratified={external_ratified}. A candidate cannot ratify itself, and a "
            "recorded ratification that the review does not carry is equally a "
            "contradiction.",
        )


class MutationTests(unittest.TestCase):
    """Each check is proved by breaking exactly the thing it claims to protect.

    Every mutation is applied to a `tempfile.mkdtemp()` copy. The candidate tree is
    never opened for writing.
    """

    def setUp(self) -> None:
        self.copies: list[_MutableCopy] = []

    def tearDown(self) -> None:
        for copy in self.copies:
            copy.close()

    def _copy(self, subtrees: tuple[str, ...] = ("contracts",)) -> _MutableCopy:
        copy = _MutableCopy(subtrees)
        self.copies.append(copy)
        return copy

    def _assert_gate_rejects(self, copy: _MutableCopy, letter: str, needle: str) -> None:
        result = copy.run_gate(letter)
        self.assertNotEqual(
            result.returncode,
            0,
            f"Gate {letter} accepted the mutation.\nstdout: {result.stdout.strip()}",
        )
        self.assertIn(needle, result.stdout + result.stderr)

    def _assert_gate_accepts(self, copy: _MutableCopy, letter: str) -> None:
        result = copy.run_gate(letter)
        self.assertEqual(
            result.returncode,
            0,
            f"Gate {letter} rejected the mutation, so it does not isolate the gate "
            f"under test.\nstderr: {result.stderr.strip()}",
        )

    def test_mutation_rotated_run_lifecycle_rule_ids(self) -> None:
        """`RC-01`..`RC-09` rotated by one across the nine triggers."""
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        triggers = registry["run_lifecycle"]["triggers"]
        rotated = [trigger["rule_id"] for trigger in triggers][1:] + [
            triggers[0]["rule_id"]
        ]
        for trigger, rule_id in zip(triggers, rotated):
            trigger["rule_id"] = rule_id
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_rejects(
            copy, "D", "a trigger carries a rule_id the owner ruling does not give it"
        )

    def test_mutation_swapped_two_canonical_stage_ids(self) -> None:
        """Two `stage_id` values exchanged. Every reference still resolves.

        This is the case existence checking cannot see: the identifier set is unchanged,
        so Gate A stays green and only Gate C's identity pin — capability evidence plus
        produced artifact roles — notices that a `stage_id` no longer denotes its stage.
        """
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        by_id = {stage["stage_id"]: stage for stage in registry["stages"]}
        by_id["text_analysis"]["stage_id"] = "block_analysis"
        by_id["block_analysis"]["stage_id"] = "text_analysis"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy,
            "C",
            "a stage_id no longer denotes the stage whose capability evidence and "
            "produced roles it carries",
        )

    def test_mutation_renamed_a_referenced_exclusion_id(self) -> None:
        """`XS-07` renamed. A name map entry points at it, so the reference dangles."""
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        for exclusion in registry["excluded_scope"]:
            if exclusion["excluded_scope_id"] == "XS-07":
                exclusion["excluded_scope_id"] = "XS-77"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_rejects(copy, "A", "excluded_scope_id absent from registry")
        self._assert_gate_rejects(
            copy,
            "C",
            "the eleven exclusion ids are not the ones every excluded_scope_id "
            "reference resolves against",
        )

    def test_mutation_renamed_an_unreferenced_exclusion_id(self) -> None:
        """`XS-02` is named by no name-map entry, so existence checking is blind to it.

        Gate A accepts the rename; Gate C's identity pin rejects it. Recorded because it
        shows the two gates are not redundant.
        """
        copy = self._copy()
        registry = copy.load(f"{ANALYSIS}/stage-registry.json")
        referenced = {
            entry["excluded_scope_id"]
            for entry in copy.load(f"{ANALYSIS}/legacy-stage-name-map.json")["names"]
            if entry["resolution"] == "excluded"
        }
        self.assertNotIn("XS-02", referenced, "XS-02 gained a reference; pick another")
        for exclusion in registry["excluded_scope"]:
            if exclusion["excluded_scope_id"] == "XS-02":
                exclusion["excluded_scope_id"] = "XS-72"
        copy.store(f"{ANALYSIS}/stage-registry.json", registry)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy,
            "C",
            "the eleven exclusion ids are not the ones every excluded_scope_id "
            "reference resolves against",
        )

    def test_mutation_observation_moved_to_a_site_that_lacks_its_name(self) -> None:
        """One evidence observation re-pointed at a declaration site in another file.

        The observed-site bookkeeping is updated with it, so Gate A stays green and the
        file-level binding in Gate B is the only thing standing between the map and an
        observation attributed to a site that never carried the name.
        """
        copy = self._copy()
        name_map = copy.load(f"{ANALYSIS}/legacy-stage-name-map.json")
        entry = name_map["names"][0]
        origin = entry["source_declaration_id"]
        entry["source_declaration_id"] = "LSD-31"
        entry["observed_declaration_ids"] = sorted(
            set(entry["observed_declaration_ids"]) - {origin} | {"LSD-31"}
        )
        copy.store(f"{ANALYSIS}/legacy-stage-name-map.json", name_map)
        self._assert_gate_accepts(copy, "A")
        self._assert_gate_rejects(
            copy, "B", "the evidence is not in the file this declaration site names"
        )

    def test_mutation_example_names_a_stage_absent_from_the_registry(self) -> None:
        """A valid example points at a stage that does not exist."""
        copy = self._copy()
        relative = f"{ANALYSIS}/examples/job-package.example.json"
        example = copy.load(relative)

        def rename(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "stage_id" and isinstance(value, str):
                        node[key] = "absent_stage_name"
                    else:
                        rename(value)
            elif isinstance(node, list):
                for value in node:
                    rename(value)

        rename(example)
        copy.store(relative, example)
        self._assert_gate_rejects(
            copy, "A", "an example names a stage_id absent from the registry"
        )

    def test_mutation_domain_reintroduces_a_bare_version_key(self) -> None:
        """The deprecated domain mirror comes back. Two independent gates reject it."""
        copy = self._copy()
        relative = f"{DOMAIN}/error-codes.json"
        catalog = copy.load(relative)
        catalog["version"] = CANDIDATE_CONTRACT_VERSION
        copy.store(relative, catalog)

        family = [
            block
            for block in _documented_blocks(DOMAIN_README)
            if "bare version key present" in block
        ]
        self.assertEqual(len(family), 1, "the domain family gate moved")
        result = copy.run_block(family[0])
        self.assertNotEqual(result.returncode, 0, "the domain family gate accepted it")
        self.assertIn("bare version key present", result.stderr)

        sweep = [
            block
            for block in _documented_blocks(EVENTS_README)
            if "if p.endswith('.invalid.json'): continue" in block
        ]
        self.assertEqual(len(sweep), 1, "the recursive version sweep moved")
        swept = copy.run_block(sweep[0])
        self.assertNotEqual(swept.returncode, 0, "the recursive sweep accepted it")
        self.assertIn("error-codes.json", swept.stderr)

        from jsonschema import Draft202012Validator

        errors = list(
            Draft202012Validator(_load(f"{DOMAIN}/error-codes.schema.json")).iter_errors(
                catalog
            )
        )
        self.assertTrue(errors, "the owning schema tolerated the reintroduced key")

    def test_mutation_events_reintroduce_schema_version(self) -> None:
        """The retired envelope key comes back, in the example and in the schema."""
        copy = self._copy()
        relative = f"{EVENTS}/examples/event-envelope.example.json"
        example = copy.load(relative)
        example["schema_version"] = 1
        copy.store(relative, example)

        sweep = [
            block
            for block in _documented_blocks(EVENTS_README)
            if "if p.endswith('.invalid.json'): continue" in block
        ]
        result = copy.run_block(sweep[0])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event-envelope.example.json", result.stderr)

        from jsonschema import Draft202012Validator

        errors = list(
            Draft202012Validator(
                _load(f"{EVENTS}/event-envelope.schema.json")
            ).iter_errors(example)
        )
        self.assertTrue(errors, "the envelope schema accepted schema_version")

        schema_copy = self._copy()
        schema_relative = f"{EVENTS}/event-envelope.schema.json"
        schema = schema_copy.load(schema_relative)
        schema["properties"]["schema_version"] = {"const": 1}
        schema["required"].append("schema_version")
        schema_copy.store(schema_relative, schema)
        swept = schema_copy.run_block(sweep[0])
        self.assertNotEqual(swept.returncode, 0)
        self.assertIn("event-envelope.schema.json", swept.stderr)

    def test_mutation_forbidden_authority_field_name(self) -> None:
        """`execution_token` renamed back to `authority_token` in a package schema."""
        copy = self._copy()
        relative = f"{ANALYSIS}/job-package.schema.json"
        schema = copy.load(relative)
        authority = schema["$defs"]["attempt_authority"]
        authority["properties"]["authority_token"] = authority["properties"].pop(
            "execution_token"
        )
        authority["required"] = [
            "authority_token" if name == "execution_token" else name
            for name in authority["required"]
        ]
        copy.store(relative, schema)
        self._assert_gate_rejects(copy, "A", "job-package.schema.json")

    def test_mutation_golden_manifest_byte_change_breaks_its_checksum(self) -> None:
        """One byte of a manifest, so the declared `manifest_sha256` no longer holds."""
        copy = self._copy(("fixtures",))
        path = copy.root / GOLDEN / "GJ-01/manifest.json"
        path.write_bytes(path.read_bytes().replace(b'"schema_version": 1', b'"schema_version":  1'))
        blocks = _documented_blocks(SELECTION_MD)
        result = copy.run_block(blocks[0])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "False",
            result.stdout,
            "the declared manifest checksum survived a change to the manifest bytes",
        )

    def test_mutation_golden_dropped_assertion_breaks_the_declared_totals(self) -> None:
        """One assertion removed from a manifest; the coverage gate must notice."""
        copy = self._copy(("fixtures",))
        relative = f"{GOLDEN}/GJ-01/manifest.json"
        manifest = copy.load(relative)
        manifest["expected_outputs"] = manifest["expected_outputs"][:-1]
        copy.store(relative, manifest)
        blocks = _documented_blocks(SELECTION_MD)
        result = copy.run_block(blocks[1])
        self.assertNotEqual(
            result.returncode, 0, "the coverage gate accepted a dropped assertion"
        )
        self.assertIn("AssertionError", result.stderr)

    def test_mutation_candidate_drift_is_detected(self) -> None:
        """The integrity check itself, exercised in the direction that must fail.

        A green byte-identity result is worthless unless the same comparison rejects a
        changed byte. This copies the object database into a scratch tree, changes one
        contract there and asserts the comparison names exactly that path — and it uses
        the same policy function the live check uses, so it exercises the real predicate
        rather than a simplified twin.
        """
        with _CheckpointSandbox() as sandbox:
            # Normalised, so this probe means the same thing before and after
            # ratification. Without it the sandbox inherits whatever the host tree
            # happens to be, and every negative assertion below inherits it too.
            sandbox.normalise_to_candidate()
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                [],
                "the scratch copy did not start out identical to the candidate",
            )
            target = sandbox.root / DOMAIN / "error-codes.json"
            # A pure reformat: the parsed value is unchanged and only the bytes move.
            target.write_text(
                json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=4)
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                [f"{DOMAIN}/error-codes.json"],
                "a re-indented contract was accepted as byte-identical",
            )
            (sandbox.root / ANALYSIS / "stage-registry.json").unlink()
            self.assertEqual(
                _undeclared_drift(sandbox.root),
                sorted(
                    [f"{DOMAIN}/error-codes.json", f"{ANALYSIS}/stage-registry.json"]
                ),
                "a deleted contract was not reported as drift",
            )
            new_artifact = sandbox.root / "docs/architecture/NEW_DOCUMENT.md"
            new_artifact.write_text("# added after the candidate\n", encoding="utf-8")
            self.assertIn(
                "docs/architecture/NEW_DOCUMENT.md",
                _undeclared_drift(sandbox.root),
                "a file added after the candidate was invisible to the drift check",
            )

    def test_mutation_lint_rule_rename_breaks_the_identity_pin(self) -> None:
        """A `rule_id` renamed inside a rule row while its pin entry stays put."""
        copy = self._copy(("docs",))
        relative = LINT_RULES_JSON
        spec = copy.load(relative)
        spec["rules"][0]["rule_id"] = "ALR-99"
        copy.store(relative, spec)
        gate_c = [
            block
            for block in _documented_blocks(LINT_RULES_MD)
            if "identity pin ok" in block
        ]
        self.assertEqual(len(gate_c), 1)
        result = copy.run_block(gate_c[0])
        self.assertNotEqual(result.returncode, 0, "the identity pin accepted a rename")


class RatificationRecordTests(unittest.TestCase):
    """What counts as a declared ratification delta, proved in both directions.

    The policy, stated once so it cannot be widened by reading:

    * **`contracts/**`, `fixtures/**`, `scripts/**` — never.** Ratification does not
      reach them. No record licenses a byte.
    * **`docs/architecture/**` — only under all four conditions at once.** An external
      record in `artifacts/checkpoints/CP-00/manifest.json` says `ratified: true`; that
      record carries a `ratification` object naming `allowed_delta_paths` plus its task,
      date, authority and reason; every named path lies under `docs/architecture/`, is
      inside `RATIFICATION_DELTA_CEILING`, and already existed at the reviewed
      candidate. A file outside the named set is drift, exactly as before.
    * **The ceiling is pinned here, not in the record.** The record may name fewer paths
      than the ceiling and never one outside it, so nobody can widen the delta by
      editing the record they also write. Widening means editing this module, which only
      `W0-QA-01` owns, which means reopening this task and another independent review.
    * **The review may not decide its own ratification.** `ratified` in
      `CP00_ARCHITECTURE_REVIEW.json` must equal the external record's, in both
      directions.

    Every probe below runs against a throwaway copy of the whole repository. The
    candidate is never written.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = _CheckpointSandbox()
        cls.sandbox.normalise_to_candidate()
        cls.review = "docs/architecture/CP00_ARCHITECTURE_REVIEW.json"
        cls.full_delta = sorted(RATIFICATION_DELTA_CEILING)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__()

    def setUp(self) -> None:
        self.addCleanup(self.sandbox.restore)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "the sandbox did not start clean",
        )

    def _ratify(self, paths: list[str] | None = None, **kwargs: object) -> None:
        """Apply a realistic ratification: the record, the flag, and the five edits."""
        declared = self.full_delta if paths is None else paths
        self.sandbox.declare_ratification(declared, **kwargs)
        self.sandbox.patch_json(self.review, ratified=True)
        for relative in declared:
            if relative != self.review and relative in RATIFICATION_DELTA_CEILING:
                self.sandbox.edit(relative)

    # ---- the direction that must pass -------------------------------------------

    def test_declared_ratification_of_the_whole_ceiling_is_accepted(self) -> None:
        self._ratify()
        external, declared, problems = _ratification_record(self.sandbox.root)
        self.assertTrue(external)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(declared), self.full_delta)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "a fully declared ratification was rejected, so ratification is still "
            "impossible and this reopening achieved nothing",
        )
        self.assertEqual(_immutable_family_drift(self.sandbox.root), [])
        self.assertEqual(
            sorted(_drifted_reviewed_paths(self.sandbox.root)),
            self.full_delta,
            "the drift is still observed and reported; it is licensed, not invisible",
        )

    def test_a_partial_declaration_is_rejected(self) -> None:
        """Inverted in round four. It used to assert the opposite, and was wrong.

        `test_a_partial_declared_ratification_is_accepted` asserted that "the record may
        name fewer paths than the ceiling", which pinned the defect as a property: an
        independent negative probe declared all five files, changed one, and the suite
        stayed green — four obligatory reconciliations skippable with the record still
        claiming them. For CP-00 the ceiling is not a menu. Each of the five is a
        reconciliation ratification owes, so the declared set must be all of it.
        """
        subset = [self.review, "docs/architecture/ADR_INDEX.md"]
        self._ratify(subset)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("does not declare every reconciliation" in problem for problem in problems),
            problems,
        )
        self.assertNotEqual(_ratification_delta_problems(self.sandbox.root), [])

    # ---- the directions that must fail ------------------------------------------

    def test_declaring_five_reconciliations_and_making_one_is_rejected(self) -> None:
        """The exact false positive an independent negative probe produced.

        Full record, full declared set, one file actually reconciled. Nothing is
        undeclared, so the one-directional check said `[]` and the suite was green while
        four obligatory reconciliations had not been made.
        """
        self.sandbox.declare_ratification(self.full_delta)
        self.sandbox.patch_json(self.review, ratified=True)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(problems, [], "the record itself is admissible")
        self.assertEqual(sorted(declared), self.full_delta)
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            [],
            "precondition: the one-directional check sees nothing wrong here",
        )
        skipped = [path for path in self.full_delta if path != self.review]
        self.assertEqual(
            _unperformed_declarations(self.sandbox.root),
            skipped,
            "the four unmade reconciliations must be named",
        )
        delta_problems = _ratification_delta_problems(self.sandbox.root)
        self.assertTrue(
            any("Declaring the work is not doing it" in problem for problem in delta_problems),
            delta_problems,
        )

    def test_a_fully_declared_and_fully_performed_ratification_is_accepted(self) -> None:
        """The other side of the same rule: do all five and the suite is green."""
        self._ratify()
        self.assertEqual(_ratification_delta_problems(self.sandbox.root), [])
        self.assertEqual(_unperformed_declarations(self.sandbox.root), [])

    def test_ratification_without_any_record_is_drift(self) -> None:
        self.sandbox.patch_json(self.review, ratified=True)
        self.sandbox.edit("docs/architecture/ADR_INDEX.md")
        external, _, _ = _ratification_record(self.sandbox.root)
        self.assertFalse(external, "the manifest still says unratified")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            ["docs/architecture/ADR_INDEX.md", self.review],
            "a self-declared ratification with no external record was accepted",
        )

    def test_both_directions_are_reported_at_once(self) -> None:
        """One reconciliation skipped and one stranger edited, in the same tree.

        The two failure modes are independent and neither may mask the other: the
        stranger must be named as undeclared drift and the skipped file as an unmade
        reconciliation, from a single evaluation.
        """
        self._ratify()
        skipped = "docs/architecture/ADR_INDEX.md"
        self.sandbox.restore_one(skipped)
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root), ["docs/architecture/GLOSSARY.md"]
        )
        self.assertEqual(_unperformed_declarations(self.sandbox.root), [skipped])
        problems = _ratification_delta_problems(self.sandbox.root)
        self.assertTrue(any("no ratification record accounts" in x for x in problems), problems)
        self.assertTrue(any("Declaring the work is not doing it" in x for x in problems), problems)

    def test_an_undeclared_architecture_file_outside_the_ceiling_is_drift(self) -> None:
        """`GLOSSARY.md` is in the reviewed family and outside the ceiling."""
        self._ratify()
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            ["docs/architecture/GLOSSARY.md"],
        )

    def test_a_record_naming_a_path_above_the_ceiling_licenses_nothing(self) -> None:
        """The anti-widening control: the record cannot enlarge its own authority."""
        self._ratify(self.full_delta + ["docs/architecture/GLOSSARY.md"])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("outside the ratification ceiling" in problem for problem in problems),
            problems,
        )
        self.assertEqual(
            _undeclared_drift(self.sandbox.root),
            self.full_delta,
            "an inadmissible record still licensed a delta; every path it named must "
            "come back as drift, including the ones that were inside the ceiling",
        )

    def test_a_record_naming_a_path_outside_the_family_licenses_nothing(self) -> None:
        self._ratify([self.review, f"{DOMAIN}/error-codes.json"])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("may not reach outside" in problem for problem in problems), problems
        )

    def test_a_record_naming_a_path_absent_at_the_candidate_licenses_nothing(self) -> None:
        new_path = "docs/architecture/RATIFICATION_NOTE.md"
        (self.sandbox.root / new_path).write_text("# new\n", encoding="utf-8")
        self.addCleanup(lambda: (self.sandbox.root / new_path).unlink(missing_ok=True))
        self._ratify([self.review, new_path])
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(
            any("need review rather than ratification" in p for p in problems), problems
        )

    def test_every_immutable_family_stays_immutable_under_ratification(self) -> None:
        self._ratify()
        for relative in (
            f"{DOMAIN}/error-codes.json",
            f"{GOLDEN}/selection.json",
            "scripts/validate_bootstrap.py",
        ):
            with self.subTest(path=relative):
                self.sandbox.edit(relative, marker="\n")
                self.assertIn(relative, _immutable_family_drift(self.sandbox.root))
                self.assertIn(relative, _undeclared_drift(self.sandbox.root))

    def test_a_record_missing_its_provenance_licenses_nothing(self) -> None:
        for field in RATIFICATION_REQUIRED_FIELDS:
            with self.subTest(missing=field):
                self._ratify(omit=(field,))
                _, declared, problems = _ratification_record(self.sandbox.root)
                self.assertEqual(declared, frozenset())
                self.assertTrue(
                    any(f"ratification.{field}" in problem for problem in problems),
                    problems,
                )
                self.sandbox.restore()

    def test_a_record_from_the_wrong_task_licenses_nothing(self) -> None:
        self._ratify(task="W0-ARC-02")
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(any("may ratify CP-00" in problem for problem in problems))

    def test_a_ratified_flag_with_no_ratification_object_licenses_nothing(self) -> None:
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=True)
        _, declared, problems = _ratification_record(self.sandbox.root)
        self.assertEqual(declared, frozenset())
        self.assertTrue(any("carries no 'ratification' object" in p for p in problems))

    def test_an_empty_or_repeating_path_list_licenses_nothing(self) -> None:
        for paths in ([], [self.review, self.review]):
            with self.subTest(paths=paths):
                self.sandbox.declare_ratification(paths)
                _, declared, problems = _ratification_record(self.sandbox.root)
                self.assertEqual(declared, frozenset())
                self.assertTrue(problems)
                self.sandbox.restore()

    def test_a_recorded_ratification_the_review_does_not_carry_is_a_contradiction(
        self,
    ) -> None:
        """The other direction of the flag check: record true, artifact still false."""
        self.sandbox.declare_ratification(self.full_delta)
        external, _, problems = _ratification_record(self.sandbox.root)
        self.assertTrue(external)
        self.assertEqual(problems, [])
        review = json.loads(
            (self.sandbox.root / self.review).read_text(encoding="utf-8")
        )
        self.assertIs(
            review["ratified"],
            False,
            "probe precondition: the review has not been ratified in the sandbox",
        )
        self.assertNotEqual(
            review["ratified"],
            external,
            "the flag check must reject a record the artifact does not carry",
        )

    def test_the_manifest_does_not_contradict_itself(self) -> None:
        """A record cannot pre-authorise a delta it has not taken.

        Structural, and independent of the registry: whatever format the human registry
        ends up carrying, the machine record must not hold a `ratification` object while
        declaring `ratified: false`.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest)
        if manifest.get("ratified") is not True:
            self.assertNotIn(
                "ratification",
                manifest,
                f"{CHECKPOINT_MANIFEST} carries a ratification object while declaring "
                "itself unratified",
            )

    def test_the_two_external_records_do_not_contradict_each_other(self) -> None:
        """Compared by structure. The previous form read English and was wrong.

        It asked whether the row contained the word `ratified`, which matches inside
        `not ratified`: a registry line *denying* ratification was indistinguishable
        from one confirming it, in both directions — a manifest saying `ratified: true`
        beside a row reading "not ratified" passed, and today's honest "not ratified"
        beside `ratified: false` failed. That is the same defect class this wave
        rejected three candidates for: a gate whose claim lives in prose rather than in
        checkable structure. No better prose parser replaces it; the row is not read as
        English at all.

        What is read instead is the one machine-readable element the row already
        carries: it cites, in a code span, the manifest key that holds CP-00's state.
        Today it cites `ratification_blocked`; a ratified checkpoint cites
        `ratification`. The vocabulary is closed, the tokens are identifiers rather than
        words, and negation cannot flip their meaning because no English is consulted.

        This formalises an existing convention rather than inventing a field, and it is
        satisfied by the registry as it stands. If the repository owner would rather the
        registry carry a first-class state column, that is a registry-format decision
        for the checkpoint-registry owner, not something this module should guess at;
        `docs/program/reviews/W0-QA-01.md` §11.4 records the request.
        """
        self.assertIsNone(_registry_state_problem(REPOSITORY_ROOT))

    def test_the_two_records_are_compared_on_all_four_combinations(self) -> None:
        """Manifest state x registry state, every pairing, prose deliberately hostile.

        Each row pairs the structural token with English that says the opposite of what
        the token says, so a predicate that read the prose would get every row wrong.
        The two agreeing combinations must pass and the two contradicting ones must
        fail, whatever the sentence around the token happens to say.
        """
        confirming = "ratified 2026-09-02; tag not yet published"
        denying = "not ratified; not tagged"
        cases = [
            (True, RATIFIED_STATE_TOKEN, denying, None),
            (True, UNRATIFIED_STATE_TOKEN, confirming, "declares ratified=True"),
            (False, UNRATIFIED_STATE_TOKEN, confirming, None),
            (False, RATIFIED_STATE_TOKEN, denying, "declares ratified=False"),
        ]
        for ratified, token, prose, expected in cases:
            with self.subTest(manifest=ratified, registry=token):
                if ratified:
                    self.sandbox.declare_ratification(self.full_delta)
                else:
                    self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
                self.sandbox.set_registry_state(token, prose)
                problem = _registry_state_problem(self.sandbox.root)
                if expected is None:
                    self.assertIsNone(
                        problem,
                        f"agreeing records were rejected; the prose read {prose!r}",
                    )
                else:
                    self.assertIsNotNone(
                        problem,
                        f"contradicting records were accepted; the prose read {prose!r}",
                    )
                    self.assertIn(expected, problem)
                self.sandbox.restore()

    def test_a_registry_row_carrying_no_state_token_is_rejected(self) -> None:
        """The exact counterexamples the independent reviewer produced.

        Both sentences defeated the previous predicate: `\\bratified\\b` matched inside
        `not ratified`, so a denial read as a confirmation. Neither carries a state
        token, so both are now definite failures naming the token to write.
        """
        for prose in ("ratified 2026-09-02; tag not yet published", "not ratified; not tagged"):
            for ratified in (True, False):
                with self.subTest(prose=prose, manifest=ratified):
                    if ratified:
                        self.sandbox.declare_ratification(self.full_delta)
                    else:
                        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
                    self.sandbox.set_registry_state(None, prose)
                    problem = _registry_state_problem(self.sandbox.root)
                    self.assertIsNotNone(problem, "a stateless row was accepted")
                    self.assertIn("must cite exactly one manifest state key", problem)
                    self.sandbox.restore()

    def test_the_comparison_does_not_depend_on_manifest_history(self) -> None:
        """Dropping the spent `ratification_blocked` key must not change the verdict.

        The first form of this check also demanded that the manifest still carry a key
        named by the token. That coupled the two-record comparison to whether history
        was kept: a ratified manifest that retired the blocked entry, exactly as
        `W0-INT-01` would, flipped agreeing records into a failure. Removed, and pinned
        here so it cannot come back.
        """
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
        self.sandbox.drop_json_key(CHECKPOINT_MANIFEST, UNRATIFIED_STATE_TOKEN)
        self.sandbox.set_registry_state(UNRATIFIED_STATE_TOKEN, "not ratified")
        self.assertIsNone(_registry_state_problem(self.sandbox.root))

    def test_a_registry_row_citing_both_tokens_is_rejected(self) -> None:
        """Ambiguity is a failure, not a coin toss."""
        self.sandbox.patch_json(CHECKPOINT_MANIFEST, ratified=False)
        self.sandbox.set_registry_state(
            UNRATIFIED_STATE_TOKEN,
            f"not ratified, and not yet `{RATIFIED_STATE_TOKEN}`",
        )
        problem = _registry_state_problem(self.sandbox.root)
        self.assertIsNotNone(problem)
        self.assertIn("must cite exactly one manifest state key", problem)

    def test_the_acceptance_digest_model_is_structurally_sound(self) -> None:
        """The split into a tested-input digest and an evidence digest is correct.

        An earlier form recorded one digest computed after the acceptance results were
        written, so it identified the post-acceptance tree rather than the input the
        streams judged. Splitting it is the right fix and this test does not argue with
        it. What it checks is that the split is *present and closed*: both fields exist,
        the retired single field has not come back, and the model documents both.

        What it deliberately does **not** do is recompute either value. See
        `docs/program/reviews/W0-QA-01.md` §11.9: three fields are missing before that
        is possible, and a test that recomputed them anyway would be implementing a
        recipe nobody wrote down.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest, f"{CHECKPOINT_MANIFEST} is missing")
        for field in ACCEPTANCE_DIGEST_FIELDS:
            self.assertIn(
                field, manifest, f"{CHECKPOINT_MANIFEST} lost the {field} field"
            )
        self.assertNotIn(
            "candidate_digest",
            manifest,
            "the retired single-digest field is back; it identified the tree that "
            "carried the acceptance results rather than the tree the streams judged",
        )
        model = manifest.get("digest_model")
        self.assertIsInstance(model, dict, "digest_model is missing")
        for field in ACCEPTANCE_DIGEST_FIELDS + ("artifact_manifest_sha256",):
            self.assertIn(field, model, f"digest_model does not explain {field}")

    def test_the_acceptance_digests_are_well_formed_distinct_and_present_when_ratified(
        self,
    ) -> None:
        """Shape, mutual difference, and the link that stops them staying empty.

        `null` is a legitimate state — the candidate is being rebuilt and no round has
        been dispatched — but it may not survive into ratification, or the split would
        be decorative: a checkpoint could ratify with no record of what was tested.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        values = {field: manifest.get(field) for field in ACCEPTANCE_DIGEST_FIELDS}
        for field, value in values.items():
            with self.subTest(field=field):
                if value is not None:
                    self.assertRegex(
                        str(value),
                        r"^[0-9a-f]{64}$",
                        f"{field} is neither null nor a SHA-256 digest",
                    )
        if manifest.get("ratified") is True:
            unset = sorted(field for field, value in values.items() if value is None)
            self.assertEqual(
                unset,
                [],
                "CP-00 cannot ratify while these are unrecorded: a ratified checkpoint "
                "must say which tree the streams judged and which tree carries their "
                "evidence",
            )
        recorded = [value for value in values.values() if value is not None]
        if len(recorded) == 2:
            self.assertNotEqual(
                recorded[0],
                recorded[1],
                "the two digests are equal, so the evidence tree and the tested tree "
                "are the same tree — which is the defect the split exists to prevent: "
                "writing the results changes the tree",
            )

    def test_the_reviewed_manifest_recipe_moves_when_a_reviewed_file_does(self) -> None:
        """A digest nobody proves sensitive is a digest nobody has verified.

        `artifact_manifest_sha256` is the one manifest digest whose recipe is still
        recorded accurately, so it is the one whose sensitivity can be demonstrated
        rather than assumed. One byte in any tracked reviewed file must change it.
        """
        baseline, count = _reviewed_manifest_digest(self.sandbox.root)
        self.sandbox.edit("docs/architecture/GLOSSARY.md")
        changed, changed_count = _reviewed_manifest_digest(self.sandbox.root)
        self.assertNotEqual(
            baseline, changed, "a changed reviewed file left the manifest digest alone"
        )
        self.assertEqual(count, changed_count)

    def test_the_manifest_digest_describes_the_tree_it_manifests(self) -> None:
        """The external record must be true about the tree it covers.

        Recomputed with the manifest's own recipe. Before ratification this is the
        candidate digest; after ratification the integrator must recompute it, which is
        the point — a record that kept the pre-ratification digest would be describing a
        tree that no longer exists.
        """
        manifest = _checkpoint_manifest(REPOSITORY_ROOT)
        self.assertIsNotNone(manifest, f"{CHECKPOINT_MANIFEST} is missing")
        digest, count = _reviewed_manifest_digest(REPOSITORY_ROOT)
        self.assertEqual(manifest["artifact_count"], count)
        self.assertEqual(
            manifest["artifact_manifest_sha256"],
            digest,
            "artifact_manifest_sha256 does not match the tracked reviewed families; "
            "recompute it with the recipe the manifest itself records",
        )


class WriteBoundaryTests(unittest.TestCase):
    """This task owns two paths. Nothing else under them may appear.

    The gate asserts a path set, never a status code, so it holds before integration
    (`??`), while the files are being edited (` M`) and once they are committed and
    clean (no output at all) — the repair `W0-CLN-01` had to make to `GATE-F` after that
    gate became unsatisfiable by its own integration. `--untracked-files=all` is not
    decoration: `docs/program/reviews/` is a new directory, and the default
    `--untracked-files=normal` collapses a wholly untracked directory to a single
    directory entry, so without the flag the gate reports `docs/program/reviews/` and
    can never name the file it is about.
    """

    def test_only_the_two_owned_paths_are_reported_under_the_owned_trees(self) -> None:
        owned = {
            "tests/contract/test_cp00_candidate.py",
            "docs/program/reviews/W0-QA-01.md",
        }
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "tests/contract",
                "docs/program/reviews",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        reported = {line[3:] for line in result.stdout.splitlines() if line}
        self.assertEqual(
            sorted(reported - owned),
            [],
            "a path outside this task's two allowed paths is dirty",
        )
        missing = sorted(
            path for path in owned if not (REPOSITORY_ROOT / path).is_file()
        )
        self.assertEqual(missing, [], "an owned deliverable is missing")

    def test_the_reviewed_families_carry_nothing_undeclared(self) -> None:
        """No working-tree change under a reviewed family beyond the declared delta.

        The earlier form asserted the status output was empty. That was one-directional
        in the way this wave keeps finding: it passed before a ratification edit and
        again after the edit was committed, and failed only in between — a gate that
        reports on the phase of the work rather than on the work. It now asserts the
        path set against the same declared delta the drift check uses, so it holds in
        every phase and still fails on any path nobody declared.
        """
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "contracts",
                "fixtures",
                "docs/architecture",
                "scripts",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        reported = {line[3:] for line in result.stdout.splitlines() if line}
        _, declared, problems = _ratification_record(REPOSITORY_ROOT)
        licensed = frozenset() if problems else declared
        self.assertEqual(
            sorted(reported - licensed),
            [],
            "a reviewed artifact is dirty and no ratification record declares it; "
            "this review writes to nothing it reviews",
        )


if __name__ == "__main__":
    unittest.main()
