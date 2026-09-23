"""`W34-API` -- the body that replaced the static token, tested where it can be measured.

Everything here runs against :mod:`auditmanager.api.security` alone: no database, no
object store, no application. That is deliberate. The seam's *placement* -- which
operations it guards, what shape the refusal has -- is asserted through a served
application in ``tests/integration/api/test_authorization.py``; what is asserted here is
the thing the wave replaced: **that a credential this deployment did not mint, or minted
too long ago, is not a credential**.

Three properties get more than one case each, because each is a way the seam could look
right and be useless:

* **the tag is over the payload, and a caller cannot rewrite one without the other.** A
  credential whose subject was edited is refused; so is one whose expiry was pushed out.
  Both are what a caller holding their own credential would try first;
* **the key is this deployment's.** A well-formed credential minted with another secret is
  refused, and so is the deployment secret itself -- the alpha's static token, which was a
  credential until this wave and is the signing material now;
* **the expiry is checked against a clock the caller does not supply.** The lifetime comes
  back in the response as a *duration*, so the two sides never have to agree on a reading.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import pathlib
import time
from typing import Any

import pytest

from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    TOKEN_LIFETIME_SECONDS,
    UNAUTHENTICATED_OPERATIONS,
    Subject,
    TokenSigner,
    build_signer,
    derive_signing_key,
)

SECRET = "a-deployment-secret-for-this-suite"
OTHER_SECRET = "another-deployments-secret"
#: The subject this suite mints for.
#:
#: ``token_epoch`` is 4 and deliberately not 1: `W39-REVOKE` made the epoch part of the
#: payload, and a suite that always minted at the initial value would pass equally against
#: an implementation that dropped the field and defaulted to it.
SUBJECT = Subject(user_uid="usr_01M2545JSD15ETSNNV904X991Q", login="ada", token_epoch=4)


@pytest.fixture
def signer() -> TokenSigner:
    built = build_signer({API_TOKEN_VARIABLE: SECRET})
    assert built is not None
    return built


def _parts(token: str) -> tuple[str, str, str]:
    version, body, tag = token.split(".")
    return version, body, tag


def _payload(token: str) -> dict[str, Any]:
    body = _parts(token)[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def _reseal(token: str, payload: dict[str, Any]) -> str:
    """The same credential with a rewritten payload and its original tag."""
    version, _, tag = _parts(token)
    body = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    return f"{version}.{body}.{tag}"


# =======================================================================================
# It is a credential at all
# =======================================================================================


def test_a_minted_credential_names_the_subject_it_was_minted_for(signer: TokenSigner) -> None:
    issued = signer.issue(SUBJECT)
    assert signer.verify(issued.token) == SUBJECT


def test_the_response_carries_a_lifetime_and_not_a_clock_reading(signer: TokenSigner) -> None:
    """``expires_in`` is a duration, so no clock has to agree between the two sides."""
    issued = signer.issue(SUBJECT, now=1_000_000)
    assert issued.expires_in == TOKEN_LIFETIME_SECONDS
    later = signer.issue(SUBJECT, now=2_000_000)
    assert later.expires_in == issued.expires_in
    assert later.token != issued.token, "two mintings at different times are two credentials"


def test_the_payload_carries_the_subject_and_nothing_else(signer: TokenSigner) -> None:
    """No password, no digest, no role, no salt -- and the list is closed, not sampled.

    ``sorted(payload)`` rather than "the fields I thought of": a field added later is
    reported here, which is the only kind of assertion that can catch the credential
    growing a claim nobody agreed to.

    **It worked.** `W39-REVOKE` added ``ver`` and this assertion is what reported it, which
    is the whole reason the list is written out rather than sampled. ``ver`` is the account's
    credential generation at the moment of minting -- the one field on this payload the seam
    checks against the *database* rather than against the key, and therefore the one that
    makes a credential retractable. It is not a claim about the subject and grants nothing:
    a caller who reads it learns how many times that account has been revoked.
    """
    payload = _payload(signer.issue(SUBJECT).token)
    assert sorted(payload) == ["exp", "iat", "login", "sub", "ver"], payload
    assert payload["ver"] == SUBJECT.token_epoch, (
        "the credential must carry the epoch it was minted under, not a constant: a "
        "hard-coded 1 here would verify against every account that had never been revoked "
        "and fail against every one that had"
    )
    assert payload["sub"] == SUBJECT.user_uid
    assert payload["login"] == SUBJECT.login
    assert payload["exp"] - payload["iat"] == TOKEN_LIFETIME_SECONDS


def test_the_credential_is_url_safe_and_header_shaped(signer: TokenSigner) -> None:
    """It travels in an HTTP header, so it may contain nothing that has to be escaped."""
    token = signer.issue(SUBJECT).token
    assert token.count(".") == 2
    assert all(
        character.isalnum() or character in "-._" for character in token
    ), token


# =======================================================================================
# It expires
# =======================================================================================


def test_a_credential_is_refused_one_second_after_its_lifetime(signer: TokenSigner) -> None:
    minted_at = 1_700_000_000
    token = signer.issue(SUBJECT, now=minted_at).token
    assert signer.verify(token, now=minted_at) == SUBJECT
    assert signer.verify(token, now=minted_at + TOKEN_LIFETIME_SECONDS - 1) == SUBJECT
    assert signer.verify(token, now=minted_at + TOKEN_LIFETIME_SECONDS) is None
    assert signer.verify(token, now=minted_at + TOKEN_LIFETIME_SECONDS + 1) is None


def test_the_expiry_is_read_from_the_credential_and_not_from_the_signer() -> None:
    """A signer whose lifetime changed still honours what it already minted.

    The expiry travels *in* the credential, so raising or lowering
    :data:`TOKEN_LIFETIME_SECONDS` does not retroactively extend or revoke anything a
    previous process issued -- which is what would happen if verification recomputed the
    expiry from the current constant.
    """
    minted_at = 1_700_000_000
    short = TokenSigner(derive_signing_key(SECRET), lifetime_seconds=60)
    token = short.issue(SUBJECT, now=minted_at).token

    long = TokenSigner(derive_signing_key(SECRET), lifetime_seconds=86_400)
    assert long.verify(token, now=minted_at + 59) == SUBJECT
    assert long.verify(token, now=minted_at + 61) is None


def test_the_default_clock_is_the_real_one(signer: TokenSigner) -> None:
    """The ``now`` parameter is for tests; with it absent the credential is live now."""
    issued = signer.issue(SUBJECT)
    assert signer.verify(issued.token) == SUBJECT
    assert _payload(issued.token)["exp"] > time.time()


# =======================================================================================
# It is this deployment's, and it has not been edited
# =======================================================================================


def test_a_credential_minted_with_another_secret_is_refused(signer: TokenSigner) -> None:
    other = build_signer({API_TOKEN_VARIABLE: OTHER_SECRET})
    assert other is not None
    foreign = other.issue(SUBJECT).token
    assert other.verify(foreign) == SUBJECT, "the case is only a case if it is valid there"
    assert signer.verify(foreign) is None


def test_the_deployment_secret_is_not_itself_a_credential(signer: TokenSigner) -> None:
    """The alpha's static token, presented to the seam that replaced it.

    Until this wave the configured string *was* the credential, and every runbook, deploy
    script and operator note carries it. If it still opened the surface, the replacement
    would be a second door rather than a new one.
    """
    assert signer.verify(SECRET) is None
    assert signer.verify(f"am1.{SECRET}") is None
    assert signer.verify(derive_signing_key(SECRET).hex()) is None


@pytest.mark.parametrize(
    ("label", "edit"),
    [
        ("another subject", {"sub": "usr_01M2545JSD15ETSNNV904X991Z"}),
        ("another login", {"login": "root"}),
        ("a later expiry", {"exp": 4_000_000_000}),
        ("an earlier issue time", {"iat": 0}),
    ],
    ids=["subject", "login", "expiry", "issued-at"],
)
def test_an_edited_payload_is_refused(
    signer: TokenSigner, label: str, edit: dict[str, Any]
) -> None:
    """Each edit is one a holder of a real credential would actually try."""
    token = signer.issue(SUBJECT).token
    payload = _payload(token) | edit
    edited = _reseal(token, payload)
    assert edited != token, label
    assert signer.verify(edited) is None, label


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("one character removed", lambda token: token[:-1]),
        ("one character added", lambda token: token + "x"),
        ("the tag replaced by another credential's", lambda token: token),  # filled below
        ("no tag at all", lambda token: ".".join(token.split(".")[:2])),
        ("an extra field", lambda token: token + ".extra"),
        ("an unknown format version", lambda token: "am2" + token[3:]),
        ("an empty string", lambda token: ""),
        ("a tag that is not base64", lambda token: ".".join(token.split(".")[:2]) + ".!!!!"),
    ],
    ids=["short", "long", "swapped-tag", "no-tag", "extra-field", "version", "empty", "not-base64"],
)
def test_a_credential_that_is_not_one_is_refused(
    signer: TokenSigner, label: str, mutate: Any
) -> None:
    token = signer.issue(SUBJECT).token
    if label == "the tag replaced by another credential's":
        other_tag = signer.issue(
            Subject(user_uid="usr_01M2545JSD15ETSNNV904X991Z", login="bob", token_epoch=4)
        ).token.split(".")[2]
        version, body, _ = _parts(token)
        presented = f"{version}.{body}.{other_tag}"
    else:
        presented = mutate(token)
    assert signer.verify(presented) is None, label


def test_the_payload_is_not_parsed_before_the_tag_is_checked(
    signer: TokenSigner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged credential's bytes never reach this module's parser.

    Not a micro-optimisation: ``json.loads`` over attacker-chosen bytes is a decoder an
    unauthenticated caller gets to drive. The order is an assertion rather than a comment
    because it is invisible in the answer -- both orders refuse the same way.
    """
    import auditmanager.api.security as security

    calls: list[Any] = []
    real = security.json.loads

    def counting(*args: Any, **kwargs: Any) -> Any:
        calls.append(args[:1])
        return real(*args, **kwargs)

    monkeypatch.setattr(security.json, "loads", counting)

    version, body, tag = _parts(signer.issue(SUBJECT).token)
    forged = f"{version}.{body}.{tag[:-2]}xy"
    assert signer.verify(forged) is None
    assert calls == [], "the payload was parsed although the tag had not verified"

    assert signer.verify(f"{version}.{body}.{tag}") == SUBJECT
    assert len(calls) == 1, "and the real one is parsed exactly once"


