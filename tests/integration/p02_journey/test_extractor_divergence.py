"""The A4/pdfplumber extractor divergence: real, and inert. Confirmed independently.

``fixtures/synthetic/ar/expected_issues.json`` records ``baseline.page_text_sha256`` from
the corpus generator's reference extractor. The pinned ``pdfplumber`` produces different
page text -- ``extract_text()`` collapses runs of spaces -- and the hashes differ on every
page. The question that matters is not whether they differ but whether any **evidence
anchor** moved, because an anchor that shifted would make every quotation in the system
suspect.

This suite checks the anchors, not the hashes. It asserts each declared quotation appears
at its declared ``char_offset_in_page_text`` in the text the chain's own extractor
produces -- offset, not mere presence, so a shift anywhere before an anchor fails here.
It also pins the divergence itself, so that silently "fixing" the extractor to match the
reference shows up as a change rather than passing unnoticed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The corpus this suite reads. Overridable **only** so that the guards below can be
#: shown to fail, which the dispatch requires of every guard: the anchors live in a
#: tracked fixture, and mutating a tracked file to prove a test is forbidden. Point this
#: at a scratch copy with a perturbed offset and
#: ``test_every_declared_quotation_resolves_at_its_declared_offset`` goes red. It defaults
#: to the real corpus, so a normal run reads exactly what the chain reads.
CORPUS = Path(os.environ.get("B3CONV_CORPUS_DIR", REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"))
EXPECTED = CORPUS / "expected_issues.json"
BASELINE = CORPUS / "ar_baseline.pdf"


@pytest.fixture(scope="module")
def fixture_manifest() -> dict:
    return json.loads(EXPECTED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def extracted_pages():
    """The page text the chain itself produces, through the stage's own extractor.

    Calling ``pdfplumber`` directly here would test a different extractor than the one
    ``source_preparation`` runs, and could agree with the fixture while the chain did not.
    """
    from auditmanager.analysis.stages.extraction import extract_document

    return extract_document(BASELINE.read_bytes()).pages


def declared_anchors(manifest: dict) -> list[tuple[str, dict]]:
    anchors: list[tuple[str, dict]] = []

    def collect(node: object, ident: str) -> None:
        if isinstance(node, dict):
            if "quotation" in node and "page" in node:
                anchors.append((ident, node))
            for value in node.values():
                collect(value, ident)
        elif isinstance(node, list):
            for value in node:
                collect(value, ident)

    for issue in manifest["seeded_issues"]:
        collect(issue, issue["id"])
    for control in manifest.get("controls", []):
        collect(control, control.get("id", "control"))
    return anchors


def test_the_corpus_declares_the_anchors_this_suite_checks(fixture_manifest):
    """Without this, an empty anchor list would make every assertion below vacuous."""
    anchors = declared_anchors(fixture_manifest)
    assert len(anchors) == 12, f"expected 12 declared anchors, found {len(anchors)}"
    for _, anchor in anchors:
        assert "char_offset_in_page_text" in anchor
        assert anchor["quotation"]


def test_every_declared_quotation_resolves_at_its_declared_offset(
    fixture_manifest, extracted_pages
):
    """The property that makes the divergence inert."""
    failures = []
    for ident, anchor in declared_anchors(fixture_manifest):
        text = extracted_pages[anchor["page"] - 1].text
        quotation = anchor["quotation"]
        offset = anchor["char_offset_in_page_text"]
        if text[offset : offset + len(quotation)] != quotation:
            failures.append(
                f"{ident} page {anchor['page']}: declared offset {offset}, "
                f"quotation actually at {text.find(quotation)}"
            )
    assert not failures, (
        "evidence anchors have moved against the chain's extractor; every quotation in "
        "the system is suspect until this is explained:\n  " + "\n  ".join(failures)
    )


def test_the_divergence_is_real_and_is_confined_to_the_page_hashes(
    fixture_manifest, extracted_pages
):
    """Pins the known divergence. If the extractor is ever changed to agree with the
    reference, this fails and the change is noticed rather than absorbed."""
    declared = fixture_manifest["baseline"]["page_text_sha256"]
    assert len(declared) == len(extracted_pages) == 8
    differing = [
        index + 1
        for index, page in enumerate(extracted_pages)
        if hashlib.sha256(page.text.encode("utf-8")).hexdigest() != declared[index]
    ]
    assert differing == [1, 2, 3, 4, 5, 6, 7, 8], (
        f"the extractor divergence changed shape: pages differing are {differing}. "
        "It was all eight at base 92bece8."
    )


#: The field name the corpus generator's reference extractor uses for a page's text hash.
PAGE_HASH_FIELD = "page_text_sha256"

#: Modules that may *name* the field, keyed by their path under the ``auditmanager`` package,
#: with the reason. An entry is not a licence to read the manifest: the guard below still
#: rejects, in these files too, every use of the name other than declaring a field, keying a
#: dict that is being built, prose in a docstring, and the **kinds of use** that
#: :data:`OWN_PAGE_HASH_USES` lists for that one module -- and it asserts, by parsing the module,
#: that the module neither names ``expected_issues`` nor a manifest nor can open a file at all.
#: The behavioural tests after it show the values these modules put under the name are digests
#: of the text they are given. A stale entry (file gone, or no longer naming the field) is
#: itself a failure, so the list cannot outlive the thing it excuses.
OWN_PAGE_HASH_ALLOWANCES = {
    "comparison/sheet_match_suggestions.py": (
        "Sheet-pair suggestions (W59). `page_text_sha256` there is the SHA-256 the module "
        "itself computes over the UTF-8 bytes of a page's text, taken from the verified "
        "`prepared.text_layer` snapshot its caller supplies, to compare two versions' pages "
        "with each other. It reads neither the portal manifest nor `expected_issues.json`, "
        "so the pinned extractor's divergence from the reference hashes cannot reach it."
    ),
    "comparison/sheet_links.py": (
        "The store of approved sheet pairings (`COMPARE-PERSISTED-SUMMARY-01`, migration "
        "`0035`). `source_page_text_sha256` and `target_page_text_sha256` are the names of two "
        "columns of `comparison_sheet_link`, so the module declares them as fields of its row "
        "records (`LinkEvent`, `NewLinkEvent`) and spells them in the SQL text that selects and "
        "inserts them. It computes no digest: the values it stores are the ones its caller hands "
        "it, which `pairing` copies from the suggestion `sheet_match_suggestions` computed over "
        "the text it was given. It opens no file and names neither the portal manifest nor "
        "`expected_issues.json`, so the pinned extractor's divergence from the reference hashes "
        "cannot reach it. The column names are the migration's and cannot be renamed."
    ),
    "comparison/approved_evidence.py": (
        "Recomputed evidence of the approved pairs (`COMPARE-PERSISTED-SUMMARY-01`). "
        "`page_text_sha256(text)` is this module's own function: the SHA-256 of the UTF-8 bytes "
        "of a page text its caller hands it (the stored page text of a version), exported in "
        "`__all__`; `link_is_verified` compares that digest of the current text with "
        "`link.source_page_text_sha256` and `link.target_page_text_sha256`, the digests an "
        "expert's approval stored. It opens no file and names neither the portal manifest nor "
        "`expected_issues.json`, so the pinned extractor's divergence from the reference hashes "
        "cannot reach it, and a stored digest equal to the manifest's would verify no page."
    ),
    "comparison/pairing.py": (
        "The approve and withdraw commands for a sheet pairing "
        "(`COMPARE-PERSISTED-SUMMARY-01`). `proposed.source_page_text_sha256` and "
        "`proposed.target_page_text_sha256` are the digests of the suggestion "
        "`sheet_match_suggestions` computed over the text it was given, and `approval.*` the "
        "digests stored on the approval row being withdrawn; the module compares them with an "
        "active link's and copies them into the next row (keyword arguments of `NewLinkEvent`). "
        "It computes no digest, opens no file and names neither the portal manifest nor "
        "`expected_issues.json`, so the pinned extractor's divergence from the reference hashes "
        "cannot reach it."
    ),
}

#: The ways, beyond declaring a field, keying a dict being built and prose in a docstring, in
#: which a module may use the name. Every other use of the name is :data:`USE_READ` -- a
#: subscript, ``.get("page_text_sha256")``, a comparison with the bare name, a parameter, a
#: variable -- and no allowance covers it.
USE_READ = "read"
#: ``record.source_page_text_sha256``: an attribute whose name *ends with* the field, read off
#: an object of a type the allowed modules declare. The reference hashes live in a JSON file,
#: and a parsed JSON object has keys and no attributes.
USE_ATTRIBUTE = "attribute"
#: ``NewLinkEvent(source_page_text_sha256=digest)``: a keyword argument ending with the field.
USE_KEYWORD = "keyword"
#: ``def page_text_sha256(text)`` and a mention of it in the module that defines it.
USE_OWN_FUNCTION = "own function"
#: ``"page_text_sha256"`` as an entry of the module's ``__all__``.
USE_EXPORT = "export"
#: A string that contains the name **and white space**: an SQL statement or a column list. The
#: key of a lookup in the reference file is the bare name, which has none.
USE_SQL_TEXT = "sql text"

#: Per allowed module, exactly the kinds of use it makes beyond declaring and building. The
#: guard demands equality: a kind the module uses and does not list is a finding, and so is a
#: kind it lists and no longer uses (a stale kind widens the allowance for nothing). A module
#: absent here is held to declaring and building only, as `sheet_match_suggestions.py` is.
OWN_PAGE_HASH_USES = {
    "comparison/sheet_links.py": frozenset({USE_SQL_TEXT}),
    "comparison/approved_evidence.py": frozenset({USE_ATTRIBUTE, USE_OWN_FUNCTION, USE_EXPORT}),
    "comparison/pairing.py": frozenset({USE_ATTRIBUTE, USE_KEYWORD}),
}

#: What an allowed module must not be able to do, so that its attribute and keyword uses of
#: the name cannot be fed from the reference file: name it, or the portal manifest, in code
#: (a docstring may talk about both), or open any file.
REFERENCE_NAMES = ("expected_issues", "manifest")
FILE_ACCESS_MODULES = frozenset(
    {"os", "pathlib", "io", "zipfile", "shutil", "glob", "tempfile", "fileinput"}
)
FILE_ACCESS_ATTRIBUTES = frozenset({"open", "read_text", "read_bytes", "load", "loads"})

#: The classes of finding, in the order they are asserted, with what each one means.
FINDING_MESSAGES = {
    "stale": (
        f"an allowance names a module that is gone or no longer names {PAGE_HASH_FIELD}; "
        "remove it from OWN_PAGE_HASH_ALLOWANCES"
    ),
    "orphan_uses": (
        "OWN_PAGE_HASH_USES lists a module that OWN_PAGE_HASH_ALLOWANCES does not allow"
    ),
    "consumers": (
        "a module now reads the reference extractor's page hashes, which the pinned "
        "extractor does not reproduce"
    ),
    "reads": (
        f"a module allowed to name {PAGE_HASH_FIELD} reads it instead of building it; the "
        "allowance covers declaring a field, keying a dict it computes and the declared kinds "
        "of use of its own records' digests"
    ),
    "undeclared_uses": (
        f"a module allowed to name {PAGE_HASH_FIELD} makes a kind of use of it that "
        "OWN_PAGE_HASH_USES does not declare for that module"
    ),
    "stale_uses": (
        "OWN_PAGE_HASH_USES declares a kind of use that the module no longer makes; "
        "remove it so the allowance does not stay wider than the code"
    ),
    "reference_access": (
        "a module allowed to name the page-hash field names expected_issues or a manifest, or "
        "can open a file; its uses of the name are no longer known to be its own digests"
    ),
}


def _lines_naming_the_field(path: Path) -> list[int]:
    return [
        number
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if PAGE_HASH_FIELD in line
    ]


def _docstrings(tree: ast.Module) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def _field_uses(path: Path) -> list[tuple[int, str]]:
    """Where a module uses the field name for anything but declaring or building, and how.

    Not a use: a class-body field declaration (``page_text_sha256: str``), a string key of a
    dict display (``{"page_text_sha256": digest}``, where the value is whatever the module
    computed), and prose in a docstring. Every other occurrence is a ``(line, kind)`` of one of
    the ``USE_*`` kinds above, and :data:`USE_READ` when it is none of them -- a subscript, a
    ``.get("page_text_sha256")``, a comparison with the bare name, a parameter, a variable.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    declared = _docstrings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            declared.update(
                id(stmt.target)
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            )
        elif isinstance(node, ast.Dict):
            declared.update(id(key) for key in node.keys if isinstance(key, ast.Constant))
    defined_here = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.endswith(PAGE_HASH_FIELD)
    }

    def listed_in_all(node: ast.Constant) -> bool:
        container = parents.get(id(node))
        statement = parents.get(id(container))
        return (
            isinstance(container, (ast.List, ast.Tuple))
            and isinstance(statement, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in statement.targets)
            and node.value.endswith(PAGE_HASH_FIELD)
            and not any(character.isspace() for character in node.value)
        )

    def kind_of(node: ast.AST) -> str | None:
        if id(node) in declared:
            return None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if PAGE_HASH_FIELD not in node.name:
                return None
            return USE_OWN_FUNCTION if node.name.endswith(PAGE_HASH_FIELD) else USE_READ
        if isinstance(node, ast.Name):
            if PAGE_HASH_FIELD not in node.id:
                return None
            own = isinstance(node.ctx, ast.Load) and node.id in defined_here
            return USE_OWN_FUNCTION if own else USE_READ
        if isinstance(node, ast.Attribute):
            if PAGE_HASH_FIELD not in node.attr:
                return None
            return USE_ATTRIBUTE if node.attr.endswith(PAGE_HASH_FIELD) else USE_READ
        if isinstance(node, ast.keyword):
            if node.arg is None or PAGE_HASH_FIELD not in node.arg:
                return None
            return USE_KEYWORD if node.arg.endswith(PAGE_HASH_FIELD) else USE_READ
        if isinstance(node, ast.arg):
            return USE_READ if PAGE_HASH_FIELD in node.arg else None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if PAGE_HASH_FIELD not in node.value:
                return None
            if listed_in_all(node):
                return USE_EXPORT
            if any(character.isspace() for character in node.value):
                return USE_SQL_TEXT
            return USE_READ
        return None

    return sorted(
        (node.lineno, kind)
        for node in ast.walk(tree)
        if (kind := kind_of(node)) is not None
    )


