"""What stops the PC-01 browser journey from rotting.

``tests/e2e/pc01/journey/`` drives the deployed origin with a real browser. It cannot run
inside ``make gate``: it needs a built web image, a bound port and a live stack, and a gate
that needs those is a gate that gets skipped. This programme has already measured what that
costs -- the frontend suite went four waves without being run because no target named it,
and ``D-23`` is the same shape in prose.

So the journey runs *beside* the gate, under ``npm --prefix web run e2e:pc01``, and **this
file is what fails when the journey stops matching the application.** It runs inside the
canonical battery, needs no browser, no origin, no port and no service, and it checks the
journey's written-down claim -- ``manifest.json`` -- against two things the journey does not
author:

1. the route tree under ``web/src/app`` -- every screen, and only the screens that exist;
2. ``contracts/api/v1/openapi.json`` -- every operation the journey says a screen calls.

Add a screen and this goes red until the journey walks it. Rename a dynamic segment,
delete a screen, rename an operation, change a method or a path, move the BFF mount: red.
What it cannot see is behaviour -- a screen whose route and calls are unchanged but which
renders nothing is invisible here and visible only to the journey itself. That is the
stated cost of keeping the gate stack-free, and it is why the journey exists rather than
being replaced by this file.

**`W22-E2E` widened it, because the write half needed it widened.** The read walk is
addressed entirely by route and operation, so checking addressing covered it. The write
half presses named *controls* -- ``#new-project-name``, ``#upload-file``, the button whose
text is ``Запустить прогон`` -- and reads named *markers* -- ``data-created-project``,
``data-run-outcome``, ``data-run-activity``. None of those is addressing. Rename an id in
``web/src`` with the route untouched and the old guard would have stayed green while the
journey silently stopped being able to press anything, which is the rot this file exists
to stop. So the guard now also checks that every handle the write half names still exists
in the application's source, that its fixture is on disk, that each declared status is one
the contract publishes for that operation, and that every wait carries a positive bound.

The residue is stated rather than closed: **an id existing in ``web/src`` is not the same
as pressing it doing anything.** This guard proves the handle is there; only the journey,
against a running stack, proves the control works. That gap is the same one the module
already had, narrowed but not shut.

**Measured limitation, and the brief that sent this session had it wrong.**
``make mutation-copy`` copies ``src/``, ``tests/`` and ``pyproject.toml`` and *also*
provides ``contracts``, ``docs``, ``fixtures``, ``db`` and ``tools`` -- as symlinks to the
checkout, or as copies under ``FULL=1`` (``Makefile`` lines 551-578). What it does not
provide is ``web/``, and that is the only thing missing here. So **every check below that
calls ``_require`` on ``APP_DIR`` or ``WEB_SRC``** cannot run inside a mutation copy and
must be excluded by path alongside the three suites under
``tests/integration/composition``; the checks that read only ``tests/`` and the symlinked
``contracts/`` run there unchanged. That is stated as a property rather than a count
because the count has now changed twice: the figure measured in a copy on 2026-09-19 --
3 failed, 7 passed -- predates the refusal half and is no longer this file's shape.

The negative controls read nothing outside this file and run anywhere -- they are what
proves each check can fail. ``tests/e2e/pc01/journey/prove_the_guard_can_fail.py`` proves
the same against the *real* manifest, which a synthetic control cannot.

**`W28-GUARD` widened it again, for the refusal half.** See the section at the foot of
this file.

**`W41-BLIND` moved one check's SUBJECT, 2026-09-23, and it is the only change in this file
that is not a widening.** ``expects_rendered`` was asserted by substring containment against
a concatenation of every ``.ts``/``.tsx`` byte under ``web/src``. That is `D-61`: the
manifest declared ``"Run"`` and passed, because ``Run`` occurs inside ``RunPage``, and no
screen renders it. Containment had deceived two guards before it and both were repaired by
matching on a word boundary; **this one could not be, because the subject was wrong rather
than the matcher.**

The question splits in two, and neither half is the old one:

* *are these the application's own words?* -- source can answer that, scoped to the import
  closure of the ``control_module`` the manifest itself names and to authored STRINGS only.
  That is ``test_every_sentence_the_journey_requires_is_authored_by_the_control_it_presses``;
* *is the sentence evidence that the step RAN, or is it on the screen anyway?* -- only
  rendered output can answer that, and it is asserted in
  ``web/tests/guards/rendered-language.guard.test.ts`` over `W32-SEE`'s renderer, reused
  rather than rebuilt. ``test_the_rendered_half_of_d61_has_not_left_the_frontend_guard``
  keeps that obligation from leaving the gate in silence.

**Measured at `abe1c15`, before the repair: none of the manifest's fifteen sentences was
verified by either half.** Eleven are rendered by no screen this harness can reach -- they
live in branches driven by ``useState`` and by a settled ``useMutation`` -- and the other
four passed by matching text the screen renders whatever happened, in the browser as well
as in the gate. Those four were removed from the manifest, each with the reason in its own
step.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOURNEY_DIR = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "journey"
MANIFEST = JOURNEY_DIR / "manifest.json"
APP_DIR = REPOSITORY_ROOT / "web" / "src" / "app"
WEB_SRC = REPOSITORY_ROOT / "web" / "src"
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
JOURNEY = JOURNEY_DIR / "journey.mjs"

_HTTP_METHODS = ("get", "post", "put", "patch", "delete")


# --------------------------------------------------------------------------------------
# The checks, as pure functions over data. Everything below them either feeds in the real
# tree (and needs `web/` and `contracts/`) or feeds in a synthetic one (and does not).
# --------------------------------------------------------------------------------------


def route_path_of_page_module(page_module: str) -> str:
    """``web/src/app/projects/[project_uid]/page.tsx`` -> ``/projects/{project_uid}``."""
    parts = Path(page_module).parts
    assert parts[-1] == "page.tsx", page_module
    try:
        start = parts.index("app") + 1
    except ValueError:  # pragma: no cover - guarded by the caller's assertion
        raise AssertionError(f"{page_module} is not under an `app` directory")
    segments = []
    for segment in parts[start:-1]:
        if segment.startswith("[") and segment.endswith("]"):
            segments.append("{" + segment[1:-1] + "}")
        else:
            segments.append(segment)
    return "/" + "/".join(segments) if segments else "/"


def screens_in_app_tree(app_dir: Path) -> dict[str, str]:
    """Every rendered screen the application offers, as ``route path -> page module``.

    Route handlers (``route.ts``) are not screens and are excluded; the BFF mount is
    checked separately and by name.
    """
    out: dict[str, str] = {}
    for page in sorted(app_dir.rglob("page.tsx")):
        relative = page.relative_to(app_dir.parents[2]).as_posix()
        out[route_path_of_page_module(relative)] = relative
    return out


def screens_in_manifest(manifest: dict) -> dict[str, str]:
    return {route["path"]: route["page_module"] for route in manifest["routes"]}


def placeholder_sample_findings(routes: list[dict]) -> list[str]:
    """A live user detail needs the list's captured user_uid; only a stub may use a sample."""
    detail = "/admin/users/{user_uid}"
    findings = []
    matches = [route for route in routes if route.get("path") == detail]
    if len(matches) != 1:
        findings.append(f"{detail} must have exactly one journey row")
    list_captures_user = any(
        route.get("path") == "/admin/users"
        and (route.get("follow") or {}).get("capture") == "user_uid"
        for route in routes
    )
    for route in routes:
        path = route.get("path", "")
        sample = route.get("sample_identifiers")
        if path == detail and sample is None:
            if not list_captures_user or route.get("expects_api") != [
                {"method": "GET", "path": "/users/{user_uid}", "operationId": "getUser"}
            ]:
                findings.append(f"{detail} has no user_uid sample or live list capture")
            continue
        if sample is None:
            continue
        if path != detail:
            findings.append(f"{path} is not the allowed sample placeholder")
            continue
        names = set(re.findall(r"\{([a-z_]+)\}", path))
        if not isinstance(sample, dict) or set(sample) != names or names != {"user_uid"}:
            findings.append(f"{path} sample must name exactly its user_uid segment")
            continue
        value = sample["user_uid"]
        if not isinstance(value, str) or re.fullmatch(r"usr_[0-9A-HJKMNP-TV-Z]{26}", value) is None:
            findings.append(f"{path} sample is not a well-formed usr_<ULID>")
        if route.get("expects_api") != [] or route.get("optional_api"):
            findings.append(f"{path} sample is allowed only while the detail makes no API call")
    return findings


def operations_in_contract(openapi: dict) -> set[tuple[str, str, str]]:
    """``(METHOD, path, operationId)`` for every operation the contract publishes."""
    out: set[tuple[str, str, str]] = set()
    for path, item in openapi["paths"].items():
        for method, operation in item.items():
            if method.lower() in _HTTP_METHODS:
                out.add((method.upper(), path, operation["operationId"]))
    return out


def operations_claimed_by_manifest(manifest: dict) -> set[tuple[str, str, str]]:
    """Every operation the journey says a screen calls, required and optional alike.

    All three halves. The write half's three `POST`s go through the same check as the read
    walk's `GET`s, so renaming `startRun` -- the operation `D-5` actually was -- reddens
    the gate rather than waiting for someone to run a browser. `W28-GUARD` added the
    refusal half's single `uploadDocument`, which is the same `POST` seen from the other
    side: the six cases assert what it answers when the file is wrong.
    """
    out: set[tuple[str, str, str]] = set()
    for route in manifest["routes"]:
        for group in ("expects_api", "optional_api"):
            for call in route.get(group) or ():
                out.add((call["method"].upper(), call["path"], call["operationId"]))
    for step in write_steps(manifest):
        for group in ("expects_api", "expects_api_after_terminal"):
            for call in step.get(group) or ():
                out.add((call["method"].upper(), call["path"], call["operationId"]))
    call = refusal_api(manifest)
    if call is not None:
        out.add((call["method"].upper(), call["path"], call["operationId"]))
    for call in (manifest.get("identity") or {}).get("operations") or ():
        out.add((call["method"].upper(), call["path"], call["operationId"]))
    return out


# --------------------------------------------------------------------------------------
# The write half. `W22-E2E`, against `D-30`.
# --------------------------------------------------------------------------------------


def write_steps(manifest: dict) -> list[dict]:
    return list((manifest.get("write") or {}).get("steps") or ())


_ID_SELECTOR = re.compile(r"#([A-Za-z][\w-]*)")
_DATA_ATTRIBUTE = re.compile(r"\[(data-[a-z0-9-]+)")


def handles_named_by_write_step(step: dict) -> set[str]:
    """Every handle a step names that must exist in ``web/src`` for it to press anything.

    Three kinds, and only the three that are not addressing:

    * an ``#id`` in any selector -- the control the step fills, presses or attaches to;
    * a ``[data-*]`` attribute in any selector -- the marker the step reads or forbids;
    * a control's visible ``text`` -- the only handle the Start-run button has, because
      ``web/src`` gives it no id and no test id.

    Tag and attribute selectors like ``form button[type="submit"]`` name nothing
    application-specific, so nothing is claimed about them.
    """
    selectors: list[str] = []
    texts: list[str] = []
    for action in step.get("actions") or ():
        if action.get("selector") is not None:
            selectors.append(action["selector"])
        if action.get("text") is not None:
            texts.append(action["text"])
        # `BETA-LIVE-JOURNEY-01`: a field or a select is named by the words of its label, and
        # a `wait_for` by the words it waits for. Both are the application's own words.
        if action.get("label") is not None:
            texts.append(action["label"])
        # `PC01-JOURNEY-GAPS-01`: the row a click is made in is named by a selector (its words are data).
        if isinstance(action.get("within"), dict) and action["within"].get("selector") is not None:
            selectors.append(action["within"]["selector"])
        if (
            action.get("do") == "wait_for"
            and action.get("text_contains") is not None
            and not action.get("text_is_data")
        ):
            texts.append(action["text_contains"])
    for capture in [step.get("capture") or {}, *(step.get("captures") or ())]:
        if capture.get("selector") is not None:
            selectors.append(capture["selector"])
        if capture.get("attribute") is not None:
            selectors.append(f"[{capture['attribute']}]")
    for selector in step.get("forbids_rendered") or ():
        selectors.append(selector)
    for present in step.get("expects_present") or ():
        selectors.append(present["selector"])
        # Words that come from DATA (a designation the seed wrote, a vendor the step typed) are
        # not the application's and are declared `text_is_data`; every other word must be.
        if present.get("text_contains") is not None and not present.get("text_is_data"):
            texts.append(present["text_contains"])
    for absent in step.get("expects_absent") or ():
        selectors.append(absent["selector"])
        if absent.get("text") is not None:
            texts.append(absent["text"])
    await_terminal = step.get("await_terminal") or {}
    for key in ("outcome_selector", "activity_selector"):
        if await_terminal.get(key) is not None:
            selectors.append(await_terminal[key])

    out: set[str] = set()
    for selector in selectors:
        for ident in _ID_SELECTOR.findall(selector):
            out.add(f'id="{ident}"')
        for attribute in _DATA_ATTRIBUTE.findall(selector):
            out.add(attribute)
    out.update(texts)
    return out


def application_source(web_src: Path) -> str:
    """Every ``.ts``/``.tsx`` byte under ``web/src``, concatenated. Coarse on purpose.

    A finer check -- "this id is in this component" -- would encode where the programme
    keeps its features today and go red when someone moves a file without changing what
    the screen offers. What must not change silently is that the handle exists at all.
    """
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(web_src.rglob("*.ts*"))
        if path.is_file()
    )


# --------------------------------------------------------------------------------------
# `D-61`'s third instance. The subject was wrong, not the matcher.
# --------------------------------------------------------------------------------------

_IMPORT = re.compile(r"""^\s*(?:import|export)\s[^'"\n]*?from\s*['"]([^'"]+)['"]""", re.M)
#: Quoted runs of any of the three kinds, and JSX text between a `>` and the next `<`.
_LITERAL = re.compile(r"'([^'\\\n]*)'|\"([^\"\\\n]*)\"|`([^`\\]*)`|>([^<>{}\n]+)<")


def resolve_module(specifier: str, importer: Path, web_src: Path) -> Path | None:
    """``@/features/x`` or ``../model/y`` -> the file on disk, or ``None`` if it leaves ``web/src``."""
    if specifier.startswith("@/"):
        base = web_src / specifier[2:]
    elif specifier.startswith("."):
        base = (importer.parent / specifier).resolve()
    else:
        return None  # a package, not this application's source
    for candidate in (
        base.with_suffix(".ts"), base.with_suffix(".tsx"),
        base / "index.ts", base / "index.tsx", base,
    ):
        if candidate.is_file():
            return candidate
    return None


def module_closure(entry: Path, web_src: Path) -> list[Path]:
    """``entry`` and every module under ``web/src`` it imports, transitively.

    This is the scope a sentence may be authored in. The old check used the concatenation
    of the WHOLE of ``web/src``, which is how the manifest asserted ``Run`` and passed on
    ``RunPage``; the closure of the module the manifest itself names is the honest subject
    for the question *"are these the application's own words"*.
    """
    seen: set[Path] = set()
    stack = [entry]
    while stack:
        current = stack.pop()
        if current in seen or not current.is_file():
            continue
        seen.add(current)
        for specifier in _IMPORT.findall(current.read_text(encoding="utf-8")):
            resolved = resolve_module(specifier, current, web_src)
            if resolved is not None and resolved not in seen:
                stack.append(resolved)
    return sorted(seen)


def authors(text: str, sentence: str) -> bool:
    """Is ``sentence`` a WHOLE-WORD occurrence in ``text``?

    The boundary is the third repair of the same defect and it is not a substitute for
    moving the subject -- it is what is left once the subject is right. Scoping to the
    control module's closure and to authored strings removes ``Run`` inside the identifier
    ``RunPage``; it does not remove ``Run`` inside the string literal ``'RunStateBadge'``,
    which `run-state-badge.tsx` really does carry. Measured: without this, declaring
    ``expects_rendered: ["Run"]`` on the create-project step still passed.

    ``\\w`` is Unicode-aware in Python, so this holds for the Cyrillic sentences too: the
    full stop after ``Ничего не отправлено`` is a boundary and the ``S`` after ``Run`` is
    not.
    """
    return re.search(rf"(?<!\w){re.escape(sentence)}(?!\w)", text) is not None


#: `/* … */` and a `//` that is not the `//` of a scheme.
_COMMENT = re.compile(r"/\*[\s\S]*?\*/|(?<!:)//[^\n]*")


def authored_strings(modules: list[Path]) -> str:
    """Only the STRINGS these modules author: quoted literals and JSX text, comments removed.

    Identifiers are excluded on purpose. ``Run`` inside ``RunPage`` is an identifier, and
    the whole of `D-61` is that a source scan which cannot tell one from a label will
    confirm a sentence no screen renders.

    **Comments are stripped first, and that is not tidying.** This repository documents
    itself in markdown inside doc comments, so ``RunStatus``, ``useStartRun`` and
    ``listRuns`` all appear between backticks in prose -- and a literal scan that reads a
    backtick run as a template literal picks every one of them up. Measured: with comments
    left in, declaring ``expects_rendered: ["Run"]`` on the create-project step still
    passed, which is `D-61` surviving its own repair. The negative control
    ``declare a sentence that is only an identifier in the source`` in
    ``prove_the_guard_can_fail.py`` is what says so.
    """
    out: list[str] = []
    for module in modules:
        text = _COMMENT.sub(" ", module.read_text(encoding="utf-8"))
        for groups in _LITERAL.findall(text):
            out.extend(part for part in groups if part)
    return "\n".join(out)


def responses_published_for(openapi: dict, method: str, path: str) -> set[int]:
    operation = openapi["paths"].get(path, {}).get(method.lower(), {})
    return {int(code) for code in operation.get("responses", {}) if code.isdigit()}


def run_states_in_contract(openapi: dict) -> set[str]:
    return set(openapi["components"]["schemas"]["RunState"]["enum"])


# --------------------------------------------------------------------------------------
# Fixtures over the real tree.
# --------------------------------------------------------------------------------------


