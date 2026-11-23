#!/usr/bin/env python3
"""Find the ``claude`` and ``codex`` clients an account of the deploy server can run, for `local-agent.sh` (`LOCAL-AGENT-01`).

The host agent (``tools/executor-runner/detect.py``) looks for the two clients in a fixed list of directories: the account's
``~/.local/bin`` and ``~/.npm-global/bin``, then ``/usr/local/bin``, ``/usr/bin``, ``/bin``, ``/snap/bin`` -- or in the directories
``PDF_ANALYSIS_CLI_DIRS`` names. On a development machine that is also the deploy server the clients the owner is signed in to usually
live somewhere else: **inside the VS Code extensions** (``anthropic.claude-code-*`` ships ``claude``, ``openai.chatgpt-*`` ships
``codex``), under a directory whose name changes with every extension update. adm1 solved it by hand on 2026-11-10 with two wrapper
scripts in ``/opt/pdf-analysis-cli/bin`` that run the newest extension binary; this module writes exactly those wrappers.

For each client, in this order:

1. a binary inside a VS Code extension of the account (``~/.vscode-server/extensions`` or ``~/.vscode/extensions``) -- the one the
   owner actually uses and the extension keeps up to date -- gets a **wrapper** in the output directory that runs the newest such
   binary at the moment it is called, so an extension update needs nothing here;
2. otherwise a binary in one of the usual directories is used as it is, and a wrapper of ours left from an earlier run is removed;
3. otherwise the client is ``missing``.

Only a file that carries :data:`MARKER` is ever replaced or removed: anything else in the output directory is the operator's and is
left alone (and reported). Nothing is read from inside the extension but the existence of the binary; no login file is looked at --
whether a client is signed in is ``detect.py``'s question, asked as the account itself.

    python3 -I local_agent_clis.py --home /root --out /opt/pdf-analysis-cli/bin [--dry-run]

prints one line per client, ``<name> <extension|usual|missing> <path or ->``, and then one line per change, ``wrote <path>`` /
``removed <path>`` / ``kept <path> (not ours)``. Exit 0; 2 for a usage error (a home that is not a plain absolute path).
Standard library only.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

NAMES = ("claude", "codex")
#: The line that makes a file in the output directory ours; nothing without it is ever replaced or removed.
MARKER = "# local-agent.sh (LOCAL-AGENT-01): runs the newest binary of a VS Code extension."
#: The account's own directories ``detect.py`` searches, relative to its home.
HOME_SUBDIRS = (".local/bin", ".npm-global/bin")
SYSTEM_DIRS = ("/usr/local/bin", "/usr/bin", "/bin", "/snap/bin")
#: Where each client sits inside its extension, relative to the home (the platform part of the path is a wildcard).
EXTENSION_GLOBS = {
    "claude": (".vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
               ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude"),
    "codex": (".vscode-server/extensions/openai.chatgpt-*/bin/*/codex",
              ".vscode/extensions/openai.chatgpt-*/bin/*/codex"),
}
PLAIN_PATH = re.compile(r"^/[A-Za-z0-9._/-]*$")
_VERSION = re.compile(r"-(\d+(?:\.\d+)*)")


@dataclass(frozen=True)
class Found:
    name: str
    kind: str  # "extension", "usual" or "missing"
    path: Optional[str]
    patterns: tuple = ()  # the absolute globs that matched, for the wrapper (extension only)


def _executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def _version_key(path: str) -> tuple:
    """The extension's version from its directory name (``anthropic.claude-code-2.1.328-linux-x64`` -> ``(2, 1, 328)``)."""
    for part in Path(path).parts:
        if part.startswith(("anthropic.claude-code-", "openai.chatgpt-")):
            match = _VERSION.search(part)
            if match:
                return tuple(int(item) for item in match.group(1).split(".")), path
    return (), path


def find(name: str, home: str, system_dirs: Sequence[str] = SYSTEM_DIRS) -> Found:
    patterns = [os.path.join(home, pattern) for pattern in EXTENSION_GLOBS[name]]
    matched = [(pattern, path) for pattern in patterns for path in glob.glob(pattern) if _executable(path)]
    if matched:
        newest = max((path for _, path in matched), key=_version_key)
        used = tuple(dict.fromkeys(pattern for pattern, _ in matched))
        return Found(name, "extension", newest, used)
    for directory in [os.path.join(home, sub) for sub in HOME_SUBDIRS] + list(system_dirs):
        candidate = os.path.join(directory, name)
        if _executable(candidate):
            return Found(name, "usual", candidate)
    return Found(name, "missing", None)


def wrapper_text(found: Found) -> str:
    """A POSIX shell wrapper that runs the newest binary matching the extension globs when it is called."""
    patterns = " ".join(found.patterns)
    return (
        "#!/bin/sh\n"
        f"{MARKER}\n"
        "# Written for the deploy server's host agent; an extension update needs nothing here. Rewritten or removed by local-agent.sh.\n"
        f"bin=$(ls -1d {patterns} 2>/dev/null | sort -V | tail -n 1)\n"
        f'[ -n "$bin" ] || {{ echo "{found.name}: the VS Code extension that ships it is not installed any more" >&2; exit 127; }}\n'
        'exec "$bin" "$@"\n'
    )


def _ours(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding="utf-8", errors="replace").splitlines()[:3]
    except OSError:
        return False


def apply(out_dir: Path, found: Sequence[Found], *, dry_run: bool = False) -> "list[str]":
    """Write the wrapper of every client found in an extension, remove our wrapper of every other one. Returns the change lines."""
    changes: list[str] = []
    for item in found:
        target = out_dir / item.name
        if item.kind == "extension":
            text = wrapper_text(item)
            if target.exists() and not _ours(target):
                changes.append(f"kept {target} (not ours)")
                continue
            if target.exists() and target.read_text(encoding="utf-8", errors="replace") == text:
                continue
            changes.append(f"wrote {target}")
            if not dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(out_dir, 0o755)
                staged = out_dir / f".{item.name}.tmp"
                staged.write_text(text, encoding="utf-8")
                os.chmod(staged, 0o755)
                os.replace(staged, target)
        elif target.exists():
            if _ours(target):
                changes.append(f"removed {target}")
                if not dry_run:
                    target.unlink()
            else:
                changes.append(f"kept {target} (not ours)")
    return changes


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--home", required=True, help="the home directory of the account that holds the logins")
    parser.add_argument("--out", required=True, help="where the wrappers go (/opt/pdf-analysis-cli/bin)")
    parser.add_argument("--system-dirs", default=":".join(SYSTEM_DIRS), help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="say what would change and change nothing")
    args = parser.parse_args(argv)
    for value in (args.home, args.out):
        if not PLAIN_PATH.fullmatch(value) or value == "/":
            print(f"local_agent_clis.py: {value!r} is not a plain absolute path", file=sys.stderr)
            return 2
    system_dirs = [item for item in args.system_dirs.split(":") if item]
    found = [find(name, args.home.rstrip("/"), system_dirs) for name in NAMES]
    for item in found:
        print(f"{item.name} {item.kind} {item.path or '-'}")
    for line in apply(Path(args.out), found, dry_run=args.dry_run):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
