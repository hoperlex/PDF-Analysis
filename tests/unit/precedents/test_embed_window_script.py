"""`EMBED-01`: the host side of the night encoder (`infra/deploy/embed-window.sh`), driven with a docker shim.

No docker, no systemd and no network are touched: ``EMBED_DOCKER`` is a script of this test that records every call and plays the container, ``systemctl``
is another one on the ``PATH``. What is shown is what the worker relies on -- the heartbeat, the ``result`` in each way a container can end (done,
killed, stopped at the deadline, stopped by ``abort``, no image), that nothing runs without a request or twice -- and what ``deploy.sh`` relies on: a
build refused before it starts when the disk cannot hold the image.
"""

from __future__ import annotations

import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "infra" / "deploy" / "embed-window.sh"
DEADLINE_FAR = 4_102_444_800   # 2100-01-01

SHIM = r"""#!/usr/bin/env bash
# A docker for the test: every call is logged; the container is played by `compose ... run` according to $SHIM_MODE.
echo "docker $*" >>"$SHIM_DIR/calls.log"
case "$1" in
  image) [ "${SHIM_IMAGE:-present}" = present ] || [ -e "$SHIM_DIR/built" ]; exit $? ;;
  rm) exit 0 ;;
  stop) : >"$SHIM_DIR/stopped"; exit 0 ;;
  volume) echo "$EMBED_DIR"; exit 0 ;;
  info) echo "/"; exit 0 ;;
  compose)
    case " $* " in
      *" build "*) [ "${SHIM_BUILD_STATUS:-0}" = 0 ] && : >"$SHIM_DIR/built"; exit "${SHIM_BUILD_STATUS:-0}" ;;
      *" run "*)
        case "${SHIM_MODE:-ok}" in
          ok) printf '{}' >"$EMBED_DIR/response.json"; echo "encoded" >&2; exit 0 ;;
          oom) echo "Killed" >&2; exit 137 ;;
          fail) echo "refused: boom" >&2; exit 2 ;;
          hang) while [ ! -e "$SHIM_DIR/stopped" ]; do sleep 0.05; done; exit 143 ;;
        esac ;;
    esac ;;
esac
exit 0
"""

SYSTEMCTL = r"""#!/usr/bin/env bash
case "$1" in
  is-enabled) [ "${SHIM_TIMER_ENABLED:-yes}" = yes ] ;;
  is-active) [ "${SHIM_TIMER_ACTIVE:-yes}" = yes ] ;;
  *) exit 0 ;;
esac
"""


def executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class Rig:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.exchange = tmp / "exchange"
        self.exchange.mkdir()
        self.shim_dir = tmp / "shim"
        self.shim_dir.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        self.docker = executable(self.shim_dir / "docker", SHIM)
        executable(self.bin / "systemctl", SYSTEMCTL)
        self.env_file = tmp / "alpha.env"
        self.env_file.write_text("ALPHA_INSTANCE=am-test\nALPHA_MEM_LIMIT_EMBEDDER=3500m\n", encoding="utf-8")

    def run(self, command: str, **extra: str) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.tmp), "EMBED_DIR": str(self.exchange), "EMBED_DOCKER": str(self.docker),
            "SHIM_DIR": str(self.shim_dir), "EMBED_POLL_SECONDS": "0.05", **extra,
        }
        return subprocess.run(["bash", str(SCRIPT), command, "--env-file", str(self.env_file)], env=env, capture_output=True, text=True, timeout=60, check=False)

    def request(self, deadline: int = DEADLINE_FAR) -> None:
        (self.exchange / "request.json").write_text('{"format":"x"}\n', encoding="utf-8")
        (self.exchange / "deadline").write_text(f"{deadline}\n", encoding="utf-8")

    def result(self) -> dict[str, str]:
        path = self.exchange / "result"
        return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").split()) if path.exists() else {}

    def calls(self) -> list[str]:
        path = self.shim_dir / "calls.log"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def ran_a_container(self) -> bool:
        return any(" run " in f" {call} " and "compose" in call for call in self.calls())


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    return Rig(tmp_path)


# -- the tick ------------------------------------------------------------------------------------------------------------


