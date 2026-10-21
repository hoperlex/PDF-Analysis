"""`D-44`: the browser's pre-check limit must stay strictly below the application's cap for
the upload, and that cap strictly below nginx's.

**The invariant, and why it is not a taste.** The upload pre-check in
``web/src/entities/document-version/model/upload-envelope.ts`` refuses a file over its limit
in the browser, before any request is made. The application then caps the body of the upload
route (``UPLOAD_MAX_BODY`` in ``src/auditmanager/api/routers/multipart.py``) and answers an
oversized one with a typed ``ErrorEnvelope``. ``infra/deploy/proxy/nginx.conf`` and
``tls-server.conf`` raise ``client_max_body_size`` for the two upload locations only. The
gaps between the three numbers are the only reason a user never meets nginx's ``413`` --
and nginx's ``413`` is **an HTML page, not an ``ErrorEnvelope``**, so the upload screen would
classify it as ``transport`` and render *"The upload did not reach the API."*: a true
sentence naming the wrong cause.

Raise the pre-check past the application's cap, or the application's cap past nginx's,
without touching the other, and screens quietly become a generic transport failure. Nothing
in the tree recorded that dependency. This file is what records it:

    pre-check  <  UPLOAD_MAX_BODY  <  nginx's cap in each upload location

and, for every other route, ``MAX_BODY`` below nginx's server-wide default (which is not
raised for the upload: a large body is accepted on the two upload paths and on no other).

**What `W55B-INGEST-01` added: the envelope's own bound is the fourth term.** The admission
envelope (``MAX_BYTES`` in ``src/auditmanager/ingest/envelope.py``) judges the upload and
answers an oversized one with ``byte_size <= N``. It belongs between the pre-check and the
application's cap, because the browser must never *allow* a file the envelope refuses and the
transport must never refuse, with ``max_bytes``, a file the envelope would have judged:

    pre-check  <=  MAX_BYTES  <  UPLOAD_MAX_BODY  <  nginx's cap in each upload location

The pre-check may equal ``MAX_BYTES`` (both say 250 MiB once the browser's constant is raised)
and may not exceed it.

**What changed under `W55B-STREAM-01`.** There used to be one number on each side:
``maxBytes`` against the one ``client_max_body_size``. The upload route's cap moved to
251 MiB and nginx's to 260m in two locations, so the application's cap is now the middle term
and nginx has a default and two upload locations to read. The pre-check itself is still
25 MiB: `W55B-INGEST-01` raises it, and this file then holds it below the cap without being
edited. (`W55B-INGEST-01` raised the envelope to 250 MiB; the browser constant is the next
lane's.) The oversize stand-in is no longer a committed file -- it is a **sparse file
generated here, at test time** (``tools/fixtures/portal_bundle/generated.py``) and never
committed.

**Every number is READ from where it lives.** Restating any of them as a literal here would
mean editing this file at the next change, which is the failure mode itself -- ``D-23``'s
guard, ``tests/contract/api_v1/test_surface_counts_in_prose.py``, is the model, and
``OPERATING_CONSTRAINTS.md`` §12 is the rule. Nothing in this module may be edited to make
a raised limit pass: the only way to green it is to move the other end too, which is the
decision the invariant exists to force someone to make.

**This file READS the nginx files and never writes them.**

**Mutation-copy note.** Like the ``web/``-reading checks in
``test_pc01_journey_conformance.py``, the checks here that read the real tree cannot run
inside a ``make mutation-copy`` tree, which provides neither ``web/`` nor ``infra/``.
Exclude them by path there. The negative controls read nothing outside this file and run
anywhere.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ENVELOPE = (
    REPOSITORY_ROOT
    / "web"
    / "src"
    / "entities"
    / "document-version"
    / "model"
    / "upload-envelope.ts"
)
MULTIPART = REPOSITORY_ROOT / "src" / "auditmanager" / "api" / "routers" / "multipart.py"
ENVELOPE_PY = REPOSITORY_ROOT / "src" / "auditmanager" / "ingest" / "envelope.py"
PROXY = REPOSITORY_ROOT / "infra" / "deploy" / "proxy"
NGINX_CONFS = (PROXY / "nginx.conf", PROXY / "tls-server.conf")
FIXTURE_TOOLS = REPOSITORY_ROOT / "tools" / "fixtures"

#: The two locations that take the larger body, exactly as both nginx files write them.
UPLOAD_LOCATIONS = (
    "location ~ ^/api/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {",
    "location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {",
)
SERVER_SCOPE = "server {"
#: `HARDEN-AUTH-EDGE-01`. The two INTERNAL locations an upload location asks for the caller's
#: credential before it reads the body. A subrequest shares the request's headers, and nginx
#: compares the DECLARED length with the cap of the location it enters, so each must carry a
#: cap at least as large as the upload cap or the check answers 413 and the upload a 500.
CREDENTIAL_LOCATIONS = (
    "location = /_edge/credential/api {",
    "location = /_edge/credential/web {",
)

#: nginx's own size suffixes. No suffix is bytes; `k`, `m` and `g` are binary, which is
#: why a `260m` cap and a `250 MiB` pre-check are comparable at all.
_NGINX_UNITS = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}

#: The binary units `formatBytes` and `maxBytesLabel` use. The contract says MiB.
_BINARY_UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}

_MAX_BYTES = re.compile(r"\bmaxBytes:\s*([0-9_ *]+?)\s*,")
_MAX_BYTES_LABEL = re.compile(r"\bmaxBytesLabel:\s*['\"]([^'\"]+)['\"]")
_CLIENT_MAX_BODY_SIZE = re.compile(r"\bclient_max_body_size\s+(\d+)([kKmMgG]?)\s*;")
_LABEL = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB)\s*$")
#: ``UPLOAD_MAX_BODY: Final[int] = 251 * 1024 * 1024`` -- the name at the start of the line,
#: so the same words in a docstring or a comment are not read as the definition.
_API_LIMIT = re.compile(
    r"^(MAX_BODY|UPLOAD_MAX_BODY)\s*:\s*Final\[int\]\s*=\s*([0-9_ *]+?)\s*(?:#.*)?$",
    re.MULTILINE,
)


def _product(text: str, what: str) -> int:
    """A product of integer literals, evaluated. Anything else is refused, not guessed at."""
    factors = [part.strip().replace("_", "") for part in text.split("*")]
    if not all(part.isdigit() for part in factors):
        raise AssertionError(
            f"{what} reads {text!r}, which is not a product of integer literals. "
            "D-44's guard must read the real number; widen this parser deliberately "
            "rather than letting it fall back to anything."
        )
    value = 1
    for part in factors:
        value *= int(part)
    return value


def precheck_max_bytes(source: str) -> int:
    """The pre-check's limit, read out of the TypeScript the browser actually runs.

    ``maxBytes: 25 * 1024 * 1024`` is a product of integers and is evaluated as one.
    Anything else -- a call, a name, an import -- is refused rather than guessed at: a
    parser that silently returns a wrong number is worse than no parser, because the
    comparison below would then be green about nothing.
    """
    found = _MAX_BYTES.findall(source)
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one `maxBytes:` in the upload envelope, found {len(found)}. "
            "The pre-check's limit is what D-44 compares, and this guard will not guess "
            "which of several is it."
        )
    return _product(found[0], "`maxBytes`")


def precheck_max_bytes_label(source: str) -> str:
    found = _MAX_BYTES_LABEL.findall(source)
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one `maxBytesLabel:`, found {len(found)}. It is the "
            "sentence the screen shows and the refusal half requires."
        )
    return found[0]


def bytes_of_label(label: str) -> int:
    """``'25 MiB'`` -> ``26214400``. Binary units only, as the contract states them."""
    match = _LABEL.match(label)
    if match is None:
        raise AssertionError(
            f"{label!r} is not a binary byte size. The screen's own words have to be a "
            f"quantity this guard can compare, one of {sorted(_BINARY_UNITS)}."
        )
    return round(float(match.group(1)) * _BINARY_UNITS[match.group(2)])


#: ``MAX_BYTES: Final[int] = 250 * 1024 * 1024`` -- the name at the start of the line, as above.
_ENVELOPE_LIMIT = re.compile(
    r"^MAX_BYTES\s*:\s*Final\[int\]\s*=\s*([0-9_ *]+?)\s*(?:#.*)?$", re.MULTILINE
)


def envelope_max_bytes(source: str) -> int:
    """The admission envelope's size bound, read out of the module that enforces it."""
    found = _ENVELOPE_LIMIT.findall(source)
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one definition of `MAX_BYTES` in envelope.py, found {len(found)}. "
            "The envelope's bound is what the pre-check and the transport are held around."
        )
    return _product(found[0], "`MAX_BYTES`")