# =======================================================================================
# The key, and the absence of one
# =======================================================================================


def test_the_signing_key_is_derived_and_is_not_the_configured_secret() -> None:
    """Domain separation, stated as the value it must equal rather than as a property."""
    key = derive_signing_key(SECRET)
    assert key != SECRET.encode("utf-8")
    assert key == hmac.new(
        SECRET.encode("utf-8"), b"auditmanager/api/token-signing/v1", hashlib.sha256
    ).digest()
    assert len(key) == 32


def test_two_secrets_that_differ_by_one_character_derive_different_keys() -> None:
    assert derive_signing_key(SECRET) != derive_signing_key(SECRET + "x")


def test_surrounding_whitespace_in_the_configured_secret_is_not_a_second_deployment() -> None:
    """``AUDITMANAGER_API_TOKEN=" s "`` is the same deployment as ``"s"``.

    A shell that kept a trailing newline would otherwise be a deployment whose credentials
    stop verifying after a restart, which is a failure nobody would attribute to a space.
    """
    assert derive_signing_key(f"  {SECRET}\n") == derive_signing_key(SECRET)


@pytest.mark.parametrize("secret", ["", "   ", "\n\t "], ids=["empty", "spaces", "whitespace"])
def test_an_unconfigured_deployment_builds_no_signer(secret: str) -> None:
    """No key, no signer -- and every caller of :func:`build_signer` treats that as refusal."""
    assert build_signer({API_TOKEN_VARIABLE: secret}) is None
    assert build_signer({}) is None
    with pytest.raises(ValueError):
        derive_signing_key(secret)


