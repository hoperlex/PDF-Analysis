"""`EMBED-01`: one night end to end through the REAL pieces on both sides of the exchange, with only docker and the model replaced.

The worker's pass (``VectorWindowPass``) leaves the batch; the host's script (``infra/deploy/embed-window.sh tick``, the file itself) finds it, runs the
container -- here a ``docker`` that executes the real in-image entry (``infra/norms-worker/embed_intents.py``) over a fake encoder, in a process of its own, as
the container would -- and reports; the pass imports the answer. Each side is tested alone elsewhere against files its test wrote; this is where a file name, a
status or a format that the two sides understand differently would show, because nothing here is written by the test but the cases and the clock.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents.public import Exchange, VectorWindowPass
from auditmanager.precedents.vectors.intents import build_finding_view, input_sha256

pytestmark = pytest.mark.usefixtures("quiet_queue")

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra" / "deploy" / "embed-window.sh"


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


w = _load("embed01_vector_window_support", "vector_window_support.py")

#: What the container runs: the real entry, over an encoder where a character is a token (so a view of 600 characters is over the limit of 512).
CONTAINER = '''
import importlib.util, math, sys
from collections.abc import Sequence
spec = importlib.util.spec_from_file_location("embed_intents_real", sys.argv[1])
entry = importlib.util.module_from_spec(spec); sys.modules[spec.name] = entry; spec.loader.exec_module(entry)
from auditmanager.norms.embedding import vectors

class Encoder:
    def count_tokens(self, text):
        return len(text)
    def encode(self, texts):
        out = []
        for value in texts:
            seed = sum(ord(c) for c in value)
            raw = [math.sin(seed * 0.7 + i * 0.011) for i in range(1024)]
            norm = math.sqrt(sum(x * x for x in raw))
            out.append(vectors.pack([x / norm for x in raw]))
        return out

sys.exit(entry.main(sys.argv[2:], load=Encoder))
'''

DOCKER = '''#!/usr/bin/env bash
echo "docker $*" >>"$ROUND_DIR/calls.log"
case "$1" in
  image) exit 0 ;;
  rm|stop) exit 0 ;;
  volume) echo "$EMBED_DIR"; exit 0 ;;
  compose)
    case " $* " in
      *" run "*)
        exec "$PYTHON" "$ROUND_DIR/container.py" "$ENTRY" \\
          --in "$EMBED_DIR/request.json" --out "$EMBED_DIR/response.json" --over-limit-out "$EMBED_DIR/over_limit.json" ;;
    esac ;;
esac
exit 0
'''


def host_tick(tmp: Path, exchange: Path, env_file: Path, *, now: int) -> subprocess.CompletedProcess[str]:
    (tmp / "container.py").write_text(CONTAINER, encoding="utf-8")
    docker = tmp / "docker"
    docker.write_text(DOCKER, encoding="utf-8")
    docker.chmod(0o755)
    env = {
        "PATH": os.environ["PATH"], "HOME": str(tmp), "EMBED_DIR": str(exchange), "EMBED_DOCKER": str(docker), "ROUND_DIR": str(tmp),
        "PYTHON": sys.executable, "PYTHONPATH": str(ROOT / "src"), "ENTRY": str(ROOT / "infra" / "norms-worker" / "embed_intents.py"),
        "EMBED_NOW": str(now), "EMBED_POLL_SECONDS": "0.05",
    }
    return subprocess.run(["bash", str(SCRIPT), "tick", "--env-file", str(env_file)], env=env, capture_output=True, text=True, timeout=120, check=False)


def test_a_night_goes_from_the_workers_batch_through_the_host_script_and_the_real_entry_to_stored_vectors(
    tmp_path: Path, engine: Engine, sessions: sessionmaker[Session],
) -> None:
    w.reset_control(sessions)
    try:
        with sessions() as session:
            session.execute(text(
                "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = 'test_cleanup', state_changed_at = clock_timestamp() "
                "WHERE state = 'pending'"))
            session.commit()
        exchange_dir = tmp_path / "exchange"
        exchange_dir.mkdir()
        env_file = tmp_path / "alpha.env"
        env_file.write_text("ALPHA_INSTANCE=am-roundtrip\n", encoding="utf-8")
        short = w.add_case(engine, finding="Круговой рейс: короткая находка про высоту помещения")
        long = w.add_case(engine, finding="Круговой рейс: " + "очень длинная находка " * 40)
        now = int(w.INSIDE.timestamp())
        vector_pass = VectorWindowPass(sessions, Exchange(exchange_dir), interval_seconds=0)

        assert host_tick(tmp_path, exchange_dir, env_file, now=now).returncode == 0   # the timer's first look: nothing to run, a heartbeat
        assert (exchange_dir / "heartbeat").read_text(encoding="utf-8") == f"epoch={now}\n"
        vector_pass.run(w.INSIDE)
        assert w.control(sessions)["state"] == "encoding" and (exchange_dir / "request.json").is_file()

        ticked = host_tick(tmp_path, exchange_dir, env_file, now=now)
        assert ticked.returncode == 0, ticked.stderr
        assert (exchange_dir / "result").read_text(encoding="utf-8") == f"exit_code=0\nfinished_epoch={now}\n"
        assert (exchange_dir / "response.json").is_file() and (exchange_dir / "over_limit.json").is_file()

        vector_pass.run(w.INSIDE)
        assert w.control(sessions) == {"paused": False, "state": "closed", "reason": None}
        intents = w.intents_of(sessions, [short, long])
        assert intents[short]["state"] == "done" and intents[long]["state"] == "poisoned" and intents[long]["reason"] == "token_limit_exceeded"
        stored = w.embeddings_of(sessions, [short, long])
        assert set(stored) == {short}
        view = build_finding_view(category="dimensions", finding_text="Круговой рейс: короткая находка про высоту помещения", recommendation_text="Привести в соответствие.")
        assert stored[short]["digest"] == input_sha256(view) and stored[short]["dims"] == 1024 and abs(stored[short]["norm"] - 1.0) <= 0.0001
        assert sorted(p.name for p in exchange_dir.iterdir() if not p.name.startswith(".")) == ["heartbeat"], "the worker cleared the round"
        runs = [line for line in (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines() if " run " in f" {line} "]
        assert len(runs) == 1 and "--profile embedder" in runs[0]
    finally:
        w.reset_control(sessions)