def api_body_limits(source: str) -> dict[str, int]:
    """``MAX_BODY`` and ``UPLOAD_MAX_BODY``, read out of the module that enforces them."""
    found: dict[str, list[str]] = {"MAX_BODY": [], "UPLOAD_MAX_BODY": []}
    for name, expression in _API_LIMIT.findall(source):
        found[name].append(expression)
    for name, expressions in found.items():
        if len(expressions) != 1:
            raise AssertionError(
                f"expected exactly one definition of `{name}` in multipart.py, found "
                f"{len(expressions)}. Two caps would make the effective limit depend on "
                "which one a reader finds first."
            )
    return {name: _product(expressions[0], f"`{name}`") for name, expressions in found.items()}


def uncommented(conf: str) -> str:
    """The config with `#` comments removed, line by line.

    Measured, and this is why the directive is not anchored to the start of a line: a
    guard that anchors misses ``server { client_max_body_size 4m; }`` written inline, and
    a guard that does not strip comments reads a commented-out directive as the cap. The
    first of those two was a real hole in this file's first draft and only running the
    control found it.
    """
    return "\n".join(line.split("#", 1)[0] for line in conf.splitlines())


def body_caps(conf: str) -> list[tuple[str, int]]:
    """Every ``client_max_body_size`` as ``(the block it sits in, bytes)``, in file order.

    The block is the innermost enclosing ``location`` or ``server`` header with its spacing
    collapsed, or the empty string at the top of the file. Read with a brace scanner rather
    than line by line, so an inline ``server { client_max_body_size 4m; }`` is found in the
    block it is in.
    """
    text = uncommented(conf)
    scopes: list[str] = []
    found: list[tuple[str, int]] = []
    header_start = 0
    for index, char in enumerate(text):
        if char == "{":
            scopes.append(" ".join(text[header_start : index + 1].split()))
            header_start = index + 1
        elif char == "}":
            if scopes:
                scopes.pop()
            header_start = index + 1
        elif char == ";":
            statement = text[header_start : index + 1]
            header_start = index + 1
            match = _CLIENT_MAX_BODY_SIZE.search(statement)
            if match:
                digits, suffix = match.groups()
                found.append(
                    (scopes[-1] if scopes else "", int(digits) * _NGINX_UNITS[suffix.lower()])
                )
    return found