def _require(path: Path) -> Path:
    """An absent input is a hard failure, never a skip.

    A skip here would report that the journey still matches the application having checked
    nothing -- which is the exact shape of the vacuous pass this programme keeps finding.
    Inside a `make mutation-copy` tree this fires by design: see the module docstring.
    """
    if not path.exists():
        pytest.fail(
            f"{path} is missing, so this check would prove nothing. "
            "Inside a `make mutation-copy` tree this is expected for anything under web/, "
            "which that target does not provide: exclude the three web/-reading checks in "
            "this file by path rather than reading them as reds. Measured 2026-09-19 in a "
            "copy: 3 failed, 7 passed."
        )
    return path


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(_require(MANIFEST).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def openapi() -> dict:
    return json.loads(_require(OPENAPI).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# Against the real tree.
# --------------------------------------------------------------------------------------


def test_the_journey_walks_every_screen_the_application_offers(manifest: dict) -> None:
    """The anti-rot check that matters: a new screen reddens until the journey walks it."""
    _require(APP_DIR)
    in_tree = set(screens_in_app_tree(APP_DIR))
    in_manifest = set(screens_in_manifest(manifest))
    unwalked = sorted(in_tree - in_manifest)
    phantom = sorted(in_manifest - in_tree)
    assert not unwalked, (
        f"{len(unwalked)} screen(s) exist that the PC-01 journey does not walk: "
        f"{unwalked}. Add them to tests/e2e/pc01/journey/manifest.json, or the journey "
        "certifies a shrinking fraction of the product while still reporting OK."
    )
    assert not phantom, (
        f"the journey declares {len(phantom)} route(s) the application no longer has: "
        f"{phantom}."
    )


def test_each_route_agrees_with_its_own_page_module(manifest: dict) -> None:
    """A renamed dynamic segment is drift the journey would only find at run time."""
    _require(APP_DIR)
    for route in manifest["routes"]:
        module = REPOSITORY_ROOT / route["page_module"]
        assert module.is_file(), (
            f"route '{route['name']}' names page module {route['page_module']}, "
            "which does not exist"
        )
        derived = route_path_of_page_module(route["page_module"])
        assert derived == route["path"], (
            f"route '{route['name']}' declares path {route['path']} but its page module "
            f"sits at {derived}"
        )


def test_user_detail_sample_is_only_for_the_no_call_placeholder(manifest: dict) -> None:
    assert placeholder_sample_findings(manifest["routes"]) == []


def test_user_detail_sample_validation_can_fail() -> None:
    row = {
        "path": "/admin/users/{user_uid}",
        "sample_identifiers": {"user_uid": "usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F"},
        "expects_api": [],
    }
    assert placeholder_sample_findings([{**row, "sample_identifiers": None}]) == [
        "/admin/users/{user_uid} has no user_uid sample or live list capture"
    ]
    assert "not a well-formed" in placeholder_sample_findings([
        {**row, "sample_identifiers": {"user_uid": "usr_invalid"}}
    ])[0]
    assert "exactly its user_uid" in placeholder_sample_findings([
        {**row, "sample_identifiers": {"project_uid": row["sample_identifiers"]["user_uid"]}}
    ])[0]
    assert "only while" in placeholder_sample_findings([
        {**row, "expects_api": [{"method": "GET", "path": "/users/{user_uid}"}]}
    ])[0]


def test_the_journey_consumes_the_declared_sample_only_for_route_address() -> None:
    source = _require(JOURNEY).read_text(encoding="utf-8")
    assert "fill(route.path, captured, route.sample_identifiers ?? {})" in source, (
        "journey.mjs no longer consumes the manifest sample for the placeholder address"
    )
    assert "const value = captured[name] ?? samples[name]" in source, (
        "a captured real user identity must take precedence over the placeholder sample"
    )
    assert "concreteApi(e, captured, route.constants ?? {})" in source, (
        "API expectations must not use the placeholder sample; they take captured identities "
        "and the route's own declared enumeration constants (`BETA-LIVE-JOURNEY-01`)"
    )
    assert "sample_identifiers" not in source[source.index("function concreteApi"):
                                              source.index("function shapeOf")], (
        "API expectations must not use the placeholder sample"
    )


def test_every_api_call_the_journey_declares_is_in_the_contract(
    manifest: dict, openapi: dict
) -> None:
    """Method, path and operationId together -- so a rename or a re-mount reddens."""
    published = operations_in_contract(openapi)
    claimed = operations_claimed_by_manifest(manifest)
    unknown = sorted(claimed - published)
    assert not unknown, (
        f"the journey declares {len(unknown)} call(s) that are not operations of "
        f"contracts/api/v1/openapi.json: {unknown}. Either the contract moved and the "
        "journey did not, or the journey names an operation that was never published."
    )


def test_w51_identity_journey_is_complete_and_contract_bound(
    manifest: dict, openapi: dict
) -> None:
    identity = manifest.get("identity")
    assert isinstance(identity, dict), "W51 identity phase is absent"
    assert identity["runner"] == "tests/e2e/pc01/journey/identity.mjs"
    source = _require(REPOSITORY_ROOT / identity["runner"]).read_text(encoding="utf-8")
    assert "checkedExchange(page, stageSpec(manifest" in source
    assert "sessionRow(registerPath, id)" in source
    assert identity["session_store_path_env"] == "E2E_PC01_SESSION_STORE_PATH"
    stages = [call["stage"] for call in identity["operations"]]
    assert stages == [
        "register", "approve", "profile", "verdict", "remove_expert",
        "revoked_request", "denied_mutation", "archive", "purge_refused", "reject",
        "self_archive",
    ]
    assert identity["manual_steps"] == [f"A{index:02d}" for index in range(13, 21)]
    assert identity["expected_author_label"] == "Тестов И. П."
    wrong = [
        f"{call['stage']}: {call['status']}"
        for call in identity["operations"]
        if call["status"] not in responses_published_for(
            openapi, call["method"], call["path"]
        )
    ]
    assert not wrong, f"identity statuses not published by the contract: {wrong}"
    manual = _require(REPOSITORY_ROOT / "docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md")
    recorder = _require(REPOSITORY_ROOT / "scripts/manual-alpha-check.sh")
    manual_text = manual.read_text(encoding="utf-8")
    recorder_text = recorder.read_text(encoding="utf-8")
    for step in identity["manual_steps"]:
        assert f"### {step} —" in manual_text
        assert f'record_manual "{step}"' in recorder_text
    for item in identity["operations"]:
        assert "password" not in item and "credential" not in item


def test_the_bff_prefix_the_journey_uses_is_where_the_app_mounts_it(
    manifest: dict,
) -> None:
    """The browser reaches the API through the BFF, not the API's own origin."""
    _require(APP_DIR)
    prefix = manifest["api_prefix"]
    mount = APP_DIR / prefix.strip("/") / "[...path]" / "route.ts"
    assert mount.is_file(), (
        f"the journey expects the BFF at {prefix}, but {mount} does not exist. "
        "A moved mount means every API expectation in the manifest is addressed to a "
        "path the browser no longer calls."
    )


def test_the_manifest_has_a_write_half_at_all(manifest: dict) -> None:
    """`D-30`: a journey that makes no `POST` cannot catch the defect that started it."""
    steps = write_steps(manifest)
    assert steps, (
        "manifest.json declares no `write` section, so the journey makes no POST and "
        "would not have caught D-5 -- which is the whole of D-30."
    )
    posted = {
        call["operationId"]
        for step in steps
        for call in step.get("expects_api") or ()
        if call["method"].upper() == "POST"
    }
    assert "startRun" in posted, (
        "the write half declares no `startRun`. `D-5` was POST /runs -> 500: a write half "
        f"that never starts a run is not the write half D-30 names. It posts: {sorted(posted)}"
    )


def test_every_write_step_stands_on_a_screen_the_read_walk_also_covers(
    manifest: dict,
) -> None:
    """A step pressing a control on a screen nobody walks is a half-checked screen."""
    _require(APP_DIR)
    walked = set(screens_in_manifest(manifest))
    for step in write_steps(manifest):
        module = REPOSITORY_ROOT / step["page_module"]
        assert module.is_file(), (
            f"write step '{step['name']}' names page module {step['page_module']}, "
            "which does not exist"
        )
        # `BETA-LIVE-JOURNEY-01`: a step's address may carry a query (`/norms?view=catalogue`),
        # which is no part of the route. `route` names the route when `at` is not it.
        route = step.get("route", step["at"].split("?")[0])
        derived = route_path_of_page_module(step["page_module"])
        assert derived == route, (
            f"write step '{step['name']}' says it acts at {route} but its page "
            f"module sits at {derived}"
        )
        assert route in walked, (
            f"write step '{step['name']}' acts at {route}, which the read walk does "
            "not cover. Every screen the journey writes on must also be a screen it reads."
        )
        control = REPOSITORY_ROOT / step["control_module"]
        assert control.is_file(), (
            f"write step '{step['name']}' presses controls from {step['control_module']}, "
            "which does not exist"
        )


def test_every_control_the_write_half_presses_still_exists_in_the_application(
    manifest: dict,
) -> None:
    """The check the read half never needed: handles, not addresses.

    Rename `#upload-file`, drop `data-run-outcome`, or relabel the Start-run button, and
    the routes and the operations are all still correct -- while the write half can no
    longer press or read anything. This is what makes that red at gate time.
    """
    _require(WEB_SRC)
    source = application_source(WEB_SRC)
    missing: list[tuple[str, str]] = []
    for step in write_steps(manifest):
        for handle in sorted(handles_named_by_write_step(step)):
            if handle not in source:
                missing.append((step["name"], handle))
    assert not missing, (
        f"the write half names {len(missing)} handle(s) that no longer appear anywhere in "
        f"web/src: {missing}. The journey would still address the right routes and the "
        "right operations, and would be unable to press or read a thing."
    )


def test_the_write_half_uploads_a_fixture_that_is_on_disk(manifest: dict) -> None:
    """An upload step with no document is a step that proves nothing."""
    fixture = REPOSITORY_ROOT / manifest["write"]["fixture"]
    assert fixture.is_file(), (
        f"the write half uploads {manifest['write']['fixture']}, which is not on disk. "
        "There would be nothing to upload and nothing for a run to read."
    )
    assert fixture.stat().st_size > 0, f"{fixture} is empty"


def test_every_status_the_write_half_declares_is_one_the_contract_publishes(
    manifest: dict, openapi: dict
) -> None:
    """`202` is not a taste. It is what `POST /runs` publishes since `W20-EXEC`.

    If execution moved back inside the request and the contract went to `201`, this goes
    red at gate time rather than at the next person's browser run.
    """
    wrong: list[str] = []
    for step in write_steps(manifest):
        for call in step.get("expects_api") or ():
            declared = call.get("expect_status")
            if declared is None:
                continue
            published = responses_published_for(openapi, call["method"], call["path"])
            if declared not in published:
                wrong.append(
                    f"{step['name']}: {call['operationId']} declares {declared}, "
                    f"contract publishes {sorted(published)}"
                )
    assert not wrong, (
        "the write half declares statuses the contract does not publish for those "
        f"operations: {wrong}"
    )


def test_every_wait_in_the_write_half_carries_a_positive_bound(manifest: dict) -> None:
    """An unbounded wait reports nothing at all, which is the `D-5` failure mode."""
    for step in write_steps(manifest):
        capture = step.get("capture")
        if capture is not None:
            bound = capture.get("bound_ms")
            assert isinstance(bound, int) and bound > 0, (
                f"write step '{step['name']}' captures with bound_ms={bound!r}; a capture "
                "that can wait forever hangs the journey and reports nothing"
            )
        await_terminal = step.get("await_terminal")
        if await_terminal is not None:
            bound = await_terminal.get("bound_ms")
            assert isinstance(bound, int) and bound > 0, (
                f"write step '{step['name']}' waits for a terminal with "
                f"bound_ms={bound!r}; the application's own poller has no deadline by "
                "design, so the bound has to live here"
            )


def test_the_run_states_the_write_half_names_are_the_contract_s_own(
    manifest: dict, openapi: dict
) -> None:
    """`succeeded` is a stage status, never a run state. The contract decides, not this."""
    published = run_states_in_contract(openapi)
    for step in write_steps(manifest):
        await_terminal = step.get("await_terminal")
        if await_terminal is None:
            continue
        named = {await_terminal["non_terminal_value"], *await_terminal["accept"]}
        # `in_flight` is the screen's own word for "not terminal yet" and is deliberately
        # not a contract state: it is what `run-progress.tsx` renders as `data-run-outcome`
        # while `runOutcome` has no terminal to report.
        named.discard("in_flight")
        unknown = sorted(named - published)
        assert not unknown, (
            f"write step '{step['name']}' names run state(s) the contract does not "
            f"publish: {unknown}. Published: {sorted(published)}"
        )


# --------------------------------------------------------------------------------------
# The negative controls. Each one proves the matching check above can go red, and each
# reads nothing outside this file -- so these do run inside a `make mutation-copy` tree.
# --------------------------------------------------------------------------------------

_SYNTHETIC_MANIFEST = {
    "api_prefix": "/bff/v1",
    "routes": [
        {
            "name": "projects",
            "path": "/projects",
            "page_module": "web/src/app/projects/page.tsx",
            "expects_api": [
                {"method": "GET", "path": "/projects", "operationId": "listProjects"}
            ],
        }
    ],
}

_SYNTHETIC_CONTRACT = {
    "paths": {"/projects": {"get": {"operationId": "listProjects"}}},
}


def test_control_an_unwalked_screen_is_detected() -> None:
    in_tree = {"/projects", "/projects/{project_uid}/settings"}
    in_manifest = set(screens_in_manifest(_SYNTHETIC_MANIFEST))
    assert in_tree - in_manifest == {"/projects/{project_uid}/settings"}


def test_control_a_deleted_screen_is_detected() -> None:
    in_tree: set[str] = set()
    in_manifest = set(screens_in_manifest(_SYNTHETIC_MANIFEST))
    assert in_manifest - in_tree == {"/projects"}


def test_control_the_screen_scan_really_reads_a_tree(tmp_path: Path) -> None:
    """The set arithmetic above is only worth as much as the scan that feeds it.

    Built here rather than read from `web/`, so this control runs in a mutation copy and
    proves the scan finds nested and dynamic screens and ignores route handlers.
    """
    app = tmp_path / "web" / "src" / "app"
    for relative in (
        "page.tsx",
        "projects/page.tsx",
        "projects/[project_uid]/page.tsx",
        "projects/[project_uid]/runs/[run_id]/review/page.tsx",
    ):
        target = app / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    handler = app / "bff" / "v1" / "[...path]" / "route.ts"
    handler.parent.mkdir(parents=True, exist_ok=True)
    handler.write_text("", encoding="utf-8")

    assert set(screens_in_app_tree(app)) == {
        "/",
        "/projects",
        "/projects/{project_uid}",
        "/projects/{project_uid}/runs/{run_id}/review",
    }


def test_control_a_renamed_dynamic_segment_changes_the_derived_path() -> None:
    before = route_path_of_page_module("web/src/app/projects/[project_uid]/page.tsx")
    after = route_path_of_page_module("web/src/app/projects/[projectId]/page.tsx")
    assert before == "/projects/{project_uid}"
    assert after == "/projects/{projectId}"
    assert before != after


def test_control_a_renamed_operation_is_detected() -> None:
    claimed = operations_claimed_by_manifest(_SYNTHETIC_MANIFEST)
    renamed = {"paths": {"/projects": {"get": {"operationId": "listAllProjects"}}}}
    assert claimed - operations_in_contract(renamed) == {
        ("GET", "/projects", "listProjects")
    }
    assert claimed - operations_in_contract(_SYNTHETIC_CONTRACT) == set()


def test_control_a_changed_method_is_detected() -> None:
    claimed = operations_claimed_by_manifest(_SYNTHETIC_MANIFEST)
    moved = {"paths": {"/projects": {"post": {"operationId": "listProjects"}}}}
    assert claimed - operations_in_contract(moved) == {("GET", "/projects", "listProjects")}


def test_control_a_missing_input_fails_rather_than_skips(tmp_path: Path) -> None:
    # `pytest.fail` raises `Failed`, which derives from BaseException and not Exception --
    # so `pytest.raises(Exception)` here would let the failure through and this control
    # would itself be the vacuous test it exists to rule out.
    with pytest.raises(pytest.fail.Exception) as caught:
        _require(tmp_path / "absent.json")
    assert "would prove nothing" in str(caught.value)


# --------------------------------------------------------------------------------------
# The write half's negative controls. `W22-E2E`.
#
# Same rule as above: each one proves the matching check can go red, each reads nothing
# outside this file, and each was RUN and watched to catch what it claims to catch --
# `W21-E2E` shipped one that was vacuous when written and only running it found that.
# --------------------------------------------------------------------------------------

_SYNTHETIC_WRITE_MANIFEST = {
    "api_prefix": "/bff/v1",
    "routes": [
        {
            "name": "projects",
            "path": "/projects",
            "page_module": "web/src/app/projects/page.tsx",
            "expects_api": [
                {"method": "GET", "path": "/projects", "operationId": "listProjects"}
            ],
        }
    ],
    "write": {
        "fixture": "fixtures/synthetic/ar/ar_baseline.pdf",
        "steps": [
            {
                "name": "create-project",
                "at": "/projects",
                "page_module": "web/src/app/projects/page.tsx",
                "control_module": "web/src/features/create-project/ui/create-project-form.tsx",
                "actions": [
                    {"do": "fill", "selector": "#new-project-name", "value": "x"},
                    {
                        "do": "click",
                        "selector": 'form button[type="submit"]',
                        "text": "Создать",
                    },
                ],
                "expects_api": [
                    {
                        "method": "POST",
                        "path": "/projects",
                        "operationId": "createProject",
                        "expect_status": 201,
                    }
                ],
                "capture": {
                    "kind": "attribute",
                    "selector": "[data-created-project]",
                    "attribute": "data-created-project",
                    "as": ["project_uid"],
                    "bound_ms": 30000,
                },
                "forbids_rendered": ['[role="alert"]'],
            },
            {
                "name": "start-run",
                "at": "/projects",
                "page_module": "web/src/app/projects/page.tsx",
                "control_module": "web/src/features/start-run/ui/start-run-control.tsx",
                "actions": [{"do": "click", "selector": "button", "text": "Запустить прогон"}],
                "expects_api": [
                    {
                        "method": "POST",
                        "path": "/runs",
                        "operationId": "startRun",
                        "expect_status": 202,
                    }
                ],
                "await_terminal": {
                    "outcome_selector": "[data-run-outcome]",
                    "outcome_attribute": "data-run-outcome",
                    "non_terminal_value": "in_flight",
                    "accept": ["published", "partial"],
                    "activity_selector": "[data-run-activity]",
                    "activity_attribute": "data-run-activity",
                    "bound_ms": 150000,
                },
            },
        ],
    },
}

_SYNTHETIC_WRITE_CONTRACT = {
    "paths": {
        "/projects": {
            "get": {"operationId": "listProjects", "responses": {"200": {}}},
            "post": {"operationId": "createProject", "responses": {"201": {}, "409": {}}},
        },
        "/runs": {"post": {"operationId": "startRun", "responses": {"202": {}, "404": {}}}},
    },
    "components": {
        "schemas": {"RunState": {"enum": ["queued", "running", "published", "partial"]}}
    },
}


def _only_write_step(name: str) -> dict:
    return next(
        step
        for step in _SYNTHETIC_WRITE_MANIFEST["write"]["steps"]
        if step["name"] == name
    )


def test_control_a_write_half_that_never_posts_is_detected() -> None:
    read_only = {"routes": _SYNTHETIC_WRITE_MANIFEST["routes"]}
    assert write_steps(read_only) == []
    assert write_steps(_SYNTHETIC_WRITE_MANIFEST) != []


def test_control_the_write_half_s_operations_reach_the_contract_check() -> None:
    claimed = operations_claimed_by_manifest(_SYNTHETIC_WRITE_MANIFEST)
    assert ("POST", "/runs", "startRun") in claimed
    assert ("POST", "/projects", "createProject") in claimed
    renamed = {
        "paths": {
            "/projects": {
                "get": {"operationId": "listProjects"},
                "post": {"operationId": "createProject"},
            },
            "/runs": {"post": {"operationId": "beginRun"}},
        }
    }
    assert claimed - operations_in_contract(renamed) == {("POST", "/runs", "startRun")}


def test_control_a_renamed_id_is_detected() -> None:
    handles = handles_named_by_write_step(_only_write_step("create-project"))
    assert handles == {'id="new-project-name"', "data-created-project", "Создать"}
    source_after_a_rename = (
        '<input id="newProjectName" /><p data-created-project="x">Создать</p>'
    )
    missing = sorted(h for h in handles if h not in source_after_a_rename)
    assert missing == ['id="new-project-name"']


def test_control_a_dropped_marker_attribute_is_detected() -> None:
    handles = handles_named_by_write_step(_only_write_step("start-run"))
    assert handles == {"data-run-outcome", "data-run-activity", "Запустить прогон"}
    source_after_the_marker_went = '<p data-run-activity="stopped">Запустить прогон</p>'
    missing = sorted(h for h in handles if h not in source_after_the_marker_went)
    assert missing == ["data-run-outcome"]


def test_control_a_relabelled_button_is_detected() -> None:
    handles = handles_named_by_write_step(_only_write_step("start-run"))
    source_after_the_relabel = (
        '<button data-run-outcome data-run-activity>Run the audit</button>'
    )
    assert "Запустить прогон" in handles
    assert "Запустить прогон" not in source_after_the_relabel


def test_control_a_generic_selector_claims_nothing() -> None:
    """`form button[type="submit"]` names no application handle, and must claim none.

    Without this the guard would demand a literal `form button[type="submit"]` in
    `web/src` and be red forever, which is a guard nobody keeps.
    """
    step = {
        "actions": [{"do": "click", "selector": 'form button[type="submit"]'}],
    }
    assert handles_named_by_write_step(step) == set()


def test_control_the_source_scan_really_reads_a_tree(tmp_path: Path) -> None:
    """The handle arithmetic is only worth as much as the scan that feeds it."""
    web_src = tmp_path / "web" / "src"
    (web_src / "features" / "create-project" / "ui").mkdir(parents=True)
    (web_src / "features" / "create-project" / "ui" / "form.tsx").write_text(
        '<input id="new-project-name" />', encoding="utf-8"
    )
    (web_src / "shared").mkdir(parents=True)
    (web_src / "shared" / "keys.ts").write_text("data-created-project", encoding="utf-8")
    (web_src / "shared" / "notes.md").write_text(
        'id="this-is-not-source"', encoding="utf-8"
    )
    source = application_source(web_src)
    assert 'id="new-project-name"' in source
    assert "data-created-project" in source
    assert "this-is-not-source" not in source


def test_control_a_status_the_contract_does_not_publish_is_detected() -> None:
    published = responses_published_for(_SYNTHETIC_WRITE_CONTRACT, "POST", "/runs")
    assert published == {202, 404}
    assert 202 in published
    assert 201 not in published, (
        "if POST /runs ever publishes 201 again, execution moved back inside the request "
        "and the write half's 202 claim is the thing that must be corrected"
    )


def test_control_an_unbounded_wait_is_detected() -> None:
    step = json.loads(json.dumps(_only_write_step("start-run")))
    assert isinstance(step["await_terminal"]["bound_ms"], int)
    for absent in (None, 0, -1, "150000"):
        step["await_terminal"]["bound_ms"] = absent
        bound = step["await_terminal"]["bound_ms"]
        assert not (isinstance(bound, int) and not isinstance(bound, bool) and bound > 0)


def test_control_a_run_state_the_contract_does_not_publish_is_detected() -> None:
    published = run_states_in_contract(_SYNTHETIC_WRITE_CONTRACT)
    named = {"published", "partial"}
    assert named - published == set()
    # `succeeded` is a StageResult status. Naming it as a run terminal is the exact
    # mistake `shared/api/run-state.ts` exists to make impossible, and it reddens here.
    assert {"succeeded"} - published == {"succeeded"}


def test_control_a_write_step_on_an_unwalked_screen_is_detected() -> None:
    walked = set(screens_in_manifest(_SYNTHETIC_WRITE_MANIFEST))
    assert _only_write_step("create-project")["at"] in walked
    moved = dict(_only_write_step("create-project"), at="/projects/{project_uid}")
    assert moved["at"] not in walked


def test_control_a_write_step_whose_page_module_moved_is_detected() -> None:
    step = _only_write_step("create-project")
    assert route_path_of_page_module(step["page_module"]) == step["at"]
    moved = "web/src/app/projects/[project_uid]/page.tsx"
    assert route_path_of_page_module(moved) != step["at"]


# --------------------------------------------------------------------------------------
# The refusal half. `W28-GUARD`, over `W27-REFUSE`'s six measured drives.
#
# `W27-REFUSE` drove six negative fixtures through a browser, all six held, and it wrote
# the verdicts into `refusals.mjs`'s own source -- where `make gate` could not see them.
# Its own review named three additions the manifest would need. Measured against the files
# here, two of the three were already there under other names, and the missing thing was
# never a field: see `docs/program/reviews/W28-GUARD.md`.
#
# What moved to gate time is addressing, declaration coherence, and the handles and
# sentences the screens own. What did NOT move is behaviour -- that the envelope really
# carries that constraint, that the screen really renders it, that `Upload` really goes
# unpressable, that nothing was published. Those stay with `refusals.mjs` against a live
# stack, and are named in the manifest's own `$comment` rather than quietly claimed here.
# --------------------------------------------------------------------------------------


def refusal_section(manifest: dict) -> dict:
    return dict((manifest.get("refusals") or {}))


def refusal_cases(manifest: dict) -> list[dict]:
    return list(refusal_section(manifest).get("cases") or ())


def refusal_api(manifest: dict) -> dict | None:
    """The one operation a server-side refusal calls, or ``None`` if none is declared."""
    call = refusal_section(manifest).get("api")
    return call if isinstance(call, dict) and "operationId" in call else None


#: What each `refused_by` must declare, and what it must not. A client-side refusal has no
#: status, no envelope and no server classification, because no request was made -- and a
#: case that declares them anyway is a case nobody has thought through.
_REFUSAL_FIELDS = {
    "client": (
        frozenset({"precheck_problem"}),
        frozenset(
            {"expect_status", "error_code", "constraint", "failure_kind",
             "expects_rendered_from_envelope"}
        ),
    ),
    "server": (
        frozenset(
            {"expect_status", "error_code", "constraint", "failure_kind",
             "expects_rendered_from_envelope"}
        ),
        frozenset({"precheck_problem"}),
    ),
}


def handles_named_by_refusal(case: dict, section: dict) -> set[str]:
    """Every handle a refusal case names that must exist in ``web/src``.

    The marker ATTRIBUTES the panel is read by, and the marker VALUES the case declares.
    A value is a handle exactly as much as an attribute is: `data-precheck-problem` could
    survive a rename of `too_large` to `over_limit`, and the case would then assert a word
    no screen can produce.
    """
    out: set[str] = set()
    if case["refused_by"] == "client":
        out.add(section["precheck_marker"])
        out.add(case["precheck_problem"])
    else:
        out.add(section["failure_marker"])
        out.add(case["failure_kind"])
    return out


def test_the_manifest_has_a_refusal_half_at_all(manifest: dict) -> None:
    """Six drives that only one person ever saw are not a guard. This is what makes them one."""
    cases = refusal_cases(manifest)
    assert cases, (
        "manifest.json declares no `refusals` section, so `make gate` says nothing about "
        "what a person sees when they drop the wrong file in -- which is the whole of "
        "what W27-REFUSE measured and D-44 depends on."
    )
    assert refusal_api(manifest) is not None, (
        "the refusal half declares no `api`, so a renamed `uploadDocument` would not "
        "redden here."
    )
    by_where = {case["refused_by"] for case in cases}
    assert by_where == {"client", "server"}, (
        "the refusal half declares refusals at "
        f"{sorted(by_where)} only. 'the browser never sent it' and 'the server refused it' "
        "are different products, and a half that measures one of them measures half a "
        f"screen. Declared: {[(c['fixture'], c['refused_by']) for c in cases]}"
    )


#: `W55B-INGEST-01` deleted `negative/oversize.pdf` (26 MiB) and `negative/too_many_pages.pdf`
#: (31 pages): the limits are 250 MiB and 500 pages, and a file that size is never committed. The
#: two cases that used them are GENERATED when the refusal drive starts, by
#: `tools/fixtures/build_journey_inputs.py` into a temporary directory. The manifest declares them
#: twice -- `generated: true` on the case, and the tool's file set in `refusals.generated.files` --
#: and this test holds the declarations, the tool and the disk to each other.
JOURNEY_INPUTS_TOOL = REPOSITORY_ROOT / "tools" / "fixtures" / "build_journey_inputs.py"


def tool_file_names() -> list[str]:
    """The names the generator says it writes (``--list``: no builder is imported)."""
    done = subprocess.run(
        [sys.executable, "-I", str(JOURNEY_INPUTS_TOOL), "--list"],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return done.stdout.split()


def refusal_fixture_problem(
    section: dict, case: dict, generated_names: Sequence[str], tool_names: Sequence[str]
) -> str | None:
    """Why a refusal case has nothing to attach, or ``None`` when it has something.

    A committed case needs its file on disk, in its own ``fixture_dir`` if it names one and
    the section's otherwise. A generated case needs the manifest to declare the name and the
    tool to write it.
    """
    name = case["fixture"]
    if case.get("generated") is True:
        if name not in generated_names:
            return f"refusal case '{name}' says generated but `refusals.generated.files` does not name it"
        if name not in tool_names:
            return f"refusal case '{name}' is generated, and the tool's --list ({list(tool_names)}) does not write it"
        return None
    fixture = REPOSITORY_ROOT / case.get("fixture_dir", section["fixture_dir"]) / name
    if not fixture.is_file():
        return f"refusal case '{name}' names {fixture}, which is not on disk"
    return None if fixture.stat().st_size > 0 else f"{fixture} is empty"


def declared_generated(section: dict) -> list[str]:
    return list(section.get("generated", {}).get("files", []))


def test_every_refusal_fixture_the_journey_declares_is_on_disk_or_generated(manifest: dict) -> None:
    """A refusal case with no file is a case that drives nothing -- unless the tool makes the
    file when the drive starts (the two big inputs, `W55B-INGEST-01`)."""
    section = refusal_section(manifest)
    generated, tool = declared_generated(section), tool_file_names()
    for case in refusal_cases(manifest):
        problem = refusal_fixture_problem(section, case, generated, tool)
        assert problem is None, (
            f"{problem}. There would be nothing to attach and nothing to refuse."
        )


def test_the_generated_set_is_declared_once_and_agrees_everywhere(manifest: dict) -> None:
    """Three statements of the same set -- the cases that say `generated`, the section's
    `files`, the tool's `--list` -- and a name in one and not the others is a drive that
    attaches nothing or a file nobody asked for."""
    section = refusal_section(manifest)
    by_case = sorted(c["fixture"] for c in refusal_cases(manifest) if c.get("generated") is True)
    assert by_case == sorted(declared_generated(section)) == sorted(tool_file_names()), (
        f"cases {by_case}, refusals.generated.files {sorted(declared_generated(section))}, "
        f"the tool writes {sorted(tool_file_names())}"
    )
    tool = section["generated"]["tool"]
    assert (REPOSITORY_ROOT / tool).is_file(), f"refusals.generated.tool {tool} is not a file"
    assert (REPOSITORY_ROOT / tool) == JOURNEY_INPUTS_TOOL


def test_no_refusal_names_a_file_the_bundle_rules_made_stale(manifest: dict) -> None:
    """The names this lane removed or renamed must not come back: a PDF that was over a limit
    is no longer over it, and a bare PDF is refused by every upload."""
    section = refusal_section(manifest)
    names = {c["fixture"] for c in refusal_cases(manifest)}
    assert not names & {"oversize.pdf", "too_many_pages.pdf", "encrypted.pdf", "image_only.pdf"}, names
    assert section["fixture_dir"] == "fixtures/synthetic/ar/negative"
    assert "1 <= page_count <= 30" not in {c.get("constraint") for c in refusal_cases(manifest)}


def test_control_a_missing_refusal_fixture_is_still_found(tmp_path: Path) -> None:
    """Every way a case can have nothing to attach is a problem: a committed file that is
    gone or empty, a generated name the manifest does not declare, one the tool does not
    write -- and the honest cases are not."""
    section = {"fixture_dir": "fixtures/synthetic/ar/negative"}
    names = ["oversize_bundle.zip"]
    tool = ["oversize_bundle.zip"]
    honest_committed = {"fixture": "not_a_pdf.txt"}
    assert refusal_fixture_problem(section, honest_committed, names, tool) is None
    assert refusal_fixture_problem(section, {"fixture": "gone.pdf"}, names, tool) is not None
    (tmp_path / "empty.bin").write_bytes(b"")
    relative = os.path.relpath(tmp_path, REPOSITORY_ROOT)
    assert refusal_fixture_problem({"fixture_dir": relative}, {"fixture": "empty.bin"}, names, tool) is not None
    own_dir = {"fixture": "image_only.zip", "fixture_dir": "fixtures/synthetic/ar/bundles"}
    assert refusal_fixture_problem(section, own_dir, names, tool) is None
    wrong_dir = {"fixture": "image_only.zip"}
    assert refusal_fixture_problem(section, wrong_dir, names, tool) is not None
    generated = {"fixture": "oversize_bundle.zip", "generated": True}
    assert refusal_fixture_problem(section, generated, names, tool) is None
    assert refusal_fixture_problem(section, generated, [], tool) is not None
    assert refusal_fixture_problem(section, generated, names, []) is not None
    # a generated claim does not excuse a file that simply is not there
    assert refusal_fixture_problem(
        section, {"fixture": "gone.zip", "generated": True}, ["gone.zip"], ["oversize_bundle.zip"]
    ) is not None


def test_the_journey_inputs_tool_writes_a_sparse_oversize_and_a_501_page_bundle(tmp_path: Path) -> None:
    """The tool, run: the oversize file is past the limit, begins as a ZIP and takes next to
    no disk; the other is a ZIP; nothing else is written."""
    done = subprocess.run(
        [sys.executable, "-I", str(JOURNEY_INPUTS_TOOL), str(tmp_path)],
        capture_output=True, text=True, timeout=300,
    )
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(tool_file_names())
    oversize = tmp_path / "oversize_bundle.zip"
    stat = oversize.stat()
    assert stat.st_size > 250 * 1024 * 1024
    assert oversize.read_bytes()[:4] == b"PK\x03\x04"
    assert stat.st_blocks * 512 <= 1024 * 1024, "the stand-in was allocated, not sparse"
    assert (tmp_path / "bundle_501_pages.zip").read_bytes()[:4] == b"PK\x03\x04"
    # one page past the limit: not 500 (which the server accepts) and not 31 (the old one)
    import zipfile

    with zipfile.ZipFile(tmp_path / "bundle_501_pages.zip") as archive:
        pdf = next(name for name in archive.namelist() if name.endswith(".pdf"))
        assert re.findall(rb"/Count (\d+)", archive.read(pdf)) == [b"501"]


def test_the_journey_inputs_tool_refuses_to_allocate_the_oversize_file(tmp_path: Path) -> None:
    """The guard that keeps the stand-in sparse can fail: a file system that gave no hole
    makes the build fail and leaves nothing behind, instead of writing 251 MiB."""
    sys.path.insert(0, str(REPOSITORY_ROOT / "tools" / "fixtures"))
    try:
        import build_journey_inputs
        from portal_bundle import generated
    finally:
        sys.path.pop(0)

    def allocated_stand_in(path: Path, size: int) -> Path:
        path.write_bytes(b"PK\x03\x04" + b"\x00" * (2 * 1024 * 1024))  # really allocated
        with path.open("r+b") as handle:
            handle.truncate(size)
        return path

    original = generated.oversize_sparse_file
    generated.oversize_sparse_file = allocated_stand_in
    try:
        with pytest.raises(SystemExit) as refused:
            build_journey_inputs.build(tmp_path)
    finally:
        generated.oversize_sparse_file = original
    assert "sparse" in str(refused.value)
    assert not (tmp_path / "oversize_bundle.zip").exists()


def test_every_refusal_stands_on_the_upload_screen_the_read_walk_covers(
    manifest: dict,
) -> None:
    """The refusals press one control on one screen, and both have to be real."""
    _require(APP_DIR)
    section = refusal_section(manifest)
    module = REPOSITORY_ROOT / section["page_module"]
    assert module.is_file(), f"the refusal half names {section['page_module']}, absent"
    derived = route_path_of_page_module(section["page_module"])
    assert derived == section["at"], (
        f"the refusal half says it acts at {section['at']} but its page module sits at "
        f"{derived}"
    )
    assert section["at"] in set(screens_in_manifest(manifest)), (
        f"the refusal half acts at {section['at']}, which the read walk does not cover."
    )
    control = REPOSITORY_ROOT / section["control_module"]
    assert control.is_file(), (
        f"the refusal half presses controls from {section['control_module']}, which does "
        "not exist"
    )


def test_every_refusal_declares_the_fields_that_go_with_where_it_was_refused(
    manifest: dict,
) -> None:
    """`refused_by` is the field the six cases exist to assert, so it decides the rest."""
    wrong: list[str] = []
    for case in refusal_cases(manifest):
        where = case.get("refused_by")
        if where not in _REFUSAL_FIELDS:
            wrong.append(f"{case.get('fixture')}: refused_by={where!r} is neither client nor server")
            continue
        required, forbidden = _REFUSAL_FIELDS[where]
        for field in sorted(required):
            if case.get(field) is None:
                wrong.append(f"{case['fixture']}: refused at the {where} and declares no {field}")
        for field in sorted(forbidden):
            if field in case:
                wrong.append(
                    f"{case['fixture']}: refused at the {where} and declares {field}, "
                    "which only the other side can produce"
                )
        if not (case.get("expects_rendered") or ()):
            wrong.append(
                f"{case['fixture']}: declares no expects_rendered, so it asserts a panel "
                "appeared and nothing about what it said"
            )
    assert not wrong, f"the refusal half declares {len(wrong)} incoherent claim(s): {wrong}"


def test_every_status_a_refusal_declares_is_one_the_contract_publishes(
    manifest: dict, openapi: dict
) -> None:
    """A `422` is as declarable as a `201`: the contract decides, not the shape of the half.

    `W27-REFUSE` read the existing status check as accepting success statuses only. It
    does not -- `responses_published_for` returns every published code -- and this is what
    holds that open. Drop `422` from `uploadDocument` and the six cases go red here.
    """
    call = refusal_api(manifest)
    assert call is not None
    published = responses_published_for(openapi, call["method"], call["path"])
    wrong: list[str] = []
    for case in refusal_cases(manifest):
        declared = case.get("expect_status")
        if declared is None:
            continue
        if declared not in published:
            wrong.append(
                f"{case['fixture']}: declares {declared}, {call['operationId']} publishes "
                f"{sorted(published)}"
            )
    assert not wrong, (
        f"the refusal half declares statuses the contract does not publish: {wrong}"
    )


def test_every_marker_a_refusal_names_still_exists_in_the_application(
    manifest: dict,
) -> None:
    """Rename `data-upload-failure` or `too_large` and the six drives read nothing."""
    _require(WEB_SRC)
    source = application_source(WEB_SRC)
    section = refusal_section(manifest)
    missing: list[tuple[str, str]] = []
    for case in refusal_cases(manifest):
        for handle in sorted(handles_named_by_refusal(case, section)):
            if handle not in source:
                missing.append((case["fixture"], handle))
    assert not missing, (
        f"the refusal half names {len(missing)} marker(s) that no longer appear anywhere "
        f"in web/src: {missing}. The drives would attach the right files and read nothing."
    )


#: The frontend guard that carries the half of `D-61` this file cannot check.
RENDERED_EVIDENCE_GUARD = REPOSITORY_ROOT / "web" / "tests" / "guards" / "rendered-language.guard.test.ts"


def test_every_sentence_the_journey_requires_is_authored_by_the_control_it_presses(
    manifest: dict,
) -> None:
    """The copy-rot check, with its subject corrected. `D-61`, third instance.

    **What this used to do, and why a word boundary would not have fixed it.** It asserted
    each ``expects_rendered`` sentence by substring containment against
    ``application_source(WEB_SRC)`` -- *every* ``.ts``/``.tsx`` byte under ``web/src``,
    concatenated. So the manifest declared the sentence ``"Run"`` and passed, because
    ``Run`` occurs inside ``RunPage``, and **no screen renders it**. Containment had
    already deceived two guards before this one and both were repaired by matching on a
    word boundary; this one could not be, because **the subject was wrong rather than the
    matcher**.

    **The subject, corrected, is two questions and neither is the old one.**

    1. *Are these the application's own words, written by the thing the journey presses?*
       That is answerable from source, and it is what this test asks -- but scoped to the
       **import closure of the ``control_module`` the manifest itself names**, and over
       **authored strings only**: quoted literals and JSX text, never identifiers. ``Run``
       inside ``RunPage`` is an identifier and is no longer visible to this check.
    2. *Is the sentence evidence that the step ran, or is it on the screen anyway?* That is
       answerable only from **rendered output**, and it is asserted in
       ``web/tests/guards/rendered-language.guard.test.ts`` -- `W32-SEE`'s renderer, reused
       rather than rebuilt, because two renderers is two truths. The test below keeps that
       obligation from leaving the gate in silence.

    ``expects_rendered_from_envelope`` is still not checked here: the server supplies those
    words at run time and they are in ``web/src`` at all. They are checked against the
    declared ``constraint``, one test down.
    """
    _require(WEB_SRC)
    missing: list[str] = []
    for where, module_path, sentences in _sentences_with_their_control(manifest):
        control = REPOSITORY_ROOT / module_path
        assert control.is_file(), (
            f"{where} names control_module {module_path!r} and no such file exists. "
            "test_every_module_the_journey_names_is_on_disk covers the routes; this is "
            "the control half of the same claim."
        )
        authored = authored_strings(module_closure(control, WEB_SRC))
        for sentence in sentences:
            if not authors(authored, sentence):
                missing.append(f"{where}: {sentence!r} (not authored by {module_path} or what it imports)")
    assert not missing, (
        f"the journey requires {len(missing)} sentence(s) that the control it presses does "
        f"not author: {missing}. A reworded panel turns the journey red only when someone "
        "runs a browser, which is the rot this file exists to stop. Note the scope: this "
        "reads the control module's import closure and only its STRING literals, so a "
        "sentence that merely occurs somewhere in web/src no longer satisfies it -- that "
        "was D-61."
    )


def _sentences_with_their_control(manifest: dict) -> list[tuple[str, str, list[str]]]:
    """``(where, control_module, sentences)`` for every step and case that declares any."""
    out: list[tuple[str, str, list[str]]] = []
    for step in write_steps(manifest):
        sentences = list(step.get("expects_rendered") or ())
        if sentences:
            out.append((step["name"], step["control_module"], sentences))
    section = refusal_section(manifest)
    for case in refusal_cases(manifest):
        sentences = list(case.get("expects_rendered") or ())
        if sentences:
            out.append((case["fixture"], section["control_module"], sentences))
    return out


def test_the_rendered_half_of_d61_has_not_left_the_frontend_guard(manifest: dict) -> None:
    """The obligation this file hands to the renderer must not be able to leave in silence.

    `OPERATING_CONSTRAINTS.md` §4.65 is the precedent and the reason: a rule that lives in
    a command nothing runs is documentation. ``query-key-shape.guard.test.ts`` asserts the
    ``Makefile`` line that runs the typechecker for exactly this reason.

    Here the risk is sharper, because deleting the rendered check would leave **this** file
    green and looking complete: the source half above would go on passing and nobody would
    be told that the *"is it evidence"* half had gone. So the marker is named, and its
    absence is red in the canonical battery, which runs with no ``node_modules`` at all.
    """
    _require(RENDERED_EVIDENCE_GUARD)
    guard = RENDERED_EVIDENCE_GUARD.read_text(encoding="utf-8")
    for marker in (
        "D-61: every sentence the journey calls evidence is evidence",
        "export function journeySentences",
        "tests/e2e/pc01/journey/manifest.json",
        "STILL_EVIDENCE_THOUGH_RENDERED",
    ):
        assert marker in guard, (
            f"{RENDERED_EVIDENCE_GUARD.name} no longer carries {marker!r}. The half of D-61 "
            "that needs a RENDERED screen -- that a sentence offered as proof a step ran is "
            "not already on the screen before it runs -- lives there and nowhere else. "
            "Restore it, or move it somewhere this assertion names."
        )
    # Non-vacuous: the sentences this file checks and the ones that guard checks are the
    # same set, so a manifest that stopped declaring any would make BOTH halves trivial.
    declared = sum(len(s) for _, _, s in _sentences_with_their_control(manifest))
    assert declared > 5, (
        f"the manifest declares {declared} expects_rendered sentence(s); both halves of "
        "D-61 are close to vacuous and that is the state this check exists to report"
    )


def test_every_envelope_sentence_a_refusal_requires_is_part_of_its_own_constraint(
    manifest: dict,
) -> None:
    """The half the gate CAN check about server-supplied text: that it is self-consistent.

    The screen echoes the envelope's `details.constraint`. If a case declares that the
    screen must say `page_count` while declaring the envelope carries `not_encrypted`, one
    of the two is wrong and no stack is needed to know it.
    """
    wrong: list[str] = []
    for case in refusal_cases(manifest):
        constraint = case.get("constraint")
        if constraint is None:
            continue
        for sentence in case.get("expects_rendered_from_envelope") or ():
            if sentence not in constraint:
                wrong.append(
                    f"{case['fixture']}: requires the screen to render {sentence!r} from "
                    f"the envelope, and declares the envelope carries {constraint!r}"
                )
    assert not wrong, f"the refusal half contradicts itself in {len(wrong)} place(s): {wrong}"


def test_no_refusal_declares_the_generic_classification_it_exists_to_rule_out(
    manifest: dict,
) -> None:
    """The check that stops a red being 'fixed' by declaring defeat.

    `W27-REFUSE`'s point was that a fault the catalog names precisely must not render as
    `server_error`. The cheapest way to make a failing drive pass is to declare the
    generic kind here, and that would silently retire the measurement.
    """
    section = refusal_section(manifest)
    generic = set(section.get("generic_kinds") or ())
    assert generic, "the refusal half declares no `generic_kinds`, so this check is vacuous"
    declared = {
        case["fixture"]: case["failure_kind"]
        for case in refusal_cases(manifest)
        if case.get("failure_kind") is not None
    }
    surrendered = sorted(f for f, kind in declared.items() if kind in generic)
    assert not surrendered, (
        f"{surrendered} declare a generic classification ({sorted(generic)}) for a fault "
        "the catalog names. That is the defect W27-REFUSE went looking for, written down "
        "as the expectation."
    )


# --------------------------------------------------------------------------------------
# The refusal half's negative controls. Same rule as the other two: pure functions over
# synthetic data, each one RUN and watched to catch what it claims to catch.
# --------------------------------------------------------------------------------------

_SYNTHETIC_REFUSALS = {
    "refusals": {
        "at": "/projects/{project_uid}",
        "page_module": "web/src/app/projects/[project_uid]/page.tsx",
        "control_module": "web/src/features/upload-document/ui/upload-document-form.tsx",
        "fixture_dir": "fixtures/synthetic/ar/negative",
        "api": {
            "method": "POST",
            "path": "/projects/{project_uid}/documents",
            "operationId": "uploadDocument",
        },
        "precheck_marker": "data-precheck-problem",
        "failure_marker": "data-upload-failure",
        "generic_kinds": ["server_error", "unknown", "unrecognized", "transport"],
        "cases": [
            {
                "fixture": "not_a_pdf.txt",
                "refused_by": "client",
                "precheck_problem": "not_pdf",
                "expects_rendered": ["не является PDF", "Ничего не отправлено"],
            },
            {
                "fixture": "encrypted.pdf",
                "refused_by": "server",
                "expect_status": 422,
                "error_code": "validation_failed",
                "constraint": "not_encrypted",
                "failure_kind": "unsupported_input",
                "expects_rendered": ["выходит за допустимые ограничения"],
                "expects_rendered_from_envelope": ["not_encrypted"],
            },
        ],
    }
}

_SYNTHETIC_REFUSAL_CONTRACT = {
    "paths": {
        "/projects/{project_uid}/documents": {
            "post": {"operationId": "uploadDocument", "responses": {"201": {}, "422": {}}}
        }
    }
}


def _only_refusal(fixture: str) -> dict:
    return next(
        case for case in _SYNTHETIC_REFUSALS["refusals"]["cases"] if case["fixture"] == fixture
    )


def test_control_a_manifest_with_no_refusal_half_is_detected() -> None:
    assert refusal_cases({"routes": []}) == []
    assert refusal_api({"routes": []}) is None
    assert len(refusal_cases(_SYNTHETIC_REFUSALS)) == 2


def test_control_the_refusal_half_s_operation_reaches_the_contract_check() -> None:
    claimed = operations_claimed_by_manifest(dict(_SYNTHETIC_MANIFEST, **_SYNTHETIC_REFUSALS))
    assert ("POST", "/projects/{project_uid}/documents", "uploadDocument") in claimed
    renamed = {
        "paths": {
            "/projects": {"get": {"operationId": "listProjects"}},
            "/projects/{project_uid}/documents": {"post": {"operationId": "postDocument"}},
        }
    }
    assert claimed - operations_in_contract(renamed) == {
        ("POST", "/projects/{project_uid}/documents", "uploadDocument")
    }


def test_control_a_refusal_claiming_the_wrong_side_is_detected() -> None:
    """`W27-REFUSE`'s own reddening fixture in miniature: a client refusal called a server one."""
    honest = _only_refusal("not_a_pdf.txt")
    required, forbidden = _REFUSAL_FIELDS[honest["refused_by"]]
    assert not [f for f in required if honest.get(f) is None]
    assert not [f for f in forbidden if f in honest]

    lying = dict(honest, refused_by="server")
    required, forbidden = _REFUSAL_FIELDS["server"]
    assert sorted(f for f in required if lying.get(f) is None) == [
        "constraint",
        "error_code",
        "expect_status",
        "expects_rendered_from_envelope",
        "failure_kind",
    ]
    assert sorted(f for f in forbidden if f in lying) == ["precheck_problem"]


def test_control_a_status_no_operation_publishes_is_detected() -> None:
    published = responses_published_for(
        _SYNTHETIC_REFUSAL_CONTRACT, "POST", "/projects/{project_uid}/documents"
    )
    assert published == {201, 422}, (
        "a refusal declares 422 and the existing status check accepts it unchanged -- "
        "the third addition W27-REFUSE named was already there"
    )
    assert 413 not in published, (
        "nginx's own 413 is not an operation of this contract, which is exactly why D-44's "
        "headroom has to hold"
    )


def test_control_a_renamed_marker_value_is_detected() -> None:
    section = _SYNTHETIC_REFUSALS["refusals"]
    handles = handles_named_by_refusal(_only_refusal("not_a_pdf.txt"), section)
    assert handles == {"data-precheck-problem", "not_pdf"}
    source_after_a_rename = "<p data-precheck-problem={p}>{message(p)}</p> 'not_a_pdf'"
    assert sorted(h for h in handles if h not in source_after_a_rename) == ["not_pdf"]

    server_handles = handles_named_by_refusal(_only_refusal("encrypted.pdf"), section)
    assert server_handles == {"data-upload-failure", "unsupported_input"}


def test_control_a_reworded_panel_is_detected() -> None:
    case = _only_refusal("not_a_pdf.txt")
    source_after_the_rewrite = "Этот файл не является PDF. Мы его не загрузили."
    missing = [s for s in case["expects_rendered"] if s not in source_after_the_rewrite]
    assert missing == ["Ничего не отправлено"]


def test_control_a_sentence_that_is_only_an_identifier_is_detected() -> None:
    """`D-61` itself, in miniature and over a synthetic source. Reads nothing on disk.

    The three things the repaired subject rules out, one per assertion: an identifier, a
    sentence authored by a module the control does not import, and a word that is only a
    fragment of a longer one inside a real string literal.
    """
    source = "export function RunPage() { return <p>Прогон завершился</p>; } const n = 'RunStateBadge';"
    # The old check -- containment against source -- accepted all three of these.
    assert "Run" in source and "RunPage" in source
    # The repaired one accepts none.
    assert not authors(authored_strings_of(source), "Run")
    assert not authors(authored_strings_of(source), "RunPage")
    # And still accepts what a screen actually renders.
    assert authors(authored_strings_of(source), "Прогон завершился")


def test_control_a_doc_comment_does_not_author_a_sentence() -> None:
    """Comments are stripped before literals are read, and the control says why it matters.

    This repository writes markdown in its doc comments, so an identifier between
    backticks reads as a template literal to any scan that does not strip them first --
    measured on the real tree, where it kept `D-61`'s own `Run` alive through the first
    version of this repair.
    """
    commented = "/** `RunStatus` and `useStartRun` are the seam. */ const a = 1;"
    assert not authors(authored_strings_of(commented), "RunStatus")
    assert authors(authored_strings_of("const a = 'RunStatus';"), "RunStatus")


def authored_strings_of(source: str) -> str:
    """`authored_strings` over one in-memory module, for the controls above."""
    out: list[str] = []
    for groups in _LITERAL.findall(_COMMENT.sub(" ", source)):
        out.extend(part for part in groups if part)
    return "\n".join(out)


def test_control_the_rendered_half_cannot_leave_without_being_noticed() -> None:
    """The marker check is only worth having if a deletion really reddens it."""
    guard = RENDERED_EVIDENCE_GUARD.read_text(encoding="utf-8")
    marker = "D-61: every sentence the journey calls evidence is evidence"
    assert marker in guard
    assert marker not in guard.replace(marker, "some other describe title")


def test_control_an_envelope_sentence_that_contradicts_its_constraint_is_detected() -> None:
    case = _only_refusal("encrypted.pdf")
    assert all(s in case["constraint"] for s in case["expects_rendered_from_envelope"])
    contradictory = dict(case, constraint="a_constraint_no_envelope_carries")
    assert [
        s
        for s in contradictory["expects_rendered_from_envelope"]
        if s not in contradictory["constraint"]
    ] == ["not_encrypted"]


def test_control_a_surrendered_classification_is_detected() -> None:
    generic = set(_SYNTHETIC_REFUSALS["refusals"]["generic_kinds"])
    assert _only_refusal("encrypted.pdf")["failure_kind"] not in generic
    assert "server_error" in generic


# =====================================================================================
# `W32-SEE`: the instrument keeps the capability `D-55` was opened for.
#
# `D-55` was opened because `cdp.mjs` could not screenshot, so `R-18`'s rendered evidence
# could only come from a harness outside the tree -- which died with the session that
# wrote it, `D-5` again. The method exists now. **Nothing in the gate would notice it
# being deleted**, and a capability nothing checks is a capability that goes away.
#
# What these two can and cannot prove is stated rather than implied, because it is the
# same residue this file already carries for handles: they prove the primitive is
# **declared and used**, not that it photographs anything. The behavioural proof is
# `tests/e2e/pc01/journey/prove_the_screenshot_sees.mjs`, which decodes the PNG and
# checks the pixels -- and needs a Chromium binary, so it cannot live in a stack-free
# gate any more than the journey can.
# =====================================================================================

CDP = JOURNEY_DIR / "cdp.mjs"
LOOK = JOURNEY_DIR / "look.mjs"


def test_the_instrument_still_declares_a_screenshot_primitive() -> None:
    source = _require(CDP).read_text(encoding="utf-8")
    assert "async screenshot(" in source, (
        "cdp.mjs no longer declares a screenshot primitive. D-55 was opened because it "
        "had none and R-18 makes rendered evidence an acceptance condition; removing it "
        "sends the next design wave back to a harness outside the tree."
    )
    assert "Page.captureScreenshot" in source, (
        "cdp.mjs declares screenshot() but no longer speaks Page.captureScreenshot, so "
        "whatever it now writes is not a photograph of the page."
    )


def test_the_reading_tool_and_the_instrument_still_agree_about_it() -> None:
    """The cross-file half, which a single-file check cannot give.

    `look.mjs --shot` is the only caller in the tree. If the method is renamed on one
    side only, the flag silently stops working -- exactly the rot this module exists to
    catch for controls and markers. Checked as a pair for the same reason.
    """
    look = _require(LOOK).read_text(encoding="utf-8")
    assert "--shot" in look, "look.mjs no longer offers --shot"
    assert "page.screenshot(" in look, (
        "look.mjs declares --shot but calls no screenshot primitive, so the flag writes "
        "nothing."
    )


def test_control_a_removed_screenshot_is_detected() -> None:
    """Anti-vacuity: the two checks above, against sources that lost the method."""
    without_method = "class Page { async goto(url) {} }"
    assert "async screenshot(" not in without_method
    renamed = _require(CDP).read_text(encoding="utf-8").replace("async screenshot(", "async capture(")
    assert "async screenshot(" not in renamed
    assert "page.screenshot(" not in "  await page.capture(join(OUT_DIR, name));"


# =====================================================================================
# `W44-JOURNEY`: the sign-in and the declared width.
#
# `D-92`. The BFF has answered `401` without a session cookie since wave 34 and the
# journey had no sign-in, so it walked route 2 of 15 for nine waves. The repair is a
# `session` section here and `tests/e2e/pc01/journey/session.mjs` beside the walk.
#
# What these checks are for is the same thing the rest of this file is for -- the journey
# rots when the application moves under it -- plus one property the others do not have:
# **the gate, not a paragraph, is what keeps a credential out of this repository.** A
# `session` action names the FIELD it fills and never a value, and
# `test_no_session_action_carries_a_credential` is what makes that true rather than
# intended.
#
# `D-93`. The `viewport` section is the declared width `journey.mjs` lays every route out
# at. These checks cannot see a layout -- nothing in a stack-free gate can, which is the
# whole of the row -- so they check that the declaration is well-formed and that the
# assertion is still wired to it. The behavioural proof is
# `tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs`, which needs a browser.
# =====================================================================================

SESSION_MODULE = JOURNEY_DIR / "session.mjs"
WIDTH_MODULE = JOURNEY_DIR / "width.mjs"
JOURNEY_SCRIPT = JOURNEY_DIR / "journey.mjs"
WIDTH_PROOF = JOURNEY_DIR / "prove_the_width_assertion_can_fail.mjs"

#: The two fields the environment supplies, and the only two a `fill` may name.
SESSION_FIELDS = {"login", "password"}


def session_section(manifest: dict) -> dict:
    return manifest["session"]


def handles_named_by_session(section: dict) -> set[str]:
    """The same three kinds as a write step: ids, ``data-`` markers and control labels."""
    selectors = [action["selector"] for action in section["actions"]]
    texts = [a["text"] for a in section["actions"] if a.get("text") is not None]
    selectors.append(f"[{section['refusal_marker']}]")
    out: set[str] = set()
    for selector in selectors:
        for ident in _ID_SELECTOR.findall(selector):
            out.add(f'id="{ident}"')
        for attribute in _DATA_ATTRIBUTE.findall(selector):
            out.add(attribute)
    out.update(texts)
    return out


def test_the_manifest_has_a_session_half_at_all(manifest: dict) -> None:
    """A manifest with no sign-in is `D-92` exactly, and it went nine waves unnoticed."""
    assert "session" in manifest, (
        "manifest.json declares no `session` section. The BFF answers 401 without a "
        "session cookie (wave 34, by design), so a journey without one walks two routes "
        "of fifteen and reports on thirteen it never opened. That is D-92."
    )
    section = session_section(manifest)
    for key in ("at", "page_module", "control_module", "cookie", "api", "actions",
                "lands_on", "bound_ms", "refusal_marker"):
        assert key in section, f"the session section declares no `{key}`"
    assert section["actions"], "the session section presses nothing"
    assert isinstance(section["bound_ms"], int) and section["bound_ms"] > 0, (
        "the session's wait carries no positive bound; an unbounded wait reports nothing "
        "at all, which is the D-5 failure mode"
    )


def test_no_session_action_carries_a_credential(manifest: dict) -> None:
    """The guard that keeps a password out of this repository.

    A `fill` in the `write` half declares `value` and that is right there -- a project
    name is not a secret. A `fill` in the `session` half declares `from`, naming which of
    the two values the ENVIRONMENT supplies, and may not declare `value` at all. So the
    obvious way to make the journey run on somebody's machine -- typing the password into
    the manifest -- fails in `make gate` rather than in review.
    """
    section = session_section(manifest)
    offending = [a for a in section["actions"] if "value" in a]
    assert not offending, (
        f"{len(offending)} session action(s) carry a literal `value`: {offending}. The "
        "sign-in's two values come from E2E_PC01_LOGIN and E2E_PC01_PASSWORD at run time "
        "and may never be written down here. A credential in a manifest is a credential "
        "in this repository."
    )
    fills = [a for a in section["actions"] if a["do"] == "fill"]
    assert fills, "the session section fills nothing, so it types no credential at all"
    named = {a.get("from") for a in fills}
    assert named <= SESSION_FIELDS, (
        f"a session `fill` names {sorted(named - SESSION_FIELDS)}, which the environment "
        f"does not supply. It supplies exactly {sorted(SESSION_FIELDS)}."
    )
    assert named == SESSION_FIELDS, (
        f"the session fills {sorted(named)} and the exchange needs both of "
        f"{sorted(SESSION_FIELDS)}"
    )


def test_the_session_stands_on_a_screen_the_read_walk_also_covers(manifest: dict) -> None:
    """Two claims about one address, so a moved sign-in screen cannot pass here."""
    section = session_section(manifest)
    routes = {route["path"]: route for route in manifest["routes"]}
    assert section["at"] in routes, (
        f"the journey signs in at {section['at']}, which is not a route it walks. A "
        "screen the journey uses and does not check is a screen nobody checks."
    )
    assert routes[section["at"]]["page_module"] == section["page_module"], (
        f"the session says the sign-in screen is {section['page_module']} and the route "
        f"for {section['at']} says {routes[section['at']]['page_module']}"
    )
    assert section["lands_on"] in routes, (
        f"a completed sign-in lands on {section['lands_on']}, which is not a route this "
        "journey walks"
    )
    assert (REPOSITORY_ROOT / section["page_module"]).is_file(), (
        f"the sign-in screen {section['page_module']} does not exist"
    )
    assert (REPOSITORY_ROOT / section["control_module"]).is_file(), (
        f"the sign-in form {section['control_module']} does not exist"
    )


def test_every_control_the_sign_in_presses_still_exists_in_the_application(
    manifest: dict,
) -> None:
    """Rename `#sign-in-password` or relabel `Войти` and the journey signs in nowhere."""
    _require(WEB_SRC)
    source = application_source(WEB_SRC)
    missing = sorted(h for h in handles_named_by_session(session_section(manifest))
                     if h not in source)
    assert not missing, (
        f"the sign-in names {len(missing)} handle(s) that no longer appear anywhere in "
        f"web/src: {missing}. The journey would address the right screen and be unable "
        "to type into it -- and would then walk two routes of fifteen, which is D-92."
    )


def test_the_session_cookie_and_mount_are_the_ones_the_application_uses(
    manifest: dict,
) -> None:
    """The two strings that decide whether a session can be carried at all.

    Both are spelled in `web/src` -- `SESSION_COOKIE` in `app/bff/session/store.ts` and
    the exchange's own mount in `features/sign-in/model/exchange.ts`. Renaming either
    leaves every route and every operation in this manifest correct and leaves the walk
    signed out, which is exactly the shape this file exists to catch for controls.
    """
    _require(WEB_SRC)
    source = application_source(WEB_SRC)
    section = session_section(manifest)
    assert f"'{section['cookie']}'" in source or f'"{section["cookie"]}"' in source, (
        f"the journey carries a cookie named {section['cookie']!r}, which no longer "
        "appears in web/src. A session it cannot carry is no session."
    )
    mount = f"{manifest['api_prefix']}{section['api']['path']}"
    assert mount.startswith(manifest["api_prefix"]), mount
    assert f"{section['api']['path']}`" in source or section["api"]["path"] in source, (
        f"the exchange path {section['api']['path']!r} no longer appears in web/src"
    )


def test_the_session_is_never_forwarded_as_a_contract_operation(
    manifest: dict, openapi: dict
) -> None:
    """`/session` is this tier's own and is deliberately NOT a contract path.

    The BFF refuses to forward the whole `auth` segment, because `changePassword` answers
    with a credential and a browser that reached it through the catch-all would be handed
    one in a page body -- what `JUDGE-SEC` drove against `issueToken`. So a `session`
    entry appearing in the contract would mean the seam had moved, and this journey would
    be posting a password at an operation.
    """
    section = session_section(manifest)
    assert section["api"]["path"] not in openapi["paths"], (
        f"{section['api']['path']} is now a contract path. The journey posts a password "
        "at it, and the BFF answers it locally precisely because it is not forwarded."
    )


def test_the_viewport_declares_a_width_every_route_is_held_to(manifest: dict) -> None:
    """`D-93`. A width assertion against an unstated viewport measures nothing."""
    assert "viewport" in manifest, (
        "manifest.json declares no `viewport`, so no route can be held to a width. Wave "
        "43 put a horizontal scrollbar on every screen in the product below 839 px and "
        "1085 frontend tests could not see it."
    )
    viewport = manifest["viewport"]
    for key in ("width", "height"):
        assert isinstance(viewport[key], int) and viewport[key] > 0, (
            f"the viewport's {key} is {viewport[key]!r} and must be a positive integer"
        )
    assert viewport["width"] < 839, (
        f"the declared width is {viewport['width']} px, which is at or above the 839 px "
        "threshold W43-JUDGE-B measured. A width the wave-43 bar already fitted inside "
        "cannot see the class this assertion exists for."
    )


def test_the_instrument_still_asserts_a_width_on_every_route() -> None:
    """The assertion is one import and one call away from silently leaving.

    Same shape as the screenshot pair above: a capability nothing checks is a capability
    that goes away. This checks it is wired, not that it fires -- the firing is
    `prove_the_width_assertion_can_fail.mjs`, which needs a browser.
    """
    width = _require(WIDTH_MODULE).read_text(encoding="utf-8")
    assert "scrollWidth" in width and "innerWidth" in width, (
        "width.mjs no longer compares scrollWidth to innerWidth, so whatever it returns "
        "is not D-93's assertion"
    )
    journey = _require(JOURNEY_SCRIPT).read_text(encoding="utf-8")
    assert "widthFindings(" in journey, (
        "journey.mjs no longer calls widthFindings, so no route is held to a width"
    )
    assert "measureWidth(" in journey, "journey.mjs no longer measures a width"
    proof = _require(WIDTH_PROOF).read_text(encoding="utf-8")
    assert "widthFindings" in proof, (
        "the proof no longer imports the journey's own assertion, so it would prove a "
        "second copy of it can fail. OPERATING_CONSTRAINTS.md section 12."
    )


def test_the_instrument_still_reads_back_the_jar_every_route_started_with() -> None:
    """`D-16`: exercise the real Page snapshot against an independent browser reply.

    A session carried deliberately and state leaking between routes look identical in a
    passing run. What tells them apart is that every route's profile is read BEFORE it
    navigates and must hold exactly what the walk handed it. Delete that and the journey
    still passes, and nothing distinguishes it from a warm browser again.

    This used to assert only that several method names occurred somewhere in ``cdp.mjs``.
    `W44-JUDGE-X` replaced the snapshot with the caller's cookie declarations and all 78
    tests stayed green; `W44-JUDGE-Y` supplied an expired cookie and showed why the two
    values are not interchangeable. The seam below constructs the real private ``Page``
    inside its own module, feeds it a fake CDP connection, and requires the result to come
    from ``Storage.getCookies``. It does not export ``Page`` or permit browser reuse.
    """
    module_url = json.dumps((JOURNEY_DIR / "cdp.mjs").as_uri())
    script = f"""
      import {{ recordStartingJarForConformance }} from {module_url};
      const calls = [];
      const connection = {{
        async send(method, params, sessionId) {{
          calls.push({{ method, params, sessionId }});
          if (method !== 'Storage.getCookies') throw new Error(`unexpected ${{method}}`);
          return {{ cookies: [{{ name: 'extra_cookie' }}, {{ name: 'am_session' }}] }};
        }},
      }};
      const startedWith = await recordStartingJarForConformance(connection, 'judge-session');
      process.stdout.write(JSON.stringify({{ startedWith, calls }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    assert observed == {
        "startedWith": ["am_session", "extra_cookie"],
        "calls": [
            {
                "method": "Storage.getCookies",
                "params": {},
                "sessionId": "judge-session",
            }
        ],
    }, (
        "recordStartingJar did not read the browser's Storage cookie jar. Copying the "
        "caller's declarations here makes the live D-16 comparison a tautology."
    )

    cdp = _require(JOURNEY_DIR / "cdp.mjs").read_text(encoding="utf-8")
    assert "export class Page" not in cdp, (
        "cdp.mjs exports Page, so callers can reuse a browser across routes; the narrow "
        "conformance seam must not become a browser-reuse API"
    )
    journey = _require(JOURNEY_SCRIPT).read_text(encoding="utf-8")
    assert "startedWith" in journey, (
        "journey.mjs no longer asserts what each route's browser started with"
    )


def test_the_journey_requires_both_environment_credentials_at_runtime() -> None:
    """No default survives the observable missing-value behaviour.

    `D-92` named `--session <cookie>` as the other candidate shape. It puts a live
    credential on a command line, where it reaches the process table and every transcript
    of the run.

    **THIS CHECK USED TO LIST FOUR LITERALS AND CLAIM TO CATCH ANY SPELLING.**
    `W44-JUDGE-A` defeated it in one character: it forbade `?? 'admin'` and three
    siblings, and `||` is not `??`. `env[PASSWORD_ENV] || 'password'` put the stand's
    password in this repository with all 78 tests green and `rc=2` no longer firing --
    and a ternary, a destructuring default and `?? DEFAULT` with a named constant all
    pass the same way. A docstring saying *"however it was spelled"* over a list of four
    spellings is `OPERATING_CONSTRAINTS.md` §12: the query shared its assumption with its
    subject, because both were written by somebody thinking of `??`.

    The line-shape replacement failed too: both closing judges moved a fallback to a
    second assignment, and this suite remained green while the exported function returned
    the default. The independent question is behavioural. With both process-environment
    values it must return the exact sentinels; with either one absent it must throw and
    name that environment variable. A fallback's spelling and location are irrelevant.
    """
    module_url = json.dumps(SESSION_MODULE.as_uri())
    script = f"""
      import {{ credentialsFromEnvironment, LOGIN_ENV, PASSWORD_ENV }} from {module_url};
      const exact = credentialsFromEnvironment();
      const missing = [];
      for (const [name, env] of [
        ['password', {{ [LOGIN_ENV]: 'login-sentinel' }}],
        ['login', {{ [PASSWORD_ENV]: 'password-sentinel' }}],
        ['both', {{}}],
      ]) {{
        try {{
          credentialsFromEnvironment(env);
          missing.push({{ name, threw: false }});
        }} catch (error) {{
          const headline = error.message.split('\\n', 1)[0];
          missing.push({{
            name,
            threw: true,
            marked: error.isMissingCredential === true,
            loginNamed: headline.includes(LOGIN_ENV),
            passwordNamed: headline.includes(PASSWORD_ENV),
          }});
        }}
      }}
      process.stdout.write(JSON.stringify({{ exact, missing }}));
    """
    environment = os.environ.copy()
    environment["E2E_PC01_LOGIN"] = "login-sentinel"
    environment["E2E_PC01_PASSWORD"] = "password-sentinel"
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    assert observed["exact"] == {
        "login": "login-sentinel",
        "password": "password-sentinel",
    }
    assert observed["missing"] == [
        {
            "name": "password",
            "threw": True,
            "marked": True,
            "loginNamed": False,
            "passwordNamed": True,
        },
        {
            "name": "login",
            "threw": True,
            "marked": True,
            "loginNamed": True,
            "passwordNamed": False,
        },
        {
            "name": "both",
            "threw": True,
            "marked": True,
            "loginNamed": True,
            "passwordNamed": True,
        },
    ], (
        "credentialsFromEnvironment accepted a missing value or failed to name it. A "
        "default after an environment read must fail this behavioural control."
    )


# --------------------------------------------------------------------------------------
# Controls. Every check above, against a declaration that is wrong in exactly one way.
# --------------------------------------------------------------------------------------


def _session_of(**overrides: object) -> dict:
    base = json.loads(MANIFEST.read_text(encoding="utf-8"))["session"]
    return {**base, **overrides}


def test_control_a_session_action_with_a_password_in_it_is_detected() -> None:
    actions = [dict(a) for a in _session_of()["actions"]]
    actions[1]["value"] = "hunter2"
    offending = [a for a in actions if "value" in a]
    assert offending, "the control did not construct the thing it is controlling for"
    assert offending[0]["value"] == "hunter2"


def test_control_a_session_fill_naming_a_field_nobody_supplies_is_detected() -> None:
    actions = [dict(a) for a in _session_of()["actions"]]
    actions[0]["from"] = "totp"
    named = {a.get("from") for a in actions if a["do"] == "fill"}
    assert named - SESSION_FIELDS == {"totp"}


def test_control_a_sign_in_screen_that_moved_is_detected() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    moved = _session_of(at="/sign-in")
    assert moved["at"] not in {route["path"] for route in manifest["routes"]}


def test_control_a_renamed_sign_in_control_is_detected() -> None:
    renamed = _session_of(
        actions=[{"do": "fill", "selector": "#sign-in-username", "from": "login"}],
        refusal_marker="data-sign-in-refusal",
    )
    assert 'id="sign-in-username"' in handles_named_by_session(renamed)
    assert 'id="sign-in-username"' not in application_source(WEB_SRC)


def test_control_a_relabelled_sign_in_button_is_detected() -> None:
    relabelled = _session_of(
        actions=[{"do": "click", "selector": "form button", "text": "Log in"}],
        refusal_marker="data-sign-in-refusal",
    )
    assert "Log in" in handles_named_by_session(relabelled)
    assert "Log in" not in application_source(WEB_SRC)


def test_control_an_unbounded_session_wait_is_detected() -> None:
    for bound in (0, -1, None):
        unbounded = _session_of(bound_ms=bound)
        assert not (isinstance(unbounded["bound_ms"], int) and unbounded["bound_ms"] > 0)


def test_control_a_viewport_too_wide_to_see_the_class_is_detected() -> None:
    """839 is the threshold wave 43 produced, so a width at or above it sees nothing."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["viewport"]["width"] < 839
    for blind in (839, 1024, 1440):
        assert not blind < 839


def test_control_a_width_assertion_that_left_is_detected() -> None:
    journey = _require(JOURNEY_SCRIPT).read_text(encoding="utf-8")
    assert "widthFindings(" in journey
    assert "widthFindings(" not in journey.replace("widthFindings(", "somethingElse(")
    width = _require(WIDTH_MODULE).read_text(encoding="utf-8")
    assert "scrollWidth" not in width.replace("scrollWidth", "clientWidthOnly")


# --------------------------------------------------------------------------------------
# `W44-JOURNEY`: the refusal drive's own controls, which `W28-GUARD` left behind.
#
# `W28-GUARD` moved the six refusal EXPECTATIONS into the manifest, stating the cost it
# was paying off: expectations in a script's own source are expectations `make gate`
# cannot read. It left the CONTROLS -- `Create`, `Upload`, `Retry`, `Chosen: ` -- in
# `refusals.mjs`. The application was then translated and all four stopped matching.
#
# Measured 2026-09-24: `node tests/e2e/pc01/journey/refusals.mjs --origin ...` threw
# `click form button[type="submit"] [text="Create"]: no element matches it` before driving
# a single fixture. So `D-83`'s standing sentence -- the eleven sentences are "verified
# only against a live stand" by this script -- was itself untrue: they were verified by
# nothing anywhere. A check nobody has run since the screens changed is not a check.
# --------------------------------------------------------------------------------------


def refusal_controls(manifest: dict) -> dict:
    return refusal_section(manifest)["controls"]


def closure_source(control_module: Path) -> str:
    """Every byte of the control module and what it imports, comments stripped."""
    return "\n".join(
        _COMMENT.sub(" ", module.read_text(encoding="utf-8"))
        for module in module_closure(control_module, WEB_SRC)
    )


def test_the_refusal_half_declares_the_controls_it_presses(manifest: dict) -> None:
    section = refusal_section(manifest)
    assert "controls" in section, (
        "the refusal half declares no `controls`. They were literals in refusals.mjs, "
        "which the gate cannot read, and every one of them went stale when the "
        "application was translated."
    )
    controls = section["controls"]
    for key in ("file_input", "title_input", "submit_label",
                "retry_action_selector", "chosen_selector", "chosen_label"):
        assert controls.get(key), f"the refusal half declares no `{key}`"


def test_every_control_the_refusals_press_still_exists_in_the_application(
    manifest: dict,
) -> None:
    """Relabel the upload button and the six drives press nothing -- red here instead.

    **The LABEL is scoped to the control module's own import closure and matched on a word
    boundary**, not by containment against every byte of ``web/src``. That is not a
    refinement, it is the difference between a check and a vacuous one: ``Upload`` -- the
    literal that actually rotted -- is contained in ``web/src`` right now, inside
    ``import { UploadPanel } from '@/widgets/upload-panel'``. A containment check would
    have stayed green over the exact defect it is written for, and the first draft of this
    one did.

    It reads the closure's **source with comments stripped** rather than
    ``authored_strings``, and the reason is measured: ``_LITERAL``'s JSX arm is
    ``>([^<>{}\n]+)<``, which requires the text to sit between the two angle brackets on
    one line. This repository formats a labelled button over four lines, so ``Загрузить``
    is authored and invisible to that helper. Widening ``_LITERAL`` would loosen the
    `D-61` sentence guard that shares it, which is the wrong direction; scoping plus a word
    boundary is strictly stronger than the whole-tree containment this replaces, and the
    control below proves it.

    Selectors keep the broad scan, as ids and markers do everywhere else in this file:
    ``#upload-file`` and ``am-state__action`` are not words and cannot be matched by
    accident.
    """
    _require(WEB_SRC)
    source = application_source(WEB_SRC)
    controls = refusal_controls(manifest)
    section = refusal_section(manifest)

    control_module = REPOSITORY_ROOT / section["control_module"]
    assert control_module.is_file(), section["control_module"]
    authored = closure_source(control_module)
    assert authors(authored, controls["submit_label"]), (
        f"the refusal drive presses a control labelled {controls['submit_label']!r}, "
        f"which {section['control_module']} and what it imports do not author. The six "
        "drives would attach the right files and press nothing -- which is exactly what "
        "happened while the label was the literal `Upload` inside refusals.mjs."
    )
    assert authors(authored, controls["chosen_label"]), (
        f"the refusal drive expects the chosen-file prefix {controls['chosen_label']!r}, "
        f"which {section['control_module']} and what it imports do not author. The line "
        "would still be found by class while its visible wording silently rotted."
    )

    handles: set[str] = set()
    for key in ("file_input", "title_input", "retry_action_selector", "chosen_selector"):
        for ident in _ID_SELECTOR.findall(controls[key]):
            handles.add(f'id="{ident}"')
        for klass in re.findall(r"\.([a-z][\w-]*)", controls[key]):
            handles.add(klass)
    missing = sorted(h for h in handles if h not in source)
    assert not missing, (
        f"the refusal drive names {len(missing)} control(s) that no longer appear "
        f"anywhere in web/src: {missing}."
    )


def test_the_refusal_drive_reads_its_controls_from_the_manifest() -> None:
    """The literals must not come back, and a source check is what stops them.

    Narrow on purpose: it asserts the four that rotted are no longer addressed by word in
    `refusals.mjs`. A wider "no string literals" rule would be unenforceable and would
    redden on prose.
    """
    source = (JOURNEY_DIR / "refusals.mjs").read_text(encoding="utf-8")
    assert "REFUSALS?.controls" in source or "REFUSALS.controls" in source, (
        "refusals.mjs no longer reads its controls from the manifest, so the gate is "
        "back to guarding nothing about them"
    )
    assert "CONTROLS.chosen_label" in source, (
        "refusals.mjs reads the chosen-file element by class but no longer checks its "
        "manifest-declared visible prefix"
    )
    for gone in ("text: 'Create'", 'text: "Create"', "text: 'Upload'", 'text: "Upload"',
                 "startsWith('Retry')", "startsWith('Chosen: ')"):
        assert gone not in source, (
            f"refusals.mjs addresses a control as {gone}. Those four literals are what "
            "the application's translation broke silently; they are declared in "
            "manifest.json so `make gate` reddens next time."
        )


def test_the_refusal_drive_signs_in_before_it_drives_anything() -> None:
    """`D-92` reaches this script too: without a session every upload is a 401."""
    source = (JOURNEY_DIR / "refusals.mjs").read_text(encoding="utf-8")
    assert "openSession" in source, (
        "refusals.mjs does not open a session. The BFF answers 401 without one, so the "
        "six drives would measure an authorization refusal and report it as an envelope "
        "refusal -- a passing-looking measurement of the wrong thing."
    )


def test_control_a_relabelled_upload_control_is_detected(manifest: dict) -> None:
    """And it doubles as the proof that containment would NOT have detected it.

    ``Upload`` is the label that rotted. It is still contained in ``web/src`` -- inside
    ``UploadPanel`` -- so the first version of the check above passed over it. Under the
    authored-strings subject it is correctly not authored, and the live label is.
    """
    section = refusal_section(manifest)
    authored = closure_source(REPOSITORY_ROOT / section["control_module"])
    assert authors(authored, refusal_controls(manifest)["submit_label"])
    assert authors(authored, refusal_controls(manifest)["chosen_label"])
    assert not authors(authored, "Chosen:"), (
        "the English chosen-file prefix still appears in the upload control's closure"
    )
    assert not authors(authored, "Upload"), (
        "the control did not construct a label the application has stopped authoring"
    )
    assert "Upload" in application_source(WEB_SRC), (
        "the second half of this control: a containment check over all of web/src would "
        "have stayed GREEN over the very rename this guard exists to catch"
    )


def test_control_a_refusal_drive_that_lost_its_session_is_detected() -> None:
    source = (JOURNEY_DIR / "refusals.mjs").read_text(encoding="utf-8")
    assert "openSession" not in source.replace("openSession", "someOtherThing")


# --------------------------------------------------------------------------------------
# `BETA-LIVE-JOURNEY-01`. The night window's screens, in the write half.
#
# The first four write steps (project, upload, classify, run) were the whole of the half
# until the night window of 2026-10-20 added the screens `docs/program/BETA-MATRIX-01.md`
# section B12 lists as never walked live. The steps after them carry a `screen` (which
# screen they belong to) and a `case` (`action`, or `refused` -- the role, the input or the
# second submit the screen must refuse), a session (`as`), a `bind` that renames what a
# template variable means inside the step, and a few expectations the first four did not
# need. The checks below read all of that against the contract and the application's source
# and against each other, with no browser and no stack.
#
# What they cannot see is the same residue the module's header states: a handle that exists
# is not a handle that works. Only `npm --prefix web run e2e:pc01 -- --phase all` against a
# stack shows that, and the report of this task quotes the run.
# --------------------------------------------------------------------------------------

ACTION_KINDS = frozenset({"fill", "click", "select", "attach_file", "goto", "wait_for"})
CAPTURE_KINDS = frozenset({"attribute", "location", "response", "text"})
FIRST_FOUR = ("create-project", "upload-document", "classify-version", "start-run")
#: What the first four steps capture, which every later step may use.
FIRST_FOUR_PRODUCE = frozenset({"project_uid", "version_uid", "document_uid", "run_id"})

#: The screens the night window added (BETA-MATRIX-01 section B12), each of which the write
#: half must perform an action on AND refuse something on. The names are the steps' own
#: `screen` values. A screen that cannot be refused anything says so in `no_negative_case`.
NIGHT_SCREENS = (
    "version-upload",
    "version-classification",
    "version-comparison",
    "stage-comparison",
    "analysis-settings",
    "dispatcher",
    "my-tasks",
    "price-lists",
    "vendor-lists",
    "specification-prices",
    "optimisation-passes",
    "optimisation-proposals",
    "section-form7",
    "dashboard-sections",
    "norms-designation",
    "norms-search",
    "norms-catalogue",
    "run-exports",
    "queue",
    "workers",
    "account-profile",
    "account-password",
    "user-management",
    "release-history",
    "sign-out",
    # `PC01-JOURNEY-GAPS-01`
    "blocks",
    "norms-document",
)

#: Operations the write half must perform at least once, because each is a thing the matrix
#: says was never done live.
NIGHT_OPERATIONS = (
    "classifyDocumentVersion",
    "uploadDocumentVersion",
    "compareDocumentVersions",
    "carryOverDecision",
    "createAssignment",
    "transitionAssignment",
    "uploadPriceList",
    "setGlobalVendorList",
    "setProjectVendorList",
    "getSpecificationPrices",
    "startOptimisationPass",
    "decideOptimisationProposal",
    "exportOptimisationProposalsCsv",
    "getSectionSpecification",
    "getDashboardSummary",
    "listAnalysisProfiles",
    "listNormDocuments",
    "searchNorms",
    "setCurrentNormSnapshot",
    "exportRunCsv",
    "exportRunXlsx",
    "setExecutionPaused",
    "setJobPriority",
    "cancelRun",
    "reauditRun",
    "listWorkers",
    "setWorkerIntake",
    "updateMyProfile",
    "resetUserPassword",
    "archiveUser",
    "restoreUser",
    "listReleases",
    # `PC01-JOURNEY-GAPS-01`
    "listVersionPortalBlocks",
    "streamVersionPortalBlockCrop",
    "getVersionBlocks",
    "correctVersionClassification",
    "getNormDocument",
    "listNormParagraphs",
    "streamNormDocumentContent",
)

_TEMPLATE = re.compile(r"\{([a-z_]+)\}")


def _templates(value: object) -> list[str]:
    return _TEMPLATE.findall(value) if isinstance(value, str) else []


def night_steps(manifest: dict) -> list[dict]:
    """Every write step after the first four, in order."""
    return [step for step in write_steps(manifest) if step["name"] not in FIRST_FOUR]


def roster_names(manifest: dict) -> list[str]:
    return [entry["name"] for entry in (manifest.get("accounts") or {}).get("roster") or ()]


def _step_templates(step: dict) -> list[tuple[str, dict | None]]:
    """Every `{name}` a step mentions, with the call-level `bind` that governs it (or `None`)."""
    found: list[tuple[str, dict | None]] = []
    for name in _templates(step.get("at")):
        found.append((name, None))
    for key in ("expects_api", "expects_api_after_terminal", "expects_not_called", "expects_bff"):
        for call in step.get(key) or ():
            for name in _templates(call.get("path")):
                found.append((name, call.get("bind")))
    for action in step.get("actions") or ():
        for key in ("selector", "value", "text", "to", "option_text", "option_value", "label"):
            for name in _templates(action.get(key)):
                found.append((name, None))
        if isinstance(action.get("within"), dict):
            for name in _templates(action["within"].get("text_contains")):
                found.append((name, None))
    for present in step.get("expects_present") or ():
        for name in (
            _templates(present.get("selector"))
            + _templates(present.get("text_contains"))
            + _templates(present.get("text_matches"))
        ):
            found.append((name, None))
    for selector in step.get("forbids_rendered") or ():
        for name in _templates(selector):
            found.append((name, None))
    for absent in step.get("expects_absent") or ():
        for name in _templates(absent.get("selector")) + _templates(absent.get("text")):
            found.append((name, None))
    return found


def _path_parameter_enum(openapi: dict, step: dict, parameter_name: str) -> list | None:
    """The enumeration the contract publishes for a path parameter this step addresses."""
    paths = {call["path"] for call in step.get("expects_api") or ()}
    paths |= {call["path"] for call in step.get("expects_not_called") or ()}
    for path in sorted(paths):
        item = openapi["paths"].get(path) or {}
        candidates = list(item.get("parameters") or ())
        for method, operation in item.items():
            if method.lower() in _HTTP_METHODS:
                candidates += list(operation.get("parameters") or ())
        for parameter in candidates:
            if parameter.get("name") != parameter_name or parameter.get("in") != "path":
                continue
            schema = parameter.get("schema") or {}
            if "$ref" in schema:
                schema = openapi["components"]["schemas"][schema["$ref"].split("/")[-1]]
            if "enum" in schema:
                return list(schema["enum"])
    return None


def night_window_findings(manifest: dict, openapi: dict) -> list[str]:
    """Everything checkable about the night-window steps without a browser or the web tree."""
    findings: list[str] = []
    steps = write_steps(manifest)
    names = [step["name"] for step in steps]
    for name in sorted({n for n in names if names.count(n) > 1}):
        findings.append(f"two write steps are named '{name}'")
    roster = set(roster_names(manifest))
    contract_ops = operations_in_contract(openapi)
    contract_by_id = {operation_id: (method, path) for method, path, operation_id in contract_ops}
    contract_paths = {(method, path) for method, path, _ in contract_ops}

    secrets_provided = {f"{name}_password" for name in roster} | set(
        (manifest.get("accounts") or {}).get("generated_secrets") or ()
    )
    produced: set[str] = set(FIRST_FOUR_PRODUCE) | {f"{name}_user_uid" for name in roster}
    for index, step in enumerate(steps):
        label = step["name"]
        late = label not in FIRST_FOUR
        if late:
            for required in ("screen", "case"):
                if required not in step:
                    findings.append(f"{label}: no `{required}`")
            if step.get("case") not in ("action", "refused"):
                findings.append(f"{label}: `case` is {step.get('case')!r}, not action or refused")
        session = step.get("as", "admin")
        if session != "admin" and session not in roster:
            findings.append(f"{label}: runs as '{session}', which the accounts roster does not name")
        operations_here = {call["operationId"] for call in step.get("expects_api") or ()}

        # ---- the vocabulary -------------------------------------------------------
        for action in step.get("actions") or ():
            kind = action.get("do")
            if kind not in ACTION_KINDS:
                findings.append(f"{label}: unknown action '{kind}'")
                continue
            if kind == "fill" and ("value" in action) == ("secret" in action):
                findings.append(f"{label}: a fill names exactly one of value and secret")
            if kind == "fill" and "secret" in action and action["secret"] not in secrets_provided:
                findings.append(f"{label}: a fill names the secret {action['secret']!r}, which no account or generated secret provides")
            if kind in ("fill", "click", "select", "attach_file", "wait_for") and "selector" not in action:
                findings.append(f"{label}: a {kind} with no selector")
            if kind == "click" and action.get("times", 1) not in (1, 2, 3):
                findings.append(f"{label}: click.times must be 1, 2 or 3")
            if "within" in action:
                row = action["within"]
                if kind != "click":
                    findings.append(f"{label}: only a click is made within a row, not a {kind}")
                if not (
                    isinstance(row, dict)
                    and set(row) == {"selector", "text_contains"}
                    and isinstance(row["selector"], str)
                    and row["selector"]
                    and isinstance(row["text_contains"], str)
                    and row["text_contains"]
                ):
                    findings.append(
                        f"{label}: `within` is {{selector, text_contains}}, both non-empty text; got {row!r}"
                    )
            if kind == "select" and ("option_text" in action) == ("option_value" in action):
                findings.append(f"{label}: a select names exactly one of option_text and option_value")
            if kind == "attach_file":
                fixture = action.get("fixture")
                if fixture is not True and not (
                    isinstance(fixture, str) and (REPOSITORY_ROOT / fixture).is_file()
                ):
                    findings.append(f"{label}: attach_file names a fixture that is not on disk: {fixture!r}")
            if kind == "goto" and "to" not in action:
                findings.append(f"{label}: a goto with no address")
            if kind == "wait_for":
                bound = action.get("bound_ms")
                if not (isinstance(bound, int) and not isinstance(bound, bool) and bound > 0):
                    findings.append(f"{label}: a wait_for with bound_ms={bound!r}")
        captures = [c for c in [step.get("capture"), *(step.get("captures") or ())] if c]
        for capture in captures:
            if capture.get("kind") not in CAPTURE_KINDS:
                findings.append(f"{label}: unknown capture kind {capture.get('kind')!r}")
            bound = capture.get("bound_ms")
            if not (isinstance(bound, int) and not isinstance(bound, bool) and bound > 0):
                findings.append(f"{label}: a capture with bound_ms={bound!r}")
            if capture.get("when") not in (None, "before_actions"):
                findings.append(f"{label}: capture.when is {capture.get('when')!r}")
            if capture.get("kind") == "response" and capture.get("of") not in operations_here:
                findings.append(f"{label}: captures a response of {capture.get('of')!r}, which the step does not declare")
        for present in step.get("expects_present") or ():
            bound = present.get("bound_ms", 1)
            if not (isinstance(bound, int) and not isinstance(bound, bool) and bound > 0):
                findings.append(f"{label}: expects_present with bound_ms={bound!r}")
            if present.get("min_count", 1) < 1:
                findings.append(f"{label}: expects_present with min_count < 1")
        for key in ("expects_request", "expects_response", "expects_download"):
            for check in step.get(key) or ():
                if check.get("of") not in operations_here:
                    findings.append(f"{label}: {key} names '{check.get('of')}', which the step does not declare")

        # ---- the calls ------------------------------------------------------------
        for call in step.get("expects_api") or ():
            status = call.get("expect_status")
            if call.get("refusal") is True:
                if not (isinstance(status, int) and status >= 400):
                    findings.append(f"{label}: refusal {call['operationId']} declares status {status!r}")
                if not call.get("expect_error_code"):
                    findings.append(f"{label}: refusal {call['operationId']} names no error code")
                codes = {
                    c for c in (openapi["components"]["schemas"].get("ErrorCode") or {}).get("enum", [])
                }
                if codes and call.get("expect_error_code") not in codes:
                    findings.append(
                        f"{label}: refusal {call['operationId']} expects error code "
                        f"{call.get('expect_error_code')!r}, which the contract does not publish"
                    )
            for key in ("count", "max_count"):
                if key in call and not (isinstance(call[key], int) and call[key] >= 1):
                    findings.append(f"{label}: {call['operationId']} {key}={call[key]!r}")
        for absent in step.get("expects_not_called") or ():
            if (absent["method"].upper(), absent["path"]) not in contract_paths:
                findings.append(
                    f"{label}: expects {absent['method']} {absent['path']} NOT to be called, "
                    "but that is no operation of the contract"
                )

        # ---- a step that says it only reads must do nothing else ----------------------
        if step.get("reads_only") is True:
            writes = [
                call["operationId"] for call in step.get("expects_api") or ()
                if call["method"].upper() != "GET"
            ]
            if step.get("actions") or writes:
                findings.append(
                    f"{label}: says it only reads, and presses {len(step.get('actions') or [])} control(s) / "
                    f"declares writes {writes}; the spend guard lets a read-only step run first"
                )

        # ---- the web tier's own doors and where a step ends -------------------------
        for door in step.get("expects_bff") or ():
            if (door["method"].upper(), door["path"]) in contract_paths:
                findings.append(
                    f"{label}: {door['method']} {door['path']} is declared a door of the web tier but it is an "
                    "operation of the contract; declare it in expects_api"
                )
            if not (isinstance(door.get("expect_status"), int) and 200 <= door["expect_status"] < 400):
                findings.append(f"{label}: a door of the web tier answers a redirect or success, not {door.get('expect_status')!r}")
        if "expects_location" in step and not str(step["expects_location"]).startswith("/"):
            findings.append(f"{label}: expects_location must be an address starting with /")

        # ---- constants, bind and the flow of identifiers ---------------------------
        constants = step.get("constants") or {}
        for name, value in constants.items():
            enum = _path_parameter_enum(openapi, step, name)
            if enum is None or value not in enum:
                findings.append(
                    f"{label}: constant {name}={value!r} is not a member of an enumeration "
                    "the contract publishes for that path parameter"
                )
        bind = step.get("bind") or {}
        used = {name for name, _local in _step_templates(step)}
        produced_here = {n for c in captures for n in c.get("as") or ()}
        for name, target in bind.items():
            # A bind for a variable the step never mentions is shared, not wrong.
            if name in used and target not in produced and target not in produced_here:
                findings.append(f"{label}: binds {name} to '{target}', which no earlier step produces")
        for name, local in _step_templates(step):
            wanted = (local or {}).get(name, bind.get(name, name))
            if wanted in constants or wanted in produced:
                continue
            if any(wanted == capture_name for capture in captures for capture_name in capture.get("as") or ()):
                continue
            findings.append(
                f"{label}: needs {{{name}}}"
                + (f" (bound to '{wanted}')" if wanted != name else "")
                + ", which no earlier step produces"
            )
        for capture in captures:
            produced.update(capture.get("as") or ())

        # ---- a refused case must refuse something ----------------------------------
        if late and step.get("case") == "refused":
            refuses = (
                any(c.get("refusal") is True for c in step.get("expects_api") or ())
                or bool(step.get("expects_not_called"))
                or bool(step.get("expects_absent"))
                or bool(step.get("forbids_rendered"))
                or session != "admin"
            )
            if not refuses:
                findings.append(
                    f"{label}: is a refused case but declares no refusal, no absent call, no absent "
                    "control, no forbidden marker and runs as the journey's own account"
                )

    # ---- coverage: every night screen is acted on and refused ------------------------
    by_screen: dict[str, list[dict]] = {}
    for step in night_steps(manifest):
        by_screen.setdefault(step.get("screen", ""), []).append(step)
    for screen in NIGHT_SCREENS:
        members = by_screen.get(screen, [])
        if not any(s.get("case") == "action" for s in members):
            findings.append(f"screen '{screen}': no step performs its action")
        refused = any(s.get("case") == "refused" for s in members)
        exempt = any(len(str(s.get("no_negative_case", ""))) >= 30 for s in members)
        if not refused and not exempt:
            findings.append(f"screen '{screen}': no step refuses anything, and none says why it cannot")
    declared = {
        call["operationId"]
        for step in steps
        for call in step.get("expects_api") or ()
    }
    for operation in NIGHT_OPERATIONS:
        if operation not in declared:
            findings.append(f"operation {operation}: no write step performs it")
    return findings


def account_findings(manifest: dict, source: str, repo: Path) -> list[str]:
    """The accounts roster and the screens that make them: addressed, existing, contract-bound."""
    findings: list[str] = []
    accounts = manifest.get("accounts")
    if not isinstance(accounts, dict):
        return ["the manifest declares no `accounts`, so no refusal by role can be driven"]
    roster = accounts.get("roster") or []
    names = [entry.get("name") for entry in roster]
    if len(set(names)) != len(names) or not names:
        findings.append("the accounts roster is empty or repeats a name")
    for entry in roster:
        roles = entry.get("roles")
        if not roles or not set(roles) <= {"expert", "admin"}:
            findings.append(f"account {entry.get('name')}: roles {roles!r}")
        if any(key in entry for key in ("password", "login", "secret")):
            findings.append(f"account {entry.get('name')}: carries a credential")
    if not {("expert",), ("admin",)} <= {tuple(sorted(e.get("roles") or ())) for e in roster}:
        findings.append("the roster must hold an expert without admin and an admin without expert")
    for part in ("register", "decide"):
        spec = accounts.get(part) or {}
        for key in ("page_module", "control_module"):
            if not (repo / spec.get(key, "no-such-file")).is_file():
                findings.append(f"accounts.{part}.{key} {spec.get(key)!r} does not exist")
    register = accounts.get("register") or {}
    decide = accounts.get("decide") or {}
    handles = set()
    selectors = list((register.get("fields") or {}).values())
    selectors.append((register.get("submit") or {}).get("selector", ""))
    selectors += [decide.get("queue_marker", ""), decide.get("row", ""), decide.get("request_id_from", "")]
    for selector in selectors:
        for ident in _ID_SELECTOR.findall(selector):
            handles.add(f'id="{ident}"')
        handles.update(_DATA_ATTRIBUTE.findall(selector))
    handles.add((register.get("submit") or {}).get("text", ""))
    handles.add((decide.get("approve") or {}).get("text", ""))
    handles.add((decide.get("pager_next") or {}).get("text", ""))
    handles.update((decide.get("role_labels") or {}).values())
    handles.discard("")
    for handle in sorted(handles):
        if handle not in source:
            findings.append(f"accounts: the handle {handle!r} no longer appears in web/src")
    return findings


def test_the_night_window_steps_agree_with_the_contract_and_with_each_other(
    manifest: dict, openapi: dict
) -> None:
    findings = night_window_findings(manifest, openapi)
    assert not findings, "the night-window half of the journey is incoherent:\n  " + "\n  ".join(findings)


def test_the_accounts_a_refusal_by_role_needs_are_made_through_screens_that_exist(
    manifest: dict,
) -> None:
    _require(WEB_SRC)
    findings = account_findings(manifest, application_source(WEB_SRC), REPOSITORY_ROOT)
    assert not findings, "\n  ".join(findings)


def test_the_accounts_screens_walk_and_operations_are_in_the_contract(
    manifest: dict, openapi: dict
) -> None:
    published = operations_in_contract(openapi)
    accounts = manifest["accounts"]
    claimed = {
        (accounts["register"]["operation"]["method"], accounts["register"]["operation"]["path"],
         accounts["register"]["operation"]["operationId"]),
        (accounts["decide"]["approve"]["operation"]["method"], accounts["decide"]["approve"]["operation"]["path"],
         accounts["decide"]["approve"]["operation"]["operationId"]),
    }
    assert claimed <= published, f"accounts claim operations the contract lacks: {sorted(claimed - published)}"
    walked = set(screens_in_manifest(manifest))
    assert accounts["register"]["at"] in walked and accounts["decide"]["at"] in walked


def test_every_hand_off_the_night_window_makes_to_the_dispatcher_selects_by_value(
    manifest: dict,
) -> None:
    """A name is not an identity: earlier runs left projects and accounts with the same names."""
    for step in night_steps(manifest):
        for action in step.get("actions") or ():
            if action.get("do") == "select" and "%STAMP%" in str(action.get("option_text", "")):
                raise AssertionError(
                    f"{step['name']}: selects an option by a name carrying the run's stamp; "
                    "use the identity the journey captured"
                )


def test_the_journey_driver_reads_the_vocabulary_the_manifest_uses() -> None:
    """The manifest's words are only worth what `write.mjs` does with them."""
    source = _require(JOURNEY_DIR / "write.mjs").read_text(encoding="utf-8")
    for word in (
        "expects_present", "expects_absent", "expects_not_called", "expects_download",
        "same_response_at", "max_count", "refusal", "bind", "constants", "before_actions",
        "'wait_for'", "'select'", "'goto'", "csv_no_formula_cells", "csv_data_rows", "continue_if_captured",
    ):
        assert word in source, f"write.mjs no longer reads '{word}', which the manifest uses"
    accounts = _require(JOURNEY_DIR / "accounts.mjs").read_text(encoding="utf-8")
    assert "randomBytes" in accounts and "redact" in accounts, (
        "accounts.mjs must generate each password at random and redact it from every message"
    )
    journey = _require(JOURNEY).read_text(encoding="utf-8")
    assert "provisionAccounts" in journey and "process.exit(3)" in journey, (
        "journey.mjs must make the accounts and must never call a partial run a pass"
    )


def test_a_manifest_with_fixtures_for_the_price_list_has_them_on_disk(manifest: dict) -> None:
    for step in night_steps(manifest):
        for action in step.get("actions") or ():
            if action.get("do") == "attach_file" and isinstance(action.get("fixture"), str):
                path = REPOSITORY_ROOT / action["fixture"]
                assert path.is_file(), f"{step['name']}: {action['fixture']} is not on disk"


# ---- the negative controls: each check above shown failing on synthetic data ---------


def _night_manifest(*extra_steps: dict, roster: list[dict] | None = None) -> dict:
    """The smallest manifest `night_window_findings` accepts, plus the steps given."""
    base_steps = [
        {"name": name, "at": "/projects", "expects_api": [], "actions": []} for name in FIRST_FOUR
    ]
    return {
        "accounts": {"roster": roster if roster is not None else [
            {"name": "expert_only", "roles": ["expert"]},
            {"name": "admin_only", "roles": ["admin"]},
        ]},
        "write": {"steps": [*base_steps, *extra_steps]},
    }


_NIGHT_CONTRACT = {
    "paths": {
        "/assignments": {"post": {"operationId": "createAssignment", "responses": {"200": {}, "403": {}}}},
        "/sections/{section_code}/specification": {
            "get": {
                "operationId": "getSectionSpecification",
                "parameters": [{"name": "section_code", "in": "path", "schema": {"enum": ["AR", "KJ"]}}],
                "responses": {"200": {}},
            }
        },
    },
    "components": {"schemas": {"ErrorCode": {"enum": ["permission_denied", "conflict"]}}},
}


def _night_step(**overrides: object) -> dict:
    step: dict = {
        "name": "assign-work", "screen": "dispatcher", "case": "action",
        "at": "/dispatcher", "actions": [], "expects_api": [],
    }
    step.update(overrides)
    return step


def _only_step_findings(step: dict, **kwargs: object) -> list[str]:
    found = night_window_findings(_night_manifest(step, **kwargs), _NIGHT_CONTRACT)
    return [f for f in found if f.startswith(f"{step['name']}:") or step["name"] in f.split(":")[0]]


def test_control_an_unknown_session_is_detected() -> None:
    assert any("roster does not name" in f for f in _only_step_findings(_night_step(**{"as": "ghost"})))
    assert not any("roster does not name" in f for f in _only_step_findings(_night_step(**{"as": "expert_only"})))


def test_control_an_identifier_no_earlier_step_produced_is_detected() -> None:
    step = _night_step(at="/projects/{assignment_uid}")
    assert any("assignment_uid" in f for f in _only_step_findings(step))
    producer = _night_step(name="make", at="/dispatcher", captures=[
        {"kind": "attribute", "selector": "[data-x]", "attribute": "data-x",
         "as": ["assignment_uid"], "bound_ms": 1000}])
    manifest = _night_manifest(producer, _night_step(name="use", at="/projects/{assignment_uid}"))
    assert not any("use: needs" in f for f in night_window_findings(manifest, _NIGHT_CONTRACT))


def test_control_a_bind_to_nothing_is_detected() -> None:
    step = _night_step(bind={"version_uid": "second_version_uid"}, at="/x/{version_uid}")
    found = _only_step_findings(step)
    assert any("binds version_uid to 'second_version_uid'" in f for f in found)


def test_control_a_constant_that_is_not_in_the_contract_enumeration_is_detected() -> None:
    call = {"method": "GET", "path": "/sections/{section_code}/specification",
            "operationId": "getSectionSpecification", "expect_status": 200}
    good = _night_step(constants={"section_code": "AR"}, expects_api=[call])
    bad = _night_step(constants={"section_code": "XX"}, expects_api=[call])
    assert not any("constant" in f for f in _only_step_findings(good))
    assert any("constant section_code='XX'" in f for f in _only_step_findings(bad))


def test_control_a_refusal_without_a_status_or_a_known_code_is_detected() -> None:
    call = {"method": "POST", "path": "/assignments", "operationId": "createAssignment",
            "expect_status": 200, "refusal": True, "expect_error_code": "permission_denied"}
    assert any("declares status 200" in f for f in _only_step_findings(_night_step(expects_api=[call])))
    no_code = dict(call, expect_status=403)
    no_code.pop("expect_error_code")
    assert any("names no error code" in f for f in _only_step_findings(_night_step(expects_api=[no_code])))
    wrong = dict(call, expect_status=403, expect_error_code="teapot")
    assert any("'teapot'" in f for f in _only_step_findings(_night_step(expects_api=[wrong])))
    right = dict(call, expect_status=403)
    assert not any("refusal" in f for f in _only_step_findings(_night_step(expects_api=[right])))


def test_control_a_call_that_is_not_in_the_contract_cannot_be_declared_absent() -> None:
    step = _night_step(expects_not_called=[{"method": "POST", "path": "/nowhere"}])
    assert any("NOT to be called" in f for f in _only_step_findings(step))
    ok = _night_step(expects_not_called=[{"method": "POST", "path": "/assignments"}])
    assert not any("NOT to be called" in f for f in _only_step_findings(ok))


def test_control_an_unknown_action_and_an_unbounded_wait_are_detected() -> None:
    found = _only_step_findings(_night_step(actions=[{"do": "teleport", "selector": "x"}]))
    assert any("unknown action 'teleport'" in f for f in found)
    found = _only_step_findings(_night_step(actions=[{"do": "wait_for", "selector": "x"}]))
    assert any("wait_for with bound_ms=None" in f for f in found)
    found = _only_step_findings(_night_step(actions=[{"do": "select", "selector": "x"}]))
    assert any("exactly one of option_text and option_value" in f for f in found)
    found = _only_step_findings(_night_step(actions=[{"do": "click", "selector": "x", "times": 9}]))
    assert any("click.times" in f for f in found)


def test_control_a_missing_fixture_is_detected() -> None:
    step = _night_step(actions=[{"do": "attach_file", "selector": "#f", "fixture": "tests/no/such.csv"}])
    assert any("not on disk" in f for f in _only_step_findings(step))


def test_control_a_refused_case_that_refuses_nothing_is_detected() -> None:
    nothing = _night_step(case="refused")
    assert any("refuses" in f or "refusal" in f for f in _only_step_findings(nothing))
    by_role = _night_step(case="refused", **{"as": "admin_only"})
    assert not any("is a refused case" in f for f in _only_step_findings(by_role))
    absent = _night_step(case="refused", forbids_rendered=["[data-create-assignment]"])
    assert not any("is a refused case" in f for f in _only_step_findings(absent))


def test_control_a_screen_without_an_action_or_without_a_refusal_is_detected() -> None:
    action_only = _night_manifest(_night_step())
    found = night_window_findings(action_only, _NIGHT_CONTRACT)
    assert "screen 'dispatcher': no step refuses anything, and none says why it cannot" in found
    refused_only = _night_manifest(_night_step(case="refused", **{"as": "admin_only"}))
    assert "screen 'dispatcher': no step performs its action" in night_window_findings(
        refused_only, _NIGHT_CONTRACT
    )
    exempt = _night_manifest(_night_step(no_negative_case="a read-only panel with nothing to refuse"))
    assert "screen 'dispatcher': no step refuses anything, and none says why it cannot" not in (
        night_window_findings(exempt, _NIGHT_CONTRACT)
    )
    missing_screen = night_window_findings(_night_manifest(), _NIGHT_CONTRACT)
    assert "screen 'norms-search': no step performs its action" in missing_screen
    assert "operation setCurrentNormSnapshot: no write step performs it" in missing_screen


def test_control_a_duplicate_step_name_is_detected() -> None:
    twice = _night_manifest(_night_step(), _night_step())
    assert "two write steps are named 'assign-work'" in night_window_findings(twice, _NIGHT_CONTRACT)


def test_control_a_credential_in_the_roster_is_detected() -> None:
    roster = [{"name": "expert_only", "roles": ["expert"], "password": "x"},
              {"name": "admin_only", "roles": ["admin"]}]
    manifest = {"accounts": {"roster": roster, "register": {}, "decide": {}}}
    found = account_findings(manifest, "", REPOSITORY_ROOT)
    assert any("carries a credential" in f for f in found)
    both = {"accounts": {"roster": [{"name": "a", "roles": ["expert", "admin"]}], "register": {}, "decide": {}}}
    assert any("an expert without admin and an admin without expert" in f
               for f in account_findings(both, "", REPOSITORY_ROOT))
    assert account_findings({}, "", REPOSITORY_ROOT) == [
        "the manifest declares no `accounts`, so no refusal by role can be driven"
    ]


def test_control_a_handle_the_accounts_press_that_left_the_source_is_detected(manifest: dict) -> None:
    findings = account_findings(manifest, "no handle appears in this text", REPOSITORY_ROOT)
    assert any("no longer appears in web/src" in f for f in findings)


def test_control_the_new_handles_are_read_from_the_new_keys() -> None:
    step = {
        "actions": [{"do": "select", "selector": "form[data-create-assignment]", "label": "Эксперт"}],
        "expects_present": [
            {"selector": "[data-create-assignment-done]", "text_contains": "Назначение создано."},
            {"selector": "tr[data-norm-document]", "text_contains": "СП 54.13330.2022", "text_is_data": True},
        ],
        "expects_absent": [{"selector": "li button", "text": "Сделать текущим"}],
        "captures": [{"kind": "attribute", "selector": "tr[data-norm-document]",
                      "attribute": "data-norm-document", "as": ["x"], "bound_ms": 1}],
    }
    handles = handles_named_by_write_step(step)
    assert {"data-create-assignment", "data-create-assignment-done", "data-norm-document",
            "Эксперт", "Назначение создано.", "Сделать текущим"} <= handles
    assert "СП 54.13330.2022" not in handles, "words that come from data are not the application's"


def test_the_read_walk_s_constants_are_members_of_a_contract_enumeration(
    manifest: dict, openapi: dict
) -> None:
    """A route's `constants` stand in for a path value that is not an identity, and only for one
    the contract enumerates (`section_code: "AR"`). An identifier is captured from a link the
    application rendered, never declared."""
    wrong = []
    for route in manifest["routes"]:
        for name, value in (route.get("constants") or {}).items():
            enum = _path_parameter_enum(openapi, route, name)
            if enum is None or value not in enum:
                wrong.append(f"{route['name']}: {name}={value!r}")
    assert not wrong, f"read-walk constants outside a contract enumeration: {wrong}"


def test_control_a_route_constant_outside_its_enumeration_is_detected(openapi: dict) -> None:
    route = {
        "expects_api": [
            {"method": "GET", "path": "/sections/{section_code}/specification",
             "operationId": "getSectionSpecification"}
        ]
    }
    assert "AR" in _path_parameter_enum(openapi, route, "section_code")
    assert "ZZ" not in _path_parameter_enum(openapi, route, "section_code")
    assert _path_parameter_enum(openapi, route, "project_uid") is None


# ---- the stack preparations the night-window steps need (BETA-LIVE-JOURNEY-01) -----------


def _run_tool(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT / "src"), **(env or {})}
    return subprocess.run(
        [sys.executable, *argv], cwd=REPOSITORY_ROOT, env=environment,
        capture_output=True, text=True, timeout=300,
    )


COMMITTED_SET = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar_specification"
COMMITTED_RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections" / "ar_specification"
HOSTILE_PRICES = JOURNEY_DIR / "fixtures" / "optimisation" / "prices_hostile.csv"


def _expect(step: dict, operation: str, json_path: str):
    """What the step declares its `operation`'s response must hold at `json_path` (`equals`)."""
    for check in step.get("expects_response") or ():
        if check.get("of") == operation and check.get("json_path") == json_path and "equals" in check:
            return check["equals"]
    raise AssertionError(f"{step['name']}: declares nothing about {operation} {json_path}")


def oracle_findings(manifest: dict, oracle: dict) -> list[str]:
    """Every figure the journey declares about the specification set, against the oracle's.

    `expected_specification.json` is computed by `tools/fixtures/build_ar_specification.py` from
    the authored numbers, never read from the product. The journey's steps carry the same
    figures as literals (the driver cannot read the oracle); this is what keeps the two from
    drifting: a moved oracle is red here and a moved literal is red here.
    """
    steps = {step["name"]: step for step in manifest["write"]["steps"]}
    findings: list[str] = []

    def agree(step: str, operation: str, json_path: str, wanted) -> None:
        try:
            declared = _expect(steps[step], operation, json_path)
        except (AssertionError, KeyError) as error:
            findings.append(f"{step}: {error}")
            return
        if declared != wanted:
            findings.append(f"{step}: {operation} {json_path} is declared {declared!r}, the oracle says {wanted!r}")

    spec, matching, proposals = oracle["specification"], oracle["matching"], oracle["proposals"]
    agree("price-list-upload", "uploadPriceList", "accepted_row_count", oracle["price_list_positions"])
    prices = "getSpecificationPrices"
    agree("specification-and-prices", prices, "rows.total", spec["row_count"])
    agree("specification-and-prices", prices, "matching.counts.matched", matching["counts"]["matched"])
    agree("specification-and-prices", prices, "matching.counts.unmatched", matching["counts"]["unmatched"])
    total = matching["totals"][0]
    agree("specification-and-prices", prices, "matching.totals.0.currency", total["currency"])
    agree("specification-and-prices", prices, "matching.totals.0.amount", total["amount"])
    agree("specification-and-prices", prices, "matching.totals.0.row_count", total["row_count"])
    start = "startOptimisationPass"
    agree("optimisation-pass", start, "specification_row_count", spec["row_count"])
    agree("optimisation-pass", start, "matched_row_count", matching["counts"]["matched"])
    agree("optimisation-pass", start, "proposal_count", proposals["count"])
    agree("optimisation-pass", start, "decision_counts.pending", proposals["count"])
    rows_with_proposal = len({item["row_position"] for item in proposals["items"]})
    agree("optimisation-pass", start, "proposed_row_count", rows_with_proposal)
    listing = "listOptimisationProposals"
    agree("proposal-revise-needs-a-comment", listing, "total", proposals["count"])
    for index, item in enumerate(proposals["items"]):
        agree("proposal-revise-needs-a-comment", listing, f"items.{index}.saving", item["saving"])
    agree("proposal-revise-needs-a-comment", listing, "items.0.proposed_vendor", proposals["items"][0]["proposed_vendor"])
    # The CSV step counts the same four rows.
    csv_step = steps["proposals-csv"]
    rows = [c.get("csv_data_rows") for c in csv_step.get("expects_download") or ()]
    if rows != [proposals["count"]]:
        findings.append(f"proposals-csv: declares {rows} data rows, the oracle says {proposals['count']}")
    return findings


def test_the_journey_declares_the_figures_the_committed_oracle_computes(manifest: dict) -> None:
    oracle = json.loads((COMMITTED_SET / "expected_specification.json").read_text(encoding="utf-8"))
    assert oracle_findings(manifest, oracle) == []


def test_control_a_figure_the_oracle_does_not_hold_is_found(manifest: dict) -> None:
    oracle = json.loads((COMMITTED_SET / "expected_specification.json").read_text(encoding="utf-8"))
    moved = copy.deepcopy(oracle)
    moved["proposals"]["count"] = 5
    assert any("proposal_count" in f for f in oracle_findings(manifest, moved))
    moved = copy.deepcopy(oracle)
    moved["matching"]["totals"][0]["amount"] = "1"
    assert any("matching.totals.0.amount" in f for f in oracle_findings(manifest, moved))
    drifted = copy.deepcopy(manifest)
    for step in drifted["write"]["steps"]:
        if step["name"] == "specification-and-prices":
            for check in step["expects_response"]:
                if check["json_path"] == "rows.total":
                    check["equals"] = 8
    assert any("rows.total" in f for f in oracle_findings(drifted, oracle))
    forgotten = copy.deepcopy(manifest)
    for step in forgotten["write"]["steps"]:
        if step["name"] == "optimisation-pass":
            step["expects_response"] = []
    assert any("declares nothing" in f for f in oracle_findings(forgotten, oracle))


def committed_set_findings(manifest: dict, root: Path, recordings: Path) -> list[str]:
    """The journey uploads the committed set itself: by name, by digest, with its recording.

    No copy of the bundle lives in the journey's own directory and no recording is installed by
    the journey: a copy would drift from the committed set, and an untracked recording makes the
    checkout dirty (`tests/contract/test_alpha_acceptance_command.py` refuses such a tree).
    """
    findings: list[str] = []
    oracle = json.loads((root / "expected_specification.json").read_text(encoding="utf-8"))
    fixtures = {
        action.get("fixture")
        for step in manifest["write"]["steps"]
        for action in step.get("actions") or ()
        if action.get("do") == "attach_file"
    }
    bundle = oracle["files"]["bundle"]
    prices = oracle["files"]["price_list"]
    for label, entry in (("bundle", bundle), ("price list", prices)):
        if entry["path"] not in fixtures:
            findings.append(f"the journey never attaches the committed {label} {entry['path']}")
            continue
        digest = hashlib.sha256((REPOSITORY_ROOT / entry["path"]).read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            findings.append(f"{entry['path']} is {digest}, the oracle says {entry['sha256']}")
    recorded = sorted(recordings.glob("*.json"))
    if len(recorded) != 1:
        findings.append(f"{recordings} holds {len(recorded)} recording(s), expected the one committed answer")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *[str(r) for r in recorded]],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True,
    )
    if recorded and tracked.returncode != 0:
        findings.append("the recording the specification run needs is not a tracked file")
    for stale in ("build_specification_bundle.py", "fixtures/optimisation/ar_specification.zip",
                  "fixtures/optimisation/prices.csv"):
        if (JOURNEY_DIR / stale).exists():
            findings.append(f"{stale}: the interim bundle the committed set replaced is still in the journey")
    return findings


def test_the_journey_uploads_the_committed_specification_set_and_installs_nothing(manifest: dict) -> None:
    assert committed_set_findings(manifest, COMMITTED_SET, COMMITTED_RECORDINGS) == []


def test_control_a_journey_with_its_own_copy_or_an_untracked_recording_is_found(
    manifest: dict, tmp_path: Path
) -> None:
    other = copy.deepcopy(manifest)
    for step in other["write"]["steps"]:
        for action in step.get("actions") or ():
            if action.get("fixture") == "fixtures/synthetic/ar_specification/ar_specification.zip":
                action["fixture"] = "tests/e2e/pc01/journey/fixtures/optimisation/empty.csv"
    assert any("never attaches the committed bundle" in f
               for f in committed_set_findings(other, COMMITTED_SET, COMMITTED_RECORDINGS))
    empty = tmp_path / "recordings"
    empty.mkdir()
    assert any("expected the one committed answer" in f
               for f in committed_set_findings(manifest, COMMITTED_SET, empty))
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / ("0" * 64 + ".json")).write_text("{}", encoding="utf-8")
    assert any("not a tracked file" in f for f in committed_set_findings(manifest, COMMITTED_SET, loose))


