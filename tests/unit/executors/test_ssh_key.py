"""`EXEC-SEAL-01`: the generated SSH key is OpenSSH format, sealed to its endpoint.

Verified against OpenSSH 9.6 by the SSH transport lane: a PKCS#8 ed25519 key is rejected by
`ssh -i` as "invalid format", so the sealed private half must be an `OPENSSH PRIVATE KEY` and the
public half an `ssh-ed25519 <base64>` line. Container-free: the repository and the command
ledger are fakes, so the command's own sealing is what runs.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_ssh_private_key,
)

from auditmanager.executors import commands
from auditmanager.executors.model import (
    ConnectionRecord,
    RevisionRecord,
    RevisionSettings,
    SecretRecord,
    destination_for,
)
from auditmanager.executors.sealing import associated_data, load_private_ring, load_public_ring

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)
ACTOR = "usr_" + "0" * 26
CONNECTION = "exc_" + "0" * 26
SSH = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="metered",
    allow_client_documents=False, timeout_seconds=120, ssh_host="gpu.test", ssh_port=22,
    ssh_user="am", ssh_profile="claude_code_headless",
)


@dataclass
class FakeStore:
    kind: str = "ssh_command"
    stored: dict[str, Any] | None = None

    def get_connection(self, session: Any, connection_id: str, *, lock: bool = False):
        return ConnectionRecord(connection_id, self.kind, "gpu", NOW, ACTOR)

    def current_revisions(self, session: Any, ids: Any):
        return {CONNECTION: RevisionRecord("excr_" + "0" * 26, CONNECTION, 1, NOW, ACTOR, SSH)}

    def replace_secret(self, session: Any, **row: Any) -> SecretRecord:
        self.stored = row
        return SecretRecord(
            row["secret_id"], row["connection_id"], row["purpose"], row["kid"], row["destination"],
            row["last4"], row["public_material"], NOW, ACTOR,
        )


class FakeLedger:
    class _Started:
        command_id = "cmd_" + "0" * 26

    def begin(self, session: Any, **kwargs: Any) -> Any:
        return commands.CommandStarted(command_id=self._Started.command_id)  # type: ignore[arg-type]

    def succeed(self, session: Any, command_id: Any, outcome: Any) -> None:
        self.outcome = outcome


def _rings():
    key = X25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    private = base64.b64encode(
        key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode()
    return load_public_ring(f"k1:{public}", "k1"), load_private_ring(f"k1:{private}")


def test_the_sealed_half_is_an_openssh_key_and_the_public_half_an_ed25519_line(monkeypatch) -> None:
    monkeypatch.setattr(commands, "append_execution_event", lambda *a, **k: None)
    public_ring, private_ring = _rings()
    store = FakeStore()
    generated = commands.generate_ssh_key(
        object(), connection_id=CONNECTION, ring=public_ring, roles={"admin"},  # type: ignore[arg-type]
        idempotency_key="exec-1", actor_uid=ACTOR, repository=store,  # type: ignore[arg-type]
        commands=FakeLedger(),  # type: ignore[arg-type]
    )
    row = store.stored
    assert row is not None
    destination = destination_for("ssh_command", SSH, "ssh_private_key")
    assert row["destination"] == destination == "ssh_command|gpu.test:22|"
    opened = private_ring.open(
        row["kid"], row["ciphertext"],
        associated_data(secret_id=row["secret_id"], connection_id=CONNECTION,
                        purpose="ssh_private_key", kid=row["kid"], destination=destination),
    ).decode()
    assert opened.startswith("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert "BEGIN PRIVATE KEY" not in opened  # PKCS#8 is what `ssh -i` rejects
    loaded = load_ssh_private_key(opened.encode(), password=None)
    assert loaded.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode() == (
        generated.public_key)
    assert generated.public_key.startswith("ssh-ed25519 ") and len(generated.public_key.split()) == 2
    assert generated.authorized_keys_line == f"restrict {generated.public_key} auditmanager:{CONNECTION}"
    assert "PRIVATE" not in repr(generated) and opened not in repr(generated)
    assert row["public_material"] == generated.public_key


def test_without_a_public_ring_no_key_is_generated_or_stored() -> None:
    store = FakeStore()
    with pytest.raises(Exception) as refused:
        commands.generate_ssh_key(
            object(), connection_id=CONNECTION, ring=None, roles={"admin"},  # type: ignore[arg-type]
            idempotency_key="exec-1", actor_uid=ACTOR, repository=store,  # type: ignore[arg-type]
            commands=FakeLedger(),  # type: ignore[arg-type]
        )
    assert refused.value.detail_fields == {"dependency": "secrets_public_key_missing"}
    assert store.stored is None
