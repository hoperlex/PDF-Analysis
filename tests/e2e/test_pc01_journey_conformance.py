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
text is ``Start run`` -- and reads named *markers* -- ``data-created-project``,
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
provide is ``web/``, and that is the only thing missing here. So of the four checks below
that read the real tree, the three that read ``web/src/app`` cannot run inside a mutation
copy and must be excluded by path alongside the three suites under
``tests/integration/composition``; the contract check reads only ``tests/`` and the
symlinked ``contracts/`` and runs there unchanged.

The six negative controls read nothing outside this file and run anywhere -- they are what
proves each check can fail.
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

    Both halves. The write half's three `POST`s go through the same check as the read
    walk's `GET`s, so renaming `startRun` -- the operation `D-5` actually was -- reddens
    the gate rather than waiting for someone to run a browser.
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
                        "text": "Create",
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
                "actions": [{"do": "click", "selector": "button", "text": "Start run"}],
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
    assert handles == {'id="new-project-name"', "data-created-project", "Create"}
    source_after_a_rename = (
        '<input id="newProjectName" /><p data-created-project="x">Created</p>'
    )
    missing = sorted(h for h in handles if h not in source_after_a_rename)
    assert missing == ['id="new-project-name"']


def test_control_a_dropped_marker_attribute_is_detected() -> None:
    handles = handles_named_by_write_step(_only_write_step("start-run"))
    assert handles == {"data-run-outcome", "data-run-activity", "Start run"}
    source_after_the_marker_went = '<p data-run-activity="stopped">Start run</p>'
    missing = sorted(h for h in handles if h not in source_after_the_marker_went)
    assert missing == ["data-run-outcome"]


def test_control_a_relabelled_button_is_detected() -> None:
    handles = handles_named_by_write_step(_only_write_step("start-run"))
    source_after_the_relabel = (
        '<button data-run-outcome data-run-activity>Run the audit</button>'
    )
    assert "Start run" in handles
    assert "Start run" not in source_after_the_relabel


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
