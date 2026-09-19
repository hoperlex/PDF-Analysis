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

**Measured limitation.** ``make mutation-copy`` copies ``src/``, ``tests/`` and
``pyproject.toml`` only. ``web/`` and ``contracts/`` are not copied, so the four tests here
that read the real tree cannot run inside a mutation copy and must be excluded by path
alongside the three suites under ``tests/integration/composition``. The negative controls
below read nothing outside this file and do run there -- they are what proves each check
can fail.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOURNEY_DIR = REPOSITORY_ROOT / "tests" / "e2e" / "pc01" / "journey"
MANIFEST = JOURNEY_DIR / "manifest.json"
APP_DIR = REPOSITORY_ROOT / "web" / "src" / "app"
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
    """Every operation the journey says a screen calls, required and optional alike."""
    out: set[tuple[str, str, str]] = set()
    for route in manifest["routes"]:
        for group in ("expects_api", "optional_api"):
            for call in route.get(group) or ():
                out.add((call["method"].upper(), call["path"], call["operationId"]))
    return out


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
            "`make mutation-copy` copies only src/, tests/ and pyproject.toml, so these "
            "four checks must be excluded by path inside a mutation copy rather than read "
            "as reds."
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