def nginx_limits(conf: str) -> tuple[int, dict[str, int]]:
    """``(the server-wide default, {upload location: its cap})`` for one nginx file.

    A cap anywhere else is refused: it would make the effective limit of some request depend
    on which block serves it, and `D-44` is about the effective limit. A missing cap, a
    repeated one and an upload location without one are refused for the same reason.
    """
    caps = body_caps(conf)
    default = [value for scope, value in caps if scope == SERVER_SCOPE]
    if len(default) != 1:
        raise AssertionError(
            f"expected exactly one server-wide `client_max_body_size`, found {len(default)}. "
            "More than one means the cap of an ordinary route depends on which block serves it."
        )
    stray = [
        scope
        for scope, _ in caps
        if scope != SERVER_SCOPE and scope not in UPLOAD_LOCATIONS and scope not in CREDENTIAL_LOCATIONS
    ]
    if stray:
        raise AssertionError(
            f"`client_max_body_size` is set in {stray}, which is neither the server nor an "
            "upload location; the effective cap of that block would not be the one D-44 reads."
        )
    uploads: dict[str, int] = {}
    for location in UPLOAD_LOCATIONS:
        values = [value for scope, value in caps if scope == location]
        if not values:
            raise AssertionError(
                f"`{location}` sets no `client_max_body_size`, so it takes the server's "
                "default and a bundle would meet nginx's 413."
            )
        if len(values) > 1:
            raise AssertionError(
                f"`{location}` sets `client_max_body_size` {len(values)} times; the "
                "effective cap there is ambiguous."
            )
        uploads[location] = values[0]
    declared = " ".join(uncommented(conf).split())
    for location in CREDENTIAL_LOCATIONS:
        if location not in declared:
            continue
        values = [value for scope, value in caps if scope == location]
        if len(values) != 1 or values[0] < max(uploads.values()):
            raise AssertionError(
                f"`{location}` must set `client_max_body_size` once, to at least the upload "
                f"cap {max(uploads.values())}; it sets {values}. The credential check is a "
                "subrequest that re-reads the declared length against this cap, and a smaller "
                "one answers 413 to the check and 500 to every legitimate upload."
            )
    return default[0], uploads


