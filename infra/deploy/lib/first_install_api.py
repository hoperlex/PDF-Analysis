#!/usr/bin/env python3
"""The two things a first install asks of the running stack through its loopback port: finish the administrator's account, and
make the imported norms snapshot the current one. For `infra/deploy/first-install.sh`; standard library only.

    first_install_api.py wait      --base URL [--seconds N]
    first_install_api.py admin     --base URL --password-file FILE --email ADDRESS
    first_install_api.py designate --base URL --password-file FILE [--content-key KEY]

`--base` is the stack's own loopback address, `http://127.0.0.1:<ALPHA_HTTP_PORT>/api/v1`. Nothing here leaves the host.

WHY AN `admin` ACCOUNT HAS TO BE FINISHED. The database is seeded with the published pair `admin` / `password`
(`access/policy.py`, `SHIPPED_DEFAULT_PASSWORD`). While it is valid the deploy ends `[default_credential]` (`R-146s`), and
while the profile is incomplete every operation but `getMe`, `updateMyProfile` and `changePassword` answers `403` with
`required_capability: profile_completed` -- the norms operations included (`STAND-NORMS-IMPORT-RUNBOOK-01.md` section 0
item 5). So `admin` changes its password (`POST /auth/password`) and then gives its names and an e-mail address
(`PATCH /me`), which becomes its login in the same write.

THE PASSWORD IS NEVER ON A COMMAND LINE, IN AN ENVIRONMENT OR IN OUTPUT. It is generated here, written first to the
password file (mode 600, created exclusively, outside the checkout) and only then sent, from this process's memory, in a request
body. The file holds two lines, `login=` and `password=`; a rerun reads it, so a run that died between the file and the
change, or between the change and the profile, continues instead of generating a second password.

Exit codes: 0 done; 2 usage; 20 the stack did not answer; 21 the administrator's password is neither the published one nor
the one in the file; 22 the stack refused (the line names the error code); 23 the edge rate-limited the sign-in and the
retries ran out; 24 an answer this script does not understand; 30 no qualified snapshot; 31 more than one candidate snapshot;
32 someone designated another snapshot first (`stale_current_snapshot`).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

PUBLISHED_LOGIN = "admin"
#: The password `0006_app_user` seeds; published in the repository, so naming it here leaks nothing.
PUBLISHED_PASSWORD = "password"  # noqa: S105
#: The profile an installer completes. They are placeholders for a person to change in the profile page; the e-mail is the
#: login and cannot be changed afterwards (`updateMyProfile`), which is why it is the owner's address and not invented.
LAST_NAME = "Администратор"
FIRST_NAME = "Системный"

EXIT_OK, EXIT_USAGE, EXIT_DOWN, EXIT_PASSWORD, EXIT_REFUSED, EXIT_RATE, EXIT_ODD = 0, 2, 20, 21, 22, 23, 24
EXIT_NO_SNAPSHOT, EXIT_AMBIGUOUS, EXIT_STALE = 30, 31, 32


class ApiError(Exception):
    """An answer the caller handles by status. Carries no request body and no credential."""

    def __init__(self, status: int, error_code: str = "", message: str = "", details: Mapping[str, Any] | None = None):
        super().__init__(f"{status} {error_code}")
        self.status = status
        self.error_code = error_code
        self.message = message
        self.details = dict(details or {})


class StackDown(Exception):
    """The loopback port did not answer at all."""


class Client:
    def __init__(self, base: str, *, timeout: float = 30.0, sleep: Callable[[float], None] = time.sleep):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.sleep = sleep
        # No proxy, whatever the environment says: this is the loopback interface.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None, token: str | None = None) -> Any:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise _api_error(error) from None
        except (urllib.error.URLError, OSError, TimeoutError):
            raise StackDown() from None
        try:
            return json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            raise ApiError(0, "unreadable_answer") from None

    def sign_in(self, login: str, password: str, *, attempts: int = 4, pause: float = 15.0) -> str | None:
        """A bearer token, or None when the pair is not valid. A `429` from the edge (six exchanges a minute) is waited out."""
        for attempt in range(attempts):
            try:
                answer = self.request("POST", "/auth/token", {"login": login, "password": password})
            except ApiError as error:
                if error.status == 401:
                    return None
                if error.status == 429 and attempt + 1 < attempts:
                    self.sleep(pause)
                    continue
                raise
            return str(answer["token"])
        return None


def _api_error(error: urllib.error.HTTPError) -> ApiError:
    code, message, details = "", "", {}
    try:
        envelope = json.loads(error.read().decode("utf-8"))
        code = str(envelope.get("error_code", ""))
        message = str(envelope.get("message", ""))[:200]
        details = envelope.get("details") or {}
    except (ValueError, AttributeError, OSError):
        pass
    return ApiError(error.code, code or f"http_{error.code}", message, details)


# ------------------------------------------------------------------------------------------------- the password file


def read_credentials(path: Path) -> tuple[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    fields = dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
    if not fields.get("login") or not fields.get("password"):
        raise ValueError(f"{path} is not a login/password file this script wrote")
    return fields["login"], fields["password"]


def _file_text(login: str, password: str) -> str:
    return (
        "# The administrator account of this installation. Written by first-install.sh; for the owner only.\n"
        "# Change the password in the application when you wish; this file then no longer states it.\n"
        f"login={login}\npassword={password}\n")


def ensure_credentials(path: Path, new_password: Callable[[], str]) -> tuple[str, str]:
    """The file's login and password, creating the file (exclusively, mode 600) when there is none."""
    existing = read_credentials(path)
    if existing is not None:
        return existing
    password = new_password()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(_file_text(PUBLISHED_LOGIN, password))
    return PUBLISHED_LOGIN, password


