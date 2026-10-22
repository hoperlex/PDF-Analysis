"""Sealed secrets: X25519 + HKDF-SHA256 + AES-256-GCM, bound to the place they were entered for.

`EXEC-SEAL-01`, plan sections 4.1 and 4.2. The ``api`` process holds **public keys only**: it
seals a secret on write and can never open one. The ``worker`` holds the private ring and is
the only process that uses a secret. A stolen admin session or a compromised ``api`` can
therefore *replace* a secret but cannot *read* one.

The envelope is ``version (1 byte) | ephemeral public key (32) | nonce (12) | ciphertext+tag``.
The AES key comes from an ephemeral X25519 exchange with the ring's public key, through
HKDF-SHA256 whose salt is the ephemeral public key and whose info names this scheme and both
public keys. The associated data is::

    secret_id|connection_id|purpose|kid|destination

with ``destination`` the whole route the secret travels, ``transport|ssh_endpoint|origin``
(:func:`auditmanager.executors.model.destination_for`). It is the last field and the only one
that may contain ``|``, so the string is unambiguous. Consequences, each shown by a test:

* the ciphertext cannot be moved to another row, another connection or another purpose;
* **a key opens only for the destination it was entered for**: the caller of :func:`open_secret`
  recomputes the destination from the revision it is about to call and passes it; the row's
  own ``destination`` column is informational and is never read here;
* a ciphertext whose key id is missing from the ring, or that fails authentication for any
  reason, is :class:`SecretUnreadable`, never an exception carrying bytes.

Nothing in this module logs, formats or returns a key. The rings print only their key ids.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

__all__ = [
    "ENVELOPE_VERSION",
    "KID_PATTERN",
    "PrivateRing",
    "PublicRing",
    "SealingConfigurationError",
    "SecretUnreadable",
    "associated_data",
    "load_private_ring",
    "load_public_ring",
    "seal",
]

ENVELOPE_VERSION: Final[int] = 1
_INFO: Final[bytes] = b"auditmanager/executors/sealed-secret/v1"
_KEY_BYTES: Final[int] = 32
_NONCE_BYTES: Final[int] = 12

#: A key id: what ``executor_secret.kid`` stores (``ck_executor_secret_kid``).
KID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,64}")


class SealingConfigurationError(ValueError):
    """A key ring variable is malformed. The message names the variable and the position of
    the entry, never any part of a key."""


class SecretUnreadable(Exception):
    """A sealed secret cannot be opened here: its key id is not in the ring, or it does not
    authenticate for the associated data it was asked to open under. Carries no bytes."""

    def __init__(self) -> None:
        super().__init__("the sealed secret cannot be opened")


def associated_data(
    *, secret_id: str, connection_id: str, purpose: str, kid: str, destination: str
) -> bytes:
    """``secret_id|connection_id|purpose|kid|destination``, UTF-8."""
    return "|".join((secret_id, connection_id, purpose, kid, destination)).encode("utf-8")


def _derive(shared: bytes, ephemeral_public: bytes, recipient_public: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=_KEY_BYTES, salt=ephemeral_public,
        info=_INFO + b"|" + ephemeral_public + b"|" + recipient_public,
    ).derive(shared)


def _raw(public_key: X25519PublicKey) -> bytes:
    return public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def seal(public_key: X25519PublicKey, plaintext: bytes, associated: bytes) -> bytes:
    """Seal ``plaintext`` to ``public_key`` under ``associated``. A fresh ephemeral key and a
    fresh nonce per call: sealing the same value twice gives two unrelated envelopes."""
    ephemeral = X25519PrivateKey.generate()
    ephemeral_public = _raw(ephemeral.public_key())
    key = _derive(ephemeral.exchange(public_key), ephemeral_public, _raw(public_key))
    nonce = os.urandom(_NONCE_BYTES)
    body = AESGCM(key).encrypt(nonce, plaintext, associated)
    return bytes([ENVELOPE_VERSION]) + ephemeral_public + nonce + body


def _open(private_key: X25519PrivateKey, envelope: bytes, associated: bytes) -> bytes:
    if len(envelope) < 1 + _KEY_BYTES + _NONCE_BYTES + 16 or envelope[0] != ENVELOPE_VERSION:
        raise SecretUnreadable()
    ephemeral_public = envelope[1 : 1 + _KEY_BYTES]
    nonce = envelope[1 + _KEY_BYTES : 1 + _KEY_BYTES + _NONCE_BYTES]
    body = envelope[1 + _KEY_BYTES + _NONCE_BYTES :]
    try:
        shared = private_key.exchange(X25519PublicKey.from_public_bytes(ephemeral_public))
        key = _derive(shared, ephemeral_public, _raw(private_key.public_key()))
        return AESGCM(key).decrypt(nonce, body, associated)
    except (InvalidTag, ValueError):
        raise SecretUnreadable() from None


@dataclass(frozen=True, slots=True)
class PublicRing:
    """What the ``api`` holds: public keys by key id, and which one seals new secrets."""

    keys: Mapping[str, X25519PublicKey]
    active_kid: str

    def __repr__(self) -> str:
        return f"PublicRing(kids={sorted(self.keys)!r}, active_kid={self.active_kid!r})"

    def seal(self, plaintext: bytes, associated_for: Mapping[str, str]) -> tuple[str, bytes]:
        """Seal to the active key. ``associated_for`` carries every field of the associated
        data except ``kid``, which is the active one and is returned with the envelope."""
        kid = self.active_kid
        associated = associated_data(kid=kid, **associated_for)  # type: ignore[arg-type]
        return kid, seal(self.keys[kid], plaintext, associated)


@dataclass(frozen=True, slots=True)
class PrivateRing:
    """What the ``worker`` holds: private keys by key id. Never logged, never serialised."""

    keys: Mapping[str, X25519PrivateKey]
    active_kid: str | None = None

    def __repr__(self) -> str:
        return f"PrivateRing(kids={sorted(self.keys)!r})"

    def open(self, kid: str, envelope: bytes, associated: bytes) -> bytes:
        private_key = self.keys.get(kid)
        if private_key is None:
            raise SecretUnreadable()
        return _open(private_key, bytes(envelope), associated)

    def public_ring(self, active_kid: str | None = None) -> PublicRing:
        """The matching public ring, for the worker's own sealing (a re-wrap)."""
        chosen = active_kid or self.active_kid or sorted(self.keys)[0]
        if chosen not in self.keys:
            raise SealingConfigurationError("the active key id is not in the private ring")
        return PublicRing(
            keys={kid: key.public_key() for kid, key in self.keys.items()}, active_kid=chosen
        )


