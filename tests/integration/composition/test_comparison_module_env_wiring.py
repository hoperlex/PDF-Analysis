"""The deployed API and worker must receive one comparison module choice."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/deploy/compose.server.yml"
ENV_EXAMPLE = ROOT / "infra/deploy/env/alpha.env.example"
FLAG = "AUDITMANAGER_COMPARISON_MODULES"


def test_comparison_module_choice_reaches_exactly_api_and_worker() -> None:
    carriers: dict[str, str] = {}
    service: str | None = None
    in_environment = False
    for line in COMPOSE.read_text(encoding="utf-8").splitlines():
        named = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line)
        if named:
            service = named.group(1)
            in_environment = False
        elif line == "    environment:":
            in_environment = True
        elif line.startswith("    ") and not line.startswith("      ") and not line.lstrip().startswith("#"):
            in_environment = False
        if in_environment and line.startswith(f"      {FLAG}: "):
            assert service is not None
            assert service not in carriers, f"{service} declares {FLAG} twice"
            carriers[service] = line.split(": ", 1)[1]
    assert carriers == {
        "api": "${AUDITMANAGER_COMPARISON_MODULES:-versions,stages}",
        "worker": "${AUDITMANAGER_COMPARISON_MODULES:-versions,stages}",
    }


def test_example_keeps_activation_explicit() -> None:
    assignments = [
        line for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if line.startswith(f"{FLAG}=")
    ]
    assert assignments == [f"{FLAG}=versions,stages"]
