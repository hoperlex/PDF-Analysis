"""Where the worker may send a stored key: the destination rules of plan T-9.

`EXEC-HTTP-01` (`R-143`). A connection's address is typed by an administrator, so it is also
the address a stolen admin session would type. The worker therefore checks it **twice**, in the
probe and in every call, and not only by name: the name is resolved here, every address it
resolves to is classified, and the connection is made to the *validated address*, never to
the name again. A name that resolves to loopback, link-local metadata or the compose network
is refused, whatever the name says.

Refused by default, for every transport:

* a name that cannot leave the host: ``localhost``, a single-label name (a compose service name
  such as ``postgres``, ``s3`` or ``api``), ``host.docker.internal``;
* loopback, link-local (the cloud metadata address included), unspecified, multicast and other
  reserved addresses;
* the compose network: the networks the worker container is directly attached to
  (:func:`connected_networks`).

A private range (RFC 1918, unique-local, shared address space) is accepted **only** for
``transport: vpn``. For ``ssh_tunnel`` the rule applies to the SSH endpoint; the tunnel target is
resolved on the remote host, so a remote ``localhost`` (Ollama) is not this module's business.
``AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS`` narrows further: when set, the configured host must match
one entry (a host name, ``*.suffix``, an IP literal or a CIDR).

Nothing here logs or returns an address. A refusal carries a category from a closed list, which is
all the probe stores and all a caller may say.
"""

from __future__ import annotations

import http.client
import ipaddress
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "ALLOWED_HOSTS_ENV",
    "CATEGORIES",
    "DestinationPolicy",
    "DestinationRefused",
    "DestinationUnresolvable",
    "build_opener",
    "connected_networks",
    "normalise_target",
    "parse_allowed_hosts",
    "system_resolver",
]

ALLOWED_HOSTS_ENV: Final[str] = "AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS"

#: The closed list of reasons a destination is refused; the probe's stored detail names one.
CATEGORIES: Final[tuple[str, ...]] = (
    "service_name", "loopback", "link_local", "reserved", "compose_network", "private_range",
    "not_in_allowed_hosts",
)

_LOCAL_NAMES: Final[frozenset[str]] = frozenset({
    "localhost", "host.docker.internal", "gateway.docker.internal", "ip6-localhost",
    "ip6-loopback", "broadcasthost",
})
_VPN: Final[str] = "vpn"

Address = ipaddress.IPv4Address | ipaddress.IPv6Address
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class DestinationRefused(ConnectionRefusedError):
    """The destination is not one the worker may send a key to. ``category`` is one of
    :data:`CATEGORIES`; the message carries nothing else (no host, no address)."""

    def __init__(self, category: str) -> None:
        super().__init__(f"destination refused: {category}")
        self.category = category


class DestinationUnresolvable(socket.gaierror):
    """The name does not resolve. Not a refusal: the probe reports ``unreachable``. It is a
    ``gaierror`` so the proxy adapter, which proves a DNS failure precedes the request, classes
    the call as not sent."""

    def __init__(self) -> None:
        super().__init__(socket.EAI_NONAME, "destination does not resolve")


def system_resolver(host: str, port: int) -> list[str]:
    """Every address ``host`` resolves to, as text. Raises :class:`DestinationUnresolvable`."""
    try:
        found = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise DestinationUnresolvable() from None
    addresses: list[str] = []
    for info in found:
        address = str(info[4][0])
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise DestinationUnresolvable()
    return addresses


def connected_networks(route_table: str = "/proc/net/route") -> tuple[Network, ...]:
    """The IPv4 networks this container is directly attached to (the compose network among
    them), read from the kernel's route table: the rows with no gateway. Empty where the table
    is unreadable (not Linux); the other rules still hold."""
    networks: list[Network] = []
    try:
        with open(route_table, encoding="ascii") as handle:
            rows = handle.read().splitlines()[1:]
    except OSError:
        return ()
    for row in rows:
        fields = row.split()
        if len(fields) < 8:
            continue
        try:
            destination = int(fields[1], 16)
            gateway = int(fields[2], 16)
            mask = int(fields[7], 16)
        except ValueError:
            continue
        if gateway != 0 or mask == 0:
            continue
        # The table stores the words in host order of a little-endian machine.
        base = int.from_bytes(destination.to_bytes(4, "little"), "big")
        prefix = int.from_bytes(mask.to_bytes(4, "little"), "big").bit_count()
        networks.append(ipaddress.IPv4Network((base, prefix), strict=False))
    return tuple(networks)


def normalise_target(url: str) -> tuple[str, int]:
    """``(host, port)`` of a URL or a bare ``host[:port]``; the scheme's default port otherwise."""
    parts = urllib.parse.urlsplit(url if "//" in url else "//" + url)
    host = parts.hostname
    if not host:
        raise ValueError("no host")
    return host, parts.port or (443 if parts.scheme == "https" else 80)


def parse_allowed_hosts(raw: str | None) -> tuple[str, ...]:
    """``AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS``: comma-separated, lower-cased, blanks dropped."""
    return tuple(item.strip().lower() for item in (raw or "").split(",") if item.strip())


def _literal(host: str) -> Address | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def _unwrap(address: Address) -> Address:
    mapped = getattr(address, "ipv4_mapped", None)
    return mapped if mapped is not None else address


