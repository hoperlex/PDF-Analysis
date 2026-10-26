"""`PROD-01-TLS-ACME-01` -- what the compose files, the challenge block, the image recipe and the listener
library COMMIT the stack to, read off the files with no daemon.

`ADR-0021` section 2 and its rows 1 to 6 are commitments about a running stack. Rows 2 to 5 are claims about
bytes a client receives and are the owner's to read after the first issuance; what a tree can hold is every
fact that must be true for those bytes to come out right. This file is those facts, one test each, and every
test is shown red by a mutation in the table of ``docs/program/PROD-01-TLS-ACME-01.md``:

* row 1 -- *only the proxy publishes a port*, across the whole file list a deploy can pass;
* the three listeners of ``R-146s`` -- loopback application port in the base, port 80 in the ACME overlay,
  port 443 in the TLS overlay, and no other container port published anywhere;
* the ACME service's isolation -- no port, no Docker socket, the account key on a volume the proxy never
  mounts, the pair on a volume the proxy mounts read-only;
* the challenge block -- two locations, no route to any other tier;
* the image recipe -- a base pinned by digest, an unprivileged user, a build that refuses without a version;
* rows 3 and 4 -- HSTS on the TLS block and ``https`` forwarded to the web tier that sets ``Secure``;
* the decision library ``infra/deploy/lib/proxy-listeners.sh`` -- driven through every row of its table.

**Why these files are read with an indentation split and not a YAML parser.** The repository's venv has no
YAML library and ``test_session_register_volume.py`` says why that stays so ("a pin bought for a test").
The compose files here are two-space indented throughout, and :func:`test_the_split_finds_what_it_claims_to`
asserts the split found the services rather than an empty dictionary. The same files were also parsed once
with PyYAML 6.0.1 (the system python's), by hand, and the result is in the report; that is evidence for the
reader, not a test.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "infra/deploy/compose.server.yml"
ACME_OVERLAY = ROOT / "infra/acme/compose.acme.yml"
TLS_OVERLAY = ROOT / "infra/deploy/proxy/compose.tls.yml"
CHALLENGE = ROOT / "infra/deploy/proxy/acme-challenge.conf"
TLS_BLOCK = ROOT / "infra/deploy/proxy/tls-server.conf"
PLAIN = ROOT / "infra/deploy/proxy/nginx.conf"
DOCKERFILE = ROOT / "infra/acme/Dockerfile"
MINIO_DOCKERFILE = ROOT / "infra/minio/Dockerfile"
LIBRARY = ROOT / "infra/deploy/lib/proxy-listeners.sh"
WEB_STORE = ROOT / "web/src/app/bff/session/store.ts"

#: The Alpine the MinIO image already pins. Spelled out here, not read from there, and then compared.
ALPINE_DIGEST = "sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1"


# --- reading a compose file without a YAML parser ------------------------------------------------------------------


def code(text: str) -> list[str]:
    """The lines of a YAML file that are not comments or blank, with trailing newlines gone."""
    return [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def services(text: str) -> dict[str, dict[str, list[str]]]:
    """``{service: {key: [value lines]}}`` for a two-space-indented compose file. A key's value lines are its
    indented children, stripped (so a list item reads ``- "..."`` and a mapping entry ``NAME: value``)."""
    found: dict[str, dict[str, list[str]]] = {}
    lines = code(text)
    try:
        start = lines.index("services:")
    except ValueError:
        return found
    service = key = ""
    for line in lines[start + 1 :]:
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            break
        if indent == 2 and stripped.endswith(":"):
            service, key = stripped[:-1], ""
            found[service] = {}
        elif indent == 4 and service:
            name, _, value = stripped.partition(":")
            key = name
            found[service][key] = [value.strip()] if value.strip() else []
        elif indent > 4 and service and key:
            found[service][key].append(stripped)
    return found


def volume_names(text: str) -> list[str]:
    """The top-level ``volumes:`` keys of an overlay."""
    lines = code(text)
    if "volumes:" not in lines:
        return []
    names = []
    for line in lines[lines.index("volumes:") + 1 :]:
        if not line.startswith(" "):
            break
        if len(line) - len(line.lstrip()) == 2 and line.strip().endswith(":"):
            names.append(line.strip()[:-1])
    return names


def published(text: str) -> list[str]:
    """Every ``ports:`` item of every service, as written (quotes and leading dash removed)."""
    out = []
    for body in services(text).values():
        for item in body.get("ports", []):
            out.append(item.removeprefix("- ").strip().strip('"'))
    return out


def network_names(body: dict[str, list[str]]) -> set[str]:
    """The networks a service lists, from either spelling: ``networks: [a, b]`` or a ``- a`` item per line."""
    found: set[str] = set()
    for item in body.get("networks", []):
        item = item.removeprefix("- ").strip()
        if item.startswith("[") and item.endswith("]"):
            found |= {name.strip() for name in item[1:-1].split(",") if name.strip()}
        elif item and not item.endswith(":"):
            found.add(item)
        elif item.endswith(":"):
            found.add(item[:-1])
    return found


def top_level_networks(text: str) -> dict[str, list[str]]:
    """``{network: [its attribute lines]}`` for the top-level ``networks:`` block of a compose file."""
    lines = code(text)
    if "networks:" not in lines:
        return {}
    found: dict[str, list[str]] = {}
    current = ""
    for line in lines[lines.index("networks:") + 1 :]:
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if indent == 2 and line.strip().endswith(":"):
            current = line.strip()[:-1]
            found[current] = []
        elif current:
            found[current].append(line.strip())
    return found


FILES = {"base": BASE, "acme": ACME_OVERLAY, "tls": TLS_OVERLAY}


def test_the_split_finds_what_it_claims_to() -> None:
    """Without this a parse that found nothing would make every assertion below vacuous."""
    base = services(BASE.read_text())
    assert {"postgres", "s3", "api", "worker", "web", "proxy"} <= set(base), sorted(base)
    assert set(services(ACME_OVERLAY.read_text())) == {"acme", "proxy"}
    assert set(services(TLS_OVERLAY.read_text())) == {"proxy"}
    assert volume_names(ACME_OVERLAY.read_text()) == ["acme-state", "acme-webroot", "certs"]


# --- row 1 and the three listeners ------------------------------------------------------------------------------------


def test_only_the_proxy_publishes_a_port_across_every_file_a_deploy_can_pass() -> None:
    """`ADR-0021` row 1, over the union of the three files: the check there is a `docker compose config`
    pipe; this is its tree form. Adding the acme service or a second overlay must not add a publisher."""
    publishers = set()
    for path in FILES.values():
        publishers |= {name for name, body in services(path.read_text()).items() if "ports" in body}
    assert publishers == {"proxy"}, publishers


def test_each_file_publishes_exactly_one_listener_and_no_other_container_port() -> None:
    """The three listeners of `R-146s`, by container port: 8080 (the application, on loopback unless the
    operator says otherwise), 8081 (the challenge block, public 80) and 8443 (the TLS block, public 443)."""
    assert published(BASE.read_text()) == ["${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTP_PORT:?ALPHA_HTTP_PORT is unset.}:8080"]
    assert published(ACME_OVERLAY.read_text()) == ["${ALPHA_PUBLIC_ADDRESS:-0.0.0.0}:${ALPHA_ACME_HTTP_PORT:-80}:8081"]
    assert published(TLS_OVERLAY.read_text()) == ["${ALPHA_PUBLIC_ADDRESS:-0.0.0.0}:${ALPHA_HTTPS_PORT:-443}:8443"]


def test_the_application_listener_defaults_to_loopback_in_the_base_and_the_public_ones_do_not() -> None:
    """The distinction `R-146s` draws, in the one place it is made: the plain application port is loopback
    by default (`D-49`); the two PUBLIC ports default to all interfaces because their overlays are only ever
    passed on a deliberate decision, and a loopback default would make 80 and 443 useless."""
    assert ":-127.0.0.1}" in published(BASE.read_text())[0]
    for path in (ACME_OVERLAY, TLS_OVERLAY):
        assert ":-0.0.0.0}" in published(path.read_text())[0], path.name


def test_the_tls_overlay_adds_a_port_and_nothing_else() -> None:
    assert services(TLS_OVERLAY.read_text()) == {"proxy": {"ports": ['- "${ALPHA_PUBLIC_ADDRESS:-0.0.0.0}:${ALPHA_HTTPS_PORT:-443}:8443"']}}
    assert volume_names(TLS_OVERLAY.read_text()) == []


def test_the_base_file_gained_no_acme_service_and_no_tls_term() -> None:
    """The rollback is the absence of the overlays, so the base must be the stack without them. The sibling
    guard in `test_proxy_tls_path.py` asserts the same for `tls` and `443`; this adds the new service."""
    base = services(BASE.read_text())
    assert "acme" not in base
    for forbidden in ("acme", "certs", "ALPHA_CERT_NAME", "letsencrypt"):
        assert forbidden not in "\n".join(code(BASE.read_text())), forbidden


# --- the ACME service's isolation -----------------------------------------------------------------------------------------


class TestTheAcmeService:
    def body(self) -> dict[str, list[str]]:
        return services(ACME_OVERLAY.read_text())["acme"]

    def test_it_publishes_no_port_and_asks_for_no_privilege(self) -> None:
        body = self.body()
        assert "ports" not in body and "expose" not in body
        text = ACME_OVERLAY.read_text()
        for forbidden in ("privileged", "network_mode", "cap_add", "pid:", "userns_mode", "devices", "security_opt"):
            assert forbidden not in "\n".join(code(text)), forbidden

    def test_it_never_mounts_the_docker_socket_or_a_host_path(self) -> None:
        """`ADR-0021`: *"It does not mount the Docker socket."* No bind mount at all: its three mounts are
        named volumes, so it cannot read the host's files or the other services' secrets."""
        mounts = [item.removeprefix("- ") for item in self.body()["volumes"]]
        assert sorted(mounts) == sorted(["acme-state:/etc/letsencrypt", "acme-webroot:/var/www/acme", "certs:/export"]), mounts
        assert not [m for m in mounts if m.startswith(("/", "./", "../", "~"))], mounts
        assert "docker.sock" not in ACME_OVERLAY.read_text()

    def test_its_environment_is_three_values_and_no_secret(self) -> None:
        env = self.body()["environment"]
        assert [line.split(":", 1)[0] for line in env] == ["ACME_NAME", "ACME_EMAIL", "ACME_STAGING"], env
        staging = next(line for line in env if line.startswith("ACME_STAGING"))
        assert "${ALPHA_ACME_STAGING:-yes}" in staging, "the default must be the TEST endpoint (R-146ac)"

    def test_it_is_on_a_network_of_its_own_and_waits_for_the_proxy_to_have_started(self) -> None:
        """Before `D-229` item 3 this read ``["[alpha]"]``: the client sat on the data tier's network. The only
        peer it needs is the proxy (the probe on 8081, the verification script on 8443)."""
        body = self.body()
        assert body["networks"] == ["[acme-edge]"]
        assert body["depends_on"] == ["proxy:", "condition: service_started"]
        assert body["restart"] == ["unless-stopped"]

    def test_it_shares_no_network_with_the_data_tier(self) -> None:
        """`D-229` item 3. The client holds no credential, socket or port, but a container with TCP reach to
        postgres, s3 and the api is one floating certbot dependency away from using it. Whatever network any
        base service other than the proxy is on, the client is not on it."""
        base = services(BASE.read_text())
        data_tier = set()
        for name, body in base.items():
            if name != "proxy":
                data_tier |= network_names(body)
        assert data_tier == {"alpha"}, f"the premise changed: the base services are on {sorted(data_tier)}"
        assert network_names(self.body()).isdisjoint(data_tier), network_names(self.body())

    def test_only_the_proxy_and_the_client_are_on_the_client_network(self) -> None:
        members = {
            name
            for path in FILES.values()
            for name, body in services(path.read_text()).items()
            if "acme-edge" in network_names(body)
        }
        assert members == {"acme", "proxy"}, members

    def test_the_proxy_stays_on_the_data_network_and_joins_the_client_network(self) -> None:
        """The proxy is the bridge between the two and must keep reaching api and web. It lists BOTH names in
        the overlay so the result is the same whether compose merges the lists or replaces one with the other."""
        assert network_names(services(BASE.read_text())["proxy"]) == {"alpha"}
        assert network_names(services(ACME_OVERLAY.read_text())["proxy"]) == {"alpha", "acme-edge"}

    def test_the_client_network_is_declared_by_the_overlay_and_is_not_internal(self) -> None:
        """Declared here and not in the base (the rollback is the absence of the overlays); named from the
        instance like every other network and volume; NOT ``internal``: the client must reach the authority."""
        declared = top_level_networks(ACME_OVERLAY.read_text())
        assert set(declared) == {"acme-edge"}, sorted(declared)
        assert declared["acme-edge"] == ["name: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-acme-net"], declared
        assert "acme-edge" not in top_level_networks(BASE.read_text())
        assert "internal" not in "\n".join(code(ACME_OVERLAY.read_text()))

    def test_it_is_healthy_when_a_pair_has_been_exported(self) -> None:
        health = " ".join(self.body()["healthcheck"])
        assert '"test", "-s", "/export/fullchain.pem"' in health, health

    def test_it_is_built_from_the_acme_directory_and_named_as_deploy_sh_expects(self) -> None:
        body = self.body()
        assert "context: ../acme" in body["build"] and "dockerfile: Dockerfile" in body["build"], body["build"]
        assert (ROOT / "infra/deploy" / "../acme" / "Dockerfile").resolve().is_file()
        assert body["image"] == ["${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-acme"]
        assert "$INSTANCE-acme" in (ROOT / "infra/deploy/deploy.sh").read_text(), "deploy.sh no longer checks for this image"


class TestTheVolumes:
    """Who may see what. The account key is in `acme-state`, which the proxy -- the process on the public
    path -- must never mount; the pair it serves is on `certs`, read-only."""

    def mounts_of(self, service: str, file: Path = ACME_OVERLAY) -> list[str]:
        return [item.removeprefix("- ") for item in services(file.read_text())[service].get("volumes", [])]

    def test_the_proxy_never_mounts_the_acme_state(self) -> None:
        for path in FILES.values():
            for name, body in services(path.read_text()).items():
                if name == "acme":
                    continue
                assert not [m for m in body.get("volumes", []) if "acme-state" in m], (path.name, name)

    def test_the_proxy_mounts_the_pair_and_the_webroot_read_only(self) -> None:
        mounts = self.mounts_of("proxy")
        assert "certs:/etc/nginx/tls:ro" in mounts and "acme-webroot:/var/www/acme:ro" in mounts, mounts

    def test_the_acme_service_writes_both_and_the_proxy_writes_neither(self) -> None:
        acme = self.mounts_of("acme")
        assert "certs:/export" in acme and "acme-webroot:/var/www/acme" in acme
        for mount in self.mounts_of("proxy"):
            if mount.split(":", 1)[0] in ("certs", "acme-webroot"):
                assert mount.endswith(":ro"), mount

    def test_every_bind_mount_on_the_proxy_is_under_the_proxy_directory(self) -> None:
        """`reload-proxy.sh` and `verify-deployed.sh` read the running proxy's bind mounts from the container
        and refuse a source that is not `infra/deploy/proxy/`. A mount from `infra/acme/` would turn every
        deploy red with a message about a proxy that was 'not created from this checkout'."""
        for path in FILES.values():
            body = services(path.read_text()).get("proxy", {})
            for mount in body.get("volumes", []):
                source = mount.removeprefix("- ").split(":", 1)[0]
                if source.startswith(("./", "../", "/")):
                    assert source.startswith("./proxy/"), (path.name, mount)
                    assert (ROOT / "infra/deploy" / source).is_file(), (path.name, mount)

    def test_the_volume_names_carry_the_instance_so_two_stands_never_share_a_pair(self) -> None:
        text = ACME_OVERLAY.read_text()
        for volume in ("acme-state", "acme-webroot", "certs"):
            assert re.search(rf"^  {volume}:\n    name: \$\{{ALPHA_INSTANCE:\?[^}}]*\}}-{volume}$", text, re.M), volume


# --- the challenge block ------------------------------------------------------------------------------------------------------

#: A directive that hands a request to another tier. The list is the nginx modules that do it; none may appear.
HANDS_OVER = re.compile(
    r"^(proxy_pass|fastcgi_pass|uwsgi_pass|scgi_pass|grpc_pass|memcached_pass|auth_request|"
    r"proxy_set_header|proxy_redirect|rewrite|include|upstream|autoindex|alias)\b"
)
#: http-level directives: declaring one here would stop the master (a duplicate) or leak state to the others.
HTTP_LEVEL = re.compile(r"^(map|limit_req_zone|limit_conn_zone|upstream|geo|log_format|proxy_cache_path)\b")


def directives(text: str) -> list[str]:
    return [" ".join(line.split("#", 1)[0].split()) for line in text.splitlines() if line.split("#", 1)[0].strip()]


class TestTheChallengeBlock:
    def test_it_is_one_server_on_8081_with_no_ssl(self) -> None:
        lines = directives(CHALLENGE.read_text())
        assert lines[0] == "server {" and lines[-1] == "}"
        assert [line for line in lines if line.startswith("listen ")] == ["listen 8081;"]
        assert not [line for line in lines if line.startswith(("ssl", "http2", "listen 8443"))]

    def test_it_has_exactly_two_locations_and_the_second_is_a_redirect(self) -> None:
        lines = directives(CHALLENGE.read_text())
        locations = [line for line in lines if line.startswith("location ")]
        assert locations == ["location /.well-known/acme-challenge/ {", "location / {"], locations
        assert "return 301 https://$host$request_uri;" in lines

    def test_the_webroot_location_serves_files_and_nothing_else(self) -> None:
        lines = directives(CHALLENGE.read_text())
        start = lines.index("location /.well-known/acme-challenge/ {")
        block = lines[start + 1 : lines.index("}", start)]
        assert block == ["root /var/www/acme;", "default_type text/plain;", "try_files $uri =404;"], block

    def test_no_directive_hands_a_request_to_another_tier(self) -> None:
        """The commitment of `R-146s`: port 80 is open before the seeded password is changed, and nothing
        behind it can be asked for anything. A `proxy_pass` here would be exactly the hole."""
        offenders = [line for line in directives(CHALLENGE.read_text()) if HANDS_OVER.match(line)]
        assert offenders == [], offenders

    def test_it_declares_nothing_at_http_level(self) -> None:
        assert [line for line in directives(CHALLENGE.read_text()) if HTTP_LEVEL.match(line)] == []

    def test_the_webroot_path_is_the_one_the_overlay_mounts(self) -> None:
        assert "acme-webroot:/var/www/acme:ro" in ACME_OVERLAY.read_text()
        assert "root /var/www/acme;" in directives(CHALLENGE.read_text())

    def test_the_overlay_loads_it_into_conf_d_and_the_tls_block_stays_out(self) -> None:
        text = ACME_OVERLAY.read_text()
        assert "./proxy/acme-challenge.conf:/etc/nginx/conf.d/acme-challenge.conf:ro" in text
        assert "tls-server.conf:/etc/nginx/conf.d" not in text


# --- the image recipe ------------------------------------------------------------------------------------------------------------


def _from_line() -> str:
    return next(line for line in DOCKERFILE.read_text().splitlines() if line.startswith("FROM "))


class TestTheImageRecipe:
    def test_the_base_is_pinned_by_digest_and_is_the_one_minio_already_pins(self) -> None:
        assert _from_line() == f"FROM alpine:3.22.1@{ALPINE_DIGEST}"
        assert f"alpine:3.22.1@{ALPINE_DIGEST}" in MINIO_DOCKERFILE.read_text(), "the digest is no longer the repository's other Alpine pin"

    def test_it_runs_as_an_unprivileged_user_and_starts_the_loop(self) -> None:
        text = DOCKERFILE.read_text()
        assert re.search(r"^USER acme$", text, re.M) and "adduser -D -H -u 10002 acme" in text
        assert re.search(r'^ENTRYPOINT \["/usr/local/bin/entrypoint.sh"\]$', text, re.M)
        assert "docker" not in "\n".join(code(text)).lower().replace("dockerfile", "")

    def test_every_script_it_copies_exists_and_is_executable_in_git(self) -> None:
        copied = re.search(r"^COPY (entrypoint\.sh export-pair\.sh check-served\.sh) /usr/local/bin/$", DOCKERFILE.read_text(), re.M)
        assert copied, "the COPY line of the three scripts changed"
        for name in copied.group(1).split():
            assert (ROOT / "infra/acme" / name).is_file(), name
            mode = subprocess.run(
                ["git", "ls-files", "--stage", "--", f"infra/acme/{name}"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.split()
            assert mode and mode[0] == "100755", (name, mode)

    def test_the_hook_scripts_the_proxy_runs_are_executable_in_git(self) -> None:
        """The official image runs only EXECUTABLE `*.sh` in `/docker-entrypoint.d/` and says
        'Ignoring ...: not executable' otherwise, which is the quietest way for the watcher to do nothing."""
        for name in ("watch-certificate.sh", "enable-tls.sh"):
            mode = subprocess.run(
                ["git", "ls-files", "--stage", "--", f"infra/deploy/proxy/{name}"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.split()
            assert mode and mode[0] == "100755", (name, mode)

    def _install_step(self) -> str:
        """The `RUN` that installs the client, as a shell script with its backslash continuations joined."""
        text = DOCKERFILE.read_text()
        start = text.index("RUN set -eu; ")
        end = text.index("\n\nRUN adduser")
        return text[start + len("RUN ") : end].replace("\\\n", " ")

    def _run_install(self, tmp_path: Path, pin_line: str, *, reported: str = "certbot 9.9.9") -> subprocess.CompletedProcess[str]:
        binary = tmp_path / "bin"
        binary.mkdir()
        (binary / "apk").write_text('#!/bin/sh\necho "apk $*" >> "$APK_LOG"\n', encoding="utf-8")
        (binary / "certbot").write_text(f'#!/bin/sh\necho "{reported}"\n', encoding="utf-8")
        for name in ("apk", "certbot"):
            (binary / name).chmod(0o755)
        pin = tmp_path / "client.pin"
        pin.write_text(pin_line + "\n", encoding="utf-8")
        script = self._install_step().replace("/etc/acme/client.pin", str(pin))
        return subprocess.run(
            ["sh", "-c", script],
            capture_output=True,
            text=True,
            env={"PATH": f"{binary}{os.pathsep}{os.environ['PATH']}", "APK_LOG": str(tmp_path / "apk.log")},
        )

    def test_the_build_refuses_the_shipped_unresolved_word_and_installs_nothing(self, tmp_path: Path) -> None:
        shipped = next(
            line for line in (ROOT / "infra/acme/client.pin").read_text().splitlines() if line.startswith("ACME_CLIENT_APK_VERSION=")
        )
        result = self._run_install(tmp_path, shipped)
        assert result.returncode != 0
        assert "does not name a client version" in result.stderr
        assert not (tmp_path / "apk.log").exists(), "apk was run although no version was resolved"

    @pytest.mark.parametrize("pin", ["ACME_CLIENT_APK_VERSION=", "ACME_CLIENT_APK_VERSION=4.1.1", "ACME_CLIENT_APK_VERSION=latest-r0"])
    def test_the_build_refuses_a_value_that_is_not_a_package_version(self, pin: str, tmp_path: Path) -> None:
        result = self._run_install(tmp_path, pin)
        assert result.returncode != 0, result.stdout
        assert not (tmp_path / "apk.log").exists()

    def test_a_package_version_is_installed_exactly_and_the_installed_client_must_report_it(self, tmp_path: Path) -> None:
        good = self._run_install(tmp_path, "ACME_CLIENT_APK_VERSION=9.9.9-r0")
        assert good.returncode == 0, good.stderr
        assert (tmp_path / "apk.log").read_text().strip() == "apk add --no-cache certbot=9.9.9-r0 openssl ca-certificates"
        other = tmp_path / "other"
        other.mkdir()
        wrong = self._run_install(other, "ACME_CLIENT_APK_VERSION=9.9.9-r0", reported="certbot 1.2.3")
        assert wrong.returncode != 0, "a client that reports another version was accepted"


# --- rows 3 and 4: HSTS and the Secure cookie --------------------------------------------------------------------------------


class TestHstsAndTheSecureCookie:
    def test_the_tls_block_is_the_only_one_that_listens_with_ssl_and_sets_hsts_without_widening_it(self) -> None:
        tls = directives(TLS_BLOCK.read_text())
        assert "listen 8443 ssl;" in tls
        hsts = [line for line in tls if line.startswith("add_header Strict-Transport-Security")]
        assert hsts == ['add_header Strict-Transport-Security "max-age=31536000" always;']
        assert not [line for line in tls if "includeSubDomains" in line or "preload" in line]
        assert not [line for line in directives(PLAIN.read_text()) if "Strict-Transport-Security" in line]

    def test_the_proxy_tells_the_web_tier_the_scheme_it_was_reached_by(self) -> None:
        """The chain that makes the session cookie `Secure` (`ADR-0021` row 4), link by link. The TLS block
        forwards `$scheme`, which on an `ssl` listener is `https`; the web tier reads the first element of that
        header (`requestIsSecure`) and adds `Secure` to the cookie it sets and to the one it clears."""
        for path in (TLS_BLOCK, PLAIN):
            lines = directives(path.read_text())
            forwarded = [line for line in lines if line.startswith("proxy_set_header X-Forwarded-Proto")]
            assert forwarded == ["proxy_set_header X-Forwarded-Proto $scheme;"] * 3, (path.name, forwarded)
        store = WEB_STORE.read_text()
        assert "request.headers.get('x-forwarded-proto')" in store
        assert "forwarded.split(',')[0]?.trim() === 'https'" in store
        assert "if (secure) attributes.push('Secure');" in store

    def test_a_forwarded_scheme_is_never_taken_from_the_client(self) -> None:
        """If a location copied the client's header instead of `$scheme`, a client could claim `https` on the
        plain listener; or claim `http` on TLS and lose `Secure`. Neither file may use `$http_x_forwarded_proto`."""
        for path in (TLS_BLOCK, PLAIN, CHALLENGE):
            assert "http_x_forwarded_proto" not in path.read_text(), path.name


# --- the decision library -------------------------------------------------------------------------------------------------------


def _bash(program: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'. "{LIBRARY}"\n{program}'], capture_output=True, text=True, timeout=30, cwd=cwd
    )


GOOD_NAMES = ["audit.sslip.io", "a.b", "x-y.example.co", "a1.b2.c3", "audit.1.2.3.4.sslip.io", "n" * 63 + ".io"]
BAD_NAMES = {
    "": "empty",
    "single": "single label",
    "Upper.io": "lower case only",
    "a b.io": "lower case only",
    "*.sslip.io": "lower case only",
    "a..io": "empty label",
    ".a.io": "starts or ends with a dot",
    "a.io.": "starts or ends with a dot",
    "-a.io": "starts or ends with a hyphen",
    "a-.io": "starts or ends with a hyphen",
    "203.0.113.7": "IP address",
    "a.io:443": "lower case only",
    "https://a.io": "lower case only",
    "host.example.invalid": "reserved or documentation",
    "host.test": "reserved or documentation",
    "x.localhost": "reserved or documentation",
    "example.com": "reserved or documentation",
    "x.example.org": "reserved or documentation",
    "n" * 64 + ".io": "longer than 63",
    ("n" * 60 + ".") * 5 + "io": "longer than 253",
}


class TestTheListenerLibrary:
    @pytest.mark.parametrize("name", GOOD_NAMES)
    def test_a_public_dns_name_is_accepted(self, name: str) -> None:
        result = _bash(f'listeners_name_problem "{name}"; echo "rc=$?"')
        assert result.stdout.strip() == "rc=0", result.stdout

    @pytest.mark.parametrize("name", sorted(BAD_NAMES))
    def test_anything_else_is_refused_with_a_reason(self, name: str) -> None:
        result = _bash(f'listeners_name_problem "{name}"; echo "rc=$?"')
        reason, _, rc = result.stdout.rstrip("\n").rpartition("\n")
        assert rc == "rc=1", result.stdout
        assert BAD_NAMES[name] in reason, (name, reason)

    @pytest.mark.parametrize("wanted", ["yes", "no"])
    @pytest.mark.parametrize("pair", ["yes", "no", "unknown"])
    def test_the_overlay_list_for_a_name(self, wanted: str, pair: str) -> None:
        result = _bash(f'listeners_overlay_files "{ROOT}/infra/deploy" "x.sslip.io" {wanted} {pair}')
        files = result.stdout.split()
        assert result.returncode == 0, result.stderr
        assert files[0] == str(ROOT / "infra/acme/compose.acme.yml")
        if wanted == "yes" and pair == "yes":
            assert files == [str(ROOT / "infra/acme/compose.acme.yml"), str(ROOT / "infra/deploy/proxy/compose.tls.yml")]
        else:
            assert files == [str(ROOT / "infra/acme/compose.acme.yml")], (wanted, pair, files)

    @pytest.mark.parametrize("wanted", ["yes", "no", ""])
    @pytest.mark.parametrize("pair", ["yes", "no", "unknown", ""])
    def test_without_a_name_there_is_no_overlay_whatever_else_is_true(self, wanted: str, pair: str) -> None:
        result = _bash(f'listeners_overlay_files "{ROOT}/infra/deploy" "" "{wanted}" "{pair}"; echo "rc=$?"')
        assert result.stdout == "rc=0\n", result.stdout

    @pytest.mark.parametrize("name", ["", "x.sslip.io"])
    @pytest.mark.parametrize("wanted", ["yes", "no", "maybe", ""])
    @pytest.mark.parametrize("pair", ["yes", "no", "unknown", "garbage", ""])
    def test_443_is_never_published_without_the_acme_overlay_and_never_on_anything_but_two_yeses(
        self, name: str, wanted: str, pair: str
    ) -> None:
        files = _bash(f'listeners_overlay_files "{ROOT}/infra/deploy" "{name}" "{wanted}" "{pair}"').stdout.split()
        verdict = _bash(f'listeners_https_verdict "{name}" "{wanted}" "{pair}"').stdout.strip()
        has_tls = any(f.endswith("compose.tls.yml") for f in files)
        has_acme = any(f.endswith("compose.acme.yml") for f in files)
        assert has_tls <= has_acme, (name, wanted, pair, files)
        assert has_tls == (name != "" and wanted == "yes" and pair == "yes"), (name, wanted, pair, files)
        assert (verdict == "published") == has_tls, (verdict, files)
        assert verdict == "published" or verdict.startswith("withheld: "), verdict

    @pytest.mark.parametrize(
        ("name", "wanted", "pair", "says"),
        [
            ("", "yes", "yes", "no certificate name is configured"),
            ("x.sslip.io", "no", "yes", "credential gate is not satisfied"),
            ("x.sslip.io", "yes", "no", "no certificate pair exists yet (no)"),
            ("x.sslip.io", "yes", "unknown", "no certificate pair exists yet (unknown)"),
        ],
    )
    def test_the_verdict_names_the_first_thing_that_is_false(self, name: str, wanted: str, pair: str, says: str) -> None:
        verdict = _bash(f'listeners_https_verdict "{name}" "{wanted}" "{pair}"').stdout.strip()
        assert says in verdict, verdict

    def test_an_incomplete_clone_is_an_error_and_not_a_shorter_list(self, tmp_path: Path) -> None:
        deploy = tmp_path / "infra/deploy"
        (deploy / "proxy").mkdir(parents=True)
        (tmp_path / "infra/acme").mkdir()
        result = _bash(f'listeners_overlay_files "{deploy}" "x.sslip.io" yes yes; echo "rc=$?"')
        assert result.stdout == "rc=2\n", result.stdout
        (tmp_path / "infra/acme/compose.acme.yml").write_text("", encoding="utf-8")
        result = _bash(f'listeners_overlay_files "{deploy}" "x.sslip.io" yes yes; echo "rc=$?"')
        assert result.stdout == "rc=2\n", result.stdout
