"""Release loading is ordered between migration and API startup on both paths."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy"


def _service(compose: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
        compose,
    )
    assert match is not None, f"missing compose service {name}"
    return match.group("body")


def test_one_shot_service_is_between_migrate_and_api() -> None:
    compose = (DEPLOY / "compose.server.yml").read_text()
    migrate = _service(compose, "migrate")
    notes = _service(compose, "release-notes")
    api = _service(compose, "api")
    assert 'command: ["alembic", "--config", "db/migrations/alembic.ini", "upgrade", "head"]' in migrate
    assert "      migrate:\n        condition: service_completed_successfully" in notes
    assert 'command: ["python", "-m", "auditmanager.releases.load"]' in notes
    assert "      release-notes:\n        condition: service_completed_successfully" in api
    assert "DATABASE_URL:" in notes

    deploy = (DEPLOY / "deploy.sh").read_text()
    assert "for service in s3-init migrate release-notes; do" in deploy


def test_reset_wipe_and_restore_both_run_the_loader_after_migration() -> None:
    reset = (DEPLOY / "reset.sh").read_text()
    restore = reset.split('if [ -n "$RESTORE" ]; then', 1)[-1].split(
        "reset.sh: restored. Verify", 1
    )[0]
    assert restore.index("pg_restore --clean") < restore.index(
        "compose run --rm migrate"
    ) < restore.index("compose run --rm --no-deps release-notes")
    assert "RESTORE_NOTES_STATUS" in restore

    wipe = reset.split('echo "reset.sh: re-running migrations to head"', 1)[-1]
    assert wipe.index("compose run --rm migrate") < wipe.index(
        "compose run --rm --no-deps release-notes"
    ) < wipe.index("mc_run s3-init")
