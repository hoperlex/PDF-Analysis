"""`EXEC-SEAL-01`: the sealing scheme, container-free.

Each property the plan (section 4.1) states is shown, and each guard is shown able to fail:
a changed associated-data field, a missing key id, a flipped byte and a public ring that has
no way to open anything all end as ``SecretUnreadable``, never as a plaintext and never as an
exception carrying bytes.
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from auditmanager.executors.sealing import (
    PrivateRing,
    PublicRing,
    SealingConfigurationError,
    SecretUnreadable,
    associated_data,
    load_private_ring,
    load_public_ring,
)

FIELDS = {
    "secret_id": "exs_01M2545JSD15ETSNNV904X991K",
    "connection_id": "exc_01M2545JSD15ETSNNV904X991M",
    "purpose": "api_key",
    "destination": "direct||https://proxy.test:443",
}
SECRET = "sk-test-0123456789abcdef"


def _pair() -> tuple[str, str]:
    key = X25519PrivateKey.generate()
    private = base64.b64encode(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
    public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    return private.decode(), public.decode()


@pytest.fixture
def rings() -> tuple[PublicRing, PrivateRing]:
    private, public = _pair()
    public_ring = load_public_ring(f"k1:{public}", "k1")
    private_ring = load_private_ring(f"k1:{private}")
    assert public_ring is not None and private_ring is not None
    return public_ring, private_ring


def _ad(kid: str, **changes: str) -> bytes:
    return associated_data(kid=kid, **{**FIELDS, **changes})


def test_a_sealed_secret_opens_with_the_private_ring_for_its_own_destination(rings) -> None:
    public, private = rings
    kid, envelope = public.seal(SECRET.encode(), FIELDS)
    assert SECRET.encode() not in envelope
    assert private.open(kid, envelope, _ad(kid)) == SECRET.encode()


def test_the_associated_data_is_the_five_fields_joined_by_a_pipe() -> None:
    assert _ad("k1") == (
        "exs_01M2545JSD15ETSNNV904X991K|exc_01M2545JSD15ETSNNV904X991M|api_key|k1|"
        "direct||https://proxy.test:443"
    ).encode()


@pytest.mark.parametrize("field", ["secret_id", "connection_id", "purpose", "destination"])
def test_a_changed_field_makes_the_secret_unreadable(rings, field: str) -> None:
    """The ciphertext cannot be moved to another row, connection or purpose, and a key opens
    only for the destination it was entered for."""
    public, private = rings
    kid, envelope = public.seal(SECRET.encode(), FIELDS)
    changed = {
        "secret_id": "exs_01M2545JSD15ETSNNV904X991Z",
        "connection_id": "exc_01M2545JSD15ETSNNV904X991Z",
        "purpose": "ssh_private_key",
        "destination": "direct||https://other.test:443",
    }[field]
    with pytest.raises(SecretUnreadable):
        private.open(kid, envelope, _ad(kid, **{field: changed}))


def test_a_changed_ssh_endpoint_unbinds_a_tunnelled_key(rings) -> None:
    """`ssh_tunnel|host:port|origin`: the tunnelled origin may stay `http://localhost:11434`
    while the SSH endpoint moves, and the key still does not open."""
    public, private = rings
    destination = "ssh_tunnel|gpu.test:22|http://localhost:11434"
    kid, envelope = public.seal(SECRET.encode(), {**FIELDS, "destination": destination})
    assert private.open(kid, envelope, _ad(kid, destination=destination)) == SECRET.encode()
    with pytest.raises(SecretUnreadable):
        private.open(kid, envelope, _ad(
            kid, destination="ssh_tunnel|elsewhere.test:22|http://localhost:11434"))


def test_a_missing_key_id_or_a_flipped_byte_is_unreadable_without_bytes(rings) -> None:
    public, private = rings
    kid, envelope = public.seal(SECRET.encode(), FIELDS)
    with pytest.raises(SecretUnreadable) as missing:
        private.open("k-gone", envelope, _ad("k-gone"))
    assert SECRET not in str(missing.value) and not missing.value.args[1:]
    flipped = bytearray(envelope)
    flipped[-1] ^= 1
    with pytest.raises(SecretUnreadable):
        private.open(kid, bytes(flipped), _ad(kid))
    for broken in (b"", b"\x01" + b"\x00" * 10, b"\x09" + envelope[1:]):
        with pytest.raises(SecretUnreadable):
            private.open(kid, broken, _ad(kid))


def test_another_rings_private_key_cannot_open_it(rings) -> None:
    public, _ = rings
    private_other, _public_other = _pair()
    stranger = load_private_ring(f"k1:{private_other}")
    assert stranger is not None
    kid, envelope = public.seal(SECRET.encode(), FIELDS)
    with pytest.raises(SecretUnreadable):
        stranger.open(kid, envelope, _ad(kid))


def test_two_seals_of_one_value_are_unrelated_envelopes(rings) -> None:
    public, _ = rings
    assert public.seal(SECRET.encode(), FIELDS)[1] != public.seal(SECRET.encode(), FIELDS)[1]


def test_the_public_ring_has_no_way_to_open_and_no_ring_prints_a_key(rings) -> None:
    """The `api` holds public keys only: the type it is given cannot decrypt, and neither
    ring's text names anything but its key ids."""
    public, private = rings
    assert not hasattr(public, "open") and not hasattr(public, "private")
    for ring in (public, private):
        shown = repr(ring) + str(ring)
        assert "k1" in shown and "=" not in shown.replace("active_kid=", "").replace("kids=", "")


@pytest.mark.parametrize("raw", [
    "k1", "k1:", "k1:not base64!", "bad kid:AAAA", f"k1:{base64.b64encode(b'short').decode()}",
])
def test_a_malformed_ring_variable_is_refused_without_naming_a_key(raw: str) -> None:
    with pytest.raises(SealingConfigurationError) as refused:
        load_private_ring(raw)
    assert raw.partition(":")[2] not in str(refused.value) or raw.partition(":")[2] == ""


def test_the_active_kid_must_be_in_the_ring_and_a_kid_may_not_repeat() -> None:
    _, public = _pair()
    with pytest.raises(SealingConfigurationError):
        load_public_ring(f"k1:{public}", "k2")
    with pytest.raises(SealingConfigurationError):
        load_public_ring(f"k1:{public}", None)
    with pytest.raises(SealingConfigurationError):
        load_public_ring(f"k1:{public},k1:{public}", "k1")
    assert load_public_ring(None, None) is None and load_private_ring("  ") is None
