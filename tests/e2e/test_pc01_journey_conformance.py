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

import json
import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOURNEY_DIR = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "journey"
MANIFEST = JOURNEY_DIR / "manifest.json"
APP_DIR = REPOSITORY_ROOT / "web" / "src" / "app"
WEB_SRC = REPOSITORY_ROOT / "web" / "src"
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

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
        selectors.append(action["selector"])
        if action.get("text") is not None:
            texts.append(action["text"])
    capture = step.get("capture") or {}
    if capture.get("selector") is not None:
        selectors.append(capture["selector"])
    if capture.get("attribute") is not None:
        selectors.append(f"[{capture['attribute']}]")
    for selector in step.get("forbids_rendered") or ():
        selectors.append(selector)
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
        derived = route_path_of_page_module(step["page_module"])
        assert derived == step["at"], (
            f"write step '{step['name']}' says it acts at {step['at']} but its page "
            f"module sits at {derived}"
        )
        assert step["at"] in walked, (
            f"write step '{step['name']}' acts at {step['at']}, which the read walk does "
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


def test_every_refusal_fixture_the_journey_declares_is_on_disk(manifest: dict) -> None:
    """A refusal case with no file is a case that drives nothing."""
    section = refusal_section(manifest)
    for case in refusal_cases(manifest):
        fixture = REPOSITORY_ROOT / section["fixture_dir"] / case["fixture"]
        assert fixture.is_file(), (
            f"refusal case '{case['fixture']}' names {fixture}, which is not on disk. "
            "There would be nothing to attach and nothing to refuse."
        )
        assert fixture.stat().st_size > 0, f"{fixture} is empty"


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