def write_login(path: Path, login: str, password: str) -> None:
    """Replace the file's login (the e-mail address replaces `admin` when the profile is completed), atomically, mode 600."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(_file_text(login, password))
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def generate_password() -> str:
    """43 characters of `A-Za-z0-9_-`: far above the policy's floor, with no character that needs quoting anywhere."""
    return secrets.token_urlsafe(32)


# ------------------------------------------------------------------------------------------------------- the commands


def wait_for_stack(client: Client, seconds: int) -> bool:
    """The proxy's own answer on a path that is closed behind a credential: 401 means the API is there (`deploy.sh`)."""
    deadline = time.monotonic() + seconds
    while True:
        try:
            client.request("GET", "/openapi.json")
        except ApiError as error:
            if error.status == 401:
                return True
        except StackDown:
            pass
        if time.monotonic() >= deadline:
            return False
        client.sleep(3)


def admin(client: Client, password_file: Path, email: str, say: Callable[[str], None]) -> int:
    try:
        login, password = ensure_credentials(password_file, generate_password)
    except (ValueError, OSError) as error:
        say(f"the password file cannot be used: {error}")
        return EXIT_ODD
    try:
        token = client.sign_in(PUBLISHED_LOGIN, PUBLISHED_PASSWORD)
        if token is not None:
            say("the administrator still has the published password: changing it")
            try:
                answer = client.request(
                    "POST", "/auth/password", {"current_password": PUBLISHED_PASSWORD, "new_password": password}, token)
            except ApiError as error:
                return _refused("changePassword", error, say)
            token = str(answer["token"])
            say("the administrator's password is changed; it is in the password file")
        else:
            token = client.sign_in(login, password)
            if token is None and login != email:
                token = client.sign_in(email, password)
            if token is None:
                say("the administrator's password is neither the published one nor the one in the password file")
                return EXIT_PASSWORD
            say("the administrator already has the password of the password file")
        try:
            me = client.request("GET", "/me", None, token)
            if not me.get("profile_complete"):
                me = client.request(
                    "PATCH", "/me", {"last_name": LAST_NAME, "first_name": FIRST_NAME, "email": email}, token)
                say("the administrator's profile is complete")
            else:
                say("the administrator's profile was already complete")
        except ApiError as error:
            return _refused("updateMyProfile", error, say)
    except StackDown:
        say("the stack did not answer on the loopback port")
        return EXIT_DOWN
    except ApiError as error:
        if error.status == 429:
            say("the edge rate-limits sign-in (six a minute); wait a minute and run again")
            return EXIT_RATE
        return _refused("sign-in", error, say)
    except (KeyError, TypeError):
        say("the stack answered in a shape this script does not know")
        return EXIT_ODD
    final_login = str(me.get("login") or email)
    if final_login != login:
        write_login(password_file, final_login, password)
    say(f"administrator login: {final_login}")
    return EXIT_OK


