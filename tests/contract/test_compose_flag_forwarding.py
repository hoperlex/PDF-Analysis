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

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

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


# -- `EMBED-01` (ADR-0029 decision 8): the night encoder's service ---------------------------------------------------------------
#
# The service `embedder` is the encoder of the precedents' vectors: offline, with a hard memory limit. Its `${ALPHA_MEM_LIMIT_EMBEDDER:-3g}` default exists
# only so that Compose renders the file on a stand that has not set the variable (Compose renders the whole file for every command); the encoder is never
# started on it, which is `embed-window.sh`'s refusal, held in `tests/unit/precedents/test_embed_window_script.py`. What is held here is what the decision says
# about the definition, on the file as written; each guard is shown refusing a copy of the file that broke it.

EMBEDDER = "embedder"
LIMIT_NAME = "ALPHA_MEM_LIMIT_EMBEDDER"
SERVICE_LINE = re.compile(r"  ([a-z0-9-]+):[ ]*")
LIMIT_EXPRESSION = "${" + LIMIT_NAME + ":-3g}"


def service_names(compose: str) -> list[str]:
    """The totality query of the task file (`awk '/^services:/{s=1;next} /^[a-z]/{s=0} s && /^  [a-z0-9-]+:[ ]*$/{print $1}'`), in Python."""
    found: list[str] = []
    inside = False
    for line in compose.splitlines():
        if line.startswith("services:"):
            inside = True
        elif re.match(r"[a-z]", line):
            inside = False
        elif inside and SERVICE_LINE.fullmatch(line):
            found.append(line.strip().rstrip(":"))
    return found


def service_block(compose: str, name: str) -> list[str]:
    """The lines of one service, comments and blanks left out, indentation kept."""
    lines = compose.splitlines()
    start = lines.index(f"  {name}:")
    block: list[str] = []
    for line in lines[start + 1:]:
        if line and not line.startswith("    ") and not line.startswith("  #") and line.strip():
            break
        if line.startswith("  ") and not line.startswith("   ") and not line.lstrip().startswith("#") and line.strip():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            block.append(line)
    return block


