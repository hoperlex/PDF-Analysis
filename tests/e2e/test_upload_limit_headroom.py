"""`D-44`: the browser's pre-check limit must stay strictly below nginx's body cap.

**The invariant, and why it is not a taste.** The upload pre-check in
``web/src/entities/document-version/model/upload-envelope.ts`` refuses a file over
25 MiB in the browser, before any request is made. ``infra/deploy/proxy/nginx.conf`` sets
``client_max_body_size`` to 32m. The gap between them is the only reason a user never
meets nginx's ``413`` -- and nginx's ``413`` is **an HTML page, not an ``ErrorEnvelope``**,
so the upload screen would classify it as ``transport`` and render *"The upload did not
reach the API."*: a true sentence naming the wrong cause.

Raise the pre-check to 32 MiB without touching nginx and three of the six refusal screens
`W27-REFUSE` measured quietly become a generic transport failure. Nothing in the tree
recorded that dependency. This file is what records it.

**Why it lives in ``tests/e2e/``.** The invariant is a claim of the PC-01 journey, not of
the API contract and not of the composition root. ``manifest.json``'s refusal half
declares ``oversize.pdf`` is ``refused_by: client``, and that declaration is true exactly
while this headroom holds. Put the guard next to the claim it protects.

**Both numbers are READ from where they live.** Restating either as a literal here would
mean editing this file at the next change, which is the failure mode itself -- ``D-23``'s
guard, ``tests/contract/api_v1/test_surface_counts_in_prose.py``, is the model, and
``OPERATING_CONSTRAINTS.md`` §12 is the rule. Nothing in this module may be edited to make
a raised limit pass: the only way to green it is to move nginx too, which is the decision
the invariant exists to force someone to make.

**This file READS ``infra/deploy/proxy/nginx.conf`` and never writes it.**

**Mutation-copy note.** Like the ``web/``-reading checks in
``test_pc01_journey_conformance.py``, the three checks here that read the real tree cannot
run inside a ``make mutation-copy`` tree, which provides neither ``web/`` nor ``infra/``.
Exclude them by path there. The negative controls read nothing outside this file and run
anywhere.
"""

from __future__ import annotations

import re
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
NGINX_CONF = REPOSITORY_ROOT / "infra" / "deploy" / "proxy" / "nginx.conf"
OVERSIZE_FIXTURE = (
    REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "negative" / "oversize.pdf"
)

#: nginx's own size suffixes. No suffix is bytes; `k`, `m` and `g` are binary, which is
#: why a `32m` cap and a `25 MiB` pre-check are comparable at all.
_NGINX_UNITS = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}

#: The binary units `formatBytes` and `maxBytesLabel` use. The contract says MiB.
_BINARY_UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}

_MAX_BYTES = re.compile(r"\bmaxBytes:\s*([0-9_ *]+?)\s*,")
_MAX_BYTES_LABEL = re.compile(r"\bmaxBytesLabel:\s*['\"]([^'\"]+)['\"]")
_CLIENT_MAX_BODY_SIZE = re.compile(r"\bclient_max_body_size\s+(\d+)([kKmMgG]?)\s*;")
_LABEL = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB)\s*$")


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
    factors = [part.strip().replace("_", "") for part in found[0].split("*")]
    if not all(part.isdigit() for part in factors):
        raise AssertionError(
            f"`maxBytes` reads {found[0]!r}, which is not a product of integer literals. "
            "D-44's guard must read the real number; widen this parser deliberately "
            "rather than letting it fall back to anything."
        )
    value = 1
    for part in factors:
        value *= int(part)
    return value


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


def uncommented(conf: str) -> str:
    """The config with `#` comments removed, line by line.

    Measured, and this is why the directive is not anchored to the start of a line: a
    guard that anchors misses ``server { client_max_body_size 4m; }`` written inline, and
    a guard that does not strip comments reads a commented-out directive as the cap. The
    first of those two was a real hole in this file's first draft and only running the
    control found it.
    """
    return "\n".join(line.split("#", 1)[0] for line in conf.splitlines())


def nginx_body_limit(conf: str) -> int:
    """``client_max_body_size 32m;`` -> ``33554432``, read out of the served config."""
    found = _CLIENT_MAX_BODY_SIZE.findall(uncommented(conf))
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one `client_max_body_size` directive, found {len(found)}. "
            "More than one means the effective cap depends on which block serves the "
            "upload, and D-44 is about the effective cap."
        )
    digits, suffix = found[0]
    return int(digits) * _NGINX_UNITS[suffix.lower()]


def _read(path: Path) -> str:
    """An absent input fails, never skips. A skip here would report headroom it never read."""
    if not path.exists():
        pytest.fail(
            f"{path} is missing, so this check would prove nothing. Inside a "
            "`make mutation-copy` tree this is expected -- that target provides neither "
            "web/ nor infra/ -- and the three real-tree checks here must be excluded by "
            "path rather than read as reds."
        )
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------
# Against the real tree.
# --------------------------------------------------------------------------------------


def test_the_browser_refuses_an_oversize_upload_before_nginx_ever_could() -> None:
    """`D-44`. Strictly below, not below-or-equal: equal means a cap-sized file races."""
    precheck = precheck_max_bytes(_read(UPLOAD_ENVELOPE))
    proxy = nginx_body_limit(_read(NGINX_CONF))
    assert precheck < proxy, (
        f"the upload pre-check refuses at {precheck} bytes and nginx accepts up to "
        f"{proxy} bytes, so a file between them reaches nginx and is refused by it. "
        "nginx's 413 carries an HTML page and no ErrorEnvelope, so the upload screen "
        "classifies it as `transport` and tells the user 'The upload did not reach the "
        "API.' -- true, and the wrong cause. D-44. Either lower the pre-check or raise "
        "`client_max_body_size` in infra/deploy/proxy/nginx.conf; do not edit this test."
    )