def _entries(raw: str, variable: str) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    for position, item in enumerate(part for part in raw.split(",") if part.strip()):
        kid, separator, encoded = item.strip().partition(":")
        if not separator or not KID_PATTERN.fullmatch(kid):
            raise SealingConfigurationError(
                f"{variable} entry {position + 1} is not <kid>:<base64 key>"
            )
        try:
            key = base64.b64decode(encoded.strip(), validate=True)
        except (binascii.Error, ValueError):
            raise SealingConfigurationError(
                f"{variable} entry {position + 1} is not valid base64"
            ) from None
        if len(key) != _KEY_BYTES:
            raise SealingConfigurationError(
                f"{variable} entry {position + 1} is not a 32-byte X25519 key"
            )
        if any(kid == existing for existing, _ in entries):
            raise SealingConfigurationError(f"{variable} entry {position + 1} repeats a key id")
        entries.append((kid, key))
    return entries


def load_public_ring(
    public_keys: str | None, active_kid: str | None,
    *, public_variable: str = "AUDITMANAGER_SECRETS_PUBLIC_KEYS",
    active_variable: str = "AUDITMANAGER_SECRETS_ACTIVE_KID",
) -> PublicRing | None:
    """The ``api``'s loader: public keys only. ``None`` when no key is configured, in which
    case ``setExecutorSecret`` is a typed refusal and nothing is ever stored in the clear."""
    if not (public_keys or "").strip():
        return None
    keys = {
        kid: X25519PublicKey.from_public_bytes(raw)
        for kid, raw in _entries(public_keys or "", public_variable)
    }
    kid = (active_kid or "").strip()
    if not kid or kid not in keys:
        raise SealingConfigurationError(
            f"{active_variable} must name one of the key ids in {public_variable}"
        )
    return PublicRing(keys=keys, active_kid=kid)


def load_private_ring(
    keys: str | None, active_kid: str | None = None,
    *, variable: str = "AUDITMANAGER_SECRETS_KEYS",
) -> PrivateRing | None:
    """The worker's loader: ``kid:private-key-base64``, comma-separated. ``None`` when unset."""
    if not (keys or "").strip():
        return None
    ring = {
        kid: X25519PrivateKey.from_private_bytes(raw)
        for kid, raw in _entries(keys or "", variable)
    }
    chosen = (active_kid or "").strip() or None
    if chosen is not None and chosen not in ring:
        raise SealingConfigurationError("the active key id is not in the private ring")
    return PrivateRing(keys=ring, active_kid=chosen)