def hostile_price_list_findings(committed: bytes, hostile: bytes) -> list[str]:
    """The second price-list revision extends the committed one by exactly the hostile rows."""
    findings: list[str] = []
    if not hostile.startswith(committed):
        return ["the hostile price list does not begin with the committed one, byte for byte"]
    lines = hostile[len(committed):].decode("utf-8").splitlines()
    width = len(committed.decode("utf-8").splitlines()[0].split(";"))
    cells = [line.split(";") for line in lines]
    for line, row in zip(lines, cells):
        if len(row) != width:
            findings.append(f"{line!r}: {len(row)} cell(s) for a header of {width}; a `;` inside a cell splits the row")
    if findings:
        return findings
    vendors = [row[6] for row in cells]
    for lead in ("=", "+", "@", "-"):
        if not any(v.startswith(lead) for v in vendors):
            findings.append(f"no hostile vendor begins with {lead!r}")
    if not any(row[4] == "" for row in cells):
        findings.append("no row without a price, so the skipped-row report is not exercised")
    analog = next((row for row in cells if row[6].startswith("=")), None)
    membrane = next(
        (r for r in (line.split(";") for line in committed.decode("utf-8").splitlines()) if "Техноэласт" in r[1]), None
    )
    if analog is None or membrane is None:
        findings.append("the formula-named vendor sells no analog of the committed membrane")
    else:
        if not analog[1].startswith(membrane[1]) or analog[1] == membrane[1]:
            findings.append("the formula-named vendor's product is not a named variant of the committed membrane")
        if analog[3] != membrane[3] or analog[5] != membrane[5]:
            findings.append("the analog is not in the membrane's unit and currency")
        if float(analog[4].replace(",", ".")) >= float(membrane[4].replace(",", ".")):
            findings.append("the analog is not cheaper than the membrane")
    return findings


