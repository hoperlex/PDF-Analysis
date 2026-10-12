"""`W54-WORKER-01` (R-105) -- the worker's configuration, wiring and compose service.

Container-free: nothing here opens a database or object-store connection. The environment
names a closed local port, which the composition root never dials at construction (an
engine and an S3 client are lazy), and the one case that does try to connect proves that a
``LISTEN`` that cannot be established is logged rather than silent.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path

import pytest

from auditmanager.bootstrap.public import (
    ConfigurationError,
    build_application,
    build_worker_runtime,
)
from auditmanager.bootstrap.settings import (
    API_TOKEN_ENV,
    EXECUTION_ROLE_ENV,
    WORKER_STATE_DIR_ENV,
    load,
)
from auditmanager.runs.public import DurableCarrier, ReclaimingCarrier
from auditmanager.workers.__main__ import HEALTH_MAX_AGE_SECONDS, health, serve
from auditmanager.workers.service import HEARTBEAT_FILE, IDENTITY_FILE, JobWakeup, healthy

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/deploy/compose.server.yml"

#: Literals: a configuration that is complete and points at nothing that answers.
_ENV = {
    "DATABASE_URL": "postgresql+psycopg://user:password@127.0.0.1:9/nothing",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "an-access-key",
    "S3_SECRET_ACCESS_KEY": "a-secret-key",
    "S3_BUCKET": "a-bucket",
}
_TOKEN = {API_TOKEN_ENV: "worker-suite-deployment-secret"}


# --- the role and the token exemption ---------------------------------------------------


class TestTheRoleIsExplicitAndTheWorkerHoldsNoSecret:
    def test_an_unset_role_is_w53s_in_process_execution(self) -> None:
        assert load(_ENV | _TOKEN).execution_role == "all"

    @pytest.mark.parametrize("role", ["all", "api", "worker"])
    def test_each_declared_role_is_read(self, role: str) -> None:
        token = {} if role == "worker" else _TOKEN
        assert load(_ENV | token | {EXECUTION_ROLE_ENV: role}).execution_role == role

    def test_an_undeclared_role_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="declared roles"):
            load(_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "both"})

    def test_the_worker_starts_without_the_deployment_secret(self) -> None:
        settings = load(_ENV | {EXECUTION_ROLE_ENV: "worker"})
        assert settings.api_token is None

    def test_the_worker_refuses_to_hold_the_deployment_secret(self) -> None:
        with pytest.raises(ConfigurationError, match=API_TOKEN_ENV):
            load(_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "worker"})

    @pytest.mark.parametrize("role", [None, "all", "api"])
    def test_a_serving_role_still_requires_the_secret(self, role: str | None) -> None:
        environ = dict(_ENV) | ({} if role is None else {EXECUTION_ROLE_ENV: role})
        with pytest.raises(ConfigurationError, match=API_TOKEN_ENV):
            load(environ)


# --- who claims, as built by the composition root -----------------------------------------


class TestTheCompositionRootWiresTheRole:
    def test_all_keeps_the_in_process_claimant(self) -> None:
        application = build_application(environ=_ENV | _TOKEN)
        assert application.execution_role == "all"
        assert isinstance(application.carrier, DurableCarrier)

    def test_api_claims_nothing_and_only_reclaims(self) -> None:
        application = build_application(environ=_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "api"})
        assert application.execution_role == "api"
        assert isinstance(application.carrier, ReclaimingCarrier)
        assert not isinstance(application.carrier, DurableCarrier)

    def test_the_api_refuses_the_worker_role(self) -> None:
        with pytest.raises(ConfigurationError, match="worker service's role"):
            build_application(environ=_ENV | {EXECUTION_ROLE_ENV: "worker"})

    def test_the_worker_runtime_refuses_any_other_role(self) -> None:
        with pytest.raises(ConfigurationError, match="EXECUTION_ROLE=worker"):
            build_worker_runtime(environ=_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "api"})
        with pytest.raises(ConfigurationError, match="EXECUTION_ROLE=worker"):
            build_worker_runtime(environ=_ENV | _TOKEN)

    def test_the_worker_runtime_is_built_without_a_router_or_a_secret(
        self, tmp_path: Path
    ) -> None:
        runtime = build_worker_runtime(environ=_ENV | {
            EXECUTION_ROLE_ENV: "worker", WORKER_STATE_DIR_ENV: str(tmp_path),
        })
        assert runtime.settings.api_token is None
        assert runtime.slots == 1
        assert runtime.state_dir == tmp_path
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        assert re.fullmatch(re.escape(version) + r"\+b[0-9a-f]{16}", runtime.version)
        assert callable(runtime.execute)

    def test_the_api_carrier_submits_nothing(self) -> None:
        """`api` never executes: the accepted Job and its NOTIFY are the hand-over."""
        carrier = ReclaimingCarrier(sessionmaker_that_must_not_be_used())

        def must_not_run() -> None:
            raise AssertionError("the API process executed a run")

        carrier.submit(must_not_run)


def sessionmaker_that_must_not_be_used():  # noqa: ANN201 - a test double
    def refuse():
        raise AssertionError("submit opened a session")

    return refuse


# --- the entry point ----------------------------------------------------------------------


class TestTheEntryPoint:
    def test_serve_refuses_before_registering_when_the_secret_is_present(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = serve(_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "worker"})
        assert code == 2
        assert "refusing to start" in capsys.readouterr().err

    def test_serve_refuses_without_the_worker_role(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert serve(_ENV | _TOKEN | {EXECUTION_ROLE_ENV: "api"}) == 2
        assert "EXECUTION_ROLE=worker" in capsys.readouterr().err

    def test_health_reads_the_identity_and_a_recent_heartbeat(self, tmp_path: Path) -> None:
        (tmp_path / IDENTITY_FILE).write_text("wrk_01M2545JSD15ETSNNV904X991K\n")
        (tmp_path / HEARTBEAT_FILE).touch()
        assert health({WORKER_STATE_DIR_ENV: str(tmp_path)}) == 0

    def test_health_fails_on_an_old_heartbeat(self, tmp_path: Path) -> None:
        (tmp_path / IDENTITY_FILE).write_text("wrk_01M2545JSD15ETSNNV904X991K\n")
        (tmp_path / HEARTBEAT_FILE).touch()
        old = time.time() - HEALTH_MAX_AGE_SECONDS - 5
        os.utime(tmp_path / HEARTBEAT_FILE, (old, old))
        assert health({WORKER_STATE_DIR_ENV: str(tmp_path)}) == 1

    def test_health_fails_without_an_identity_or_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / HEARTBEAT_FILE).touch()
        assert not healthy(tmp_path, max_age_seconds=90, now=time.time())
        assert health({}) == 1


# --- a LISTEN that cannot be had is logged, and the poll is the fallback --------------------


def test_a_listen_that_cannot_be_established_is_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(_ENV["DATABASE_URL"]))
    )
    wakeup = JobWakeup(engine)
    stop = threading.Event()
    try:
        with caplog.at_level(logging.WARNING, logger="auditmanager.workers.service"):
            assert wakeup.wait(0.01, stop=stop) is False
            assert wakeup.wait(0.01, stop=stop) is False
    finally:
        wakeup.close()
        engine.dispose()
    warnings = [r for r in caplog.records if "LISTEN" in r.getMessage()]
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]
    assert "polling every 5 s" in warnings[0].getMessage(), warnings[0].getMessage()
    assert not wakeup.listening


# --- the compose service ------------------------------------------------------------------


def _service_blocks(text: str) -> dict[str, str]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "services:")
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if indent == 2 and line.rstrip().endswith(":"):
            current = line.strip().rstrip(":")
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(line)
    return {name: "\n".join(body) for name, body in blocks.items()}


def _environment_names(block: str) -> set[str]:
    names: set[str] = set()
    inside = False
    for line in block.splitlines():
        if line.strip() == "environment:":
            inside = True
            continue
        if inside:
            if len(line) - len(line.lstrip()) == 6 and ":" in line:
                names.add(line.strip().split(":", 1)[0])
                continue
            inside = False
    return names


class TestTheComposeService:
    blocks = _service_blocks(COMPOSE.read_text(encoding="utf-8"))

    def test_both_roles_are_literal_lines(self) -> None:
        assert "      EXECUTION_ROLE: api" in self.blocks["api"].splitlines()
        assert "      EXECUTION_ROLE: worker" in self.blocks["worker"].splitlines()

    def test_the_worker_has_the_apis_environment_except_the_secret(self) -> None:
        api = _environment_names(self.blocks["api"])
        worker = _environment_names(self.blocks["worker"])
        assert API_TOKEN_ENV in api
        assert API_TOKEN_ENV not in worker
        assert API_TOKEN_ENV not in self.blocks["worker"]
        assert worker - {WORKER_STATE_DIR_ENV} == api - {API_TOKEN_ENV}

    def test_the_worker_runs_the_api_image_as_the_worker_command(self) -> None:
        worker = self.blocks["worker"]
        assert "image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-api" in worker
        assert 'command: ["python", "-m", "auditmanager.workers", "serve"]' in worker
        assert "dockerfile: infra/deploy/Dockerfile.api" in worker

    def test_the_worker_publishes_nothing_and_reads_the_provider_file(self) -> None:
        worker = self.blocks["worker"]
        assert "ports:" not in worker
        assert "volumes:" not in worker
        assert "path: env/provider.env" in worker

    def test_the_identity_is_on_a_tmpfs_the_health_check_reads(self) -> None:
        worker = self.blocks["worker"]
        assert "- /run/auditmanager:" in worker
        assert f"{WORKER_STATE_DIR_ENV}: /run/auditmanager" in worker
        assert '["CMD", "python", "-m", "auditmanager.workers", "health"]' in worker

    def test_the_stop_grace_outlasts_the_drain(self) -> None:
        from auditmanager.workers.__main__ import DRAIN_SECONDS

        grace = re.search(r"stop_grace_period: (\d+)s", self.blocks["worker"])
        assert grace is not None and int(grace.group(1)) > DRAIN_SECONDS

    def test_the_role_is_never_in_the_environment_file(self) -> None:
        example = (ROOT / "infra/deploy/env/alpha.env.example").read_text(encoding="utf-8")
        assert EXECUTION_ROLE_ENV not in example
