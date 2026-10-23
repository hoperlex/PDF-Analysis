"""Probe the forced SSH command without trusting a newly seen host key."""

from __future__ import annotations

import time

from auditmanager.analysis.public import ModelRequest
from auditmanager.executors.destinations import DestinationPolicy, DestinationRefused, DestinationUnresolvable
from auditmanager.executors.identity import PROMPT, assess_identity, rate_check
from auditmanager.executors.model import RevisionSettings
from auditmanager.executors.probes import ProbeResult
from auditmanager.executors.ssh_adapter import MAX_ANSWER_BYTES, _reply, _task
from auditmanager.executors.ssh_transport import (
    HostKeyFormatError,
    SshEndpoint,
    SshFailure,
    normalise_host_key_line,
    run_command,
    scan_host_key,
)


def probe_ssh_command(
    settings: RevisionSettings, private_key: str, *, policy: DestinationPolicy,
    input_per_mtok_usd: float | None = None, output_per_mtok_usd: float | None = None,
) -> ProbeResult:
    assert settings.ssh_host and settings.ssh_port and settings.ssh_user
    started = time.monotonic()
    try:
        addresses = policy.check(settings.ssh_host, settings.ssh_port, transport="ssh_command")
    except DestinationRefused as failure:
        return ProbeResult("destination_refused", f"the SSH address is not permitted ({failure.category})")
    except DestinationUnresolvable:
        return ProbeResult("unreachable", "the SSH address does not resolve")
    endpoint = SshEndpoint(addresses[0], settings.ssh_port, settings.ssh_user)
    try:
        observed = scan_host_key(endpoint, timeout=min(10.0, float(settings.timeout_seconds)))
    except SshFailure as failure:
        return ProbeResult(failure.outcome, "the SSH host key could not be read")
    if settings.host_key is None:
        return ProbeResult(
            "host_key_unpinned", "confirm the observed SSH host key before running a model call",
            observed_host_key=observed,
        )
    try:
        pinned = normalise_host_key_line(settings.host_key)
    except HostKeyFormatError:
        return ProbeResult("host_key_unpinned", "the saved SSH host key is invalid",
                           observed_host_key=observed)
    if pinned != observed:
        return ProbeResult("host_key_changed", "the SSH host key differs from the saved pin",
                           observed_host_key=observed)
    request = ModelRequest(
        model_id=settings.pin_id,
        body={"system": "Ответь кратко.", "messages": [{"role": "user", "content": PROMPT}],
              "max_tokens": 16},
    )
    try:
        raw, _stderr = run_command(
            endpoint, private_key, pinned, _task(request, settings.gateway_model),
            timeout_s=float(settings.timeout_seconds), max_output_bytes=MAX_ANSWER_BYTES,
        )
        answer = _reply(raw, int((time.monotonic() - started) * 1000))
    except SshFailure as failure:
        return ProbeResult(failure.outcome, "the SSH model call failed",
                           latency_ms=int((time.monotonic() - started) * 1000))
    except Exception:
        # No remote stdout/stderr or prompt content enters the probe row.
        return ProbeResult("protocol_error", "the SSH model answer is invalid",
                           latency_ms=int((time.monotonic() - started) * 1000))
    outcome, model = assess_identity(answer.model, settings.gateway_model)
    if settings.billing == "not_metered":
        rate = "not_metered"
    elif input_per_mtok_usd is None or output_per_mtok_usd is None:
        rate = "not_reported"
    else:
        rate = rate_check(
            {"cost": answer.reported_cost_usd, "prompt_tokens": answer.input_tokens,
             "completion_tokens": answer.output_tokens},
            billing=settings.billing, input_per_mtok_usd=input_per_mtok_usd,
            output_per_mtok_usd=output_per_mtok_usd,
        )
    if outcome == "ok" and rate == "mismatch":
        outcome = "rate_mismatch"
    return ProbeResult(
        outcome, None if outcome == "ok" else "the SSH model or cost differs from the saved pin",
        reported_model=model, identity_basis="reported", latency_ms=answer.latency_ms,
        rate_check=rate,
    )