def _read(path: Path) -> str:
    """An absent input fails, never skips. A skip here would report headroom it never read."""
    if not path.exists():
        pytest.fail(
            f"{path} is missing, so this check would prove nothing. Inside a "
            "`make mutation-copy` tree this is expected -- that target provides neither "
            "web/ nor infra/ -- and the real-tree checks here must be excluded by "
            "path rather than read as reds."
        )
    return path.read_text(encoding="utf-8")


def headroom_problems(
    precheck: int, api: dict[str, int], nginx: tuple[int, dict[str, int]]
) -> list[str]:
    """Everything wrong with the chain, so the controls can run the very function the real
    check does."""
    problems: list[str] = []
    default, uploads = nginx
    if not precheck < api["UPLOAD_MAX_BODY"]:
        problems.append(
            f"the pre-check refuses at {precheck} bytes and the application accepts an upload "
            f"body of up to {api['UPLOAD_MAX_BODY']}: a file between them is refused by the "
            "server, not by the browser, and the screen is not the one the refusal half names"
        )
    for location, cap in uploads.items():
        if not api["UPLOAD_MAX_BODY"] < cap:
            problems.append(
                f"the application accepts an upload body of up to {api['UPLOAD_MAX_BODY']} "
                f"bytes and `{location}` accepts up to {cap}, so a body between them is "
                "refused by nginx with an HTML 413 and no ErrorEnvelope"
            )
    if not api["MAX_BODY"] < default:
        problems.append(
            f"every other route takes up to {api['MAX_BODY']} bytes of body and nginx's "
            f"server-wide default is {default}: a body between them meets nginx's HTML 413 "
            "instead of the application's typed refusal"
        )
    if default >= api["UPLOAD_MAX_BODY"]:
        problems.append(
            f"the server-wide default {default} reaches the upload cap "
            f"{api['UPLOAD_MAX_BODY']}: the larger cap is meant for the two upload "
            "locations and for nothing else"
        )
    return problems


def envelope_problems(precheck: int, envelope: int, api: dict[str, int]) -> list[str]:
    """The envelope's place in the chain: ``precheck <= MAX_BYTES < UPLOAD_MAX_BODY``."""
    problems: list[str] = []
    if not precheck <= envelope:
        problems.append(
            f"the pre-check lets a file of up to {precheck} bytes through and the envelope "
            f"refuses anything over {envelope}: the browser would send what the server then "
            "refuses, and the refusal half of the journey would be about the wrong rule"
        )
    if not envelope < api["UPLOAD_MAX_BODY"]:
        problems.append(
            f"the envelope judges uploads of up to {envelope} bytes and the transport accepts a "
            f"body of up to {api['UPLOAD_MAX_BODY']}: a file over the envelope's bound could "
            "never reach it, and would be refused by the transport with `max_bytes` instead"
        )
    return problems


# --------------------------------------------------------------------------------------
# Against the real tree.
# --------------------------------------------------------------------------------------


def _real_chain() -> tuple[int, dict[str, int], list[tuple[str, tuple[int, dict[str, int]]]]]:
    precheck = precheck_max_bytes(_read(UPLOAD_ENVELOPE))
    api = api_body_limits(_read(MULTIPART))
    nginx = [(path.name, nginx_limits(_read(path))) for path in NGINX_CONFS]
    return precheck, api, nginx


