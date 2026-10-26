"""`HARDEN-01` / `F-03` (`EXPOSURE-REVIEW-02`, `D-235`): the `web` container does not hold the key that signs every
user credential, and nothing in `web/src` needs it to.

The finding: ``compose.server.yml`` handed ``AUDITMANAGER_API_TOKEN`` to the ``web`` service under the comment "the web
tier forwards it; without it every operation answers 401". The comment had been false since the bearer became a
per-session credential: ``getApiToken`` and ``hasServerCredential`` (``web/src/shared/config/server-env.ts``) have no
caller, and ``credentialed-forward.ts`` presents "a session's, never the deployment's signing key". With the key,
``am2.<payload>.<HMAC>`` for any known ``usr_`` id is minted offline, and roles are read from the row, so an ``admin``
uid is an administrator -- and the web tier is the container an internet visitor reaches first.

**Two halves, because the removal is only safe if both hold.** (1) No compose file under ``infra/`` gives the ``web``
service that variable, by ``environment`` or by ``env_file``; (2) no module under ``web/src`` calls the readers of it
or reads it. The second is what makes the first a repair and not an outage, and it is asserted here against the real
tree so that a later web change which starts to read the key fails THIS test (and the web guard) instead of failing
at run time with a missing variable in a container nobody is watching.

No docker: the service blocks are split by indentation, as the neighbours do (this venv has no YAML library).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VARIABLE = "AUDITMANAGER_API_TOKEN"

_spec = importlib.util.spec_from_file_location(
    "session_register_volume", ROOT / "tests/integration/composition/test_session_register_volume.py"
)
assert _spec is not None and _spec.loader is not None
_volume = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_volume)


def _without_comments(block: str) -> str:
    return "\n".join(line.split("  #", 1)[0] for line in block.splitlines() if not line.lstrip().startswith("#"))


def web_service_problems(compose_text: str) -> list[str]:
    """What is wrong with the ``web`` service of one compose file, in words. Empty when it holds no key."""
    blocks = _volume._service_blocks(compose_text)
    if "web" not in blocks:
        return []
    body = _without_comments(blocks["web"])
    problems: list[str] = []
    if VARIABLE in body:
        problems.append(f"the web service receives {VARIABLE}, the key that signs every user credential")
    if re.search(r"^\s*env_file\s*:", body, re.MULTILINE):
        problems.append("the web service takes an env_file, which would hand it the whole deployment environment")
    return problems


def _compose_files() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "infra").rglob("*.yml")
        if re.search(r"^services:\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    )


def test_no_compose_file_gives_the_web_service_the_signing_key() -> None:
    files = _compose_files()
    names = {path.name for path in files}
    assert "compose.server.yml" in names, "the walk found no compose files, so this passed over nothing"
    for path in files:
        assert web_service_problems(path.read_text(encoding="utf-8")) == [], str(path.relative_to(ROOT))


def test_the_control_the_api_service_still_receives_it() -> None:
    """If this goes quiet the check above reads the wrong thing: the key is still the API's, and only the API's."""
    blocks = _volume._service_blocks((ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8"))
    holders = sorted(name for name, block in blocks.items() if VARIABLE in _without_comments(block))
    assert holders == ["api"], holders


def test_the_web_service_is_still_given_what_it_does_need() -> None:
    """The removal took one variable; the upstream and the register path are what the web tier runs on."""
    blocks = _volume._service_blocks((ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8"))
    body = _without_comments(blocks["web"])
    assert "AUDITMANAGER_API_UPSTREAM: http://api:8000" in body
    assert "AUDITMANAGER_SESSION_STORE:" in body and "AUDITMANAGER_BEHIND_PROXY:" in body


def test_the_check_can_fail() -> None:
    """The variable put back on the web service, and an env_file, are each caught; a comment about it is not."""
    compose = (ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8")
    anchor = "      AUDITMANAGER_API_UPSTREAM: http://api:8000\n"
    assert compose.count(anchor) == 1
    put_back = compose.replace(anchor, anchor + f"      {VARIABLE}: ${{{VARIABLE}:?unset}}\n", 1)
    assert web_service_problems(put_back) == [f"the web service receives {VARIABLE}, the key that signs every user credential"]
    with_file = compose.replace(anchor, "    env_file: env/alpha.env\n" + anchor, 1)
    assert any("env_file" in problem for problem in web_service_problems(with_file))
    commented = compose.replace(anchor, anchor + f"      # {VARIABLE} was here\n", 1)
    assert web_service_problems(commented) == []


# ---- half two: nothing in web/src needs the key ---------------------------------------------------------------

#: A call, or a read of the variable, as opposed to the definition of the reader or a mention in prose.
_CALL = re.compile(r"\b(?:getApiToken|hasServerCredential)\s*\(")
_ENV_READ = re.compile(r"process\.env(?:\.|\[\s*['\"])" + VARIABLE)
_READER = "web/src/shared/config/server-env.ts"


def readers_of_the_signing_key(files: dict[str, str]) -> list[str]:
    """The files that call a reader of the key or read the variable, apart from the module that defines the readers."""
    found = []
    for path, text in sorted(files.items()):
        if path == _READER:
            continue
        if _CALL.search(text) or _ENV_READ.search(text):
            found.append(path)
    return found


def _web_sources() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "web/src").rglob("*"))
        if path.suffix in {".ts", ".tsx", ".mjs", ".js"} and path.is_file()
    }


def test_no_module_under_web_src_reads_the_signing_key() -> None:
    sources = _web_sources()
    assert len(sources) > 100 and _READER in sources, "the walk found too little of web/src to mean anything"
    assert readers_of_the_signing_key(sources) == []


def test_the_scan_can_fail() -> None:
    clean = {"web/src/a.ts": "const x = 1;\n", _READER: "export function getApiToken(): string { return ''; }\n"}
    assert readers_of_the_signing_key(clean) == []
    assert readers_of_the_signing_key({**clean, "web/src/b.ts": "const t = getApiToken();\n"}) == ["web/src/b.ts"]
    assert readers_of_the_signing_key({**clean, "web/src/c.ts": "if (hasServerCredential()) {}\n"}) == ["web/src/c.ts"]
    assert readers_of_the_signing_key({**clean, "web/src/d.ts": f"const t = process.env.{VARIABLE};\n"}) == ["web/src/d.ts"]
    assert readers_of_the_signing_key({**clean, "web/src/e.ts": f"const t = process.env['{VARIABLE}'];\n"}) == ["web/src/e.ts"]
    # a mention in prose, and an import of the name without a call, are not a read
    assert readers_of_the_signing_key({**clean, "web/src/f.ts": f"// {VARIABLE} is not read here; getApiToken is gone\n"}) == []
