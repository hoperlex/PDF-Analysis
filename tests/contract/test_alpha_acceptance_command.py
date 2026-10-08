from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from auditmanager.releases.build_id import compute_build_id


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manual-alpha-check.sh"
VERIFY = ROOT / "tests" / "e2e" / "pc01" / "journey" / "verify-acceptance.mjs"
MAKEFILE = ROOT / "Makefile"
MANIFEST = ROOT / "tests" / "e2e" / "pc01" / "journey" / "manifest.json"

# The cold routes a complete read phase walks: the journey manifest's own count, which the
# verifier reads the same way. Since W50 neither side writes the number down, so a wave that
# adds a screen moves both by adding it to the manifest. That the verifier still refuses a
# shorter walk is shown with a one-route-short envelope (`W50-REGISTRY-01` report).
ROUTES = len(json.loads(MANIFEST.read_text(encoding="utf-8"))["routes"])
REVIEWER_ENV = {"E2E_PC01_LOGIN": "synthetic-reviewer", "E2E_PC01_PASSWORD": "not-a-real-secret"}


@pytest.fixture
def version_server():
    """A local credentialed API with a mutable served-build answer."""
    state = {"build_id": compute_build_id(), "version_status": 200}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            pass

        def answer(self, status: int, body: dict) -> None:
            encoded = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self) -> None:
            if self.path != "/api/v1/auth/token":
                self.answer(404, {})
                return
            size = int(self.headers.get("Content-Length", "0"))
            credentials = json.loads(self.rfile.read(size))
            if credentials != {"login": REVIEWER_ENV["E2E_PC01_LOGIN"],
                               "password": REVIEWER_ENV["E2E_PC01_PASSWORD"]}:
                self.answer(401, {})
                return
            self.answer(200, {"token": "stub-private-token", "expires_in": 60,
                              "is_default_credential": False})

        def do_GET(self) -> None:
            if self.path != "/api/v1/system/version":
                self.answer(404, {})
                return
            if self.headers.get("Authorization") != "Bearer stub-private-token":
                self.answer(401, {})
                return
            self.answer(state["version_status"], {
                "product_version": "0.3.0",
                "build_id": state["build_id"],
                "contract_version": "1.0.0-draft.1",
            })

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _assert_no_served_revision_proof_claim(report: str) -> None:
    """An operator's SHA input is an attestation, never a measurement of served bytes."""

    normalized = report.replace("_", " ").replace("-", " ")
    forbidden = (
        r"\b(?:deployed|served)\s+(?:sha|revision)\s+(?:proof|proven|verified|measured)\b",
        r"\b(?:this\s+)?(?:report|acceptance)\s+(?:proves|verifies|measures)\s+"
        r"(?:the\s+)?(?:served|deployed)\b",
    )
    assert not any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in forbidden), (
        "acceptance report claims to prove the served revision from operator input"
    )


