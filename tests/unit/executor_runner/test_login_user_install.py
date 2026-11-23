"""`LOCAL-AGENT-01`: ``install.sh --login-user`` (the host agent under an existing account that holds the CLI logins) and ``--max-images``.

Every run happens under a temporary root with stand-in system commands, as in ``test_agent_install`` and ``test_host_install``; the
enrollment is real (``agent.py --enroll-only`` against the fake host stand over loopback). Nothing here touches the real system.
"""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

_NAME = "executor_runner_host_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_host_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
H = sys.modules[_NAME]
_INSTALL = "executor_runner_install_tests"
if _INSTALL not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_INSTALL, Path(__file__).with_name("test_agent_install.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_INSTALL] = _module
    _spec.loader.exec_module(_module)
TI = sys.modules[_INSTALL]
agent = TI.agent

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash and a POSIX host")

SECRET = H.HOST_SECRET

#: The stand-in ``getent``: ``root`` and ``alice`` always exist (alice's primary group is ``staff``); any other account only once
#: ``useradd`` has run, as in the shared stub.
_GETENT = r"""
  getent)
    case "$1:$2" in
      passwd:root) echo "root:x:0:0:root:/root:/bin/bash" ;;
      passwd:alice) echo "alice:x:1000:1000::/home/alice:/bin/bash" ;;
      group:0) echo "root:x:0:" ;;
      group:1000) echo "staff:x:1000:" ;;
      group:*) exit 2 ;;
      *) [ -f "$d/user" ] || exit 2
         echo "$2:x:998:998::/var/lib/pdf-analysis-agent:/usr/sbin/nologin" ;;
    esac ;;
"""


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("loginpackage")
    built = subprocess.run([sys.executable, str(H.RUNNER_DIR / "package.py"), "--version", TI.VERSION, "--out", str(out / "pkg")],
                           capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stderr
    archive = out / "pkg" / f"auditmanager-agent-{TI.VERSION}.tar.gz"
    unpacked = out / "unpacked"
    unpacked.mkdir()
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(unpacked, filter="data")
    return {"archive": archive, "unpacked": unpacked, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


@pytest.fixture
def host(tmp_path, package):
    made = TI.Host(tmp_path, package["unpacked"])
    stub = TI._STUB
    start = stub.index("  getent)")
    end = stub.index("  runuser)")
    (made.syscmd / "getent").write_text(stub[:start] + _GETENT.lstrip("\n") + stub[end:])
    return made


def _run(host, stand, *args, secret=SECRET, **kwargs):
    return host.run(stand, *args, model=None, secret=secret, **kwargs)


def _dropin(host) -> Path:
    return host.path("/etc/systemd/system/pdf-analysis-agent.service.d/20-login-user.conf")


def test_login_user_root_runs_the_host_agent_under_root_with_its_home_and_the_wrapper_directory(host):
    with H.HostStand() as stand:
        host.detected("claude_code access=subscription auth=valid version=2.1.328\ncodex access=subscription auth=valid version=0.169.0\n")
        done = _run(host, stand, "--login-user", "root")
        assert done.returncode == 0, done.stdout + done.stderr
        assert host.token().startswith("amr_enr01_")
    unit = host.unit.read_text()
    assert "\nUser=root\n" in unit and "\nGroup=root\n" in unit
    dropin = _dropin(host).read_text()
    assert "\nEnvironment=HOME=/root\n" in dropin
    assert ("\nEnvironment=PDF_ANALYSIS_CLI_DIRS=/opt/pdf-analysis-cli/bin:/root/.local/bin:/root/.npm-global/bin:"
            "/usr/local/bin:/usr/bin:/bin:/snap/bin\n") in dropin
    assert "\nProtectHome=false\n" in dropin and "\nReadWritePaths=/root\n" in dropin
    assert host.commands("useradd") == [], "no account is created for an existing login user"
    detect_calls = [line for line in host.commands("runuser") if "detect.py" in line]
    assert detect_calls and detect_calls[-1].startswith("runuser -u root -- /usr/bin/env -i HOME=/root LANG=C.UTF-8 PDF_ANALYSIS_CLI_DIRS=/opt/")
    assert "under the user root, as a host agent" in done.stdout
    assert "serves the CLIs the account root is signed in to" in done.stdout
    assert "claude auth login" not in done.stdout, "nobody signs in again: the account's own logins are used"
    assert agent.load_config(str(host.config)).mode == "host"
    assert host.leaks == []


def test_login_user_takes_the_accounts_primary_group_and_home(host):
    with H.HostStand() as stand:
        done = _run(host, stand, "--login-user", "alice")
        assert done.returncode == 0, done.stdout + done.stderr
    unit = host.unit.read_text()
    assert "\nUser=alice\n" in unit and "\nGroup=staff\n" in unit
    dropin = _dropin(host).read_text()
    assert "\nEnvironment=HOME=/home/alice\n" in dropin and "\nReadWritePaths=/home/alice\n" in dropin


def test_max_images_is_written_into_a_new_host_config_and_the_agent_reads_it(host):
    with H.HostStand() as stand:
        done = _run(host, stand, "--login-user", "root", "--max-images", "8")
        assert done.returncode == 0, done.stdout + done.stderr
    text = host.config.read_text()
    assert "\naccept_images = true\nmax_images = 8\n" in text
    cfg = agent.load_config(str(host.config))
    assert cfg.host.accept_images is True and cfg.host.max_images == 8


def test_without_max_images_the_host_config_keeps_the_default_of_no_images(host):
    with H.HostStand() as stand:
        assert _run(host, stand, "--login-user", "root").returncode == 0
    assert "# accept_images = false" in host.config.read_text()
    assert agent.load_config(str(host.config)).host.accept_images is False


@pytest.mark.parametrize(
    ("args", "words"),
    [
        (("--login-user", "root", "--service-user", "pdf-agent"), "exclude each other"),
        (("--login-user", "Root"), "--login-user must be a lower-case account name"),
        (("--max-images", "9"), "--max-images must be an integer in 1..8"),
        (("--max-images", "0"), "--max-images must be an integer in 1..8"),
    ],
)
def test_bad_login_user_or_image_options_are_refused_before_anything_changes(host, args, words):
    with H.HostStand() as stand:
        done = _run(host, stand, *args)
        assert done.returncode == 64 and words in done.stderr, done.stderr
        assert not host.root.exists() and stand.requests == []


def test_login_user_with_a_model_is_refused(host):
    with H.HostStand() as stand:
        done = host.run(stand, "--login-user", "root", model="claude-opus-5", secret=SECRET)
    assert done.returncode == 64 and "--login-user is for a host agent" in done.stderr, done.stderr


def test_an_account_that_does_not_exist_is_refused(host):
    with H.HostStand() as stand:
        done = _run(host, stand, "--login-user", "nobody-here")
    assert done.returncode == 66 and "there is no such account" in done.stderr, done.stderr
    assert host.token() == ""


def test_a_rerun_keeps_the_token_and_a_run_without_login_user_goes_back_to_the_service_user(host):
    with H.HostStand() as stand:
        assert _run(host, stand, "--login-user", "root", "--max-images", "8").returncode == 0
        token = host.token()
        again = _run(host, stand, "--login-user", "root", "--max-images", "8", secret=None)
        assert again.returncode == 0, again.stderr
        assert host.token() == token and "the service is running and nothing changed" in again.stdout
        back = _run(host, stand, secret=None)
        assert back.returncode == 0, back.stderr
    assert host.token() == token
    assert not _dropin(host).exists() and "removed the --login-user drop-in" in back.stdout
    assert "\nUser=pdf-agent\n" in host.unit.read_text()
    assert host.commands("useradd"), "the dedicated service user is created again"
    assert any(" restart " in line for line in host.commands("systemctl")), "the change of account restarts the service"


def test_uninstall_removes_the_login_user_drop_in(host):
    with H.HostStand() as stand:
        assert _run(host, stand, "--login-user", "root").returncode == 0
    (host.syscmd / "active").touch()
    gone = subprocess.run(["bash", "install.sh", "--uninstall"], cwd=host.unpacked, capture_output=True, text=True, timeout=60,
                          env={"PATH": "/usr/bin:/bin", "AUDITMANAGER_INSTALL_ROOT": str(host.root),
                               "AUDITMANAGER_INSTALL_SYSCMD_DIR": str(host.syscmd), "AUDITMANAGER_PYTHON": sys.executable})
    assert gone.returncode == 0, gone.stderr
    assert not _dropin(host).exists() and not _dropin(host).parent.exists()
    assert not host.unit.exists()