def test_a_tick_with_no_request_writes_the_heartbeat_and_runs_nothing(rig: Rig) -> None:
    done = rig.run("tick", EMBED_NOW="1800000000")
    assert done.returncode == 0, done.stderr
    assert (rig.exchange / "heartbeat").read_text(encoding="utf-8") == "epoch=1800000000\n"
    assert not rig.ran_a_container() and not (rig.exchange / "result").exists()


def test_a_request_runs_the_container_once_under_the_compose_profile_and_reports_done(rig: Rig) -> None:
    rig.request()
    done = rig.run("tick", EMBED_NOW="1800000000")
    assert done.returncode == 0, done.stderr
    assert rig.result() == {"exit_code": "0", "finished_epoch": "1800000000"}
    runs = [call for call in rig.calls() if " run " in f" {call} "]
    assert len(runs) == 1
    assert "--profile embedder" in runs[0] and "--no-deps" in runs[0] and "embedder" in runs[0].split()[-1]
    assert "--name am-test-embedder-window" in runs[0], "the container has the exact name the script may stop"
    assert "rm -f am-test-embedder-window" in "\n".join(rig.calls()), "a leftover of that exact name is removed, nothing by pattern"


def test_a_second_tick_does_not_run_the_container_again_before_the_worker_has_read_the_result(rig: Rig) -> None:
    rig.request()
    rig.run("tick", EMBED_NOW="1800000000")
    before = len(rig.calls())
    rig.run("tick", EMBED_NOW="1800000060")
    assert len(rig.calls()) == before, "docker was not asked anything"
    assert (rig.exchange / "heartbeat").read_text(encoding="utf-8") == "epoch=1800000060\n", "but the heartbeat moved"


def test_a_killed_container_is_137_and_what_it_said_is_kept(rig: Rig) -> None:
    rig.request()
    rig.run("tick", EMBED_NOW="1800000000", SHIM_MODE="oom")
    assert rig.result()["exit_code"] == "137"
    assert "Killed" in (rig.exchange / "stderr.log").read_text(encoding="utf-8")


def test_a_container_that_fails_reports_its_own_status(rig: Rig) -> None:
    rig.request()
    rig.run("tick", EMBED_NOW="1800000000", SHIM_MODE="fail")
    assert rig.result()["exit_code"] == "2"
    assert "refused: boom" in (rig.exchange / "stderr.log").read_text(encoding="utf-8")


def test_no_image_is_127_and_no_container_is_started(rig: Rig) -> None:
    rig.request()
    rig.run("tick", EMBED_NOW="1800000000", SHIM_IMAGE="absent")
    assert rig.result()["exit_code"] == "127" and not rig.ran_a_container()
    assert "ALPHA_EMBEDDER=yes" in (rig.exchange / "stderr.log").read_text(encoding="utf-8")


def test_a_request_whose_deadline_has_passed_is_124_and_no_container_is_started(rig: Rig) -> None:
    rig.request(deadline=1799999999)
    rig.run("tick", EMBED_NOW="1800000000")
    assert rig.result()["exit_code"] == "124" and not rig.ran_a_container()


def test_a_request_with_no_readable_deadline_is_refused_by_the_container_never_run(rig: Rig) -> None:
    (rig.exchange / "request.json").write_text("{}", encoding="utf-8")
    rig.run("tick", EMBED_NOW="1800000000")
    assert rig.result()["exit_code"] == "2" and not rig.ran_a_container()


def test_abort_stops_the_container_by_its_name_and_reports_130(rig: Rig) -> None:
    rig.request()
    (rig.exchange / "abort").write_text("abort\n", encoding="utf-8")
    rig.run("tick", SHIM_MODE="hang")
    assert rig.result()["exit_code"] == "130"
    assert "docker stop --time 10 am-test-embedder-window" in rig.calls()


def test_the_deadline_stops_a_container_that_is_still_running_and_reports_124(rig: Rig) -> None:
    rig.request(deadline=int(time.time()) + 1)
    started = time.monotonic()
    rig.run("tick", SHIM_MODE="hang")
    assert rig.result()["exit_code"] == "124"
    assert "docker stop --time 10 am-test-embedder-window" in rig.calls()
    assert time.monotonic() - started < 30


