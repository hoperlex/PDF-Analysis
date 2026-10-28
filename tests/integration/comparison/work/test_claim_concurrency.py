"""No item is claimed twice (`CMP-WORK-01`, ADR-0025 decision 4; ADR verification 4's claim half).

Two facts, each shown on its own. The deterministic one: a claimant that holds an item open in its
transaction is *skipped* by a second claimant, which takes the next item or nothing instead of
queueing on the same row. The stress one: many workers draining one queue at once take every item
exactly once, with no error and no item left behind.
"""

from __future__ import annotations

import threading

from sqlalchemy import text

WORKERS = 8
ITEMS = 40


def test_a_second_claimant_skips_an_item_the_first_one_still_holds_open(queue, sessions, make_worker) -> None:
    only = queue.enqueue()
    first, second = make_worker(), make_worker()
    modules, kinds = frozenset({"versions"}), frozenset({queue.kind})
    holder = sessions()
    try:
        held = queue.repository.claim(holder, worker_id=first, modules=modules, kinds=kinds)
        assert held is not None and held.work_id == only
        with sessions() as rival:
            # With the row lock the rival never waits; without it the rival would pick the same
            # item and wait for the holder's uncommitted attempt number, so it is bounded.
            rival.execute(text("SET LOCAL lock_timeout = '1500ms'"))
            assert queue.repository.claim(rival, worker_id=second, modules=modules, kinds=kinds) is None
            rival.rollback()
        holder.commit()
    finally:
        holder.close()
    assert queue.work(only)["state"] == "running"
    assert len(queue.attempts(only)) == 1


def test_many_workers_draining_one_queue_take_every_item_exactly_once(queue, make_worker) -> None:
    items = {queue.enqueue(priority=index % 3) for index in range(ITEMS)}
    workers = [make_worker() for _ in range(WORKERS)]
    start = threading.Barrier(WORKERS)
    claimed: list[tuple[str, str]] = []
    failures: list[str] = []
    guard = threading.Lock()

    def drain(worker: str) -> None:
        start.wait(timeout=30)
        while True:
            try:
                item = queue.claim(worker)
            except Exception as failure:  # a collision surfaces as an error, never as a quiet pass
                with guard:
                    failures.append(f"{type(failure).__name__}: {failure}")
                return
            if item is None:
                return
            with guard:
                claimed.append((worker, item.work_id))

    threads = [threading.Thread(target=drain, args=(worker,)) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
        assert not thread.is_alive(), "a claimant is stuck"
    assert failures == []
    taken = [work_id for _, work_id in claimed]
    assert sorted(taken) == sorted(items), "every item is claimed, none twice"
    assert len({worker for worker, _ in claimed}) > 1, "the workers really shared the queue"
    for work_id in items:
        assert len(queue.attempts(work_id)) == 1