def test_a_signer_refuses_to_exist_with_a_lifetime_that_is_already_over() -> None:
    with pytest.raises(ValueError):
        TokenSigner(derive_signing_key(SECRET), lifetime_seconds=0)
    with pytest.raises(ValueError):
        TokenSigner(b"", lifetime_seconds=60)


# =======================================================================================
# What the module is not allowed to do
# =======================================================================================


def test_the_tag_is_compared_in_constant_time() -> None:
    """Read off the source, because timing is not measurable on a shared runner.

    ``==`` over a digest returns at the first differing byte, and enough attempts recover
    the tag one byte at a time. The same rule `W34-DOM` holds ``verify_password`` to.
    """
    source = pathlib.Path("src/auditmanager/api/security.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in source
    assert "presented_tag ==" not in source
    assert "== self._tag" not in source


def test_the_register_of_open_operations_holds_only_the_exchange() -> None:
    """The one place an operation can be exempted, pinned as a literal.

    A test that read the register and compared it to itself would pass whatever was in it.
    This is the sentence an owner would have to read and agree with.
    """
    assert UNAUTHENTICATED_OPERATIONS == frozenset({"issueToken"})


def test_the_module_states_no_token_format_in_anything_a_caller_reads() -> None:
    """`T-6`: the format is the deployment's, and the document must stay silent about it.

    The contract half is `W34-CONTRACT`'s to guard. This is the half on this side: the
    scheme this module hands FastAPI carries no ``bearerFormat``, whatever the body behind
    it became.
    """
    from auditmanager.api.security import bearer_scheme

    emitted = bearer_scheme.model.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert emitted["type"] == "http"
    assert emitted["scheme"] == "bearer"
    assert "bearerFormat" not in emitted, emitted
