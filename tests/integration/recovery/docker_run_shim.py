#!/usr/bin/env python3
"""A `docker` on PATH that lets `infra/deploy/memory-setting.sh` and `memory-forget.sh` run their one-off container against a LANE stand (`D-511`).

`docker_shim.py` does this for the purge and needs the foundation's PostgreSQL container for `exec postgres`; the decision-memory wrappers never
exec into a container, they only run the module in a one-off `api` container, so this shim translates exactly the shapes they use and refuses the
rest with status 99 (a new docker call in a wrapper cannot pass unnoticed):

* ``compose ... run --rm --no-deps -T --user U -e PYTHONPATH=/app/src:/purge -v host:/purge/scripts/recovery/x.py:ro [-v dir:/dump]
  --entrypoint python api -m <module> <args>`` -> the repository's interpreter, in a sandbox that is built the way the container is: ONLY the
  files that were mounted exist under ``<sandbox>/purge``, the working directory holds nothing else, ``PYTHONPATH`` is the repository's ``src``
  plus that directory, and the environment is the container's (``DATABASE_URL`` from the environment of the compose process, which is where the
  wrapper puts the owner's url; ``S3_*`` from the ``--env-file``, which is where compose reads them; nothing else, so no ``PG*`` variable). A
  module that imports a file the wrapper did not mount fails here exactly as it fails in the image. Container paths in the arguments
  (``/dump``) are mapped back to the ``-v`` host paths;
* ``compose ... ps --status running --services`` -> the names in ``$SHIM_RUNNING`` (comma separated);
* ``compose ... stop ...`` and ``compose ... up ...`` -> recorded, not executed.

Every call is appended to ``$SHIM_LOG``. ``$SHIM_PRELUDE``, if set, is Python run before the module's ``run()`` in the same process, with the
module imported as ``m`` (to make a phase crash: ``m.delete_objects = ...``).

What this does NOT prove: that the real ``api`` image has ``/app/src`` and a Python that imports the closure, that ``docker compose`` accepts the
flags, that the operator's uid can read the mounts. Those need the production compose and its images (runbook sections 20 and 21 say so).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _log(argv: list[str]) -> None:
    with open(os.environ["SHIM_LOG"], "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": argv, "database_url": os.environ.get("DATABASE_URL", "<unset>")}) + "\n")


def _env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ")
        name, separator, value = line.partition("=")
        if separator and not name.startswith("#"):
            values[name.strip()] = value.strip().strip("\"'")
    return values


def main(argv: list[str]) -> int:
    _log(argv)
    if argv[:1] != ["compose"]:
        print(f"docker run shim: refuses a non-compose call: {' '.join(argv)}", file=sys.stderr)
        return 99
    args, env_file = argv[1:], ""
    while args and args[0] in ("--env-file", "--file"):
        if args[0] == "--env-file":
            env_file = args[1]
        args = args[2:]
    verb, rest = (args[0], args[1:]) if args else ("", [])
    if verb == "ps":
        assert rest == ["--status", "running", "--services"], rest
        print("\n".join(name for name in os.environ.get("SHIM_RUNNING", "").split(",") if name))
        return 0
    if verb in ("stop", "up"):
        return 0
    if verb != "run" or "--entrypoint" not in rest:
        print(f"docker run shim: refuses a compose call it does not know: {' '.join(argv)}", file=sys.stderr)
        return 99

    mounts: dict[str, str] = {}
    environment: dict[str, str] = {}
    index = 0
    while rest[index] != "--entrypoint":
        if rest[index] == "-v":
            host, container = rest[index + 1].split(":")[:2]
            mounts[container] = host
            index += 2
        elif rest[index] == "-e":
            name, _, value = rest[index + 1].partition("=")
            environment[name] = value
            index += 2
        elif rest[index] == "--user":
            index += 2
        else:
            index += 1
    assert rest[index + 1:index + 4] == ["python", "api", "-m"], rest
    module, tool_args = rest[index + 4], rest[index + 5:]
    assert environment.get("PYTHONPATH") == "/app/src:/purge", environment

    sandbox = Path(tempfile.mkdtemp(prefix="memory-ops-container-"))
    try:
        for container, host in mounts.items():
            if container.startswith("/purge/"):
                target = sandbox / container.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(host, target)
        repository = os.environ["SHIM_REPOSITORY"]
        configured = _env_file(env_file) if env_file else {}
        container_env = {"PATH": os.environ["PATH"], "HOME": str(sandbox), "PYTHONPATH": f"{repository}/src:{sandbox}/purge",
                         "DATABASE_URL": os.environ.get("DATABASE_URL") or configured.get("DATABASE_URL", "")}
        container_env.update({name: value for name, value in configured.items() if name.startswith("S3_")})
        translated = []
        for item in tool_args:
            for container, host in mounts.items():
                if item == container or item.startswith(container + "/"):
                    item = host + item[len(container):]
            translated.append(item)
        python = os.environ["SHIM_PYTHON"]
        prelude = os.environ.get("SHIM_PRELUDE")
        if prelude:
            command = [python, "-c", f"import sys, importlib\nm = importlib.import_module({module!r})\n{prelude}\nsys.exit(m.run(sys.argv[1:]))",
                       *translated]
        else:
            command = [python, "-m", module, *translated]
        return subprocess.call(command, env=container_env, cwd=sandbox)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