def _reference_access(path: Path) -> list[str]:
    """What, in a module's code, could carry it to the reference file or the portal manifest.

    The relaxed rule for attribute and keyword uses is sound only if the module cannot be
    handed the reference hashes by its own hand. So, by the syntax tree and not by trust: no
    identifier, string, import or alias of the module names ``expected_issues`` or a manifest
    (docstrings may talk about both), it imports none of the file-access modules, and it calls
    ``open``, ``read_text``, ``read_bytes`` or ``load``/``loads`` nowhere.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = _docstrings(tree)
    found: list[str] = []

    def check(line: int, spelled: str | None) -> None:
        if spelled and any(name in spelled.lower() for name in REFERENCE_NAMES):
            found.append(f"{line}: names {spelled!r}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                check(node.lineno, node.value)
        elif isinstance(node, ast.Name):
            check(node.lineno, node.id)
        elif isinstance(node, ast.Attribute):
            check(node.lineno, node.attr)
            if node.attr in FILE_ACCESS_ATTRIBUTES:
                found.append(f"{node.lineno}: uses .{node.attr}")
        elif isinstance(node, (ast.arg, ast.keyword)):
            check(node.lineno, node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            check(node.lineno, node.name)
        elif isinstance(node, ast.alias):
            check(node.lineno, node.name)
            check(node.lineno, node.asname)
        elif isinstance(node, ast.ImportFrom):
            check(node.lineno, node.module)
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            roots = [(node.module or "").split(".")[0]]
        else:
            roots = []
        found.extend(
            f"{node.lineno}: imports {root}" for root in roots if root in FILE_ACCESS_MODULES
        )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                found.append(f"{node.lineno}: calls open")
    return sorted(set(found), key=lambda item: (int(item.split(":")[0]), item))


def page_hash_guard_findings(
    root: Path,
    allowances: Mapping[str, str],
    uses: Mapping[str, frozenset[str]],
) -> dict[str, list[str]]:
    """Every way the tree under ``root`` breaks the page-hash claim, by class.

    The classes are the keys of :data:`FINDING_MESSAGES`.

    A function of its arguments, so that the same code that judges the real package is shown
    failing on a synthetic one below.
    """
    findings: dict[str, list[str]] = {name: [] for name in FINDING_MESSAGES}
    allowed = {root / relative: relative for relative in allowances}

    findings["stale"] = [
        str(path) for path in allowed if not path.is_file() or not _lines_naming_the_field(path)
    ]
    findings["orphan_uses"] = [relative for relative in uses if relative not in allowances]
    findings["consumers"] = [
        f"{path}:{number}"
        for path in sorted(root.rglob("*.py"))
        if path not in allowed
        for number in _lines_naming_the_field(path)
    ]
    for path, relative in allowed.items():
        if not path.is_file():
            continue  # already reported as stale
        declared = uses.get(relative, frozenset())
        found = _field_uses(path)
        findings["reads"] += [f"{path}:{line}" for line, kind in found if kind == USE_READ]
        findings["undeclared_uses"] += [
            f"{path}:{line} ({kind})"
            for line, kind in found
            if kind != USE_READ and kind not in declared
        ]
        findings["stale_uses"] += [
            f"{path} ({kind})" for kind in sorted(declared - {kind for _, kind in found})
        ]
        findings["reference_access"] += [f"{path}:{item}" for item in _reference_access(path)]
    return findings


def _package_root() -> Path:
    import auditmanager

    # The package as actually imported, not a hardcoded path: a mutation applied through
    # ``-o pythonpath=<copy>/src`` must be visible here, or the "proof" that this guard
    # can fail would be scanning a tree the run never used.
    return Path(auditmanager.__file__).resolve().parent


def test_no_module_consumes_the_manifest_page_hashes():
    """The structural half of the claim: nothing in the chain reads the manifest's page hashes.

    Source text is scanned rather than imported, because the property is an absence and
    an absence cannot be asserted by calling something. Every module naming the field is a
    suspect, except the named allowances above -- which may only declare and build with the
    name, make the kinds of use they list, and never reach the reference file: the name is
    theirs, as the DB columns' and the records' name for digests they hold, and the values are
    shown to be their own by the behavioural tests below.
    """
    findings = page_hash_guard_findings(
        _package_root(), OWN_PAGE_HASH_ALLOWANCES, OWN_PAGE_HASH_USES
    )
    for name, message in FINDING_MESSAGES.items():
        assert not findings[name], f"{message}: {findings[name]}"


# ---------------------------------------------------------------------------------------
# The guard is shown able to fail: the same function, on synthetic packages.
# ---------------------------------------------------------------------------------------

_OWN_RECORDS = '''"""Own records. The reference file and the portal manifest are not read here."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Link:
    source_page_text_sha256: str