def _refused(operation: str, error: ApiError, say: Callable[[str], None]) -> int:
    extra = ""
    for key in ("reference_kind", "conflict_reason", "required_capability", "field"):
        if error.details.get(key):
            extra += f" {key}={error.details[key]}"
    say(f"{operation} was refused: {error.status} {error.error_code}{extra}: {error.message}")
    return EXIT_REFUSED


def _all_snapshots(client: Client, token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor = None
    for _ in range(50):
        path = "/norms/snapshots?limit=200" + (f"&cursor={cursor}" if cursor else "")
        page = client.request("GET", path, None, token)
        items.extend(page["items"])
        cursor = (page.get("page") or {}).get("next_cursor")
        if not cursor:
            break
    return items


def designate(client: Client, password_file: Path, content_key: str | None, say: Callable[[str], None]) -> int:
    try:
        credentials = read_credentials(password_file)
    except (ValueError, OSError) as error:
        say(f"the password file cannot be used: {error}")
        return EXIT_ODD
    if credentials is None:
        say("there is no administrator password file")
        return EXIT_PASSWORD
    try:
        token = client.sign_in(*credentials)
        if token is None:
            say("the administrator's password of the password file is not accepted")
            return EXIT_PASSWORD
        snapshots = _all_snapshots(client, token)
        if content_key:
            candidates = [item for item in snapshots if item["content_key"] == content_key]
        else:
            candidates = [item for item in snapshots if item["qualified"]]
        if not candidates:
            say(f"no snapshot matches ({len(snapshots)} loaded): " + "; ".join(
                f"{s['norms_snapshot_id']} build={s['build_state']} qualified={s['qualified']} current={s['current']}"
                for s in snapshots[:5]))
            return EXIT_NO_SNAPSHOT
        if len(candidates) > 1:
            say("more than one snapshot qualifies: " + ", ".join(s["norms_snapshot_id"] for s in candidates[:5]))
            return EXIT_AMBIGUOUS
        chosen = candidates[0]
        if chosen["current"]:
            say(f"{chosen['norms_snapshot_id']} is already the current norms snapshot")
            return EXIT_OK
        if not chosen["qualified"]:
            say(f"{chosen['norms_snapshot_id']} does not qualify yet: build_state={chosen['build_state']}")
            return EXIT_NO_SNAPSHOT
        current = next((s["norms_snapshot_id"] for s in snapshots if s["current"]), None)
        try:
            client.request("PUT", "/norms/snapshots/current",
                           {"norms_snapshot_id": chosen["norms_snapshot_id"], "expected_current": current}, token)
        except ApiError as error:
            if error.status == 409:
                say(f"another snapshot was designated first ({error.details.get('conflict_reason', 'conflict')})")
                return EXIT_STALE
            return _refused("setCurrentNormSnapshot", error, say)
        say(f"{chosen['norms_snapshot_id']} is now the current norms snapshot")
        return EXIT_OK
    except StackDown:
        say("the stack did not answer on the loopback port")
        return EXIT_DOWN
    except ApiError as error:
        return _refused("the norms call", error, say)
    except (KeyError, TypeError):
        say("the stack answered in a shape this script does not know")
        return EXIT_ODD


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="first_install_api.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_wait = sub.add_parser("wait")
    p_wait.add_argument("--base", required=True)
    p_wait.add_argument("--seconds", type=int, default=120)
    p_admin = sub.add_parser("admin")
    p_admin.add_argument("--base", required=True)
    p_admin.add_argument("--password-file", required=True)
    p_admin.add_argument("--email", required=True)
    p_designate = sub.add_parser("designate")
    p_designate.add_argument("--base", required=True)
    p_designate.add_argument("--password-file", required=True)
    p_designate.add_argument("--content-key")
    args = parser.parse_args(argv)

    def say(line: str) -> None:
        print(f"first_install_api: {line}", flush=True)

    client = Client(args.base)
    if args.command == "wait":
        return EXIT_OK if wait_for_stack(client, args.seconds) else EXIT_DOWN
    if args.command == "admin":
        return admin(client, Path(args.password_file), args.email, say)
    return designate(client, Path(args.password_file), args.content_key, say)


if __name__ == "__main__":
    sys.exit(main())