def scalars(block: list[str]) -> dict[str, str]:
    """The `key: value` lines at four spaces of a service block."""
    found: dict[str, str] = {}
    for line in block:
        match = re.fullmatch(r"    ([a-z_]+):[ ]+(.*)", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def embedder_problems(compose: str) -> list[str]:
    """Every way the file's `embedder` can fail the decision; an empty list is a service that is offline, hard-limited and not started by `up`."""
    out: list[str] = []
    if EMBEDDER not in service_names(compose):
        return [f"{EMBEDDER} is not a service of the file"]
    block = service_block(compose, EMBEDDER)
    keys = scalars(block)
    text = "\n".join(block)
    if keys.get("profiles") != "[embedder]":
        out.append(f"profiles is {keys.get('profiles')!r}, not [embedder]: `up` would start it")
    if keys.get("network_mode") != "none":
        out.append(f"network_mode is {keys.get('network_mode')!r}, not none")
    for forbidden in ("networks", "depends_on", "env_file", "ports", "links", "extra_hosts", "dns"):
        if forbidden in keys or re.search(rf"^    {forbidden}:", text, re.MULTILINE):
            out.append(f"it declares {forbidden}: the container has no network and reaches nothing")
    environment = re.findall(r"^      ([A-Z][A-Z0-9_]*):", text, re.MULTILINE)
    for name in environment:
        if name not in {"OMP_NUM_THREADS", "MKL_NUM_THREADS", "HOME"}:
            out.append(f"the environment names {name}: it has no database, no store and no secret")
    if re.search(r"DATABASE|S3_|SECRET|TOKEN|PASSWORD|API_KEY", text):
        out.append("a database, store or secret appears in its definition")
    for key in ("mem_limit", "memswap_limit"):
        value = keys.get(key, "")
        if value != LIMIT_EXPRESSION:
            out.append(f"{key} is {value!r}: it must be exactly {LIMIT_EXPRESSION}, so that Compose renders the file with the variable unset")
    if re.search(r"\$\{" + LIMIT_NAME + r":?\?", text):
        out.append(f"{LIMIT_NAME} is required (`:?`): every compose command of a stack that has not set it would refuse, for a service that is off by default")
    if keys.get("oom_score_adj") != "1000":
        out.append(f"oom_score_adj is {keys.get('oom_score_adj')!r}, not 1000")
    if keys.get("cpus") != "2":
        out.append(f"cpus is {keys.get('cpus')!r}, not 2")
    if 'OMP_NUM_THREADS: "2"' not in text or 'MKL_NUM_THREADS: "2"' not in text:
        out.append("the thread variables are not 2")
    if keys.get("read_only") != "true" or keys.get("cap_drop") != "[ALL]":
        out.append("the root filesystem is not read-only or the capabilities are not dropped")
    if keys.get("restart") != '"no"':
        out.append("it restarts: a round runs once")
    mounts = re.findall(r"^      - (\S+)$", text.split("volumes:", 1)[1].split("command:", 1)[0], re.MULTILINE) if "volumes:" in text else []
    if mounts != ["embed-exchange:/embed", "../norms-worker/embed_intents.py:/opt/norms-worker/embed_intents.py:ro"]:
        out.append(f"its mounts are {mounts}")
    return out


def test_the_embedder_is_in_the_file_and_the_enumerator_counts_it_once() -> None:
    names = service_names(COMPOSE.read_text(encoding="utf-8"))
    assert len(names) == 10 and names.count(EMBEDDER) == 1, names
    assert sorted(set(names) - {EMBEDDER}) == ["api", "migrate", "postgres", "proxy", "release-notes", "s3", "s3-init", "web", "worker"]


def test_the_embedder_is_offline_hard_limited_and_not_started_by_up() -> None:
    assert embedder_problems(COMPOSE.read_text(encoding="utf-8")) == []


def test_only_the_embedder_is_in_a_profile_so_up_starts_every_other_service() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    gated = [name for name in service_names(compose) if "profiles" in scalars(service_block(compose, name))]
    assert gated == [EMBEDDER]


def test_the_embedder_runs_the_entry_the_checkout_mounts_and_that_file_exists() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    text = "\n".join(service_block(compose, EMBEDDER))
    assert "      - /opt/norms-worker/embed_intents.py\n" in text + "\n"
    assert (ROOT / "infra" / "norms-worker" / "embed_intents.py").is_file()
    assert "      - /embed/request.json\n" in text + "\n" and "      - /embed/response.json\n" in text + "\n"


def test_the_worker_and_the_embedder_share_the_exchange_and_the_worker_has_no_other_mount() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    environments = service_environments(compose)
    assert environments["worker"]["AUDITMANAGER_EMBED_DIR"] == "/embed"
    assert "AUDITMANAGER_EMBED_DIR" not in environments["api"], "only the worker drives the window"
    worker = "\n".join(service_block(compose, "worker"))
    assert re.findall(r"^      - (\S+)$", worker.split("\n    volumes:\n", 1)[1].split("\n    stop_grace_period", 1)[0], re.MULTILINE) == ["embed-exchange:/embed"]
    assert re.search(r"^  embed-exchange:\n    name: \$\{ALPHA_INSTANCE:\?[^}]*\}-embed-exchange$", compose, re.MULTILINE)


@pytest.mark.parametrize(("old", "new", "expected"), [
    ("    profiles: [embedder]\n", "", "profiles is None"),
    ("    network_mode: none\n", "", "network_mode is None"),
    ("    network_mode: none\n", "    network_mode: none\n    networks: [alpha]\n", "it declares networks"),
    ("    mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-3g}\n", "    mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-0}\n", "mem_limit is '${ALPHA_MEM_LIMIT_EMBEDDER:-0}'"),
    ("    mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-3g}\n", "    mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:?unset}\n", "is required (`:?`)"),
    ("    mem_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-3g}\n", "    mem_limit: 3g\n", "mem_limit is '3g'"),
    ("    memswap_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-3g}\n", "    memswap_limit: 4g\n", "memswap_limit is '4g'"),
    ("    memswap_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-3g}\n", "    memswap_limit: ${ALPHA_MEM_LIMIT_EMBEDDER:-4g}\n", "memswap_limit is '${ALPHA_MEM_LIMIT_EMBEDDER:-4g}'"),
    ("    oom_score_adj: 1000\n", "    oom_score_adj: 500\n", "oom_score_adj is '500'"),
    ("    cpus: 2\n", "    cpus: 4\n", "cpus is '4'"),
    ("      OMP_NUM_THREADS: \"2\"\n", "      OMP_NUM_THREADS: \"8\"\n", "thread variables are not 2"),
    ("      HOME: /tmp\n", "      HOME: /tmp\n      DATABASE_URL: x\n", "DATABASE_URL"),
    ("    read_only: true\n", "", "read-only"),
    ("    restart: \"no\"\n", "    restart: unless-stopped\n", "it restarts"),
    ("      - ../norms-worker/embed_intents.py:/opt/norms-worker/embed_intents.py:ro\n", "", "its mounts are"),
])
def test_the_embedder_check_can_fail(old: str, new: str, expected: str) -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    start = compose.index("  embedder:\n")
    head, tail = compose[:start], compose[start:]
    assert old in tail, old
    broken = head + tail.replace(old, new, 1)
    found = embedder_problems(broken)
    assert any(expected in line for line in found), (expected, found)


def _docker_compose(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", "compose", "--file", str(COMPOSE), *args], env=env, capture_output=True, text=True, timeout=120, check=False)


def test_compose_itself_renders_the_file_without_the_limit_and_the_embedder_carries_a_memory_limit() -> None:
    """The real thing, where there is a `docker compose` to ask (it needs no daemon): with the variable unset or empty the file still renders -- every
    other compose command of a stack that has not set it keeps working -- the embedder is not listed without its profile, and with it carries a `mem_limit`
    and the same `memswap_limit` (the default, 3g, only so that the file renders)."""
    if shutil.which("docker") is None or _docker_compose(["version"], dict(os.environ)).returncode != 0:
        pytest.skip("no `docker compose` on this machine; the text of the definition is held by the tests above")
    required = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):\?", COMPOSE.read_text(encoding="utf-8")))
    assert LIMIT_NAME not in required, "the limit is not a required variable"
    base = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/root"), **{name: "x" for name in required}, "ALPHA_HTTP_PORT": "8080"}
    for env in (base, {**base, LIMIT_NAME: ""}):
        plain = _docker_compose(["config", "--services"], env)
        assert plain.returncode == 0, plain.stderr
        assert EMBEDDER not in plain.stdout.split() and len(plain.stdout.split()) == 9, "`up` and `ps` see the nine services of before"
        profiled = _docker_compose(["--profile", EMBEDDER, "config"], env)
        assert profiled.returncode == 0, profiled.stderr
        block = profiled.stdout.split("  embedder:\n", 1)[1].split("\n  postgres:", 1)[0]
        assert 'mem_limit: "3221225472"' in block and 'memswap_limit: "3221225472"' in block, block
        assert "oom_score_adj: 1000" in block and "network_mode: none" in block and "cpus: 2" in block
    given = _docker_compose(["--profile", EMBEDDER, "config"], {**base, LIMIT_NAME: "3500m"})
    assert given.returncode == 0, given.stderr
    block = given.stdout.split("  embedder:\n", 1)[1].split("\n  postgres:", 1)[0]
    assert 'mem_limit: "3670016000"' in block and 'memswap_limit: "3670016000"' in block, "an explicit value reaches both limits"
