from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manual-alpha-check.sh"
VERIFY = ROOT / "tests" / "e2e" / "pc01" / "journey" / "verify-acceptance.mjs"
MAKEFILE = ROOT / "Makefile"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_alpha_acceptance_is_named_beside_but_not_inside_gate() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "alpha-acceptance:" in text
    assert "--automated" in text
    assert '"$${ALPHA_ORIGIN:-}"' in text
    assert '"$${ALPHA_CANDIDATE_SHA:-}"' in text
    assert '"$${ALPHA_DEPLOYED_SHA:-}"' in text
    assert "gate: foundation\n" in text
    assert "gate: foundation alpha-acceptance" not in text


def test_missing_origin_sha_and_credential_never_print_pass() -> None:
    sha = "a" * 40
    attempts = [
        ("--automated",),
        ("--automated", "--origin", "https://alpha.example.test"),
        (
            "--automated",
            "--origin",
            "https://alpha.example.test",
            "--candidate-sha",
            sha,
            "--deployed-sha",
            sha,
        ),
    ]
    for args in attempts:
        result = run(str(SCRIPT), *args, env={**os.environ, "E2E_PC01_LOGIN": "", "E2E_PC01_PASSWORD": ""})
        assert result.returncode != 0
        assert "ALPHA ACCEPTANCE PASS" not in result.stdout + result.stderr


def _journey(*, phase: str = "all", provider_mode: str = "live", dependency: bool = False) -> dict:
    run_id = "run_01K00000000000000000000000"
    terminal = {
        "run_id": run_id,
        "state": "failed" if dependency else "published",
        "provider_mode": provider_mode,
        "stages": (
            [{"stage_id": "text_analysis", "error_code": "dependency_unavailable"}]
            if dependency
            else []
        ),
    }
    if dependency:
        terminal["terminal_reason"] = "dependency_unavailable"
    steps = [
        {"name": "create-project", "exchanges": []},
        {"name": "upload-document", "exchanges": []},
        {
            "name": "start-run",
            "exchanges": [
                {
                    "method": "GET",
                    "url": f"https://alpha.example.test/bff/v1/runs/{run_id}",
                    "responseBody": json.dumps(terminal),
                }
            ],
        },
    ]
    return {
        "origin": "https://alpha.example.test",
        "phase": phase,
        "session": {"opened": True},
        "viewport": {"width": 780, "height": 900},
        "write": {
            "ran": phase != "read",
            "stepsChecked": 3 if phase != "read" else 0,
            "stepsDeclared": 3,
            "stoppedAt": None,
            "captured": {"run_id": run_id},
            "steps": steps if phase != "read" else [],
        },
        "routesChecked": 16 if phase != "write" else 0,
        "routesDeclared": 16,
        "failures": ["start-run: dependency_unavailable"] if dependency else [],
        "records": [
            {
                "name": f"route-{index}",
                "width": {"innerWidth": 780, "scrollWidth": 780},
            }
            for index in range(16 if phase != "write" else 0)
        ],
    }


def _refusals() -> dict:
    return {
        "origin": "https://alpha.example.test",
        "records": [
            {"fixture": f"negative-{index}.pdf", "findings": []} for index in range(6)
        ],
    }


def _write_stub_commands(bin_dir: Path, real_node: str) -> None:
    curl = bin_dir / "curl"
    curl.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys

args = sys.argv[1:]
headers = pathlib.Path(args[args.index('--dump-header') + 1])
url = args[-1]
if url.endswith('/api/v1/openapi.json'):
    status, extra = '401', ''
elif url.endswith('/login'):
    status, extra = '200', ''
else:
    status, extra = '307', 'Location: /projects\\r\\n'
