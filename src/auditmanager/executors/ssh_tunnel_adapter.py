"""Short-lived SSH forward for the existing HTTP model adapters, including their ordered PNG blocks."""

from __future__ import annotations

import socket
import urllib.parse
from typing import Any

from auditmanager.analysis.public import ModelRequest, ModelResponse, ProviderMode, ProxyDispatchError
from auditmanager.executors.destinations import DestinationPolicy, DestinationRefused, DestinationUnresolvable
from auditmanager.executors.http_adapter import build_http_adapter, effective_timeout
from auditmanager.executors.image_input import checked_pngs
from auditmanager.executors.model import RevisionRecord
from auditmanager.executors.ssh_transport import SshEndpoint, SshFailure, open_tunnel
from auditmanager.shared.errors import ErrorCode


def remote_target(base_url: str) -> tuple[str, int]:
    parts = urllib.parse.urlsplit(base_url)
    assert parts.hostname is not None
    return parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)


class TunnelPolicy:
    """Only the revision's HTTP origin may reach this call's loopback forward.

    The URL, Host header and TLS server name stay the original remote origin.
    ``check`` rejects a redirected or re-aimed HTTP request, and ``connect`` / ``dial``
    hand both urllib and httpx the same short-lived local TCP endpoint.
    """

    def __init__(self, base_url: str, local_port: int) -> None:
        self._host, self._port = remote_target(base_url)
        self._local_port = local_port

    def check(self, host: str, port: int, *, transport: str) -> tuple[str, ...]:
        if host.lower().rstrip(".") != self._host.lower().rstrip(".") or port != self._port:
            raise DestinationRefused("reserved")
        return ("127.0.0.1",)

    def dial(self, address: str, port: int) -> tuple[str, int]:
        if address != "127.0.0.1" or port != self._port:
            raise DestinationRefused("reserved")
        return ("127.0.0.1", self._local_port)

    def connect(self, host: str, port: int, *, transport: str, timeout: float | None,
                source_address: tuple[str, int] | None = None) -> socket.socket:
        address = self.check(host, port, transport=transport)[0]
        return socket.create_connection(self.dial(address, port), timeout=timeout,
                                        source_address=source_address)


def checked_endpoint(revision: RevisionRecord, policy: DestinationPolicy) -> SshEndpoint:
    settings = revision.settings
    assert settings.ssh_host and settings.ssh_port and settings.ssh_user
    addresses = policy.check(settings.ssh_host, settings.ssh_port, transport="ssh_tunnel")
    return SshEndpoint(addresses[0], settings.ssh_port, settings.ssh_user)


def _not_sent(message: str, *, retry_safe: bool = False) -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=retry_safe,
        message=message, details={"dependency": "model_provider"},
    )


class SshTunnelAdapter:
    provider_mode = ProviderMode.LIVE

    def __init__(self, revision: RevisionRecord, api_key: str, ssh_key: str,
                 policy: DestinationPolicy, context: Any | None) -> None:
        self._revision = revision
        self._api_key = api_key
        self._ssh_key = ssh_key
        self._policy = policy
        self._context = context

    def complete(self, request: ModelRequest) -> ModelResponse:
        # The descriptor/bytes mismatch must fail before an SSH or HTTP connection opens.
        checked_pngs(request)
        settings = self._revision.settings
        assert settings.base_url and settings.api_flavour
        try:
            endpoint = checked_endpoint(self._revision, self._policy)
        except (DestinationRefused, DestinationUnresolvable):
            raise _not_sent("the SSH destination is not available") from None
        timeout = effective_timeout(settings.timeout_seconds, self._context)
        if timeout is None:
            raise _not_sent("the attempt has too little time left")
        host, port = remote_target(settings.base_url)
        try:
            with open_tunnel(endpoint, self._ssh_key, settings.host_key, host, port,
                             timeout_s=min(15.0, timeout)) as local_port:
                http = build_http_adapter(
                    api_flavour=settings.api_flavour, base_url=settings.base_url,
                    api_key=self._api_key, gateway_model=settings.gateway_model,
                    timeout_seconds=settings.timeout_seconds, transport="direct",
                    policy=TunnelPolicy(settings.base_url, local_port), context=self._context,
                )
                return http.complete(request)
        except SshFailure as failure:
            raise _not_sent(f"the SSH tunnel did not open ({failure.outcome})",
                            retry_safe=failure.outcome in ("unreachable", "timeout")) from None


def build_ssh_tunnel_adapter(
    revision: RevisionRecord, api_key: str, ssh_key: str,
    policy: DestinationPolicy, context: Any | None,
) -> SshTunnelAdapter:
    return SshTunnelAdapter(revision, api_key, ssh_key, policy, context)