def test_operator_attestation_must_not_be_described_as_proof() -> None:
    good = "- attested_deployed_sha: " + "a" * 40
    _assert_no_served_revision_proof_claim(good)
    with pytest.raises(AssertionError, match="claims to prove"):
        _assert_no_served_revision_proof_claim(
            good + "\n- deployed_sha_proof: this report proves the served revision\n"
        )


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
        (("--automated",), "укажите --origin"),
        (
            ("--automated", "--origin", "https://alpha.example.test"),
            "укажите --candidate-sha",
        ),
        (
            (
                "--automated",
                "--origin",
                "https://alpha.example.test",
                "--candidate-sha",
                sha,
                "--deployed-sha",
                sha,
            ),
            "E2E_PC01_LOGIN не задан",
        ),
    ]
    fired: set[str] = set()
    for args, expected_guard in attempts:
        result = run(str(SCRIPT), *args, env={**os.environ, "E2E_PC01_LOGIN": "", "E2E_PC01_PASSWORD": ""})
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "ALPHA ACCEPTANCE PASS" not in output
        assert output.count("ALPHA ACCEPTANCE BLOCKED:") == 1, output
        assert f"ALPHA ACCEPTANCE BLOCKED: {expected_guard}" in output
        fired.add(expected_guard)
    assert fired == {
        "укажите --origin",
        "укажите --candidate-sha",
        "E2E_PC01_LOGIN не задан",
    }


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
        "routesChecked": ROUTES if phase != "write" else 0,
        "routesDeclared": ROUTES,
        "failures": ["start-run: dependency_unavailable"] if dependency else [],
        "records": [
            {
                "name": f"route-{index}",
                "width": {"innerWidth": 780, "scrollWidth": 780},
            }
            for index in range(ROUTES if phase != "write" else 0)
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
import os
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
    location = os.environ.get('ALPHA_STUB_ROOT_LOCATION', '/login?next=%2F')
    status, extra = '307', f'Location: {location}\\r\\n'
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
        'routesChecked': {ROUTES},
        'routesDeclared': {ROUTES},
        'failures': ['start-run: dependency_unavailable'] if dependency else [],
        'records': [{{
            'name': 'route-' + str(i),
            'width': {{'innerWidth': 780, 'scrollWidth': 780}},
        }} for i in range({ROUTES})],
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
    tmp_path: Path, version_server,
) -> None:
    origin, _ = version_server
    real_node = shutil.which("node")
    assert real_node is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_stub_commands(bin_dir, real_node)
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    base_env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        **REVIEWER_ENV,
    }

    expected = {"pass": 0, "skipped": 1, "recorded": 1, "dependency": 2}
    for scenario, exit_code in expected.items():
        evidence = tmp_path / f"evidence-{scenario}"
        result = run(
            str(SCRIPT),
            "--automated",
            "--origin",
            origin,
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
        assert machine["phases"]["apiBuild"]["outcome"] == "PASS"
        assert machine["phases"]["apiBuild"]["candidateMeasured"] == compute_build_id()
        assert machine["phases"]["apiBuild"]["servedMeasured"] == compute_build_id()
        assert machine["humanChecklist"] == {
            "required": True,
            "automated": False,
            "outcome": "PENDING",
        }
        if machine["verdict"] == "PASS":
            assert {phase["outcome"] for phase in machine["phases"].values()} == {"PASS"}
        assert "not-a-real-secret" not in output
        assert "stub-private-token" not in output
        report = (evidence / "report.md").read_text()
        assert f"- attested_deployed_sha: {head}" in report
        assert "deployed_sha_attestation: operator_input" in report
        _assert_no_served_revision_proof_claim(report)
        assert "not-a-real-secret" not in report
        assert "stub-private-token" not in report
        assert f"candidate_api_build_id_measured: {compute_build_id()}" in report
        assert f"served_api_build_id_measured: {compute_build_id()}" in report


def test_verifier_itself_rejects_a_partial_or_non_live_envelope(tmp_path: Path, version_server) -> None:
    origin, _ = version_server
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
            "--origin",
            origin,
            "--candidate-build-id",
            compute_build_id(),
            "--journey-exit",
            "0",
            "--refusals-exit",
            "0",
            env={**os.environ, **REVIEWER_ENV},
        )
        assert result.returncode == 1
        assert json.loads(out.read_text())["verdict"] == "FAIL"
        assert "acceptance verdict: PASS" not in result.stdout


def test_dependency_outage_blocks_even_when_partial_journey_exits_zero(
    tmp_path: Path, version_server,
) -> None:
    origin, _ = version_server
    sha = "c" * 40
    journey = _journey(dependency=True)
    terminal_exchange = journey["write"]["steps"][-1]["exchanges"][0]
    terminal = json.loads(terminal_exchange["responseBody"])
    terminal["state"] = "partial"
    terminal_exchange["responseBody"] = json.dumps(terminal)
    journey["failures"] = []

    journey_path = tmp_path / "journey.json"
    refusals_path = tmp_path / "refusals.json"
    verdict_path = tmp_path / "verdict.json"
    journey_path.write_text(json.dumps(journey), encoding="utf-8")
    refusals_path.write_text(json.dumps(_refusals()), encoding="utf-8")

    result = run(
        "node",
        str(VERIFY),
        "--journey",
        str(journey_path),
        "--refusals",
        str(refusals_path),
        "--out",
        str(verdict_path),
        "--candidate-sha",
        sha,
        "--deployed-sha",
        sha,
        "--origin",
        origin,
        "--candidate-build-id",
        compute_build_id(),
        "--journey-exit",
        "0",
        "--refusals-exit",
        "0",
        env={**os.environ, **REVIEWER_ENV},
    )

    evidence = json.loads(verdict_path.read_text())
    assert result.returncode == 2
    assert evidence["phases"]["providerLive"]["outcome"] == "BLOCKED"
    assert evidence["verdict"] == "BLOCKED"
    assert "acceptance verdict: PASS" not in result.stdout


