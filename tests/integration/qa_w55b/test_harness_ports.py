"""`D-189` (`GATE-REPAIR-01`): the QA harness's own port discipline, with no database and no real API.

Two things went wrong in the complete gate on `59a1be91`, and both are properties of
``qa_support.py`` rather than of the application it drives:

* **the default pair sat inside the kernel's ephemeral range** (57500/57501; the range here is
  ``/proc/sys/net/ipv4/ip_local_port_range``, 32768-60999), and the free-port probe *connected*.
  A connect to an unused port in that range can connect to itself, and a connect says nothing
  about a socket that holds a port without listening. The probe now binds the way ``uvicorn``
  does, and the default pair is below the range;
* **readiness was one plane's.** ``serve.py`` starts the health plane on a thread and the API in
  the main thread, so ``/readyz`` answers about 25 ms before the API port is bound; a poll that
  landed in that window declared the child ready and the first call got
  ``ConnectionRefusedError`` (it failed one run in each of the two measurements of
  `GATE-REPAIR-01`, in ``test_p3_input_budget`` both times, the file that restarts the child at
  each ceiling). Ready now means both planes answer.

Each test below is built so that the old behaviour fails it; the module's docstrings name the
precondition they assert so that a kernel that behaves differently fails loudly, not silently.
The stand-in server is this file's own ``python -c`` child, never ``serve.py``, and it is the
only process these tests start.
"""

from __future__ import annotations

import http.server
import os
import shutil
import socket
import socketserver
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import w55b_qa_support as support
from w55b_qa_support import DEFAULT_API_PORT, HOST

#: A stand-in for ``serve.py``'s start-up order: the health plane first, the API plane later.
#: Both answer any ``GET`` with ``200``. It reads the ports the harness hands every child.
SLOW_API_STAND_IN = """
import http.server, os, socketserver, threading, time

class Answer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_):
        pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

host = os.environ["AUDITMANAGER_BIND_HOST"]
health = Server((host, int(os.environ["AUDITMANAGER_HEALTH_PORT"])), Answer)
threading.Thread(target=health.serve_forever, daemon=True).start()
time.sleep(1.5)  # the API binds well after the health plane
Server((host, int(os.environ["AUDITMANAGER_API_PORT"])), Answer).serve_forever()
"""


def _ephemeral_range() -> tuple[int, int]:
    low, high = Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()
    return int(low), int(high)


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def _strictly_free(port: int) -> bool:
    """Free even to a plain bind: no listener, no holder, no ``TIME_WAIT`` leftover."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
        return True


def _free_pair() -> tuple[int, int]:
    """Two consecutive ports below the ephemeral range, strictly free now, near the default pair.

    Strictly, because a test that holds one of them with a plain socket must be able to bind it:
    the previous test's stand-in leaves ``TIME_WAIT`` connections on its ports.
    """
    for api in range(DEFAULT_API_PORT + 100, DEFAULT_API_PORT + 200, 2):
        if _strictly_free(api) and _strictly_free(api + 1):
            return api, api + 1
    pytest.fail(f"no free port pair in {DEFAULT_API_PORT + 100}-{DEFAULT_API_PORT + 200}")


def _connect_says_free(port: int) -> bool:
    """The probe this module replaces: ``connect_ex`` != 0, i.e. nothing *listens* there."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((HOST, port)) != 0


@contextmanager
def _holding(port: int) -> Iterator[socket.socket]:
    """A socket that holds ``port`` and never listens: the case a connect cannot see."""
    held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        held.bind((HOST, port))
        yield held
    finally:
        held.close()


# --------------------------------------------------------------------------------------------
# the default pair
# --------------------------------------------------------------------------------------------


def test_the_default_port_pair_is_below_the_ephemeral_range() -> None:
    low, high = _ephemeral_range()
    for port in (DEFAULT_API_PORT, DEFAULT_API_PORT + 1):
        assert not low <= port <= high, (
            f"the harness default {port} is inside the kernel's ephemeral range {low}-{high}: "
            "the kernel hands it out as a client source port, a connect to it can connect to "
            "itself, and the served child then cannot bind (`D-189`)"
        )


def test_the_harness_uses_the_default_pair_unless_it_is_overridden() -> None:
    assert support.API_PORT == int(os.environ.get("W55B_QA_API_PORT", DEFAULT_API_PORT))
    assert support.HEALTH_PORT == int(os.environ.get("W55B_QA_HEALTH_PORT", support.API_PORT + 1))


# --------------------------------------------------------------------------------------------
# the probe binds
# --------------------------------------------------------------------------------------------


def test_a_port_nothing_holds_is_free() -> None:
    assert support._port_is_free(_unused_port())


def test_a_port_something_listens_on_is_not_free() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # as uvicorn sets it
        listener.bind((HOST, 0))
        listener.listen()
        assert not support._port_is_free(listener.getsockname()[1])


def test_a_port_held_without_listening_is_not_free() -> None:
    """The case ``connect_ex`` cannot see: the old probe called this port free."""
    port = _unused_port()
    with _holding(port):
        assert _connect_says_free(port), "premise: a connect to a held, silent port is refused"
        assert not support._port_is_free(port)