def test_the_hostile_price_list_extends_the_committed_one_by_formula_rows() -> None:
    committed = (COMMITTED_SET / "ar_specification_prices.csv").read_bytes()
    assert hostile_price_list_findings(committed, HOSTILE_PRICES.read_bytes()) == []


def test_control_a_hostile_price_list_that_is_not_what_the_journey_needs_is_found() -> None:
    committed = (COMMITTED_SET / "ar_specification_prices.csv").read_bytes()
    good = HOSTILE_PRICES.read_bytes()
    assert hostile_price_list_findings(committed, b"x" + good)
    split = good + ";Лишняя;;шт;1;RUB;a;b\n".encode()
    assert any("splits the row" in f for f in hostile_price_list_findings(committed, split))
    lines = good.decode("utf-8").splitlines(keepends=True)
    no_formula = "".join(line for line in lines if "=HYPERLINK" not in line).encode()
    assert any("begins with '='" in f for f in hostile_price_list_findings(committed, no_formula))
    no_gap = "".join(line for line in lines if "керамогранитная" not in line).encode()
    assert any("without a price" in f for f in hostile_price_list_findings(committed, no_gap))
    dearer = good.decode("utf-8").replace(";350;RUB;=", ";450;RUB;=").encode()
    assert any("not cheaper" in f for f in hostile_price_list_findings(committed, dearer))