def test_the_browser_refuses_an_oversize_upload_before_the_server_ever_could() -> None:
    """`D-44`. Strictly below, not below-or-equal: equal means a cap-sized file races."""
    precheck, api, nginx = _real_chain()
    for name, limits in nginx:
        problems = headroom_problems(precheck, api, limits)
        assert not problems, (
            f"{name}: " + "; ".join(problems) + ". nginx's 413 carries an HTML page and no "
            "ErrorEnvelope, so the upload screen classifies it as `transport` and tells the "
            "user 'The upload did not reach the API.' -- true, and the wrong cause. D-44. "
            "Either move the pre-check, `UPLOAD_MAX_BODY` or `client_max_body_size`; do not "
            "edit this test."
        )


def test_the_envelope_sits_between_the_precheck_and_the_transport() -> None:
    """`W55B-INGEST-01`: the fourth term of the chain, read from `ingest/envelope.py`."""
    precheck = precheck_max_bytes(_read(UPLOAD_ENVELOPE))
    api = api_body_limits(_read(MULTIPART))
    envelope = envelope_max_bytes(_read(ENVELOPE_PY))
    problems = envelope_problems(precheck, envelope, api)
    assert not problems, "; ".join(problems) + ". D-44. Move one end; do not edit this test."


def test_both_nginx_files_say_the_same_about_size() -> None:
    """The TLS body is a copy of the plain one; a cap that drifted would be a cap the
    tunnelled stand does not have."""
    _, _, nginx = _real_chain()
    assert nginx[0][1] == nginx[1][1], (
        f"nginx.conf and tls-server.conf disagree on the body caps: {nginx}"
    )


def test_the_limit_the_screen_shows_is_the_limit_the_screen_enforces() -> None:
    """The label is not decoration: the refusal half requires the screen to render it.

    ``manifest.json``'s oversize case requires the words ``25 MiB`` on screen. If
    `maxBytes` moved and `maxBytesLabel` did not, the browser would refuse at one number
    while naming another, and the refusal would stop being actionable.
    """
    source = _read(UPLOAD_ENVELOPE)
    limit = precheck_max_bytes(source)
    label = precheck_max_bytes_label(source)
    assert bytes_of_label(label) == limit, (
        f"the pre-check refuses above {limit} bytes and the screen says {label!r}, which "
        f"is {bytes_of_label(label)} bytes. The user is told a rule the application does "
        "not enforce."
    )


def generated_oversize(directory: Path, size: int) -> Path:
    """The oversize stand-in: a sparse file made now, by the fixture tools, and never kept.

    Imported by path, as the other tests that use ``tools/fixtures`` do: it is on no import
    path and the root ``pyproject`` is a single-owner hotspot.
    """
    if not FIXTURE_TOOLS.is_dir():
        pytest.fail(f"{FIXTURE_TOOLS} is missing, so there is no stand-in to generate.")
    if str(FIXTURE_TOOLS) not in sys.path:
        sys.path.insert(0, str(FIXTURE_TOOLS))
    from portal_bundle import generated

    return generated.oversize_sparse_file(directory / "oversize.stand-in", size)


def test_the_oversize_stand_in_sits_in_the_gap_the_invariant_protects(tmp_path: Path) -> None:
    """The file that proves the invariant is the one the invariant has to cover.

    The smallest file the browser refuses -- one byte past its pre-check -- is generated,
    sparse, and must still be inside what the application accepts and what nginx accepts.
    That verdict holds only while the file is *above* the pre-check limit, and its being
    *below* both caps is what makes it a test of the pre-check rather than of the server's
    own refusal: were the pre-check ever removed, this file would meet the application's
    typed envelope, not nginx's HTML 413.
    """
    precheck, api, nginx = _real_chain()
    size = precheck + 1
    stand_in = generated_oversize(tmp_path, size)
    status = stand_in.stat()
    assert status.st_size == size
    assert status.st_blocks * 512 < size // 2, (
        f"the stand-in occupies {status.st_blocks * 512} bytes of disk for a length of "
        f"{size}: it was allocated, not sparse, so a test that makes it costs what it claims "
        "to represent"
    )
    assert size > precheck, "the stand-in is not over the pre-check, so the browser would accept it"
    assert size < api["UPLOAD_MAX_BODY"], (
        f"the stand-in is {size} bytes and the application's upload cap is "
        f"{api['UPLOAD_MAX_BODY']}: it would meet `max_bytes`, not the envelope's own refusal"
    )
    for name, (_, uploads) in nginx:
        for location, cap in uploads.items():
            assert size < cap, (
                f"{name}: the stand-in is {size} bytes and `{location}` accepts up to {cap}; "
                "it would meet nginx's 413 rather than the server's typed refusal"
            )