@dataclass(frozen=True)
class DestinationPolicy:
    """The rules, with the two seams a test needs and production leaves at their defaults.

    ``resolver`` turns a name into addresses; ``dial`` maps a validated ``(address, port)`` to
    the pair actually connected to. Production dials exactly what it validated.
    """

    allowed_hosts: tuple[str, ...] = ()
    resolver: Callable[[str, int], Sequence[str]] = system_resolver
    dial: Callable[[str, int], tuple[str, int]] = lambda address, port: (address, port)
    networks: Callable[[], Iterable[Network]] = connected_networks

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> DestinationPolicy:
        env = os.environ if environ is None else environ
        return cls(allowed_hosts=parse_allowed_hosts(env.get(ALLOWED_HOSTS_ENV)))

    # -- the rules ------------------------------------------------------------------------
    def classify(self, address: Address) -> str:
        """``public`` or one of the refusal categories (``private_range`` included)."""
        address = _unwrap(address)
        if address.is_loopback:
            return "loopback"
        if address.is_link_local:
            return "link_local"
        if address.is_unspecified or address.is_multicast or address.is_reserved:
            return "reserved"
        if any(address in network for network in self._compose_networks()
               if network.version == address.version):
            return "compose_network"
        if not address.is_global:
            return "private_range"
        return "public"

    def _compose_networks(self) -> tuple[Network, ...]:
        return tuple(self.networks())

    def _name_category(self, host: str) -> str | None:
        name = host.strip("[]").lower().rstrip(".")
        if _literal(name) is not None:
            return None
        if name in _LOCAL_NAMES or name.endswith(".localhost"):
            return "loopback"
        if "." not in name:
            return "service_name"
        return None

    def _in_allowed(self, host: str, addresses: Sequence[Address]) -> bool:
        if not self.allowed_hosts:
            return True
        name = host.strip("[]").lower().rstrip(".")
        literal = _literal(name)
        for entry in self.allowed_hosts:
            if entry == name:
                return True
            if entry.startswith("*.") and name.endswith(entry[1:]):
                return True
            if "/" in entry:
                try:
                    network = ipaddress.ip_network(entry, strict=False)
                except ValueError:
                    continue
                candidates = [literal] if literal is not None else list(addresses)
                if candidates and all(
                    _unwrap(item).version == network.version and _unwrap(item) in network
                    for item in candidates if item is not None
                ):
                    return True
            elif literal is not None and _literal(entry) == literal:
                return True
        return False

    def check(self, host: str, port: int, *, transport: str) -> tuple[str, ...]:
        """The validated addresses of ``host``, or :class:`DestinationRefused` /
        :class:`DestinationUnresolvable`. Every address a name resolves to must pass: a name
        with one public and one loopback record is refused."""
        category = self._name_category(host)
        if category is not None:
            raise DestinationRefused(category)
        literal = _literal(host)
        if literal is not None:
            raw: Sequence[str] = [str(literal)]
        else:
            raw = self.resolver(host.strip("[]").rstrip("."), port)
        addresses = tuple(ipaddress.ip_address(item) for item in raw)
        if not addresses:
            raise DestinationUnresolvable()
        for address in addresses:
            category = self.classify(address)
            if category == "private_range" and transport == _VPN:
                continue
            if category != "public":
                raise DestinationRefused(category)
        if not self._in_allowed(host, addresses):
            raise DestinationRefused("not_in_allowed_hosts")
        return tuple(str(address) for address in addresses)

    def connect(
        self, host: str, port: int, *, transport: str, timeout: float | None,
        source_address: tuple[str, int] | None = None,
    ) -> socket.socket:
        """Validate, then connect to the first validated address that answers."""
        failure: OSError | None = None
        for address in self.check(host, port, transport=transport):
            target = self.dial(address, port)
            try:
                return socket.create_connection(
                    target, timeout=timeout, source_address=source_address,
                )
            except OSError as exc:
                failure = exc
        assert failure is not None
        raise failure


# -- urllib: a pinned opener ---------------------------------------------------------------


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args: Any, policy: DestinationPolicy, transport: str,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._policy = policy
        self._transport = transport

    def connect(self) -> None:
        self.sock = self._policy.connect(
            self.host, self.port, transport=self._transport, timeout=self.timeout,
            source_address=self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args: Any, policy: DestinationPolicy, transport: str,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._policy = policy
        self._transport = transport

    def connect(self) -> None:
        sock = self._policy.connect(
            self.host, self.port, transport=self._transport, timeout=self.timeout,
            source_address=self.source_address,
        )
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would re-aim an authorised request at an address nobody validated."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None


def build_opener(
    policy: DestinationPolicy, *, transport: str, context: ssl.SSLContext | None = None,
) -> urllib.request.OpenerDirector:
    """A urllib opener whose every connection goes through :meth:`DestinationPolicy.connect`.

    No proxy from the environment, no redirect, and the TLS name is the configured host while
    the TCP peer is the validated address.
    """
    tls = context or ssl.create_default_context()

    class _Http(urllib.request.HTTPHandler):
        def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
            return self.do_open(
                lambda host, **kw: _PinnedHTTPConnection(
                    host, policy=policy, transport=transport, **kw), req)

    class _Https(urllib.request.HTTPSHandler):
        def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
            return self.do_open(
                lambda host, **kw: _PinnedHTTPSConnection(
                    host, policy=policy, transport=transport, context=tls, **kw), req)

    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _Http, _Https, _NoRedirect,
    )


def refusal_of(failure: BaseException) -> DestinationRefused | None:
    """The :class:`DestinationRefused` behind a urllib failure, if that is what it was."""
    if isinstance(failure, DestinationRefused):
        return failure
    reason = failure.reason if isinstance(failure, urllib.error.URLError) else None
    return reason if isinstance(reason, DestinationRefused) else None
