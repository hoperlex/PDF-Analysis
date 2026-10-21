"""`D-185`: the compute cost of the optimisation pass, stage by stage, at the bounds, with no stack.

Not collected by pytest (the name does not match ``test_*.py``). Run it by name::

    PYTHONPATH=src .venv/bin/python tests/unit/optimisation/proposals/measure_stage_costs.py <scenario>

and it prints, for one scenario at 20 000 positions and 10 000 specification rows (the largest
inputs ``MAX_DATA_ROWS`` and ``MAX_SPECIFICATION_ROWS`` allow; ``POSITIONS`` and ``ROWS`` in the
environment shrink them), the wall and CPU time of the three pure stages of
:func:`~auditmanager.optimisation.proposals.commands.start_optimisation_pass` -- the extraction of the
specification from its text layer, the matching of its rows to the price list, and the generation of
the proposals -- and the process's peak resident set so far, then a digest of every proposal (ordinal, row, both
positions, bases, similarity, saving, rationale) so that two trees can be compared. The database, the object store and the
HTTP layer are not in it; ``tests/integration/optimisation/proposals/measure_worst_case_pass.py``
measures the whole request, with the same scenarios.

The scenarios are shapes of one input, because the bounds fix its size and not its shape and the cost
is a function of the shape (see ``docs/program/API-FOLLOWUPS-01.md``): ``catalogue``,
``one_head_similar``, ``one_head_dissimilar``, ``two_words``, ``common_code_token``, ``rich`` and the
contrived ``overlap_dissimilar``, ``long_overlap``, ``wide_vocabulary`` and ``flat_price``. A scenario names a price list and the descriptions of the rows that
each match exactly one of its positions.
"""

from __future__ import annotations

import hashlib
import os
import random
import resource
import sys
import time
from decimal import Decimal

from auditmanager.optimisation.matching import match_specification
from auditmanager.optimisation.proposals.generator import generate_cheaper_analogs
from auditmanager.optimisation.repository import PriceListPositionRecord
from auditmanager.optimisation.specification import MAX_SPECIFICATION_ROWS, extract_specification

HEADER = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
)
POSITIONS = int(os.environ.get("POSITIONS", 20_000))
ROWS = int(os.environ.get("ROWS", MAX_SPECIFICATION_ROWS))
ROWS_PER_PAGE = 40
VENDORS = [f"Поставщик{n}" for n in range(500)]