def same(a, b):
    return a.source_page_text_sha256 == b.source_page_text_sha256


def make(digest):
    return Link(source_page_text_sha256=digest)
'''
_OWN_USES = frozenset({USE_ATTRIBUTE, USE_KEYWORD})
_ONE = {"a.py": "reason"}


def _package(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "auditmanager"
    for relative, source in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(source, encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("label", "files", "allowances", "uses", "expected"),
    [
        ("own records, declared kinds, nothing else", {"a.py": _OWN_RECORDS}, _ONE,
         {"a.py": _OWN_USES}, set()),
        ("a docstring may talk about the manifest and expected_issues.json",
         {"a.py": _OWN_RECORDS + '\n\ndef f():\n'
                  '    """Never reads expected_issues.json or the manifest."""\n    return 1\n'},
         _ONE, {"a.py": _OWN_USES}, set()),
        ("an SQL text or column list that names the column",
         {"a.py": '_COLUMNS = "a, source_page_text_sha256, b"\n'}, _ONE,
         {"a.py": frozenset({USE_SQL_TEXT})}, set()),
        ("own function, its call and its export",
         {"a.py": 'import hashlib\n__all__ = ["page_text_sha256"]\n'
                  'def page_text_sha256(text):\n'
                  '    return hashlib.sha256(text.encode()).hexdigest()\n'
                  'def twice(text):\n    return page_text_sha256(text)\n'},
         _ONE, {"a.py": frozenset({USE_OWN_FUNCTION, USE_EXPORT})}, set()),
        # (a) a module reads the reference file's page hashes
        ("(a) an allowed module reads expected_issues.json",
         {"a.py": 'import json\nfrom pathlib import Path\n\ndef hashes():\n    return json.loads('
                  'Path("fixtures/synthetic/ar/expected_issues.json").read_text())'
                  '["baseline"]["page_text_sha256"]\n'}, _ONE, {}, {"reads", "reference_access"}),
        ("(a) an allowed module takes the reference hashes by key from a dict it is handed",
         {"a.py": 'def hashes(baseline):\n    return baseline.get("page_text_sha256")\n'},
         _ONE, {}, {"reads"}),
        ("(a) the relaxed attribute rule is no loophole: a module that opens a manifest",
         {"a.py": _OWN_RECORDS + '\nfrom pathlib import Path\n'
                  'def load():\n    return Path("portal/manifest.json").read_text()\n'},
         _ONE, {"a.py": _OWN_USES}, {"reference_access"}),
        ("(a) nor a module that merely imports a manifest reader",
         {"a.py": _OWN_RECORDS + '\nfrom auditmanager.ingest import read_portal_manifest\n'},
         _ONE, {"a.py": _OWN_USES}, {"reference_access"}),
        ("(a) nor a module that opens a file under another name",
         {"a.py": _OWN_RECORDS + '\ndef grab(p):\n    return open(p).read()\n'},
         _ONE, {"a.py": _OWN_USES}, {"reference_access"}),
        ("a bare key is a read even where SQL text is allowed",
         {"a.py": 'def f(row):\n    return row["source_page_text_sha256"]\n'},
         _ONE, {"a.py": frozenset({USE_SQL_TEXT})}, {"reads", "stale_uses"}),
        # (b) a new module names the field
        ("(b) a new module outside the allowances names the field",
         {"a.py": _OWN_RECORDS, "b.py": 'X = {}.get("page_text_sha256")\n'}, _ONE,
         {"a.py": _OWN_USES}, {"consumers"}),
        ("(b) even in a comment",
         {"a.py": _OWN_RECORDS, "b.py": "# page_text_sha256\n"}, _ONE,
         {"a.py": _OWN_USES}, {"consumers"}),
        # (c) stale entries
        ("(c) an allowance for a module that no longer names the field",
         {"a.py": "VALUE = 1\n"}, _ONE, {}, {"stale"}),
        ("(c) an allowance for a module that is gone",
         {"a.py": _OWN_RECORDS}, _ONE | {"gone.py": "reason"}, {"a.py": _OWN_USES}, {"stale"}),
        ("(c) a kind of use the module no longer makes",
         {"a.py": _OWN_RECORDS}, _ONE, {"a.py": _OWN_USES | {USE_EXPORT}}, {"stale_uses"}),
        # the per-module kind table
        ("a kind of use the allowance does not declare", {"a.py": _OWN_RECORDS}, _ONE,
         {"a.py": frozenset({USE_ATTRIBUTE})}, {"undeclared_uses"}),
        ("a module absent from the table is held to declaring and building",
         {"a.py": _OWN_RECORDS}, _ONE, {}, {"undeclared_uses"}),
        ("a kinds entry for a module that is not allowed",
         {"a.py": _OWN_RECORDS}, _ONE, {"a.py": _OWN_USES, "z.py": _OWN_USES}, {"orphan_uses"}),
    ],
)
def test_the_page_hash_guard_fails_where_it_must_and_only_there(
    tmp_path, label, files, allowances, uses, expected
):
    findings = page_hash_guard_findings(_package(tmp_path, files), allowances, uses)
    assert {name for name, items in findings.items() if items} == expected, (label, findings)


def test_every_allowance_of_the_real_package_has_a_reason_and_the_kinds_are_known():
    """The tables are data a reviewer reads: no empty reason, no kind outside the vocabulary."""
    assert all(reason.strip() for reason in OWN_PAGE_HASH_ALLOWANCES.values())
    known = {USE_ATTRIBUTE, USE_KEYWORD, USE_OWN_FUNCTION, USE_EXPORT, USE_SQL_TEXT}
    for relative, kinds in OWN_PAGE_HASH_USES.items():
        assert relative in OWN_PAGE_HASH_ALLOWANCES
        assert kinds and kinds <= known, (relative, kinds - known)


def test_the_allowed_module_digests_the_text_it_is_given_and_not_the_manifest(
    fixture_manifest, extracted_pages
):
    """The behavioural half: what the allowed module puts under the name is its own digest.

    The pinned extractor's pages hash differently from the manifest's declared hashes on
    every page (pinned above). If ``sheet_match_suggestions`` consumed the manifest's value
    it could not agree with the chain's text; it digests the text it is handed, so the value
    it reports equals the SHA-256 of the extractor's own page text and equals none of the
    manifest's.
    """
    from auditmanager.comparison.sheet_match_suggestions import (
        EXACT_PAIR_ALGORITHM,
        suggest_exact_sheet_matches,
        suggest_sheet_pairs,
    )
    from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

    project, document = "prj_01M2545JSD15ETSNNV904X991J", "doc_01M2545JSD15ETSNNV904X991J"
    pair = OrderedVersionPair(
        project, document,
        VersionFacts("ver_01M2545JSD15ETSNNV904X991J", document, project, 1, "a" * 64, 100,
                     len(extracted_pages), "application/pdf"),
        VersionFacts("ver_01M2545JSD15ETSNNV904X991K", document, project, 2, "b" * 64, 101,
                     len(extracted_pages), "application/pdf"),
    )
    pages = {number: page.text for number, page in enumerate(extracted_pages, 1)}
    declared = fixture_manifest["baseline"]["page_text_sha256"]

    def own(number: int) -> str:
        return hashlib.sha256(pages[number].encode("utf-8")).hexdigest()

    bound = suggest_exact_sheet_matches(
        version_pair=pair, comparison_id="cmp_00000000000000000000000001",
        source_pages=pages, target_pages=pages,
    )
    read_only = [
        item for item in suggest_sheet_pairs(version_pair=pair, source_pages=pages, target_pages=pages)
        if item.algorithm == EXACT_PAIR_ALGORITHM
    ]
    for label, found in (("bound", bound), ("read-only", read_only)):
        assert found, f"the {label} rule paired no page of the baseline; this would be vacuous"
        for item in found:
            number = item.source_page_number
            assert item.target_page_number == number
            reported = (
                item.page_text_sha256 if label == "bound" else item.source_page_text_sha256
            )
            assert reported == own(number), f"{label}: page {number} is not the text's own digest"
            assert reported != declared[number - 1], (
                f"{label}: page {number} reports the manifest's declared hash"
            )


def test_the_approved_evidence_digests_the_text_it_is_given_and_not_the_manifest(
    fixture_manifest, extracted_pages
):
    """The behavioural half for ``approved_evidence``, the allowed module that digests page text.

    ``page_text_sha256`` there equals the SHA-256 of the pinned extractor's own page text and
    equals none of the manifest's declared hashes (pinned above to differ on every page). A link
    that stores a page's own digest verifies the pair; a link that stores the manifest's declared
    digest -- on either side -- verifies none. If the module took the manifest's value anywhere
    on this path, the first assertion about a page would fail.
    """
    from datetime import datetime, timezone

    from auditmanager.comparison.approved_evidence import link_is_verified, page_text_sha256
    from auditmanager.comparison.sheet_links import LinkEvent

    pages = {number: page.text for number, page in enumerate(extracted_pages, 1)}
    declared = fixture_manifest["baseline"]["page_text_sha256"]
    assert len(pages) == len(declared) == 8, "an empty baseline would make this vacuous"

    def link(number: int, source_digest: str, target_digest: str) -> LinkEvent:
        return LinkEvent(
            "cmp_00000000000000000000000001", 1, "approved", "sln_00000000000000000000000001",
            "prj_01M2545JSD15ETSNNV904X991J", "doc_01M2545JSD15ETSNNV904X991J",
            "ver_01M2545JSD15ETSNNV904X991J", "ver_01M2545JSD15ETSNNV904X991K",
            number, number, source_digest, target_digest, "c" * 64, None,
            "usr_01M2545JSD15ETSNNV904X991J", "Эксперт", "cmd_00000000000000000000000001",
            datetime(2026, 10, 27, tzinfo=timezone.utc),
        )

    for number, text in pages.items():
        own = hashlib.sha256(text.encode("utf-8")).hexdigest()
        reference = declared[number - 1]
        assert page_text_sha256(text) == own, f"page {number} is not the text's own digest"
        assert page_text_sha256(text) != reference, f"page {number} reports the manifest's hash"
        assert link_is_verified(link(number, own, own), pages, pages) is True
        assert link_is_verified(link(number, reference, reference), pages, pages) is False
        assert link_is_verified(link(number, own, reference), pages, pages) is False
        assert link_is_verified(link(number, reference, own), pages, pages) is False
