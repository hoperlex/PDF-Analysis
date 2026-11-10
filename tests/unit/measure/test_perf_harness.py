"""`D-577`, `D-621`: the performance harness of ``tools/measure/perf`` cannot rot silently, and it needs no database to show it.

The harness (the seed, the cold/warm bench, the drivers and the stand script) used to live in two git-ignored evidence directories and
rotted unseen: nothing imported it, so a renamed product name, a moved module or a rewritten statement broke it on the day somebody wanted
the figures again. Here, with no database and no docker:

* every driver imports (a module that cannot be imported cannot run);
* every product name the harness reaches for exists -- ``from auditmanager.x import name`` anywhere in a file, including inside a function,
  and ``A.name`` where ``A = importlib.import_module("auditmanager.x")``; the check is shown red on a file that names what is not there;
* ``--dry-run`` prints the volume the environment configures, the documented 700-document default and the smoke profile of ``perf_stand.sh``;
* the stand script refuses what it does not know before it starts a container;
* the README names every file of the directory (a file nobody documents is a file nobody runs).

The seed itself is exercised against a real, migrated PostgreSQL by ``tests/integration/measure/test_perf_seed_smoke.py``.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[3] / "tools" / "measure" / "perf"
DRIVERS = sorted(path.stem for path in HARNESS.glob("perf_*.py"))
SMOKE = {
    "PERF_P1_DOCS": "12", "PERF_P2_DOCS": "8", "PERF_PASS_SIZES": "20,30,40", "PERF_OLD_PASS_SIZE": "25", "PERF_P2_PASS_SIZE": "10",
    "PERF_MEMORY_STEPS": "150,400", "PERF_RUNS": "2",
}


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """The harness directory on ``sys.path``, an output directory and a database URL nothing listens on; the modules are imported afresh."""
    monkeypatch.setenv("PERF_OUT", str(tmp_path / "out"))
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none")
    monkeypatch.delenv("PERF_SKIP_D463", raising=False)
    for name in list(SMOKE) + ["PERF_BASE"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.syspath_prepend(str(HARNESS))
    _forget(monkeypatch)
    yield tmp_path / "out"
    for name in DRIVERS:
        sys.modules.pop(name, None)


def _forget(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in DRIVERS:
        monkeypatch.delitem(sys.modules, name, raising=False)


def test_the_directory_holds_the_drivers_the_debt_rows_named() -> None:
    assert DRIVERS == [
        "perf_base_compare", "perf_exp", "perf_explore_counters", "perf_explore_plans", "perf_final", "perf_lib", "perf_main", "perf_seed",
    ]


@pytest.mark.parametrize("name", DRIVERS)
def test_every_driver_imports_without_a_database(harness: Path, name: str) -> None:
    module = importlib.import_module(name)
    assert module.__file__ is not None and Path(module.__file__).parent == HARNESS


def test_the_dry_run_prints_the_documented_volume_and_touches_nothing(harness: Path, capsys: pytest.CaptureFixture[str]) -> None:
    perf_main = importlib.import_module("perf_main")
    perf_main.main(["--dry-run"])
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "p1_documents": 400, "p2_documents": 300, "pass_sizes": [300, 500, 800], "old_pass_size": 400, "p2_pass_size": 100,
        "memory_steps": [5000, 20000, 100000], "runs_per_figure": 5, "skip_d463": False,
    }
    assert not harness.exists(), "a dry run must not even create the output directory"
    with pytest.raises(SystemExit, match="usage"):
        perf_main.main(["--dry-runn"])


def test_the_smoke_profile_of_the_stand_script_is_the_volume_the_dry_run_reports(
    harness: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script = (HARNESS / "perf_stand.sh").read_text(encoding="utf-8")
    smoke_line = next(line for line in script.splitlines() if line.strip().startswith("export PERF_P1_DOCS="))
    declared = dict(token.split("=", 1) for token in smoke_line.replace("export", "").split())
    assert declared == SMOKE, "perf_stand.sh --smoke and the test's SMOKE table disagree"
    for name, value in SMOKE.items():
        monkeypatch.setenv(name, value)
    perf_main = importlib.import_module("perf_main")
    perf_main.main(["--dry-run"])
    assert json.loads(capsys.readouterr().out) == {
        "p1_documents": 12, "p2_documents": 8, "pass_sizes": [20, 30, 40], "old_pass_size": 25, "p2_pass_size": 10,
        "memory_steps": [150, 400], "runs_per_figure": 2, "skip_d463": False,
    }


# ---------------------------------------------------------------------------------------------------------------------
# Every product name the harness reaches for exists


def product_references(source: str) -> list[tuple[str, str | None, int]]:
    """``(module, name, line)`` for every reach into ``auditmanager``: ``from m import n`` (at any depth), ``import m``, and ``A.n`` where
    ``A = importlib.import_module("m")``. ``name`` is ``None`` for a plain ``import m``."""
    tree = ast.parse(source)
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "import_module"
            and node.value.args and isinstance(node.value.args[0], ast.Constant) and isinstance(node.value.args[0].value, str)
            and node.value.args[0].value.startswith("auditmanager")
        ):
            bound[node.targets[0].id] = node.value.args[0].value
    found: list[tuple[str, str | None, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("auditmanager"):
            found.extend((node.module, alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.Import):
            found.extend((alias.name, None, node.lineno) for alias in node.names if alias.name.startswith("auditmanager"))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in bound:
            found.append((bound[node.value.id], node.attr, node.lineno))
    return found


def _is_submodule(module: str, name: str) -> bool:
    """``from package import submodule``: the name is not an attribute until it is imported, but it is there."""
    try:
        return importlib.util.find_spec(f"{module}.{name}") is not None
    except (ImportError, ValueError):  # the parent is a plain module: it has no submodules
        return False


def missing_references(source: str) -> list[str]:
    """What ``source`` reaches for in the product that is not there, one line each."""
    problems = []
    for module, name, line in product_references(source):
        try:
            imported = importlib.import_module(module)
        except ImportError as error:
            problems.append(f"line {line}: {module} cannot be imported ({error})")
            continue
        if name is not None and not hasattr(imported, name) and not _is_submodule(module, name):
            problems.append(f"line {line}: {module} has no {name}")
    return problems


def test_every_product_name_the_harness_reaches_for_exists() -> None:
    reached: set[tuple[str, str | None]] = set()
    for path in sorted(HARNESS.glob("perf_*.py")):
        source = path.read_text(encoding="utf-8")
        assert missing_references(source) == [], path.name
        reached.update((module, name) for module, name, _ in product_references(source))
    # not vacuous: the check has seen the names the figures stand on
    assert ("auditmanager.dashboard.audit_state", "_OPTIMISATION_RULE") in reached
    assert ("auditmanager.dashboard.audit_state", "_AUDIT_GROUPS") in reached
    assert ("auditmanager.decision_memory.reads", "MemoryReader") in reached
    assert ("auditmanager.optimisation.proposals.repository", "_LIST_PASSES") in reached
    assert len(reached) >= 25, sorted(reached, key=str)


def test_the_name_check_can_fail() -> None:
    source = "\n".join(
        [
            "import importlib",
            "from auditmanager.dashboard.audit_state import _OPTIMISATION_RULE",
            "from auditmanager.dashboard.audit_state import _NO_SUCH_RULE",
            "from auditmanager.no_such_context import anything",
            "A = importlib.import_module('auditmanager.dashboard.audit_state')",
            "def f():",
            "    from auditmanager.decision_memory.reads import NoSuchReader",
            "    return A._AUDIT_GROUPS, A._ALSO_GONE",
        ]
    )
    problems = missing_references(source)
    assert [p.split(":")[0] for p in problems] == ["line 3", "line 4", "line 7", "line 8"], problems
    assert "has no _NO_SUCH_RULE" in problems[0] and "cannot be imported" in problems[1]
    assert "has no NoSuchReader" in problems[2] and "has no _ALSO_GONE" in problems[3]
    assert missing_references("import importlib\nfrom auditmanager.dashboard.audit_state import _OPTIMISATION_RULE\n") == []


# ---------------------------------------------------------------------------------------------------------------------
# The stand script and the README


def _stand(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(HARNESS / "perf_stand.sh"), *arguments], capture_output=True, text=True, timeout=30, check=False)


def test_the_stand_script_is_valid_shell_and_refuses_what_it_does_not_know_before_it_starts_a_container() -> None:
    assert subprocess.run(["bash", "-n", str(HARNESS / "perf_stand.sh")], check=False).returncode == 0
    unknown = _stand("--no-such-option")
    assert unknown.returncode == 2 and "usage" in unknown.stderr
    no_driver = _stand("--driver", "perf_nothing.py")
    assert no_driver.returncode == 2 and "no such driver" in no_driver.stderr
    # the same invocation with a driver that exists gets past the argument check, and `--dry-run` says what it would have started
    known = _stand("--driver", "perf_main.py", "--label", "unit-check", "--smoke", "--dry-run")
    assert known.returncode == 0, known.stderr
    assert "driver=perf_main.py mode=smoke container=am-lane-perf-pg port=55731" in known.stdout
    assert known.stdout.strip().endswith("/run-unit-check")
    assert not Path(known.stdout.strip().rsplit("out=", 1)[1]).exists(), "a dry run must not create the results directory"


def test_the_readme_names_every_file_of_the_directory() -> None:
    readme = (HARNESS / "README.md").read_text(encoding="utf-8")
    for path in sorted(HARNESS.iterdir()):
        if path.name == "README.md" or path.name == "__pycache__":
            continue
        assert path.name in readme, f"README.md does not mention {path.name}"