def test_the_norms_seed_refuses_a_database_that_is_not_a_lanes() -> None:
    tool = _require(JOURNEY_DIR / "seed_norms.py")
    refused = _run_tool(
        str(tool), env={"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/auditmanager_alpha"}
    )
    assert refused.returncode == 1 and "refusing to write" in refused.stderr
    # The control: a lane-shaped name gets past the refusal and fails only for want of a server.
    lane = _run_tool(
        str(tool), "--check",
        env={"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/auditmanager_beta_live_journey"},
    )
    assert "refusing to write" not in lane.stderr and lane.returncode != 0


def test_the_journey_will_not_spend_or_change_an_origin_it_was_not_told_it_may() -> None:
    """`--phase all` makes accounts, pauses dispatch and starts further runs: only where it is free.

    The pure rule is tested by `write.test.mjs` (`node --test`), run here so that a gate which
    cannot run a browser still runs it; the wiring is read in the two files that carry it.
    """
    node = shutil.which("node")
    assert node is not None, "node is required: the journey is a node program"
    ran = subprocess.run(
        [node, "--test", str(JOURNEY_DIR / "write.test.mjs")],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    write = _require(JOURNEY_DIR / "write.mjs").read_text(encoding="utf-8")
    assert "nightWindowMayRun({ providerMode, allowSpend })" in write
    assert "if (step.screen !== undefined && step.reads_only !== true) {" in write
    journey = _require(JOURNEY).read_text(encoding="utf-8")
    assert "'--allow-spend'" in journey and "E2E_PC01_ALLOW_SPEND" in journey
    assert "step.screen === undefined" in journey, "--phase core must be the steps without a screen"
    verify = _require(JOURNEY_DIR / "verify-acceptance.mjs").read_text(encoding="utf-8")
    assert "step.screen === undefined" in verify, (
        "the stand's acceptance verdict must count what a core walk declares"
    )


def test_control_a_step_that_claims_to_only_read_but_presses_a_control_is_detected() -> None:
    reading = _night_step(reads_only=True)
    assert not any("only reads" in f for f in _only_step_findings(reading))
    pressing = _night_step(reads_only=True, actions=[{"do": "click", "selector": "button"}])
    assert any("only reads" in f for f in _only_step_findings(pressing))
    writing = _night_step(reads_only=True, expects_api=[
        {"method": "PUT", "path": "/assignments", "operationId": "createAssignment", "expect_status": 200}])
    assert any("only reads" in f for f in _only_step_findings(writing))


# --------------------------------------------------------------------------------------
# `PC01-JOURNEY-GAPS-01`. The steps that close what `BETA-MATRIX-02` section B12 named as
# unwalked, each pinned by NAME, so that a step which disappears -- or which quietly becomes
# another kind of step -- is a red test and not a shrinking journey that still reports OK.
# --------------------------------------------------------------------------------------

#: step name -> (screen, case, the operations the step must declare).
GAP_STEPS: dict[str, tuple[str, str, frozenset[str]]] = {
    # «Блоки»: choose a version, read its portal blocks, one crop and its text lines; a version
    # no run has reached is told it has nothing YET.
    "blocks-portal-blocks-of-a-version-with-a-run": (
        "blocks", "action", frozenset({"listVersionPortalBlocks", "streamVersionPortalBlockCrop"})),
    "blocks-text-lines-of-the-same-version": ("blocks", "action", frozenset({"getVersionBlocks"})),
    "blocks-upload-a-document-no-run-has-read": ("version-upload", "action", frozenset({"uploadDocument"})),
    "blocks-a-version-no-run-has-read-says-so": ("blocks", "refused", frozenset({"listVersionPortalBlocks"})),
    # A successful «Вернуть»: the work is assigned, taken, then given back with its reason.
    "assign-work-to-be-given-back": ("dispatcher", "action", frozenset({"createAssignment"})),
    "my-tasks-take-the-work-to-give-it-back": ("my-tasks", "action", frozenset({"transitionAssignment"})),
    "my-tasks-give-the-work-back": ("my-tasks", "action", frozenset({"transitionAssignment"})),
    "dispatcher-shows-the-work-given-back": ("dispatcher", "action", frozenset({"listAssignments"})),
    # `correctVersionClassification`: the expert corrects a confirmed classification (revision 2, the original
    # kept in the history); an administrator without `expert` is offered nothing; a pair that matches the
    # current one and a reason with no word in it are refused by the form.
    "classification-correction-is-an-experts-act": (
        "version-classification", "refused", frozenset({"getVersionSectionReview"})),
    "classification-correction-needs-a-change": ("version-classification", "refused", frozenset()),
    "classification-correction-needs-a-reason": ("version-classification", "refused", frozenset()),
    "classification-correction": (
        "version-classification", "action", frozenset({"correctVersionClassification"})),
    # The norm document view: the document, its paragraphs and its PDF; a page it does not have.
    "norms-document-text-and-pdf": (
        "norms-document", "action",
        frozenset({"getNormDocument", "listNormParagraphs", "streamNormDocumentContent"})),
    "norms-document-page-past-the-end": (
        "norms-document", "refused", frozenset({"getNormDocument", "listNormParagraphs"})),
}


def _declared_operations(step: dict) -> set[str]:
    return {call["operationId"] for call in step.get("expects_api") or ()}


def gap_step_findings(manifest: dict) -> list[str]:
    """Every pinned gap step is there, on its screen, in its case, declaring its operations."""
    by_name = {step["name"]: step for step in write_steps(manifest)}
    findings: list[str] = []
    for name, (screen, case, operations) in GAP_STEPS.items():
        step = by_name.get(name)
        if step is None:
            findings.append(f"the gap step '{name}' is gone from the manifest")
            continue
        if step.get("screen") != screen:
            findings.append(f"{name}: belongs to screen {step.get('screen')!r}, not {screen!r}")
        if step.get("case") != case:
            findings.append(f"{name}: is a {step.get('case')!r} case, not {case!r}")
        missing = sorted(operations - _declared_operations(step))
        if missing:
            findings.append(f"{name}: no longer declares {missing}")
    return findings


def gap_content_findings(manifest: dict) -> list[str]:
    """What the pinned steps must SAY, which a step's name and operations cannot show."""
    findings: list[str] = []
    steps = {step["name"]: step for step in write_steps(manifest)}

    # A successful «Вернуть» is a transition `returned` that carries its reason and ends in `returned`.
    give_back = steps.get("my-tasks-give-the-work-back") or {}
    sent = [
        needle
        for check in give_back.get("expects_request") or ()
        if check.get("of") == "transitionAssignment"
        for needle in check.get("body_contains") or ()
    ]
    if '"kind":"returned"' not in sent:
        findings.append("my-tasks-give-the-work-back: does not require the request to be the transition `returned`")
    answered = [
        (check.get("json_path"), check.get("equals"))
        for check in give_back.get("expects_response") or ()
        if check.get("of") == "transitionAssignment"
    ]
    if ("status", "returned") not in answered:
        findings.append("my-tasks-give-the-work-back: does not require the answer to say the status is `returned`")
    if not any(
        a.get("do") == "click" and a.get("text") == "Вернуть" for a in give_back.get("actions") or ()
    ):
        findings.append("my-tasks-give-the-work-back: never presses «Вернуть»")

    # The work is taken before it is given back: the take step precedes the return step.
    order = [step["name"] for step in write_steps(manifest)]
    taken, returned = "my-tasks-take-the-work-to-give-it-back", "my-tasks-give-the-work-back"
    if taken in order and returned in order and order.index(taken) > order.index(returned):
        findings.append(f"{returned}: comes before {taken}, the step that takes the work it gives back")

    # «Блоки»: the refusal is the API's `not_produced`, and the happy path is `produced`.
    def _answers(step_name: str, path: str) -> list[object]:
        return [
            check.get("equals")
            for check in (steps.get(step_name) or {}).get("expects_response") or ()
            if check.get("json_path") == path
        ]

    # A correction is a POST to the corrections address, based on the revision shown, that stores revision 2.
    correction = steps.get("classification-correction") or {}
    based_on = [
        needle
        for check in correction.get("expects_request") or ()
        if check.get("of") == "correctVersionClassification"
        for needle in check.get("body_contains") or ()
    ]
    if '"expected_revision":1' not in based_on:
        findings.append("classification-correction: does not require the request to be based on revision 1")
    stored = [
        (check.get("json_path"), check.get("equals"))
        for check in correction.get("expects_response") or ()
        if check.get("of") == "correctVersionClassification"
    ]
    if ("revision", 2) not in stored:
        findings.append("classification-correction: does not require the answer to be revision 2")
    if not any(
        call.get("operationId") == "correctVersionClassification" and call.get("count") == 1
        for call in correction.get("expects_api") or ()
    ):
        findings.append("classification-correction: does not require exactly one request for two presses")
    # The refusals send nothing: each declares the correction as a call that must not be made.
    for refusal in (
        "classification-correction-is-an-experts-act",
        "classification-correction-needs-a-change",
        "classification-correction-needs-a-reason",
    ):
        refused = steps.get(refusal) or {}
        if not any(
            call.get("method") == "POST" and call.get("path", "").endswith("/classification/corrections")
            for call in refused.get("expects_not_called") or ()
        ):
            findings.append(f"{refusal}: does not declare that no correction is sent")

    # The norm document is read from a document the catalogue step captured, and the page past its end
    # sends no request for the PDF.
    opened = steps.get("norms-document-text-and-pdf") or {}
    if "{norm_document_id}" not in opened.get("at", ""):
        findings.append("norms-document-text-and-pdf: is not opened at the document the catalogue captured")
    if not any(
        c.get("of") == "getNormDocument" and c.get("json_path") == "content_available" and c.get("equals") is True
        for c in opened.get("expects_response") or ()
    ):
        findings.append("norms-document-text-and-pdf: does not require the document to offer its PDF")
    past = steps.get("norms-document-page-past-the-end") or {}
    if not any(
        call.get("method") == "GET" and call.get("path", "").endswith("/content")
        for call in past.get("expects_not_called") or ()
    ):
        findings.append("norms-document-page-past-the-end: does not declare that no PDF is requested")

    if "produced" not in _answers("blocks-portal-blocks-of-a-version-with-a-run", "status"):
        findings.append("blocks-portal-blocks-of-a-version-with-a-run: does not require status `produced`")
    if "not_produced" not in _answers("blocks-a-version-no-run-has-read-says-so", "status"):
        findings.append("blocks-a-version-no-run-has-read-says-so: does not require status `not_produced`")
    return findings


def test_the_gaps_beta_matrix_02_named_are_walked_by_steps_that_stay(manifest: dict) -> None:
    findings = gap_step_findings(manifest) + gap_content_findings(manifest)
    assert not findings, "a step PC01-JOURNEY-GAPS-01 added has gone or changed:\n  " + "\n  ".join(findings)


def _without_step(manifest: dict, name: str) -> dict:
    copy = json.loads(json.dumps(manifest))
    copy["write"]["steps"] = [s for s in copy["write"]["steps"] if s["name"] != name]
    return copy


def _step_of(manifest: dict, name: str) -> dict:
    return next(s for s in manifest["write"]["steps"] if s["name"] == name)


def test_control_a_removed_gap_step_is_detected(manifest: dict) -> None:
    assert gap_step_findings(manifest) == [] and gap_content_findings(manifest) == []
    for name in GAP_STEPS:
        gone = _without_step(manifest, name)
        assert any(f"'{name}' is gone" in f for f in gap_step_findings(gone)), name


def test_control_a_gap_step_that_changes_its_case_screen_or_operation_is_detected(manifest: dict) -> None:
    renamed = json.loads(json.dumps(manifest))
    _step_of(renamed, "blocks-a-version-no-run-has-read-says-so")["case"] = "action"
    assert any("is a 'action' case" in f for f in gap_step_findings(renamed))
    moved = json.loads(json.dumps(manifest))
    _step_of(moved, "blocks-text-lines-of-the-same-version")["screen"] = "norms-search"
    assert any("belongs to screen 'norms-search'" in f for f in gap_step_findings(moved))
    stripped = json.loads(json.dumps(manifest))
    _step_of(stripped, "blocks-text-lines-of-the-same-version")["expects_api"] = []
    assert any("no longer declares ['getVersionBlocks']" in f for f in gap_step_findings(stripped))


def test_control_a_return_that_is_not_a_return_is_detected(manifest: dict) -> None:
    for mutate, expected in (
        (lambda s: s.pop("expects_request"), "transition `returned`"),
        (lambda s: s["expects_response"].pop(0), "status is `returned`"),
        (lambda s: s["actions"].pop(), "never presses «Вернуть»"),
    ):
        copy = json.loads(json.dumps(manifest))
        mutate(_step_of(copy, "my-tasks-give-the-work-back"))
        assert any(expected in f for f in gap_content_findings(copy)), expected
    # the take comes first
    swapped = json.loads(json.dumps(manifest))
    steps = swapped["write"]["steps"]
    names = [s["name"] for s in steps]
    i, j = names.index("my-tasks-take-the-work-to-give-it-back"), names.index("my-tasks-give-the-work-back")
    steps[i], steps[j] = steps[j], steps[i]
    assert any("comes before" in f for f in gap_content_findings(swapped))
    # «Блоки»: the refusal that stops being a refusal of a list
    blocks = json.loads(json.dumps(manifest))
    _step_of(blocks, "blocks-a-version-no-run-has-read-says-so")["expects_response"][0]["equals"] = "produced"
    assert any("not_produced" in f for f in gap_content_findings(blocks))


def test_control_a_correction_that_is_not_one_is_detected(manifest: dict) -> None:
    for mutate, expected in (
        (lambda s: s["expects_request"][0]["body_contains"].remove('"expected_revision":1'), "based on revision 1"),
        (lambda s: s["expects_response"].pop(0), "revision 2"),
        (lambda s: s["actions"].__setitem__(3, {**s["actions"][3], "times": 1}) or s["expects_api"][0].pop("count"),
         "exactly one request"),
    ):
        copy = json.loads(json.dumps(manifest))
        mutate(_step_of(copy, "classification-correction"))
        assert any(expected in f for f in gap_content_findings(copy)), expected
    for refusal in (
        "classification-correction-is-an-experts-act",
        "classification-correction-needs-a-change",
        "classification-correction-needs-a-reason",
    ):
        copy = json.loads(json.dumps(manifest))
        _step_of(copy, refusal)["expects_not_called"] = []
        assert any(f"{refusal}: does not declare that no correction is sent" in f for f in gap_content_findings(copy)), refusal


def test_control_a_norm_document_step_that_stops_reading_the_pdf_is_detected(manifest: dict) -> None:
    for mutate, step_name, expected in (
        (lambda s: s.__setitem__("at", "/norms/document?id=ndoc_00000000000000000000000000&page=1"),
         "norms-document-text-and-pdf", "not opened at the document the catalogue captured"),
        (lambda s: s["expects_response"].pop(0), "norms-document-text-and-pdf", "offer its PDF"),
        (lambda s: s.pop("expects_not_called"), "norms-document-page-past-the-end", "no PDF is requested"),
    ):
        copy = json.loads(json.dumps(manifest))
        mutate(_step_of(copy, step_name))
        assert any(expected in f for f in gap_content_findings(copy)), expected


SEED_NORMS = JOURNEY_DIR / "seed_norms.py"


def seed_order_findings(source: str) -> list[str]:
    """The seed puts the bytes into the store before it writes a row that claims them."""
    stored, claimed = source.find("store.put_blob("), source.find("repository.record_verified(")
    if stored < 0 or claimed < 0:
        return ["the seed no longer stores the bound bytes, or no longer records their metadata"]
    if stored > claimed:
        return ["the seed claims an object (rows) before it has put the bytes into the store"]
    return []


def test_the_norms_seed_stores_the_bytes_before_the_rows_that_claim_them() -> None:
    """A binding with no object is what the document view used to meet: a store error, not a screen."""
    source = _require(SEED_NORMS).read_text(encoding="utf-8")
    assert seed_order_findings(source) == []
    assert "return 2" in source and "S3_BUCKET" in source


def test_control_a_seed_that_claims_before_it_stores_is_detected() -> None:
    source = _require(SEED_NORMS).read_text(encoding="utf-8")
    swapped = source.replace("store.put_blob(", "XX", 1).replace("repository.record_verified(", "store.put_blob(", 1)
    swapped = swapped.replace("XX", "repository.record_verified(", 1)
    assert seed_order_findings(swapped) == ["the seed claims an object (rows) before it has put the bytes into the store"]
    assert seed_order_findings("def main(): pass") == [
        "the seed no longer stores the bound bytes, or no longer records their metadata"
    ]


def test_the_norms_seed_writes_no_row_it_cannot_back_with_an_object() -> None:
    tool = _require(SEED_NORMS)
    ran = _run_tool(
        str(tool),
        env={
            "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/auditmanager_beta_live_journey",
            "S3_ENDPOINT_URL": "http://127.0.0.1:1",
            "S3_REGION": "us-east-1",
            "S3_ACCESS_KEY_ID": "journey-test",
            "S3_SECRET_ACCESS_KEY": "journey-test",
            "S3_BUCKET": "journey-test",
        },
    )
    assert ran.returncode == 2, ran.stdout + ran.stderr
    assert "object store" in ran.stderr and "refusing to write" not in ran.stderr