def test_a_response_with_no_result_means_the_container_finished_and_is_not_run_again(rig: Rig) -> None:
    rig.request()
    (rig.exchange / "response.json").write_text("{}", encoding="utf-8")
    rig.run("tick", EMBED_NOW="1800000000")
    assert rig.result()["exit_code"] == "0" and not rig.ran_a_container()


def test_a_volume_that_does_not_exist_yet_is_not_an_error(rig: Rig) -> None:
    done = rig.run("tick", EMBED_DIR=str(rig.tmp / "no-such-volume"))
    assert done.returncode == 0 and "does not exist yet" in done.stdout


def test_an_environment_with_no_instance_is_refused(rig: Rig) -> None:
    rig.env_file.write_text("OTHER=1\n", encoding="utf-8")
    done = rig.run("tick")
    assert done.returncode == 3 and "ALPHA_INSTANCE" in done.stderr


# -- the image: the disk is asked before the build --------------------------------------------------------------------------


def builds(rig: Rig) -> list[str]:
    return [call for call in rig.calls() if "compose" in call and " build " in f" {call} "]


def test_a_disk_that_cannot_hold_the_image_refuses_the_build_before_it_starts(rig: Rig) -> None:
    done = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="9")
    assert done.returncode == 3 and "9 GiB free, 12 GiB needed" in done.stderr
    assert builds(rig) == [], "the build never started"


def test_a_disk_with_room_builds_the_service_under_its_profile(rig: Rig) -> None:
    done = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="12")
    assert done.returncode == 0, done.stderr
    assert len(builds(rig)) == 1 and "--profile embedder" in builds(rig)[0] and builds(rig)[0].endswith("build embedder")


def test_the_threshold_is_the_environments_when_it_says_one(rig: Rig) -> None:
    rig.env_file.write_text("ALPHA_INSTANCE=am-test\nALPHA_MEM_LIMIT_EMBEDDER=3500m\nALPHA_EMBEDDER_BUILD_MIN_FREE_GB=20\n", encoding="utf-8")
    assert rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="15").returncode == 3
    rig.env_file.write_text("ALPHA_INSTANCE=am-test\nALPHA_MEM_LIMIT_EMBEDDER=3500m\nALPHA_EMBEDDER_BUILD_MIN_FREE_GB=lots\n", encoding="utf-8")
    refused = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="99")
    assert refused.returncode == 3 and "not a whole number" in refused.stderr


def test_an_image_that_is_there_is_not_rebuilt_unless_asked(rig: Rig) -> None:
    done = rig.run("build-image", SHIM_IMAGE="present", EMBED_FREE_GIB="1")
    assert done.returncode == 0 and builds(rig) == [] and "not rebuilt" in done.stdout
    again = rig.run("build-image", SHIM_IMAGE="present", EMBED_FREE_GIB="1", ALPHA_EMBEDDER_REBUILD="yes")
    assert again.returncode == 3, "a rebuild is a build: the disk is asked first"


def test_a_failed_build_is_a_refusal(rig: Rig) -> None:
    done = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="50", SHIM_BUILD_STATUS="1")
    assert done.returncode == 3 and "build of the encoder's image failed" in done.stderr


# -- the verification verify-deployed.sh asks -------------------------------------------------------------------------------


def test_verify_wants_the_image_the_timer_and_a_fresh_heartbeat(rig: Rig) -> None:
    (rig.exchange / "heartbeat").write_text("epoch=1799999900\n", encoding="utf-8")
    ok = rig.run("verify", EMBED_NOW="1800000000")
    assert ok.returncode == 0 and "100 s old" in ok.stdout, ok.stderr
    assert rig.run("verify", EMBED_NOW="1800000000", SHIM_IMAGE="absent").returncode == 3
    assert "not enabled" in rig.run("verify", EMBED_NOW="1800000000", SHIM_TIMER_ENABLED="no").stderr
    assert "not active" in rig.run("verify", EMBED_NOW="1800000000", SHIM_TIMER_ACTIVE="no").stderr
    stale = rig.run("verify", EMBED_NOW="1800001000")
    assert stale.returncode == 3 and "1100 s old" in stale.stderr
    (rig.exchange / "heartbeat").unlink()
    assert "never written a heartbeat" in rig.run("verify", EMBED_NOW="1800000000").stderr


