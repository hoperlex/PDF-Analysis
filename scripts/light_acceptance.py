#!/usr/bin/env python3
"""R-70 acceptance over an explicit, clean BASE..HEAD tree.

The selector is deliberately conservative. An unclassified product path fails instead of
making the light target look green while omitting a live check. A full-gate risk path is
reported before any suite starts; ``make gate`` remains the independent full target.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FULL_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")

# Each entry names integration directories known to exercise this bounded context. A new
# context is a mapping decision, never an empty selected suite.
CONTEXT_SUITES: dict[str, tuple[str, ...]] = {
    "access": ("access", "auth"),
    "analysis": ("analysis", "analysis_engine", "analysis_text"),
    "api": ("api",),
    "comparison": ("analysis",),
    "dashboard": ("api",),
    "decisions": ("decisions",),
    "documents": ("ingest",),
    "export": ("exports",),
    "exports": ("exports",),
    "findings": ("findings",),
    "ingest": ("ingest",),
    "jobs": ("runs",),
    "norms": ("norms",),
    "operations": ("api",),
    "runs": ("runs",),
    "shared": ("shared_kernel", "db"),
    "storage": ("storage",),
}

RISK_FILES = {
    "Makefile",
    "pyproject.toml",
    "uv.lock",
    "web/package.json",
    "web/package-lock.json",
    "web/FRONTEND_LOCK.json",
    "web/src/_app/providers.tsx",
}
RISK_PREFIXES = ("contracts/", "db/migrations/", "infra/", "src/auditmanager/bootstrap/", "tests/support/")
SCREEN_PREFIXES = (
    "web/src/_app/", "web/src/_pages/", "web/src/widgets/", "web/src/features/",
    "web/src/entities/", "web/src/shared/", "web/src/app/",
)


class SelectionError(Exception):
    pass


@dataclass(frozen=True)
class Selection:
    integration_dirs: tuple[str, ...]
    live_journey: bool


def classify(paths: list[str]) -> Selection:
    risks: list[str] = []
    unknown: list[str] = []
    suites: set[str] = set()
    screen = False
    for path in paths:
        if path in RISK_FILES or path.startswith(RISK_PREFIXES) or path.endswith("/conftest.py"):
            risks.append(path)
            continue
        if path.startswith("src/auditmanager/"):
            if path.endswith("/README.md") or path == "src/auditmanager/README.md":
                continue
            if not path.endswith(".py"):
                unknown.append(f"backend source path: {path}")
                continue
            context = path.split("/")[2]
            mapped = CONTEXT_SUITES.get(context)
            if mapped is None:
                unknown.append(f"backend context {context}: {path}")
            else:
                suites.update(mapped)
            continue
        if path.startswith("web/src/"):
            if path.startswith(SCREEN_PREFIXES):
                # BFF session guards and the sign-in route choose screen redirects;
                # other BFF calls can change what a screen reads. Include all of app/bff.
                screen = True
            else:
                unknown.append(f"screen-affecting path: {path}")
            continue
        if path.startswith(("docs/", "tests/", "web/tests/", "scripts/")) or path in {"AGENTS.md"}:
            continue
        # Root or new product files need a deliberate classification.
        unknown.append(f"unclassified path: {path}")
    if risks:
        raise SelectionError("complete make gate required for R-70 risk path(s): " + ", ".join(sorted(risks)))
    if unknown:
        raise SelectionError("no light-acceptance mapping for " + "; ".join(sorted(unknown)))
    for suite in suites:
        directory = ROOT / "tests" / "integration" / suite
        if not directory.is_dir() or not any(directory.rglob("test_*.py")):
            raise SelectionError(f"required integration suite unavailable or empty: {directory}")
    return Selection(tuple(sorted(suites)), screen)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)


def changed_paths(base: str) -> list[str]:
    if not FULL_SHA.fullmatch(base):
        raise SelectionError("BASE must be an explicit full 40-hex ancestor commit SHA")
    if git("cat-file", "-e", f"{base}^{{commit}}").returncode:
        raise SelectionError(f"BASE is not a commit: {base}")
    if git("merge-base", "--is-ancestor", base, "HEAD").returncode:
        raise SelectionError(f"BASE is not an ancestor of HEAD: {base}")
    dirty = git("status", "--porcelain", "--untracked-files=all")
    if dirty.returncode or dirty.stdout:
        raise SelectionError("measured tree is dirty; commit or remove all changes before light acceptance")
    diff = git("diff", "--name-status", "-z", f"{base}..HEAD")
    if diff.returncode:
        raise SelectionError(f"cannot inspect BASE..HEAD: {diff.stderr.strip()}")
    fields = diff.stdout.split("\0")
    paths: list[str] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status[0] in "RC":
            paths.extend(fields[i + 1 : i + 3])
            i += 3
        else:
            paths.append(fields[i + 1])
            i += 2
    return paths


def run(*argv: str) -> None:
    print("+ " + " ".join(argv), flush=True)
    try:
        result = subprocess.run(argv, cwd=ROOT)
    except OSError as error:
        raise SelectionError(f"required command unavailable: {argv[0]}: {error}") from error
    if result.returncode:
        raise SelectionError(f"check failed (exit {result.returncode}): {' '.join(argv)}")


def require_pytest(path: str) -> None:
    directory = ROOT / path
    if not directory.exists():
        raise SelectionError(f"required suite unavailable: {path}")
    if directory.is_dir() and not any(directory.rglob("test_*.py")):
        raise SelectionError(f"required suite empty: {path}")


def main() -> int:
    try:
        base = os.environ.get("LIGHT_ACCEPTANCE_BASE", "")
        paths = changed_paths(base)
        selected = classify(paths)
        python = ROOT / ".venv" / "bin" / "python"
        if not python.is_file():
            raise SelectionError("runtime interpreter .venv/bin/python is unavailable; run make bootstrap")
        if not (ROOT / "web" / "node_modules").is_dir():
            raise SelectionError("web/node_modules is unavailable in this checkout; run npm --prefix web ci")
        require_pytest("tests/contract")
        require_pytest("tests/e2e/test_pc01_journey_conformance.py")
        require_pytest("tests/contract/api_v1/test_doc_prose_facts.py")
        require_pytest("tests/contract/api_v1/test_surface_counts_in_prose.py")
        if selected.live_journey:
            origin = os.environ.get("E2E_PC01_ORIGIN", "")
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
                raise SelectionError("changed screen needs the lane's live PC01 stand: set E2E_PC01_ORIGIN to its loopback origin with port")
            if not os.environ.get("E2E_PC01_LOGIN") or not os.environ.get("E2E_PC01_PASSWORD"):
                raise SelectionError("changed screen needs E2E_PC01_LOGIN and E2E_PC01_PASSWORD for its lane stand")
        print(f"R-70 BASE={base}; changed paths={len(paths)}; integration={selected.integration_dirs}; live PC01={selected.live_journey}", flush=True)
        run("git", "diff", "--check", f"{base}..HEAD")
        run("npm", "--prefix", "web", "run", "lint", "--", "--quiet")
        run("npm", "--prefix", "web", "run", "typecheck")
        run("npm", "--prefix", "web", "test", "--", "--run")
        run(str(python), "-m", "pytest", "-c", "pyproject.toml", "--rootdir=.", "-q", "tests/contract",
            "--ignore=tests/contract/test_cp00_candidate.py",
            "--ignore=tests/contract/test_cp00_final_state.py",
            "--ignore=tests/contract/test_validate_bootstrap.py")
        run(str(python), "-m", "pytest", "-c", "pyproject.toml", "--rootdir=.", "-q",
            "tests/e2e/test_pc01_journey_conformance.py",
            "tests/contract/api_v1/test_doc_prose_facts.py",
            "tests/contract/api_v1/test_surface_counts_in_prose.py")
        for suite in selected.integration_dirs:
            run(str(python), "-m", "pytest", "-c", "pyproject.toml", "--rootdir=.", "-q", f"tests/integration/{suite}")
        if selected.live_journey:
            run("npm", "--prefix", "web", "run", "e2e:pc01", "--", "--phase", "all", "--origin", os.environ["E2E_PC01_ORIGIN"])
        print("LIGHT ACCEPTANCE OK", flush=True)
        return 0
    except SelectionError as error:
        print(f"LIGHT ACCEPTANCE REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