def _pages(names: list[str]) -> dict[int, str]:
    pages: dict[int, str] = {}
    for start in range(0, len(names), ROWS_PER_PAGE):
        lines = [HEADER]
        for offset, name in enumerate(names[start : start + ROWS_PER_PAGE], start=1):
            lines.append(f"{offset} {name} шт {1 + (start + offset) % 50}\n")
        pages[start // ROWS_PER_PAGE + 1] = "".join(lines)
    return pages


def _position(
    index: int, *, name: str, rnd: random.Random, code: str | None = None, mark: str | None = None,
    price: Decimal | None = None,
) -> PriceListPositionRecord:
    return PriceListPositionRecord(
        price_list_position_id=f"prp_{index:026d}", price_list_id="prl_x", row_number=index + 2,
        code=code, name=name, mark=mark, unit="шт",
        unit_price=price if price is not None else Decimal(rnd.randint(1000, 900000)) / 100,
        currency="RUB", vendor=VENDORS[rnd.randrange(len(VENDORS))], section_code=None,
    )


def _scenario(kind: str, rnd: random.Random) -> tuple[list[PriceListPositionRecord], list[str]]:
    every_other = lambda names: [names[(2 * k) % POSITIONS] for k in range(ROWS)]  # noqa: E731
    if kind == "catalogue":
        names = [f"Материал{i % 200} тип {i}" for i in range(POSITIONS)]
        return [_position(i, name=names[i], rnd=rnd) for i in range(POSITIONS)], every_other(names)
    if kind == "one_head_similar":
        names = [f"Профиль вариант {i}" for i in range(POSITIONS)]
        return [_position(i, name=names[i], rnd=rnd) for i in range(POSITIONS)], every_other(names)
    if kind == "one_head_dissimilar":
        names = [f"Профиль {i}x{(i * 7919) % 10007} z{i % 977} q{(i * 31) % 4999}" for i in range(POSITIONS)]
        return [_position(i, name=names[i], rnd=rnd) for i in range(POSITIONS)], every_other(names)
    if kind == "two_words":
        names = [f"Профиль {i}" for i in range(POSITIONS)]
        return [_position(i, name=names[i], rnd=rnd) for i in range(POSITIONS)], every_other(names)
    if kind == "common_code_token":
        names = [f"Плита {i}" for i in range(POSITIONS)]
        positions = [_position(i, name=names[i], code=f"ПК {10000 + i}", rnd=rnd) for i in range(POSITIONS)]
        return positions, [f"Плита ПК {10000 + (2 * k) % POSITIONS}" for k in range(ROWS)]
    if kind == "rich":
        filler = " ".join(f"слово{w}" for w in range(30))
        names = [f"Изделие {i} {filler} типоразмер {i % 97}" for i in range(POSITIONS)]
        positions = [
            _position(i, name=names[i], code=f"АБВ {20000 + i}", mark=f"МК-{i}", rnd=rnd)
            for i in range(POSITIONS)
        ]
        return positions, every_other(names)
    if kind == "overlap_dissimilar":
        names = [
            f"Профиль {i}n " + " ".join(f"с{slot}в{rnd.randrange(20)}" for slot in range(6))
            for i in range(POSITIONS)
        ]
        positions = [_position(i, name=names[i], price=Decimal(i + 1), rnd=rnd) for i in range(POSITIONS)]
        return positions, [names[POSITIONS - 1 - k] for k in range(ROWS)]  # the dearest: longest prefixes
    if kind == "flat_price":
        # Half the list at one price, all alike, and the rows are the other half: every row has one
        # equal-price group of POSITIONS / 2 analogs to order.
        names = [f"Профиль вариант {i}" for i in range(POSITIONS)]
        half = POSITIONS // 2
        positions = [
            _position(i, name=names[i], price=Decimal(1) if i < half else Decimal(2 + i), rnd=rnd)
            for i in range(POSITIONS)
        ]
        return positions, [names[half + (k % half)] for k in range(ROWS)]
    if kind == "long_overlap":
        # Contrived, and the dearest the search can be made: 60-word names (about 400 bytes, what the
        # 10 MiB cap allows at 20 000 rows) drawn from 200 words, so every pair shares words and none
        # comes near the threshold, and the rows are the dearest positions.
        vocabulary = [f"слово{n}" for n in range(200)]
        names = [f"Профиль {i}n " + " ".join(rnd.sample(vocabulary, 60)) for i in range(POSITIONS)]
        positions = [_position(i, name=names[i], price=Decimal(i + 1), rnd=rnd) for i in range(POSITIONS)]
        return positions, [names[POSITIONS - 1 - k] for k in range(ROWS)]
    if kind == "wide_vocabulary":
        # Contrived, against the names' masks: 60-word names drawn from as many words as there are
        # positions, so a word is in about sixty names, nearly all of them lie outside the masks'
        # 4 096 words and a pair shares a fifth of a word on average.
        vocabulary = [f"сл{n}" for n in range(POSITIONS)]
        names = [f"Профиль {i}n " + " ".join(rnd.sample(vocabulary, 60)) for i in range(POSITIONS)]
        positions = [_position(i, name=names[i], price=Decimal(i + 1), rnd=rnd) for i in range(POSITIONS)]
        return positions, [names[POSITIONS - 1 - k] for k in range(ROWS)]
    raise SystemExit(f"unknown scenario {kind!r}")


def _peak_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    kind = sys.argv[1]
    positions, row_names = _scenario(kind, random.Random(20261021))
    pages = _pages(row_names)
    print(
        f"scenario={kind} positions={len(positions)} rows={len(row_names)} pages={len(pages)} "
        f"load1={os.getloadavg()[0]:.1f}", flush=True,
    )
    wall, cpu = time.perf_counter(), time.process_time()
    extraction = extract_specification(version_uid="ver_x", pages=pages)
    print(
        f"extract:  wall={time.perf_counter() - wall:.2f}s cpu={time.process_time() - cpu:.2f}s "
        f"rows={len(extraction.rows)} over_limit={extraction.over_limit} peak={_peak_mib():.0f}MiB",
        flush=True,
    )
    wall, cpu = time.perf_counter(), time.process_time()
    outcome = match_specification(extraction.rows, positions)
    print(
        f"match:    wall={time.perf_counter() - wall:.2f}s cpu={time.process_time() - cpu:.2f}s "
        f"statuses={dict(outcome.status_counts)} peak={_peak_mib():.0f}MiB", flush=True,
    )
    wall, cpu = time.perf_counter(), time.process_time()
    generated = generate_cheaper_analogs(outcome.matches, positions, VENDORS)
    print(
        f"generate: wall={time.perf_counter() - wall:.2f}s cpu={time.process_time() - cpu:.2f}s "
        f"matched={generated.rows_matched} proposals={len(generated.proposals)} peak={_peak_mib():.0f}MiB",
        flush=True,
    )
    # What came out, as one number, so two trees (``git archive <rev> src contracts`` into a
    # directory on PYTHONPATH) can be compared on an input too large to compare by eye.
    digest = hashlib.sha256()
    for draft in generated.proposals:
        digest.update(repr((
            draft.ordinal, draft.row.row_id, draft.matched.price_list_position_id, draft.matched_basis,
            draft.proposed.price_list_position_id, draft.analog_basis, str(draft.similarity),
            str(draft.saving), draft.rationale,
        )).encode())
    print(f"digest:   {digest.hexdigest()[:16]} of {len(generated.proposals)} proposals", flush=True)


if __name__ == "__main__":
    main()
