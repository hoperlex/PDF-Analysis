"""W53-CLOSE C-14: the W53 rehearsal scripts refuse a target they do not own.

Static on purpose. Importing ``process_recovery`` loads the run test harness, and running
either script needs live services; neither is a contract test. The guard function is
compiled from the script's own source and called in isolation, so the behaviour asserted
is the shipped function's, not a copy of it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts" / "rehearsal" / "w53"
PROCESS_RECOVERY = SCRIPTS / "process_recovery.py"
MINIO_UPGRADE = SCRIPTS / "minio_upgrade.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is not a top-level function")


def _called_names(node: ast.AST) -> list[str]:
    """Plain-name calls in source order."""
    calls = [
        child for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
    ]
    calls.sort(key=lambda call: (call.lineno, call.col_offset))
    return [call.func.id for call in calls]


@pytest.fixture(scope="module")
def require_disposable_database():
    tree = _tree(PROCESS_RECOVERY)
    module = ast.Module(body=[_function(tree, "require_disposable_database")], type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(module, str(PROCESS_RECOVERY), "exec"), namespace)  # noqa: S102
    return namespace["require_disposable_database"]


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "not a url at all ://",
        "postgresql+psycopg://user:secret@db.internal:5432/w53_rehearsal_kill",
        "postgresql+psycopg://user:secret@10.0.0.5:5432/w53_rehearsal_kill",
        "postgresql+psycopg://user:secret@127.0.0.1:5432/auditmanager",
        "postgresql+psycopg://user:secret@127.0.0.1:57040/gate_w53c_store",
        "postgresql+psycopg://user:secret@localhost:5432/",
    ],
)
def test_process_recovery_refuses_a_target_that_is_not_disposable(
    require_disposable_database, url
) -> None:
    with pytest.raises(SystemExit) as refused:
        require_disposable_database(url)
    message = str(refused.value.code)
    assert message.startswith("process_recovery: refusing to run")
    assert "secret" not in message, "the refusal echoed the database password"


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_process_recovery_accepts_a_loopback_rehearsal_database(
    require_disposable_database, host
) -> None:
    require_disposable_database(
        f"postgresql+psycopg://user:secret@{host}:56880/w53_rehearsal_kill"
    )


def test_every_process_recovery_database_path_passes_the_guard_first() -> None:
    """The global ``reconcile`` runs on ``_engine()``; both are reached only after the guard."""
    tree = _tree(PROCESS_RECOVERY)
    engine_calls = _called_names(_function(tree, "_engine"))
    assert engine_calls[0] == "require_disposable_database"
    assert "create_database_engine" in engine_calls
    assert _called_names(_function(tree, "parent"))[0] == "require_disposable_database"
    creators = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and "create_database_engine" in _called_names(node)
    ]
    assert [node.name for node in creators] == ["_engine"]
    recover = _called_names(_function(tree, "recover_process"))
    assert recover.index("_engine") < recover.index("reconcile")


@pytest.mark.parametrize("path", [PROCESS_RECOVERY, MINIO_UPGRADE], ids=lambda p: p.name)
def test_no_rehearsal_check_is_an_assert(path: Path) -> None:
    """``python -O`` strips ``assert``; a stripped check would let the script pass or run."""
    asserts = [node.lineno for node in ast.walk(_tree(path)) if isinstance(node, ast.Assert)]
    assert asserts == [], f"{path.name} still checks with assert at lines {asserts}"


def test_minio_upgrade_preflight_refuses_with_explicit_raises() -> None:
    """Images present, container and volumes absent: each refusal is ``raise SystemExit``."""
    main = _function(_tree(MINIO_UPGRADE), "main")
    refusals = [
        node for node in ast.walk(main)
        if isinstance(node, ast.If)
        and any(
            isinstance(statement, ast.Raise)
            and isinstance(statement.exc, ast.Call)
            and isinstance(statement.exc.func, ast.Name)
            and statement.exc.func.id == "SystemExit"
            for statement in node.body
        )
    ]
    guarded = " ".join(ast.unparse(node.test) for node in refusals)
    for subject in ("OLD", "NEW", "CONTAINER", "clashing"):
        assert subject in guarded, f"no explicit preflight refusal mentions {subject}"


def test_minio_upgrade_require_raises_rather_than_asserts() -> None:
    tree = _tree(MINIO_UPGRADE)
    module = ast.Module(body=[_function(tree, "require")], type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(module, str(MINIO_UPGRADE), "exec"), namespace)  # noqa: S102
    namespace["require"](True, "unused")
    with pytest.raises(SystemExit, match="check failed: listed keys differ"):
        namespace["require"](False, "listed keys differ")