# --------------------------------------------------------------------------------------
# The negative controls. Each proves one check above can go red, and each reads nothing
# outside this file, so they run in a mutation copy and anywhere else.
# --------------------------------------------------------------------------------------

_ENVELOPE_LIKE = """
export const PC01_UPLOAD_ENVELOPE = {
  fileCount: 1,
  mediaType: 'application/pdf',
  maxBytes: 25 * 1024 * 1024,
  maxBytesLabel: '25 MiB',
  maxPages: 30,
} as const;
"""

_API_LIKE = '''
"""The transport's limits. MAX_BODY: Final[int] = 1 in a docstring is not a definition."""

MAX_BODY: Final[int] = 26 * 1024 * 1024
UPLOAD_MAX_BODY: Final[int] = 251 * 1024 * 1024  # a 250 MiB bundle and its framing
'''

_CONF_LIKE = """
server {
    listen 8080;
    # 32m leaves the refusal where the contract puts it.
    client_max_body_size 32m;

    location ~ ^/api/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {
        client_max_body_size 260m;
        proxy_pass http://api:8000;
    }

    location ~ ^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$ {
        client_max_body_size 260m;
        proxy_pass http://web:3000;
    }
}
"""


def _chain(envelope: str = _ENVELOPE_LIKE, api: str = _API_LIKE, conf: str = _CONF_LIKE):
    return precheck_max_bytes(envelope), api_body_limits(api), nginx_limits(conf)


def test_control_the_parsers_really_read_their_own_formats() -> None:
    assert precheck_max_bytes(_ENVELOPE_LIKE) == 26214400
    assert precheck_max_bytes_label(_ENVELOPE_LIKE) == "25 MiB"
    assert api_body_limits(_API_LIKE) == {
        "MAX_BODY": 27262976,
        "UPLOAD_MAX_BODY": 263192576,
    }
    default, uploads = nginx_limits(_CONF_LIKE)
    assert default == 33554432
    assert sorted(uploads.values()) == [272629760, 272629760]
    assert headroom_problems(*_chain()) == []


def test_control_a_raised_precheck_is_detected() -> None:
    """`D-44`'s own mutation, moved one hop in: the pre-check reaches the application's cap."""
    for raised in ("251 * 1024 * 1024", "300 * 1024 * 1024"):
        envelope = _ENVELOPE_LIKE.replace("25 * 1024 * 1024", raised)
        assert headroom_problems(*_chain(envelope=envelope)), raised


_ENVELOPE_PY_LIKE = '''
"""MAX_BYTES: Final[int] = 1 in a docstring is not a definition."""

MAX_BYTES: Final[int] = 250 * 1024 * 1024
'''


def test_control_the_envelope_bound_is_read_and_the_chain_around_it_can_fail() -> None:
    assert envelope_max_bytes(_ENVELOPE_PY_LIKE) == 262144000
    api = api_body_limits(_API_LIKE)
    assert envelope_problems(26214400, 262144000, api) == []
    assert envelope_problems(262144000, 262144000, api) == []            # equal is allowed
    assert envelope_problems(262144001, 262144000, api), "a pre-check above the envelope"
    assert envelope_problems(26214400, 263192576, api), "an envelope at the transport's cap"
    assert envelope_problems(26214400, 300 * 1024 * 1024, api), "an envelope past it"
    for unreadable in (
        _ENVELOPE_PY_LIKE.replace("250 * 1024 * 1024", "ENVELOPE_MIB * 1024 * 1024"),
        _ENVELOPE_PY_LIKE.replace("MAX_BYTES: Final[int] = 250 * 1024 * 1024", ""),
        _ENVELOPE_PY_LIKE + "MAX_BYTES: Final[int] = 5 * 1024 * 1024\n",
    ):
        with pytest.raises(AssertionError):
            envelope_max_bytes(unreadable)