def test_partial_with_failed_text_analysis_is_not_provider_live_pass(tmp_path: Path, version_server) -> None:
    origin, _ = version_server
    sha = "d" * 40
    journey = _journey()
    terminal_exchange = journey["write"]["steps"][-1]["exchanges"][0]
    terminal = json.loads(terminal_exchange["responseBody"])
    terminal["state"] = "partial"
    terminal["stages"] = [
        {"stage_id": "text_analysis", "status": "failed", "error_code": "analysis_failed"}
    ]
    terminal_exchange["responseBody"] = json.dumps(terminal)

    journey_path = tmp_path / "journey.json"
    refusals_path = tmp_path / "refusals.json"
    verdict_path = tmp_path / "verdict.json"
    journey_path.write_text(json.dumps(journey), encoding="utf-8")
    refusals_path.write_text(json.dumps(_refusals()), encoding="utf-8")

    result = run(
        "node",
        str(VERIFY),
        "--journey",
        str(journey_path),
        "--refusals",
        str(refusals_path),
        "--out",
        str(verdict_path),
        "--candidate-sha",
        sha,
        "--deployed-sha",
        sha,
        "--origin",
        origin,
        "--candidate-build-id",
        compute_build_id(),
        "--journey-exit",
        "0",
        "--refusals-exit",
        "0",
        env={**os.environ, **REVIEWER_ENV},
    )

    evidence = json.loads(verdict_path.read_text())
    assert result.returncode == 1
    assert evidence["phases"]["providerLive"]["outcome"] == "FAIL"
    assert evidence["verdict"] == "FAIL"
    assert "failed text_analysis stage" in "\n".join(evidence["findings"])
    assert "acceptance verdict: PASS" not in result.stdout


@pytest.mark.parametrize(
    ("scenario", "expected_exit", "expected_phase"),
    [
        ("served-mismatch", 1, "FAIL"),
        ("shell-mismatch", 1, "FAIL"),
        ("version-unavailable", 2, "BLOCKED"),
    ],
)
def test_build_measurement_refuses_mismatch_and_missing_response(
    tmp_path: Path, version_server, scenario: str, expected_exit: int, expected_phase: str
) -> None:
    origin, state = version_server
    candidate_build = compute_build_id()
    if scenario == "served-mismatch":
        state["build_id"] = "b" + "0" * 16 if candidate_build != "b" + "0" * 16 else "b" + "1" * 16
    if scenario == "version-unavailable":
        state["version_status"] = 503
    if scenario == "shell-mismatch":
        candidate_build = "b" + "0" * 16 if candidate_build != "b" + "0" * 16 else "b" + "1" * 16
    journey = tmp_path / "journey.json"
    refusals = tmp_path / "refusals.json"
    verdict = tmp_path / "verdict.json"
    journey.write_text(json.dumps(_journey()), encoding="utf-8")
    refusals.write_text(json.dumps(_refusals()), encoding="utf-8")
    result = run(
        "node", str(VERIFY),
        "--journey", str(journey), "--refusals", str(refusals),
        "--out", str(verdict),
        "--candidate-sha", "a" * 40, "--deployed-sha", "a" * 40,
        "--origin", origin, "--candidate-build-id", candidate_build,
        "--journey-exit", "0", "--refusals-exit", "0",
        env={**os.environ, **REVIEWER_ENV},
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    evidence = json.loads(verdict.read_text())
    assert evidence["phases"]["apiBuild"]["outcome"] == expected_phase
    assert evidence["verdict"] == expected_phase
    assert "not-a-real-secret" not in result.stdout + result.stderr + verdict.read_text()
    assert "stub-private-token" not in result.stdout + result.stderr + verdict.read_text()


@pytest.mark.parametrize(
    ("location", "passes"),
    (
        # W50: a guest's `/` is sent to sign in and back to `/`, on the same origin.
        ("/login?next=%2F", True),
        ("/login?next=/", True),
        ("https://alpha.example.test/login?next=%2F", True),
        ("https://ALPHA.EXAMPLE.TEST:443/login?next=%2F", True),
        ("https://attacker.invalid/login?next=%2F", False),
        ("http://alpha.example.test/login?next=%2F", False),
        ("https://alpha.example.test:444/login?next=%2F", False),
        ("https://reviewer@alpha.example.test/login?next=%2F", False),
        ("https://alpha.example.test.evil/login?next=%2F", False),
        ("/login/other?next=%2F", False),
        ("/login", False),
        ("/login?next=%2F%2Fevil.example", False),
        ("/login?next=%2F&next=%2Fprojects", False),
        ("/login?next=%2F#top", False),
        # The pre-W50 answer is now the wrong one.
        ("/projects", False),
    ),
)
def test_root_redirect_must_resolve_to_sign_in_on_the_declared_origin(
    tmp_path: Path, location: str, passes: bool
) -> None:
    real_node = shutil.which("node")
    assert real_node is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_stub_commands(bin_dir, real_node)
    evidence = tmp_path / "evidence"
    result = run(
        str(SCRIPT),
        "--preflight-only",
        "--origin",
        "https://alpha.example.test",
        "--evidence-dir",
        str(evidence),
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "ALPHA_STUB_ROOT_LOCATION": location,
        },
    )
    output = result.stdout + result.stderr
    report = (evidence / "report.md").read_text()
    if passes:
        assert result.returncode == 0, output
        assert "PREFLIGHT OK" in output
        assert "| HTTP-root | PASS |" in report
    else:
        assert result.returncode == 1, output
        assert "PREFLIGHT OK" not in output
        assert "| HTTP-root | FAIL |" in report