def test_the_limit_the_screen_shows_is_the_limit_the_screen_enforces() -> None:
    """The label is not decoration: the refusal half requires the screen to render it.

    ``manifest.json``'s `oversize.pdf` case requires the words `25 MiB` on screen. If
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


def test_the_oversize_fixture_sits_in_the_gap_the_invariant_protects() -> None:
    """The fixture that proves the invariant is the one the invariant has to cover.

    `W27-REFUSE` drove `oversize.pdf` and measured a client-side refusal. That verdict
    holds only while the file is above the pre-check limit -- and the file's being *below*
    nginx's cap is what makes it a test of the pre-check rather than a test of nginx.
    """
    if not OVERSIZE_FIXTURE.exists():
        pytest.fail(f"{OVERSIZE_FIXTURE} is missing; the size refusal drives nothing.")
    size = OVERSIZE_FIXTURE.stat().st_size
    precheck = precheck_max_bytes(_read(UPLOAD_ENVELOPE))
    proxy = nginx_body_limit(_read(NGINX_CONF))
    assert size > precheck, (
        f"oversize.pdf is {size} bytes and the pre-check refuses above {precheck}. The "
        "browser would accept it, and manifest.json's `refused_by: client` for that case "
        "is false."
    )
    assert size < proxy, (
        f"oversize.pdf is {size} bytes and nginx accepts up to {proxy}. Were the "
        "pre-check ever removed, this fixture would meet nginx's 413 rather than the "
        "server's typed refusal, and would stop measuring what it claims to."
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

_CONF_LIKE = """
server {
    listen 8080;
    # 32m leaves the refusal where the contract puts it.
    client_max_body_size 32m;
}
"""


def test_control_the_two_parsers_really_read_their_own_formats() -> None:
    assert precheck_max_bytes(_ENVELOPE_LIKE) == 26214400
    assert nginx_body_limit(_CONF_LIKE) == 33554432
    assert precheck_max_bytes_label(_ENVELOPE_LIKE) == "25 MiB"


def test_control_a_raised_precheck_is_detected() -> None:
    """The exact mutation `D-44` names: 25 MiB -> 32 MiB, nginx untouched."""
    raised = _ENVELOPE_LIKE.replace("maxBytes: 25 * 1024 * 1024", "maxBytes: 32 * 1024 * 1024")
    assert precheck_max_bytes(raised) == nginx_body_limit(_CONF_LIKE)
    assert not precheck_max_bytes(raised) < nginx_body_limit(_CONF_LIKE)
    # and one byte past it, so `<=` would not have caught the equal case either
    over = _ENVELOPE_LIKE.replace("maxBytes: 25 * 1024 * 1024", "maxBytes: 64 * 1024 * 1024")
    assert not precheck_max_bytes(over) < nginx_body_limit(_CONF_LIKE)


def test_control_a_lowered_nginx_cap_is_detected() -> None:
    """The invariant has two ends, and the guard must not be blind to the other one."""
    for lowered, expected in (("16m", 16777216), ("8388608", 8388608), ("16384k", 16777216)):
        conf = _CONF_LIKE.replace("client_max_body_size 32m;", f"client_max_body_size {lowered};")
        assert nginx_body_limit(conf) == expected
        assert not precheck_max_bytes(_ENVELOPE_LIKE) < nginx_body_limit(conf)


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

    with pytest.raises(AssertionError):
        nginx_body_limit(_CONF_LIKE.replace("client_max_body_size 32m;", ""))
    for nonsense in ("lots", "25 megabytes", "", "MiB"):
        with pytest.raises(AssertionError):
            bytes_of_label(nonsense)


def test_control_a_commented_out_directive_is_not_read_as_the_cap() -> None:
    """A guard that reads a comment as configuration reports headroom nobody deployed."""
    commented = _CONF_LIKE.replace(
        "    client_max_body_size 32m;", "    # client_max_body_size 32m;"
    )
    with pytest.raises(AssertionError):
        nginx_body_limit(commented)
    # and a comment beside a live directive must not hide it, nor be counted twice
    beside = _CONF_LIKE.replace(
        "    client_max_body_size 32m;",
        "    client_max_body_size 32m;  # see D-44: strictly above the pre-check",
    )
    assert nginx_body_limit(beside) == 33554432


def test_control_a_second_cap_in_another_block_is_not_missed() -> None:
    """**Found by running the controls**, not by reading the regex.

    The first draft anchored the directive to the start of a line, so a second cap written
    inline -- ``server { client_max_body_size 4m; }``, which nginx accepts -- was invisible
    and the guard reported headroom that was not the effective one. Two caps mean the
    effective limit depends on which block serves the upload, and `D-44` is about the
    effective limit, so the guard refuses to pick.
    """
    for second in (
        "\nserver { client_max_body_size 4m; }\n",
        "\nserver {\n    client_max_body_size 4m;\n}\n",
        "\nlocation /bff/ { client_max_body_size 1m; }\n",
    ):
        with pytest.raises(AssertionError) as caught:
            nginx_body_limit(_CONF_LIKE + second)
        assert "found 2" in str(caught.value)


def test_control_a_missing_input_fails_rather_than_skips(tmp_path: Path) -> None:
    with pytest.raises(pytest.fail.Exception) as caught:
        _read(tmp_path / "absent.conf")
    assert "would prove nothing" in str(caught.value)