def test_control_a_raised_application_cap_is_detected() -> None:
    """The cap past nginx's, or equal to it: the typed refusal would be nginx's HTML one."""
    for raised in ("260 * 1024 * 1024", "512 * 1024 * 1024"):
        api = _API_LIKE.replace("251 * 1024 * 1024", raised)
        assert headroom_problems(*_chain(api=api)), raised


def test_control_a_lowered_application_cap_is_detected() -> None:
    api = _API_LIKE.replace("251 * 1024 * 1024", "25 * 1024 * 1024")
    assert headroom_problems(*_chain(api=api))


_CREDENTIAL_LIKE = """
    location = /_edge/credential/api {
        internal;
        client_max_body_size 260m;
        proxy_pass http://api:8000/me;
    }
"""


def test_control_the_credential_locations_are_part_of_the_chain() -> None:
    """`HARDEN-AUTH-EDGE-01`: a credential location is allowed, and only with the upload cap."""
    with_credential = _CONF_LIKE.replace("    location ~ ^/bff", _CREDENTIAL_LIKE + "\n    location ~ ^/bff", 1)
    assert with_credential != _CONF_LIKE
    assert nginx_limits(with_credential) == nginx_limits(_CONF_LIKE)
    for broken in (
        with_credential.replace("client_max_body_size 260m;\n        proxy_pass http://api:8000/me;",
                                "proxy_pass http://api:8000/me;"),
        with_credential.replace("client_max_body_size 260m;\n        proxy_pass http://api:8000/me;",
                                "client_max_body_size 32m;\n        proxy_pass http://api:8000/me;"),
        with_credential.replace("client_max_body_size 260m;\n        proxy_pass http://api:8000/me;",
                                "client_max_body_size 260m;\n        client_max_body_size 260m;\n        proxy_pass http://api:8000/me;"),
    ):
        assert broken != with_credential
        with pytest.raises(AssertionError):
            nginx_limits(broken)


def test_control_a_lowered_nginx_upload_cap_is_detected() -> None:
    """The invariant has two ends, and the guard must not be blind to the other one."""
    for lowered, expected in (("200m", 209715200), ("251m", 263192576), ("257024k", 263192576)):
        conf = _CONF_LIKE.replace("client_max_body_size 260m;", f"client_max_body_size {lowered};")
        _, uploads = nginx_limits(conf)
        assert set(uploads.values()) == {expected}
        assert headroom_problems(*_chain(conf=conf)), lowered
    # and the unit is read: 262144k is 256 MiB, which is still above the application's cap
    conf = _CONF_LIKE.replace("client_max_body_size 260m;", "client_max_body_size 262144k;")
    assert set(nginx_limits(conf)[1].values()) == {268435456}
    assert headroom_problems(*_chain(conf=conf)) == []


def test_control_one_lowered_upload_location_is_detected() -> None:
    """Both locations are read: the tunnelled stand's browser path is one of them."""
    conf = _CONF_LIKE.replace(
        "client_max_body_size 260m;\n        proxy_pass http://web:3000;",
        "client_max_body_size 100m;\n        proxy_pass http://web:3000;",
    )
    assert headroom_problems(*_chain(conf=conf))


def test_control_a_server_default_that_swallowed_the_upload_cap_is_detected() -> None:
    """Raising the server-wide default instead of the two locations is the lazy fix."""
    conf = _CONF_LIKE.replace("client_max_body_size 32m;", "client_max_body_size 260m;")
    assert headroom_problems(*_chain(conf=conf))


def test_control_an_ordinary_route_cap_above_nginx_default_is_detected() -> None:
    api = _API_LIKE.replace("MAX_BODY: Final[int] = 26 * 1024 * 1024", "MAX_BODY: Final[int] = 40 * 1024 * 1024")
    assert headroom_problems(*_chain(api=api))


