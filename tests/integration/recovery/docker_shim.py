#!/usr/bin/env python3
"""A `docker` on PATH that lets `infra/deploy/purge-product-data.sh` run against a LANE stack.

`STAND-PURGE-TOOL-01`. The operator script reaches PostgreSQL and the bucket only through
`docker compose -f compose.server.yml`, against the `postgres` service and a one-off `api`
container. A lane has neither (it has the foundation PostgreSQL and MinIO, no deploy images), and
building the api image costs gigabytes this host does not have. So the test puts this file on PATH
as `docker` and it translates exactly the four shapes the script uses:

* `compose ... exec -T postgres <cmd>`        -> `docker exec -i <lane postgres container> <cmd>`
* `compose ... run ... --entrypoint python api -m scripts.recovery.product_purge <args>`
                                              -> the repository's interpreter, with the lane's
                                                 `DATABASE_URL`/`S3_*`, container paths
                                                 (`/dump`) mapped back to the `-v` host paths
* `compose ... stop worker` / `up -d ... worker` -> recorded, not executed

Everything else is refused with status 99, so a new docker call in the script cannot pass
unnoticed. Every call is appended to `$SHIM_LOG`. `$SHIM_FAIL`, if set, is a substring: a call
whose arguments contain it exits 1 without running (to drive the failure paths).

Nothing here weakens what is under test: the SQL, the S3 calls and the dump are real.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _log(text: str) -> None:
    with open(os.environ["SHIM_LOG"], "a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _lane_environment(path: str) -> dict[str, str]:
    values = {}
    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.strip().removeprefix("export ")
        name, separator, value = line.partition("=")
        if separator and not name.startswith("#"):
            values[name.strip()] = value.strip().strip("\"'")
    return values


def main(argv: list[str]) -> int:
    joined = " ".join(argv)
    _log(joined)
    fail = os.environ.get("SHIM_FAIL")
    if fail and fail in joined:
        print(f"docker shim: SHIM_FAIL matched {fail!r}", file=sys.stderr)
        return 1
    if argv[:1] != ["compose"]:
        print(f"docker shim: refuses a non-compose call: {joined}", file=sys.stderr)
        return 99
    args = argv[1:]
    while args and args[0] in ("--env-file", "--file"):
        args = args[2:]
    if not args:
        return 99
    verb, rest = args[0], args[1:]
    if verb == "stop" or (verb == "up" and rest and rest[-1] == "worker"):
        return 0
    if verb == "exec":
        assert rest[:2] == ["-T", "postgres"], rest
        return subprocess.call(
            [os.environ["SHIM_REAL_DOCKER"], "exec", "-i", os.environ["SHIM_POSTGRES_CONTAINER"], *rest[2:]]
        )
    if verb == "run" and "--entrypoint" in rest:
        mounts: dict[str, str] = {}
        index = 0
        while rest[index] != "--entrypoint":
            if rest[index] == "-v":
                host, container = rest[index + 1].split(":")[:2]
                mounts[container] = host
                index += 2
            elif rest[index] in ("-e", "--user"):
                index += 2
            else:
                index += 1
        assert rest[index + 1] == "python" and rest[index + 2] == "api", rest
        translated = []
        for item in rest[index + 3:]:
            for container, host in mounts.items():
                if item == container or item.startswith(container + "/"):
                    item = host + item[len(container):]
            translated.append(item)
        repository = os.environ["SHIM_REPOSITORY"]
        environment = dict(os.environ)
        environment.update(_lane_environment(os.environ["SHIM_LANE_ENV"]))
        environment["PYTHONPATH"] = f"{repository}/src:{repository}"
        return subprocess.call([os.environ["SHIM_PYTHON"], *translated], env=environment, cwd=repository)
    print(f"docker shim: refuses a compose call it does not know: {joined}", file=sys.stderr)
    return 99


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