# -- the memory limit is demanded, never defaulted -----------------------------------------------------------------------------


def without_limit(rig: Rig, how: str = "absent") -> None:
    rig.env_file.write_text("ALPHA_INSTANCE=am-test\n" + ("ALPHA_MEM_LIMIT_EMBEDDER=\n" if how == "empty" else ""), encoding="utf-8")


@pytest.mark.parametrize("how", ["absent", "empty"])
def test_the_build_refuses_without_the_limit_and_builds_nothing(rig: Rig, how: str) -> None:
    without_limit(rig, how)
    done = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="99")
    assert done.returncode == 3 and "ALPHA_MEM_LIMIT_EMBEDDER is unset or empty" in done.stderr
    assert builds(rig) == [], "compose would render 3g; nothing is built on it"


@pytest.mark.parametrize("how", ["absent", "empty"])
def test_the_run_refuses_without_the_limit_tells_the_worker_and_starts_no_container(rig: Rig, how: str) -> None:
    without_limit(rig, how)
    rig.request()
    done = rig.run("tick", EMBED_NOW="1800000000")
    assert done.returncode == 3 and "ALPHA_MEM_LIMIT_EMBEDDER is unset or empty" in done.stderr
    assert not rig.ran_a_container(), "the encoder never starts on the compose default"
    assert rig.result()["exit_code"] == "2", "the worker is told: a failed container is a loud skipped window"
    assert "ALPHA_MEM_LIMIT_EMBEDDER" in (rig.exchange / "stderr.log").read_text(encoding="utf-8")
    assert (rig.exchange / "heartbeat").exists(), "the timer is still seen alive: it is the value that is missing, not the timer"


def test_a_tick_with_nothing_to_run_does_not_need_the_limit(rig: Rig) -> None:
    without_limit(rig)
    assert rig.run("tick", EMBED_NOW="1800000000").returncode == 0


def test_install_and_verify_refuse_without_the_limit(rig: Rig) -> None:
    without_limit(rig)
    target = rig.tmp / "units"
    refused = rig.run("install", EMBED_SYSTEMD_DIR=str(target))
    assert refused.returncode == 3 and "ALPHA_MEM_LIMIT_EMBEDDER" in refused.stderr and not target.exists()
    (rig.exchange / "heartbeat").write_text("epoch=1799999900\n", encoding="utf-8")
    verified = rig.run("verify", EMBED_NOW="1800000000")
    assert verified.returncode == 3 and "ALPHA_MEM_LIMIT_EMBEDDER" in verified.stderr


def test_the_environment_of_the_call_counts_as_compose_reads_it(rig: Rig) -> None:
    without_limit(rig)
    done = rig.run("build-image", SHIM_IMAGE="absent", EMBED_FREE_GIB="99", ALPHA_MEM_LIMIT_EMBEDDER="3500m")
    assert done.returncode == 0 and len(builds(rig)) == 1


# -- the units ---------------------------------------------------------------------------------------------------------------


def test_install_writes_both_units_with_the_paths_filled_in(rig: Rig) -> None:
    target = rig.tmp / "units"
    done = rig.run("install", EMBED_SYSTEMD_DIR=str(target))
    assert done.returncode == 0, done.stderr
    service = (target / "auditmanager-embed-window.service").read_text(encoding="utf-8")
    timer = (target / "auditmanager-embed-window.timer").read_text(encoding="utf-8")
    assert "@" not in "".join(line for line in service.splitlines() if not line.startswith("#"))
    assert f"ExecStart={SCRIPT.parent.parent.parent}/infra/deploy/embed-window.sh tick --env-file {rig.env_file}" in service
    assert "Type=oneshot" in service and "TimeoutStartSec=infinity" in service
    assert "OnUnitInactiveSec=1min" in timer and "WantedBy=timers.target" in timer
