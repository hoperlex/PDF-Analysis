"""A scratch deployment directory around one `infra/deploy/*.sh` operator wrapper, with a `docker` that records and answers (`D-511`).

`tests/integration/composition/test_erase_project_script.py` carries its own copy of this idea. The two decision-memory wrappers
(`memory-setting.sh`, `memory-forget.sh`) share this one, because their tests ask the same questions of the same plumbing: which guard
refused, did the refusal come before any `docker` call, what did the one-off container get (url, mounts, uid, stdin), and does a COPY OF THE
SCRIPT WITH ONE GUARD BLOCK DELETED stop refusing. Nothing here can touch a stand: `docker` is a stub on `PATH`.

The stub appends one JSON line per call to ``STUB_LOG`` (arguments, the ``DATABASE_URL`` of its environment, how much standard input it could
read) and answers from ``STUB_CONFIG``:

* the call that runs the tool (``... --entrypoint python api -m <tool> <args>``) answers ``config[kind]``, where ``kind`` is chosen by the
  wrapper's ``flavour`` from the tool's arguments; the answer is a dict (``stdout``, ``stderr``, ``status``, optionally ``write_manifest``)
  or a LIST of them, consumed one per call and the last one repeated;
* ``ps --status running --services`` answers ``config["running"]``; ``up`` succeeds and so does ``stop``, unless ``config["stop_status"]`` is a
  non-zero status (a ``compose stop`` that stopped some of the services and then failed, or was interrupted).
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "scripts/recovery"
#: What an operator may set to make the module wait longer for a lock; each wrapper hands its own to the container (`D-515`).
LOCK_TIMEOUT_VARIABLES = ("MEMORY_SETTING_LOCK_TIMEOUT", "MEMORY_FORGET_LOCK_TIMEOUT")

STUB = r'''#!{python}
import json, os, sys
argv = sys.argv[1:]
stdin_bytes = -1 if sys.stdin.isatty() else len(sys.stdin.buffer.read())
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps({
        "argv": argv,
        # What the one-off container would be given as DATABASE_URL: compose substitutes the environment of THIS process.
        "database_url": os.environ.get("DATABASE_URL", "<unset>"),
        "stdin_bytes": stdin_bytes,
    }) + "\n")
config = json.load(open(os.environ["STUB_CONFIG"]))
rest = argv
while rest and rest[0] in ("compose", "--env-file", "--file"):
    rest = rest[1:] if rest[0] == "compose" else rest[2:]
if rest[:1] == ["ps"]:
    if config.get("ps_status", 0):
        sys.stderr.write("docker stub: compose ps failed\n")
        sys.exit(config["ps_status"])
    sys.stdout.write("".join(name + "\n" for name in config.get("running", [])))
    sys.exit(0)
if rest[:1] == ["stop"] and config.get("stop_status", 0):
    sys.stderr.write("docker stub: compose stop failed (api stopped, worker did not)\n")
    sys.exit(config["stop_status"])
if rest[:1] in (["stop"], ["up"]):
    sys.exit(0)
tool = os.environ["STUB_TOOL"]
if tool in rest:
    args = rest[rest.index(tool) + 1:]
    if os.environ["STUB_FLAVOUR"] == "setting":
        kind = "set" if "set" in args else "show"
    else:
        kind = "apply" if "--apply" in args else "resume" if "--resume" in args else "plan"
    entry = config[kind]
    if isinstance(entry, list):
        counts_path = os.environ["STUB_CONFIG"] + ".counts"
        counts = json.load(open(counts_path)) if os.path.exists(counts_path) else {}
        seen = counts.get(kind, 0)
        counts[kind] = seen + 1
        json.dump(counts, open(counts_path, "w"))
        entry = entry[min(seen, len(entry) - 1)]
    written = entry.get("write_manifest")
    if written:
        mount = next(rest[i + 1][: -len(":/dump")] for i, item in enumerate(rest)
                     if item == "-v" and rest[i + 1].endswith(":/dump"))
        directory = os.path.join(mount, written["id"])
        os.makedirs(directory, exist_ok=True)
        open(os.path.join(directory, "manifest.json"), "w").write(written["text"])
        open(os.path.join(directory, "plan.json"), "w").write("{}")
    sys.stdout.write(entry.get("stdout", ""))
    sys.stdout.flush()
    sys.stderr.write(entry.get("stderr", ""))
    sys.exit(entry.get("status", 0))
sys.stderr.write("docker stub: no answer for: " + " ".join(argv) + "\n")
sys.exit(99)
'''


@dataclass(frozen=True)
class Wrapper:
    """What differs between the wrappers: the script, the tool it runs, how the stub tells its steps apart, the environment file."""

    script: Path
    tool: str  # e.g. "scripts.recovery.memory_forget"
    flavour: str  # "setting" or "forget"
    env_text: str
    module_env: str  # the environment variable that points the script at another scripts/recovery
    dump_env: str = "ALPHA_DUMP_ROOT"


class Rig:
    """A scratch deployment directory with the script, a compose file, an env file and a stub."""

    def __init__(self, tmp_path: Path, wrapper: Wrapper, *, source: str | None = None, module_dir: Path = MODULE_DIR,
                 compose: bool = True) -> None:
        self.tmp, self.wrapper, self.module_dir = tmp_path, wrapper, module_dir
        self.deploy = tmp_path / "deploy"
        self.deploy.mkdir(parents=True, exist_ok=True)
        self.script = self.deploy / wrapper.script.name
        self.script.write_text(source if source is not None else wrapper.script.read_text(encoding="utf-8"), encoding="utf-8")
        if compose:
            (self.deploy / "compose.server.yml").write_text(
                "services:\n  api:\n    image: x\n  worker:\n    image: x\n", encoding="utf-8")
        self.env_file = tmp_path / "alpha.env"
        self.env_file.write_text(wrapper.env_text, encoding="utf-8")
        self.bin = tmp_path / "bin"
        self.bin.mkdir(exist_ok=True)
        stub = self.bin / "docker"
        stub.write_text(STUB.replace("{python}", sys.executable), encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        self.log = tmp_path / "docker.log"
        self.config = tmp_path / "stub.json"
        self.dumps = tmp_path / "dumps"
        self.answers: dict[str, Any] = {}

    # --- mutants: the same rig around a copy of the script ----------------------------------------------------------

    def mutant(self, *guards: str) -> Rig:
        """A copy of the script with those guard blocks deleted."""
        source = self.wrapper.script.read_text(encoding="utf-8")
        for guard in guards:
            block = re.compile(rf"^( *)# >>> guard: {re.escape(guard)}\n.*?^\1# <<< guard: {re.escape(guard)}\n",
                               re.DOTALL | re.MULTILINE)
            source, count = block.subn("", source)
            assert count == 1, f"the guard markers for {guard!r} are not a single block"
        return self._copy_with(source)

    def edited(self, old: str, new: str) -> Rig:
        """A copy of the script in which one piece of text is replaced."""
        source = self.wrapper.script.read_text(encoding="utf-8")
        assert source.count(old) == 1, f"{old!r} is not exactly once in the script"
        return self._copy_with(source.replace(old, new))

    def _copy_with(self, source: str) -> Rig:
        rig = Rig(self.tmp / "mutant", self.wrapper, source=source, module_dir=self.module_dir,
                  compose=(self.deploy / "compose.server.yml").exists())
        rig.answers = self.answers
        return rig

    # --- running --------------------------------------------------------------------------------------------------

    def run(self, *args: str, env: dict[str, str] | None = None, typed: str = "") -> subprocess.CompletedProcess[str]:
        self.config.write_text(json.dumps(self.answers), encoding="utf-8")
        counts = Path(str(self.config) + ".counts")
        counts.unlink(missing_ok=True)
        environment = dict(os.environ)
        for ambient in LOCK_TIMEOUT_VARIABLES:  # an operator's shell must not decide what a test passes to the container (`D-515`)
            environment.pop(ambient, None)
        environment.update(
            PATH=f"{self.bin}{os.pathsep}{environment['PATH']}", ALPHA_ENV_FILE=str(self.env_file),
            ALPHA_DUMP_ROOT=str(self.dumps), STUB_LOG=str(self.log), STUB_CONFIG=str(self.config),
            STUB_TOOL=self.wrapper.tool, STUB_FLAVOUR=self.wrapper.flavour)
        environment[self.wrapper.module_env] = str(self.module_dir)
        environment.update(env or {})
        return subprocess.run(["bash", str(self.script), *args], capture_output=True, text=True, input=typed,
                              env=environment, timeout=120)

    # --- what the stub saw ----------------------------------------------------------------------------------------

    @property
    def records(self) -> list[dict[str, Any]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    @property
    def calls(self) -> list[str]:
        return [" ".join(record["argv"]) for record in self.records]

    def called(self, needle: str) -> bool:
        return any(needle in call for call in self.calls)

    def index(self, needle: str) -> int:
        return next(i for i, call in enumerate(self.calls) if needle in call)

    def tool_calls(self) -> list[dict[str, Any]]:
        return [r for r in self.records if self.wrapper.tool in r["argv"]]

    def tool_args(self, call: dict[str, Any]) -> list[str]:
        argv: list[str] = call["argv"]
        return argv[argv.index(self.wrapper.tool) + 1:]


def env_without(env_text: str, *names: str) -> str:
    return "".join(line for line in env_text.splitlines(keepends=True) if not line.startswith(tuple(f"{n}=" for n in names)))


def guard_names(script: Path) -> set[str]:
    return set(re.findall(r"^ *# >>> guard: ([a-z0-9-]+)$", script.read_text(encoding="utf-8"), re.MULTILINE))


def runbook_guards_text(section: int) -> str:
    """The text under ``### What the script's guards are`` in section ``section`` of ``DEPLOYMENT_RUNBOOK.md``."""
    text = (ROOT / "docs/program/DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    start = re.search(rf"^## {section}\. ", text, re.MULTILINE)
    assert start is not None, f"runbook section {section} is not there"
    rest = text[start.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    body = rest[: following.start()] if following else rest
    listing = re.search(r"^### What the script's guards are\n(.*?)(?=^### |\Z)", body, re.DOTALL | re.MULTILINE)
    assert listing is not None, f"runbook section {section} has no 'What the script's guards are'"
    return listing.group(1)


def guard_names_in(text: str) -> set[str]:
    """The guard names a runbook paragraph spells out: back-quoted words with a hyphen (a file or a module has a dot or an underscore)."""
    return set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`", text))


def modules_imported_by(module: str) -> set[str]:
    """The files of ``scripts/recovery`` that ``module`` needs, transitively, read from the source (``from scripts.recovery import x`` and
    ``from scripts.recovery.x import y``): the import closure a one-off container must have mounted."""
    seen: set[str] = set()
    todo = [module]
    pattern = re.compile(r"^\s*from scripts\.recovery(?:\.(\w+))? import (\w+)", re.MULTILINE)
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        source = (MODULE_DIR / f"{current}.py").read_text(encoding="utf-8")
        for submodule, name in pattern.findall(source):
            todo.append(submodule or name)
    return seen
