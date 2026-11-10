"""`REVIEW-FIX-SEAMS-1102` -- a rollback switch the API reads must reach the API container.

`compose.server.yml` names the environment of `api` one variable at a time (it has no `env_file`),
so a switch the code reads but the file does not name can never be set from `alpha.env`: the
operator who writes `AUDITMANAGER_NORM_PARAGRAPH_CONTEXT=0` there changes nothing and the paid
behaviour stays on (code review 2026-11-02, S3-02, S9-02, S1-sprints-02).

This file reads every `AUDITMANAGER_*` name out of the two modules that decide a fresh estimate
and a fresh stage plan and holds three things for each:

* the `api` service names it in its `environment`;
* the compose default equals the default in the code, so an unset line behaves as before;
* `alpha.env.example` lists it with the same default, so the operator can find it.

`AUDITMANAGER_INTAKE_RELAXED` is read by the upload and ingest path (`REVIEW-FIX-BOUNDS-1102`), not
by those two modules; it is held to `0` in `api` and in `worker` and in the example.

There is no YAML parser in the test environment, so the file is read by indentation, as its
neighbours do. Every guard here has a test that feeds it a broken input and sees it refuse.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "deploy" / "compose.server.yml"
ENV_EXAMPLE = ROOT / "infra" / "deploy" / "env" / "alpha.env.example"
READERS = (
    "src/auditmanager/runs/preflight.py",
    "src/auditmanager/comparison/stage_v3/policy.py",
)
#: Read outside those modules; the value is fixed here because the reader is another task's.
BOTH_SERVICES = {"AUDITMANAGER_INTAKE_RELAXED": "0"}

NAME = r"AUDITMANAGER_[A-Z0-9_]+"
LITERALS = re.compile(rf'"({NAME})"')
GET = re.compile(rf'environ\.get\(\s*"({NAME})"\s*,\s*("[^"]*"|[A-Za-z_][A-Za-z0-9_]*)\s*\)')


def code_defaults(source: str) -> dict[str, str | None]:
    """Every name the module mentions, with the default of its `environ.get`, or None if unreadable."""
    names = {match.group(1): None for match in LITERALS.finditer(source)}
    for match in GET.finditer(source):
        name, default = match.groups()
        if default.startswith('"'):
            names[name] = default[1:-1]
            continue
        constant = re.search(rf'^{default}\s*=\s*"([^"]*)"\s*$', source, re.MULTILINE)
        names[name] = constant.group(1) if constant else None
    return names


def service_environments(compose: str) -> dict[str, dict[str, str]]:
    """`service -> {name: value}` for the `environment:` mapping of each service, by indentation."""
    found: dict[str, dict[str, str]] = {}
    service: str | None = None
    in_environment = False
    for line in compose.splitlines():
        named = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line)
        if named:
            service, in_environment = named.group(1), False
        elif line == "    environment:":
            in_environment = True
        elif line.startswith("    ") and not line.startswith("      ") and not line.lstrip().startswith("#"):
            in_environment = False
        elif in_environment and service is not None and line.startswith("      ") and not line.lstrip().startswith("#"):
            key, _, value = line.strip().partition(": ")
            found.setdefault(service, {})[key] = value
    return found


def compose_default(value: str, name: str) -> str | None:
    match = re.fullmatch(r"\$\{" + re.escape(name) + r":-([^}]*)\}", value)
    return match.group(1) if match else None


def example_assignments(example: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in example.splitlines():
        match = re.fullmatch(rf"({NAME})=(.*)", line)
        if match:
            found.setdefault(match.group(1), []).append(match.group(2))
    return found


def problems(compose: str, example: str, sources: dict[str, str]) -> list[str]:
    expected: dict[str, tuple[str | None, tuple[str, ...]]] = {}
    out: list[str] = []
    for path, source in sources.items():
        for name, default in code_defaults(source).items():
            if default is None:
                out.append(f"{name} is read by {path} with a default this test cannot read")
            expected[name] = (default, ("api",))
    for name, default in BOTH_SERVICES.items():
        expected[name] = (default, ("api", "worker"))
    environments = service_environments(compose)
    assignments = example_assignments(example)
    for name, (default, services) in sorted(expected.items()):
        for service in services:
            value = environments.get(service, {}).get(name)
            if value is None:
                out.append(f"{name} is not in the {service} environment of compose.server.yml")
            elif default is not None and compose_default(value, name) != default:
                out.append(f"{name} in {service} is {value!r}, the code default is {default!r}")
        listed = assignments.get(name, [])
        if len(listed) != 1:
            out.append(f"alpha.env.example lists {name} {len(listed)} times, not once")
        elif default is not None and listed[0] != default:
            out.append(f"alpha.env.example gives {name}={listed[0]!r}, the code default is {default!r}")
    return out


def _sources() -> dict[str, str]:
    return {path: (ROOT / path).read_text(encoding="utf-8") for path in READERS}


def test_every_switch_the_api_reads_reaches_the_api_container() -> None:
    sources = _sources()
    assert any("AUDITMANAGER_STAGE_V3_PLAN" in source for source in sources.values())
    assert any("AUDITMANAGER_NORM_PARAGRAPH_CONTEXT" in source for source in sources.values())
    assert problems(COMPOSE.read_text(encoding="utf-8"), ENV_EXAMPLE.read_text(encoding="utf-8"), sources) == []


def test_the_intake_switch_reaches_api_and_worker_off_by_default() -> None:
    environments = service_environments(COMPOSE.read_text(encoding="utf-8"))
    for service in ("api", "worker"):
        value = environments[service]["AUDITMANAGER_INTAKE_RELAXED"]
        assert compose_default(value, "AUDITMANAGER_INTAKE_RELAXED") == "0", (service, value)


def test_the_code_defaults_are_read_as_the_code_writes_them() -> None:
    read = {name: default for source in _sources().values() for name, default in code_defaults(source).items()}
    assert read["AUDITMANAGER_EXTENDED_ANALYSIS_PLAN"] == "v2"  # `V3-OPTIN-01` (R-154b): v3 is opt-in
    assert read["AUDITMANAGER_EXTENDED_COVERAGE"] == "batched-v1"
    assert read["AUDITMANAGER_NATIVE_PAGE_PIECES"] == "1"
    assert read["AUDITMANAGER_STAGE_V3_PLAN"] == "windowed-global-v1"


# -- the guard can fail ---------------------------------------------------------------------


def _whole() -> tuple[str, str, dict[str, str]]:
    return COMPOSE.read_text(encoding="utf-8"), ENV_EXAMPLE.read_text(encoding="utf-8"), _sources()


def test_a_name_missing_from_the_api_environment_is_refused() -> None:
    compose, example, sources = _whole()
    kept = [line for line in compose.splitlines(keepends=True)
            if not line.startswith("      AUDITMANAGER_NORM_PARAGRAPH_CONTEXT:")]
    assert len(kept) == len(compose.splitlines(keepends=True)) - 1
    assert problems("".join(kept), example, sources) == [
        "AUDITMANAGER_NORM_PARAGRAPH_CONTEXT is not in the api environment of compose.server.yml"]


def test_a_name_given_to_the_worker_only_is_refused() -> None:
    compose, example, sources = _whole()
    moved = compose.replace(
        "      AUDITMANAGER_STAGE_V3_PLAN: ${AUDITMANAGER_STAGE_V3_PLAN:-windowed-global-v1}\n", "", 1)
    moved = moved.replace(
        "      EXECUTION_ROLE: worker\n",
        "      EXECUTION_ROLE: worker\n      AUDITMANAGER_STAGE_V3_PLAN: ${AUDITMANAGER_STAGE_V3_PLAN:-windowed-global-v1}\n", 1)
    assert moved != compose
    assert problems(moved, example, sources) == [
        "AUDITMANAGER_STAGE_V3_PLAN is not in the api environment of compose.server.yml"]


def test_a_compose_default_that_differs_from_the_code_is_refused() -> None:
    compose, example, sources = _whole()
    changed = compose.replace("${AUDITMANAGER_EXTENDED_COVERAGE:-batched-v1}", "${AUDITMANAGER_EXTENDED_COVERAGE:-legacy}", 1)
    assert changed != compose
    assert problems(changed, example, sources) == [
        "AUDITMANAGER_EXTENDED_COVERAGE in api is '${AUDITMANAGER_EXTENDED_COVERAGE:-legacy}', the code default is 'batched-v1'"]


def test_the_plan_default_of_the_compose_file_and_the_example_is_held_to_the_codes_v2() -> None:
    """`V3-OPTIN-01`: the guard can fail for the plan switch itself, in both files, in the direction that would silently opt a stand into v3."""
    compose, example, sources = _whole()
    assert "${AUDITMANAGER_EXTENDED_ANALYSIS_PLAN:-v2}" in compose and "\nAUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v2\n" in example
    in_compose = compose.replace("${AUDITMANAGER_EXTENDED_ANALYSIS_PLAN:-v2}", "${AUDITMANAGER_EXTENDED_ANALYSIS_PLAN:-v3}", 1)
    assert problems(in_compose, example, sources) == [
        "AUDITMANAGER_EXTENDED_ANALYSIS_PLAN in api is '${AUDITMANAGER_EXTENDED_ANALYSIS_PLAN:-v3}', the code default is 'v2'"]
    in_example = example.replace("\nAUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v2\n", "\nAUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3\n", 1)
    assert problems(compose, in_example, sources) == [
        "alpha.env.example gives AUDITMANAGER_EXTENDED_ANALYSIS_PLAN='v3', the code default is 'v2'"]
    in_code = {path: source.replace('EXTENDED_PLAN_DEFAULT = "v2"', 'EXTENDED_PLAN_DEFAULT = "v3"', 1) for path, source in sources.items()}
    assert in_code != sources
    assert len(problems(compose, example, in_code)) == 2, "a code default moved to v3 is refused in the compose file and in the example"


def test_a_name_the_example_does_not_list_is_refused() -> None:
    compose, example, sources = _whole()
    kept = "".join(line for line in example.splitlines(keepends=True)
                   if not line.startswith("AUDITMANAGER_NATIVE_PAGE_PIECES="))
    assert problems(compose, kept, sources) == ["alpha.env.example lists AUDITMANAGER_NATIVE_PAGE_PIECES 0 times, not once"]


def test_a_new_name_read_by_a_module_is_refused_until_it_is_forwarded() -> None:
    compose, example, sources = _whole()
    path = READERS[0]
    sources[path] += '\nSWITCH = os.environ.get("AUDITMANAGER_BRAND_NEW_SWITCH", "1")\n'
    assert problems(compose, example, sources) == [
        "AUDITMANAGER_BRAND_NEW_SWITCH is not in the api environment of compose.server.yml",
        "alpha.env.example lists AUDITMANAGER_BRAND_NEW_SWITCH 0 times, not once",
    ]


def test_a_name_read_without_a_readable_default_is_refused() -> None:
    compose, example, sources = _whole()
    sources[READERS[1]] += '\nREQUIRED = os.environ["AUDITMANAGER_STAGE_V3_REQUIRED"]\n'
    found = problems(compose, example, sources)
    assert found[0] == f"AUDITMANAGER_STAGE_V3_REQUIRED is read by {READERS[1]} with a default this test cannot read"
    assert len(found) == 3