headers.write_text(f'HTTP/1.1 {status} test\\r\\n{extra}\\r\\n', encoding='utf-8')
print(status, end='')
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    node = bin_dir / "node"
    node.write_text(
        f"""#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
target = args[0]
if target.endswith('verify-acceptance.mjs'):
    os.execv({real_node!r}, [{real_node!r}, *args])

out = pathlib.Path(args[args.index('--out') + 1])
out.mkdir(parents=True, exist_ok=True)
scenario = os.environ.get('ALPHA_STUB_SCENARIO', 'pass')
run_id = 'run_01K00000000000000000000000'
if target.endswith('journey.mjs'):
    dependency = scenario == 'dependency'
    phase = 'read' if scenario == 'skipped' else 'all'
    terminal = {{
        'run_id': run_id,
        'state': 'failed' if dependency else 'published',
        'provider_mode': 'recorded' if scenario == 'recorded' else 'live',
        'stages': [{{'stage_id': 'text_analysis', 'error_code': 'dependency_unavailable'}}] if dependency else [],
    }}
    if dependency:
        terminal['terminal_reason'] = 'dependency_unavailable'
    steps = [
        {{'name': 'create-project', 'exchanges': []}},
        {{'name': 'upload-document', 'exchanges': []}},
        {{'name': 'start-run', 'exchanges': [{{
            'method': 'GET',
            'url': 'https://alpha.example.test/bff/v1/runs/' + run_id,
            'responseBody': json.dumps(terminal),
        }}]}},
    ]
    body = {{
        'origin': 'https://alpha.example.test',
        'phase': phase,
        'session': {{'opened': True}},
        'viewport': {{'width': 780, 'height': 900}},
        'write': {{
            'ran': phase != 'read',
            'stepsChecked': 3 if phase != 'read' else 0,
            'stepsDeclared': 3,
            'stoppedAt': None,
            'captured': {{'run_id': run_id}},
            'steps': steps if phase != 'read' else [],
        }},
        'routesChecked': 16,
        'routesDeclared': 16,
        'failures': ['start-run: dependency_unavailable'] if dependency else [],
        'records': [{{
            'name': 'route-' + str(i),
            'width': {{'innerWidth': 780, 'scrollWidth': 780}},
        }} for i in range(16)],
    }}
    (out / 'journey.json').write_text(json.dumps(body), encoding='utf-8')
    sys.exit(1 if dependency else 0)

body = {{
    'origin': 'https://alpha.example.test',
    'records': [{{'fixture': 'negative-' + str(i) + '.pdf', 'findings': []}} for i in range(6)],
}}
(out / 'refusals.json').write_text(json.dumps(body), encoding='utf-8')
""",
        encoding="utf-8",
    )
    node.chmod(0o755)


def test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass(
    tmp_path: Path,
) -> None:
    real_node = shutil.which("node")
    assert real_node is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_stub_commands(bin_dir, real_node)
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    base_env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "E2E_PC01_LOGIN": "synthetic-reviewer",
        "E2E_PC01_PASSWORD": "not-a-real-secret",
    }

    expected = {"pass": 0, "skipped": 1, "recorded": 1, "dependency": 2}
    for scenario, exit_code in expected.items():
        evidence = tmp_path / f"evidence-{scenario}"
        result = run(
            str(SCRIPT),
            "--automated",
            "--origin",
            "https://alpha.example.test",
            "--candidate-sha",
            head,
            "--deployed-sha",
            head,
            "--evidence-dir",
            str(evidence),
            env={**base_env, "ALPHA_STUB_SCENARIO": scenario},
        )
        assert result.returncode == exit_code, result.stdout + result.stderr
        output = result.stdout + result.stderr
        if scenario == "pass":
            assert "ALPHA ACCEPTANCE PASS" in output
        else:
            assert "ALPHA ACCEPTANCE PASS" not in output
        machine = json.loads((evidence / "automated-verdict.json").read_text())
        assert machine["candidateSha"] == head
        assert machine["deployedSha"] == head
        assert machine["humanChecklist"] == {
            "required": True,
            "automated": False,
            "outcome": "PENDING",
        }
        assert "not-a-real-secret" not in output
        assert "not-a-real-secret" not in (evidence / "report.md").read_text()


def test_verifier_itself_rejects_a_partial_or_non_live_envelope(tmp_path: Path) -> None:
    sha = "b" * 40
    refusals = tmp_path / "refusals.json"
    refusals.write_text(json.dumps(_refusals()), encoding="utf-8")
    for name, journey in {
        "skipped": _journey(phase="read"),
        "recorded": _journey(provider_mode="recorded"),
    }.items():
        journey_path = tmp_path / f"{name}.json"
        out = tmp_path / f"{name}-verdict.json"
        journey_path.write_text(json.dumps(journey), encoding="utf-8")
        result = run(
            "node",
            str(VERIFY),
            "--journey",
            str(journey_path),
            "--refusals",
            str(refusals),
            "--out",
            str(out),
            "--candidate-sha",
            sha,
            "--deployed-sha",
            sha,
            "--journey-exit",
            "0",
            "--refusals-exit",
            "0",
        )
        assert result.returncode == 1
        assert json.loads(out.read_text())["verdict"] == "FAIL"
        assert "acceptance verdict: PASS" not in result.stdout
