"""`AR-V3-OPT-IN` (design 4.2, 4.7): the deployment's allowance reaches the `api` container, and only it, off by default.

`compose.server.yml` names the environment of each service one variable at a time (it has no `env_file`), so the
permission to start AR v3 exists for an operator only if the `api` service names `AR_V3_BETA_START_ALLOWED`, with a blank
default (off). The `worker` must NOT name it: it executes what was accepted whether or not starts are still allowed, which
is what lets switching the allowance off leave runs in flight to finish. `alpha.env.example` lists it blank. Every guard
has a case that feeds it a broken input and sees it refuse.
"""

from __future__ import annotations

from pathlib import Path

from tests.contract.test_compose_flag_forwarding import (  # type: ignore[import-not-found]
    compose_default,
    example_assignments,
    service_environments,
)

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "deploy" / "compose.server.yml"
EXAMPLE = ROOT / "infra" / "deploy" / "env" / "alpha.env.example"
NAME = "AR_V3_BETA_START_ALLOWED"


def problems(compose: str, example: str) -> list[str]:
    out: list[str] = []
    environments = service_environments(compose)
    api = environments.get("api", {})
    if NAME not in api:
        out.append("the api service does not name the allowance")
    elif compose_default(api[NAME], NAME) != "":
        out.append(f"the api default is {api[NAME]!r}, not a blank (off)")
    for service, values in environments.items():
        if service != "api" and NAME in values:
            out.append(f"{service} names the allowance; only the api reads it")
    if example_assignments(example).get(NAME) != [""]:
        out.append("alpha.env.example does not list the allowance once, blank")
    return out


def test_the_api_names_the_allowance_blank_the_worker_does_not_and_the_example_lists_it_blank() -> None:
    assert problems(COMPOSE.read_text(encoding="utf-8"), EXAMPLE.read_text(encoding="utf-8")) == []


def test_the_guard_refuses_each_way_to_break_it() -> None:
    compose, example = COMPOSE.read_text(encoding="utf-8"), EXAMPLE.read_text(encoding="utf-8")
    line = f"      {NAME}: ${{{NAME}:-}}\n"
    assert compose.count(line) == 1
    assert problems(compose.replace(line, ""), example)
    assert problems(compose.replace(line, f"      {NAME}: ${{{NAME}:-1}}\n"), example)
    on_the_worker = compose.replace("      EXECUTION_ROLE: worker\n", f"      EXECUTION_ROLE: worker\n{line}", 1)
    assert on_the_worker != compose and problems(on_the_worker, example)
    assert problems(compose, example.replace(f"{NAME}=\n", ""))
    assert problems(compose, example.replace(f"{NAME}=\n", f"{NAME}=1\n"))
