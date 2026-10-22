"""T-9 (`EXEC-HTTP-01`): where the worker may send a stored key.

Every refusal below is paired with a destination that must still pass, because a rule that
refuses everything would pass the negatives too. The guards are shown failing under a quoted
mutation in the slice report.
"""

from __future__ import annotations

import ipaddress

import pytest

from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
    connected_networks,
    parse_allowed_hosts,
)

PUBLIC = "93.184.216.34"


def _policy(addresses: list[str], **options: object) -> DestinationPolicy:
    return DestinationPolicy(
        resolver=lambda host, port: addresses, networks=lambda: (), **options,  # type: ignore[arg-type]
    )


def test_a_public_name_passes_and_returns_the_validated_address() -> None:
    assert _policy([PUBLIC]).check("api.example.com", 443, transport="direct") == (PUBLIC,)


@pytest.mark.parametrize("host,category", [
    ("localhost", "loopback"), ("foo.localhost", "loopback"),
    ("host.docker.internal", "loopback"),
    ("postgres", "service_name"), ("s3", "service_name"), ("api", "service_name"),
    ("127.0.0.1", "loopback"), ("[::1]", "loopback"), ("::ffff:127.0.0.1", "loopback"),
    ("169.254.169.254", "link_local"), ("0.0.0.0", "reserved"),
])
def test_names_and_literals_that_cannot_leave_the_host_are_refused(host: str, category: str) -> None:
    with pytest.raises(DestinationRefused) as refused:
        _policy([PUBLIC]).check(host, 80, transport="vpn")
    assert refused.value.category == category


@pytest.mark.parametrize("address,category", [
    ("127.0.0.2", "loopback"), ("::1", "loopback"), ("169.254.10.10", "link_local"),
    ("fe80::1", "link_local"), ("224.0.0.1", "reserved"),
])
def test_a_name_that_resolves_to_an_unpermitted_address_is_refused_even_on_a_vpn(
    address: str, category: str
) -> None:
    with pytest.raises(DestinationRefused) as refused:
        _policy([address]).check("api.example.com", 443, transport="vpn")
    assert refused.value.category == category


def test_one_bad_record_among_good_ones_refuses_the_name() -> None:
    with pytest.raises(DestinationRefused):
        _policy([PUBLIC, "127.0.0.1"]).check("rebind.example.com", 443, transport="direct")


@pytest.mark.parametrize("address", ["10.1.2.3", "172.20.0.5", "192.168.1.9", "fd00::1", "100.64.0.1"])
def test_a_private_range_is_accepted_only_for_a_vpn(address: str) -> None:
    policy = _policy([address])
    for transport in ("direct", "ssh_tunnel"):
        with pytest.raises(DestinationRefused) as refused:
            policy.check("model.corp.example", 8000, transport=transport)
        assert refused.value.category == "private_range"
    assert policy.check("model.corp.example", 8000, transport="vpn") == (address,)


def test_the_compose_network_is_refused_even_on_a_vpn() -> None:
    policy = DestinationPolicy(
        resolver=lambda host, port: ["172.20.0.7"],
        networks=lambda: (ipaddress.ip_network("172.20.0.0/16"),),
    )
    with pytest.raises(DestinationRefused) as refused:
        policy.check("api.corp.example", 8000, transport="vpn")
    assert refused.value.category == "compose_network"
    # The same private range outside the compose network is a VPN peer.
    other = DestinationPolicy(
        resolver=lambda host, port: ["172.21.0.7"],
        networks=lambda: (ipaddress.ip_network("172.20.0.0/16"),),
    )
    assert other.check("api.corp.example", 8000, transport="vpn") == ("172.21.0.7",)


def test_an_unresolvable_name_is_not_a_refusal() -> None:
    def failing(host: str, port: int) -> list[str]:
        raise DestinationUnresolvable()

    with pytest.raises(DestinationUnresolvable):
        DestinationPolicy(resolver=failing, networks=lambda: ()).check(
            "nope.example.com", 443, transport="direct")


def test_the_allowed_hosts_narrow_further() -> None:
    policy = _policy([PUBLIC], allowed_hosts=parse_allowed_hosts("api.example.com, *.gateway.io"))
    assert policy.check("api.example.com", 443, transport="direct")
    assert policy.check("eu.gateway.io", 443, transport="direct")
    with pytest.raises(DestinationRefused) as refused:
        policy.check("other.example.org", 443, transport="direct")
    assert refused.value.category == "not_in_allowed_hosts"


def test_a_cidr_entry_admits_the_addresses_inside_it_and_nothing_outside() -> None:
    inside = _policy([PUBLIC], allowed_hosts=("93.184.216.0/24",))
    assert inside.check("any.example.org", 443, transport="direct")
    assert inside.check(PUBLIC, 443, transport="direct")
    with pytest.raises(DestinationRefused):
        _policy(["8.8.8.8"], allowed_hosts=("93.184.216.0/24",)).check(
            "any.example.org", 443, transport="direct")


def test_the_route_table_parser_reads_directly_attached_networks(tmp_path) -> None:  # type: ignore[no-untyped-def]
    table = tmp_path / "route"
    # 0x000014AC little-endian is 172.20.0.0; the second row has an empty mask field set below.
    table.write_text(
        "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n"
        "eth0\t00000000\t010014AC\t0003\t0\t0\t0\t00000000\t0\t0\t0\n"
        "eth0\t000014AC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n",
        encoding="ascii",
    )
    assert connected_networks(str(table)) == (ipaddress.ip_network("172.20.0.0/16"),)
    assert connected_networks(str(tmp_path / "missing")) == ()