def test_a_port_that_connected_to_itself_is_not_free() -> None:
    """`D-189`'s own picture, ``127.0.0.1:P -> 127.0.0.1:P``: built by a simultaneous open."""
    port = _unused_port()
    with _holding(port) as held:
        held.settimeout(2)
        assert held.connect_ex((HOST, port)) == 0, "premise: a socket bound to P can connect to P"
        assert held.getsockname() == held.getpeername()
        assert _connect_says_free(port), "premise: the old probe called the port free"
        assert not support._port_is_free(port)


def test_the_leftover_of_a_stopped_child_does_not_make_the_port_busy() -> None:
    """The harness stops the child and starts another on the same ports at every ceiling.

    The old child's server-side connections sit in ``TIME_WAIT`` on the API port afterwards. The
    new child binds with ``SO_REUSEADDR``, so the port is free to it; a probe without the option
    would refuse a start that can be made.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST, 0))
        listener.listen()
        port = listener.getsockname()[1]
        with socket.create_connection((HOST, port), timeout=2) as client:
            server_side, _ = listener.accept()
            server_side.close()  # the server closes first: TIME_WAIT stays on its side
            assert client.recv(1) == b""
    time.sleep(0.2)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as strict:
        with pytest.raises(OSError):
            strict.bind((HOST, port))  # premise: the leftover is there, a plain bind refuses
    assert support._port_is_free(port)


# --------------------------------------------------------------------------------------------
# readiness is both planes
# --------------------------------------------------------------------------------------------


def _echo_server(stop: threading.Event, ready: threading.Event, box: list[int]) -> None:
    """Accepts, sends back what it received and closes: a connection that answered with itself."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, 0))
        server.listen()
        server.settimeout(0.2)
        box.append(server.getsockname()[1])
        ready.set()
        while not stop.is_set():
            try:
                connection, _ = server.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(1)
                try:
                    connection.sendall(connection.recv(4096))
                except OSError:
                    pass


def test_the_api_probe_wants_an_http_answer_and_not_a_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """A port that accepts and answers with the request line it was sent is not an API."""
    stop, ready, box = threading.Event(), threading.Event(), []
    thread = threading.Thread(target=_echo_server, args=(stop, ready, box), daemon=True)
    thread.start()
    try:
        assert ready.wait(5)
        monkeypatch.setattr(support, "API_PORT", box[0])
        with socket.create_connection((HOST, box[0]), timeout=2):
            pass  # premise: a bare connect succeeds
        assert not support._api_answers()
    finally:
        stop.set()
        thread.join(timeout=5)


def test_the_api_probe_is_false_for_a_closed_port_and_true_for_an_answering_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Answer(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_: object) -> None:
            pass

    monkeypatch.setattr(support, "API_PORT", _unused_port())
    assert not support._api_answers()
    with socketserver.TCPServer((HOST, 0), Answer) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            monkeypatch.setattr(support, "API_PORT", server.server_address[1])
            assert support._api_answers(), "any status is an answer: this is not a health check"
        finally:
            server.shutdown()


@pytest.fixture
def stand_in_control(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[support.ApiControl]:
    """The harness's own ``ApiControl``, pointed at a stand-in on a free pair of its own."""
    script = tmp_path / "slow_api.py"
    script.write_text(SLOW_API_STAND_IN, encoding="utf-8")
    api, health = _free_pair()
    monkeypatch.setattr(support, "API_PORT", api)
    monkeypatch.setattr(support, "HEALTH_PORT", health)
    monkeypatch.setattr(support, "PYTHON", Path(sys.executable))
    monkeypatch.setattr(support, "SERVE", script)
    monkeypatch.setattr(support, "lane_environment", lambda: {})
    control = support.ApiControl()
    try:
        yield control
    finally:
        control.stop()
        shutil.rmtree(control.log_directory, ignore_errors=True)


def test_the_child_is_ready_only_when_the_api_port_answers(stand_in_control: support.ApiControl) -> None:
    """The health plane answers about a second and a half before the API does, here.

    ``ensure`` must not return before the API answers: the call below is made the instant it
    returns. With health-only readiness it returns at the first poll after the health plane is
    up (about half a second) and this call is refused.
    """
    started = time.monotonic()
    stand_in_control.ensure(None)
    waited = time.monotonic() - started
    answer = support.call("GET", "/", timeout=5)
    assert answer.status == 200, answer
    assert waited >= 1.4, f"ensure returned after {waited:.2f} s, before the stand-in's API plane existed"


def test_the_harness_refuses_to_start_on_a_port_something_holds(
    stand_in_control: support.ApiControl,
) -> None:
    """A port already in use fails the session before any child is started."""
    with _holding(support.API_PORT):
        assert _connect_says_free(support.API_PORT), "premise: the old probe called the port free"
        with pytest.raises(pytest.fail.Exception, match=f"port {support.API_PORT} is already in use"):
            stand_in_control.ensure(None)
    assert stand_in_control.current is None