def test_control_a_label_that_stopped_matching_its_limit_is_detected() -> None:
    stale = _ENVELOPE_LIKE.replace("maxBytes: 25 * 1024 * 1024", "maxBytes: 30 * 1024 * 1024")
    assert precheck_max_bytes_label(stale) == "25 MiB"
    assert bytes_of_label("25 MiB") != precheck_max_bytes(stale)


def test_control_an_unreadable_limit_fails_rather_than_defaulting() -> None:
    """`unreadable-class-excludes-nothing`: a number this guard cannot read is not a pass."""
    for unreadable in (
        _ENVELOPE_LIKE.replace("maxBytes: 25 * 1024 * 1024", "maxBytes: MAX_UPLOAD_BYTES"),
        _ENVELOPE_LIKE.replace("maxBytes: 25 * 1024 * 1024", "maxBytes: mib(25)"),
        _ENVELOPE_LIKE.replace("  maxBytes: 25 * 1024 * 1024,\n", ""),
    ):
        with pytest.raises(AssertionError):
            precheck_max_bytes(unreadable)

    for unreadable_api in (
        _API_LIKE.replace("251 * 1024 * 1024", "UPLOAD_LIMIT_MIB * 1024 * 1024"),
        _API_LIKE.replace("UPLOAD_MAX_BODY: Final[int] = 251 * 1024 * 1024", ""),
        _API_LIKE + "UPLOAD_MAX_BODY: Final[int] = 5 * 1024 * 1024\n",
    ):
        with pytest.raises(AssertionError):
            api_body_limits(unreadable_api)

    for unreadable_conf in (
        _CONF_LIKE.replace("    client_max_body_size 32m;\n", ""),
        _CONF_LIKE.replace("        client_max_body_size 260m;\n        proxy_pass http://api:8000;", "        proxy_pass http://api:8000;"),
    ):
        with pytest.raises(AssertionError):
            nginx_limits(unreadable_conf)
    for nonsense in ("lots", "25 megabytes", "", "MiB"):
        with pytest.raises(AssertionError):
            bytes_of_label(nonsense)


def test_control_a_commented_out_directive_is_not_read_as_the_cap() -> None:
    """A guard that reads a comment as configuration reports headroom nobody deployed."""
    commented = _CONF_LIKE.replace(
        "    client_max_body_size 32m;", "    # client_max_body_size 32m;"
    )
    with pytest.raises(AssertionError):
        nginx_limits(commented)
    # and a comment beside a live directive must not hide it, nor be counted twice
    beside = _CONF_LIKE.replace(
        "    client_max_body_size 32m;",
        "    client_max_body_size 32m;  # see D-44: strictly above the application's cap",
    )
    assert nginx_limits(beside)[0] == 33554432


def test_control_a_cap_in_another_block_is_not_missed() -> None:
    """**Found by running the controls**, not by reading the regex.

    The first draft anchored the directive to the start of a line, so a second cap written
    inline -- ``server { client_max_body_size 4m; }``, which nginx accepts -- was invisible
    and the guard reported headroom that was not the effective one. A cap in a block that is
    neither the server nor one of the two upload locations means the effective limit of that
    block is not one D-44 reads, so the guard refuses to pick.
    """
    for stray in (
        "\nserver { client_max_body_size 4m; }\n",
        "\nlocation /bff/ { client_max_body_size 1m; }\n",
        "\nserver {\n    location / {\n        client_max_body_size 1m;\n    }\n}\n",
    ):
        with pytest.raises(AssertionError):
            nginx_limits(_CONF_LIKE + stray)
    # and a second cap at the same level is a second server-wide cap
    with pytest.raises(AssertionError):
        nginx_limits(_CONF_LIKE.replace("    listen 8080;", "    listen 8080;\n    client_max_body_size 8m;"))


def test_control_a_missing_input_fails_rather_than_skips(tmp_path: Path) -> None:
    with pytest.raises(pytest.fail.Exception) as caught:
        _read(tmp_path / "absent.conf")
    assert "would prove nothing" in str(caught.value)
