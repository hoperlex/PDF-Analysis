"""`PROD-01-TLS-ACME-01` -- `verify-deployed.sh` fails on a certificate that is not fit to be served.

`ADR-0021` section 2 and rows 2 and 5: *"`verify-deployed.sh` fails when the served certificate has fewer than
14 days left"*, and the public name answers over a trusted chain. This file drives the new section of that
script (``# --- 4. the certificate the proxy serves``) through every answer ``check-served.sh`` can give and
through the three things that decide whether it is asked at all.

**What the script does and this file reads.** With ``ALPHA_CERT_NAME`` set it runs ``check-served.sh`` in a
one-off container of the ACME image against ``proxy:8443`` and maps its exit status: ``0`` passes, ``10`` to
``13`` (nothing served, expiring, not trusted, the wrong kind) are exit ``7``, anything else (the question
itself failed) is ``4``. A STAGING setting is a failure of its own unless the operator says
``--acme-rehearsal``, because the default of ``ALPHA_ACME_STAGING`` is ``yes`` and a host that lost the
setting must be caught here and not by a browser.

**Reuse and its limit.** The harness -- a small git repository, a staged ``infra/deploy``, an image that agrees
with the tree, a ``docker`` and a ``curl`` that answer from the fixture -- is the one
``test_deployed_stack_probe.py`` builds for the older sections, loaded from that file rather than copied, so the
two cannot drift; the only addition is one branch in the ``docker`` stub for ``check-served.sh``. The answer of
the real ``check-served.sh`` is a stand-in here (its own suite is ``test_acme_client.py``), so this file proves
how ``verify-deployed.sh`` READS the answer.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location("probe_harness", ROOT / "tests/integration/composition/test_deployed_stack_probe.py")
assert _spec is not None and _spec.loader is not None
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

world = probe.world  # the fixture, by the name pytest finds it under

NAME = "rehearsal-host.sslip.io"
CERTIFICATE = 7
UNANSWERABLE = probe.UNANSWERABLE
DRIFT = probe.DRIFT

#: One branch added to the harness's `docker`: `check-served.sh` answers from the environment. Inserted before
#: the `ps` branch, which is the first thing the original stub does after logging the call.
CERT_BRANCH = '''if "check-served.sh" in line:
    sys.stdout.write(os.environ.get("STUB_CERT_OUTPUT", "served-certificate: OK name=stub\\n"))
    sys.stderr.write(os.environ.get("STUB_CERT_STDERR", ""))
    sys.exit(int(os.environ.get("STUB_CERT_STATUS", "0")))

'''
ANCHOR = 'if "ps" in argv and "--quiet" in argv:'


@pytest.fixture(autouse=True)
def _docker_that_answers_the_certificate_question(monkeypatch: pytest.MonkeyPatch) -> None:
    assert probe.DOCKER_STUB.count(ANCHOR) == 1, "the harness's docker stub changed shape; move the branch"
    monkeypatch.setattr(probe, "DOCKER_STUB", probe.DOCKER_STUB.replace(ANCHOR, CERT_BRANCH + ANCHOR, 1))


def _tls_env(tmp_path: Path, *, name: str | None = NAME, staging: str | None = "no") -> Path:
    lines = ["ALPHA_INSTANCE=an-instance", "ALPHA_HTTP_PORT=31599"]
    if name is not None:
        lines.append(f"ALPHA_CERT_NAME={name}")
    if staging is not None:
        lines.append(f"ALPHA_ACME_STAGING={staging}")
    path = tmp_path / "tls.env"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _stage_the_terminator(deploy: Path) -> None:
    """The library and the ACME overlay the staged script resolves relative to itself."""
    (deploy / "lib").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "infra/deploy/lib/proxy-listeners.sh", deploy / "lib/proxy-listeners.sh")
    acme = deploy.parent / "acme"
    acme.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "infra/acme/compose.acme.yml", acme / "compose.acme.yml")


def _verify(world, tmp_path: Path, *args: str, env: Path, script: Path | None = None, **stub: str):  # type: ignore[no-untyped-def]
    repo, deploy, image = world
    _stage_the_terminator(deploy)
    return probe._run(
        script or deploy / "verify-deployed.sh",
        *args,
        tmp_path=tmp_path,
        repo=repo,
        env_file=env,
        STUB_IMAGE=str(image),
        **stub,
    )


def _asked(calls: str) -> list[str]:
    return [line for line in calls.splitlines() if "check-served.sh" in line]


class TestTheCertificateIsAskedForOnlyWhenThereIsAName:
    def test_without_a_name_the_script_is_what_it_was(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, env=_tls_env(tmp_path, name=None, staging=None))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "the certificate the proxy serves" not in completed.stdout
        assert _asked(calls) == []

    def test_with_a_name_the_question_is_the_right_one(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, env=_tls_env(tmp_path))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "-- the certificate the proxy serves --" in completed.stdout
        (asked,) = _asked(calls)
        # the base file and the acme overlay, in that order; the one-off container; the script; the name as SNI;
        # the proxy's own TLS listener; 14 days (`ADR-0021` row 5); production
        assert re.search(r"--file \S+compose\.server\.yml --file \S+acme/compose\.acme\.yml run --rm --no-deps -T", asked), asked
        assert asked.endswith(f"--entrypoint /usr/local/bin/check-served.sh acme {NAME} proxy:8443 14 production"), asked
        assert "IS this tree" in completed.stdout


class TestWhatItMakesOfTheAnswer:
    @pytest.mark.parametrize("status", [10, 11, 12, 13])
    def test_a_certificate_that_is_not_acceptable_is_exit_7_and_the_line_is_shown(
        self, status: int, world, tmp_path: Path
    ) -> None:
        completed, _ = _verify(
            world, tmp_path, env=_tls_env(tmp_path),
            STUB_CERT_STATUS=str(status), STUB_CERT_OUTPUT=f"served-certificate: WORD{status} -- because\n",
        )
        assert completed.returncode == CERTIFICATE, (completed.stdout, completed.stderr)
        assert f"served-certificate: WORD{status}" in completed.stdout
        assert f"check-served.sh exit {status}" in completed.stderr
        assert "IS this tree" not in completed.stdout, "it called the stack good with a bad certificate"

    def test_a_question_that_failed_is_exit_4_and_claims_nothing(self, world, tmp_path: Path) -> None:
        completed, _ = _verify(
            world, tmp_path, env=_tls_env(tmp_path),
            STUB_CERT_STATUS="125", STUB_CERT_OUTPUT="", STUB_CERT_STDERR="docker: the daemon refused\n",
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "could not be asked (exit 125)" in completed.stderr and "daemon refused" in completed.stderr
        assert "IS this tree" not in completed.stdout

    def test_a_name_that_cannot_be_used_is_exit_4_before_anything_is_asked(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, env=_tls_env(tmp_path, name="host.example.invalid"))
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "not a usable name" in completed.stderr
        assert _asked(calls) == []

    def test_a_certificate_is_judged_after_the_tree_and_never_instead_of_it(self, world, tmp_path: Path) -> None:
        """Drift is exit 6 and wins: with the images wrong the certificate is not even asked."""
        completed, calls = _verify(
            world, tmp_path, env=_tls_env(tmp_path), STUB_CORRUPT="/app/src/auditmanager/runs/carrier.py"
        )
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert _asked(calls) == []


class TestStagingIsAFailureUnlessTheRehearsalSaysSo:
    @pytest.mark.parametrize("staging", ["yes", None], ids=["explicit", "the default"])
    def test_a_stack_set_to_the_test_endpoint_fails_and_asks_nothing(self, staging: str | None, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, env=_tls_env(tmp_path, staging=staging))
        assert completed.returncode == CERTIFICATE, (completed.stdout, completed.stderr)
        assert "TEST endpoint" in completed.stderr and "--acme-rehearsal" in completed.stderr
        assert "ALPHA_ACME_STAGING=no" in completed.stderr
        assert _asked(calls) == []

    def test_the_rehearsal_flag_accepts_it_and_asks_for_a_staging_certificate(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, "--acme-rehearsal", env=_tls_env(tmp_path, staging="yes"))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        (asked,) = _asked(calls)
        assert asked.endswith(f"{NAME} proxy:8443 14 staging"), asked

    def test_the_flag_does_not_excuse_a_production_setting(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, "--acme-rehearsal", env=_tls_env(tmp_path, staging="no"))
        assert completed.returncode == CERTIFICATE, (completed.stdout, completed.stderr)
        assert "expects the TEST endpoint" in completed.stderr
        assert _asked(calls) == []

    def test_the_flag_without_a_name_changes_nothing(self, world, tmp_path: Path) -> None:
        completed, calls = _verify(world, tmp_path, "--acme-rehearsal", env=_tls_env(tmp_path, name=None, staging=None))
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert _asked(calls) == []

    def test_that_step_is_shown_able_to_fail(self, world, tmp_path: Path) -> None:
        source = (ROOT / "infra/deploy/verify-deployed.sh").read_text(encoding="utf-8")
        block = re.compile(
            r"^\s*# >>> step: staging-certificate-is-a-failure\n.*?^\s*# <<< step: staging-certificate-is-a-failure\n",
            re.DOTALL | re.MULTILINE,
        )
        mutated, count = block.subn("", source)
        assert count == 1 and mutated != source
        _, deploy, _ = world
        cut = deploy / "verify-deployed.sh"
        cut.write_text(mutated, encoding="utf-8")
        completed, calls = _verify(world, tmp_path, env=_tls_env(tmp_path, staging="yes"), script=cut)
        assert "TEST endpoint" not in completed.stderr, completed.stderr
        assert _asked(calls) != [], "the mutant did not go on to ask, so this case was not testing that step"
