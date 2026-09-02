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

#: Every reviewed family. Byte identity with the candidate is asserted over all of them.
REVIEWED_PREFIXES = ("contracts/", "fixtures/", "docs/architecture/", "scripts/")

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


def _drifted_reviewed_paths(root: Path) -> list[str]:
    """Reviewed paths whose bytes on disk differ from the candidate commit's blob.

    The comparison is byte-for-byte on purpose. A parsed-JSON comparison is blind to
    re-indentation and key reordering, and the hashes this review records are hashes of
    bytes, so anything weaker would certify a document nobody hashed.
    """
    drifted: list[str] = []
    for relative in _candidate_reviewed_paths(root):
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
        on_disk = root / relative
        if blob.returncode != 0 or not on_disk.is_file():
            drifted.append(relative)
        elif blob.stdout != on_disk.read_bytes():
            drifted.append(relative)
    return drifted


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
    """

    def test_reviewed_families_are_byte_identical_to_the_candidate(self) -> None:
        reviewed = _candidate_reviewed_paths(REPOSITORY_ROOT)
        # The candidate is immutable, so its reviewed file count is a fixed number. A
        # different count means a different tree, not a looser check.
        self.assertEqual(
            len(reviewed),
            100,
            "the candidate's reviewed file set is not the one this report describes",
        )
        self.assertEqual(
            _drifted_reviewed_paths(REPOSITORY_ROOT),
            [],
            "these reviewed artifacts differ from the candidate the report certifies",
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
        for position, (label, block) in enumerate(blocks):
            with self.subTest(gate=label, position=position):
                result = _run_shell(block, REPOSITORY_ROOT)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{label} block {position} failed: {result.stderr.strip()}",
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

    def test_the_review_is_not_yet_ratified(self) -> None:
        """`W0-INT-01` ratifies; a candidate that ratified itself would be the defect."""
        self.assertIs(self.review["ratified"], False)


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
        contract there and asserts the comparison names exactly that path.
        """
        scratch = Path(tempfile.mkdtemp(prefix="w0-qa-01-drift-"))
        try:
            shutil.copytree(REPOSITORY_ROOT / ".git", scratch / ".git")
            for subtree in ("contracts", "fixtures", "docs", "scripts"):
                shutil.copytree(REPOSITORY_ROOT / subtree, scratch / subtree)
            self.assertEqual(
                _drifted_reviewed_paths(scratch),
                [],
                "the scratch copy did not start out identical to the candidate",
            )
            target = scratch / DOMAIN / "error-codes.json"
            # A pure reformat: the parsed value is unchanged and only the bytes move.
            target.write_text(
                json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=4)
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _drifted_reviewed_paths(scratch),
                [f"{DOMAIN}/error-codes.json"],
                "a re-indented contract was accepted as byte-identical",
            )
            (scratch / ANALYSIS / "stage-registry.json").unlink()
            self.assertEqual(
                sorted(_drifted_reviewed_paths(scratch)),
                sorted(
                    [f"{DOMAIN}/error-codes.json", f"{ANALYSIS}/stage-registry.json"]
                ),
                "a deleted contract was not reported as drift",
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

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

    def test_the_reviewed_families_are_clean(self) -> None:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "status",
                "--porcelain",
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
        self.assertEqual(
            result.stdout.strip(),
            "",
            "this review wrote to an artifact it was reviewing",
        )


if __name__ == "__main__":
    unittest.main()
