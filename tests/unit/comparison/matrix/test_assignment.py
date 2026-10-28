"""The assignment is the original's Hungarian algorithm on ``numpy`` and it is optimal (`CMP-MATRIX-01`).

Two oracles, neither of them the code under test: exhaustive search (the best total weight over every one-to-one
assignment of small random matrices) and a verbatim pure-Python copy of the original's loop
(``document_matching.py:73-133`` at ``23f379fd``), which the vectorised version must equal pair for pair, ties
included, because the build's determinism rests on it.
"""

from __future__ import annotations

import itertools
import random

import numpy as np
import pytest

from auditmanager.comparison.matrix.assignment import maximum_weight_assignment


def _original(weights: list[list[float]]) -> list[tuple[int, int]]:
    """Verbatim from ``document_matching.py:73-133`` (the original's source, a test oracle only)."""
    if not weights or not weights[0]:
        return []
    rows = len(weights)
    columns = len(weights[0])
    size = max(rows, columns)
    padded = [
        [weights[row][column] if row < rows and column < columns else 0.0 for column in range(size)]
        for row in range(size)
    ]
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    matched_row = [0] * (size + 1)
    previous_column = [0] * (size + 1)
    for row in range(1, size + 1):
        matched_row[0] = row
        column0 = 0
        min_value = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[column0] = True
            row0 = matched_row[column0]
            delta = float("inf")
            column1 = 0
            for column in range(1, size + 1):
                if used[column]:
                    continue
                cost = 1.0 - padded[row0 - 1][column - 1]
                current = cost - u[row0] - v[column]
                if current < min_value[column]:
                    min_value[column] = current
                    previous_column[column] = column0
                if min_value[column] < delta:
                    delta = min_value[column]
                    column1 = column
            for column in range(size + 1):
                if used[column]:
                    u[matched_row[column]] += delta
                    v[column] -= delta
                else:
                    min_value[column] -= delta
            column0 = column1
            if matched_row[column0] == 0:
                break
        while True:
            column1 = previous_column[column0]
            matched_row[column0] = matched_row[column1]
            column0 = column1
            if column0 == 0:
                break
    assignment = []
    for column in range(1, size + 1):
        row = matched_row[column] - 1
        if 0 <= row < rows and column - 1 < columns:
            assignment.append((row, column - 1))
    return assignment


def _best_total(weights: list[list[float]]) -> float:
    """Exhaustive: the best total over every placement of the smaller side into the larger."""
    rows, columns = len(weights), len(weights[0])
    best = 0.0
    if rows <= columns:
        for chosen in itertools.permutations(range(columns), rows):
            best = max(best, sum(weights[r][c] for r, c in enumerate(chosen)))
    else:
        for chosen in itertools.permutations(range(rows), columns):
            best = max(best, sum(weights[r][c] for c, r in enumerate(chosen)))
    return best


def _total(weights: list[list[float]], pairs: list[tuple[int, int]]) -> float:
    return sum(weights[r][c] for r, c in pairs)


def test_an_empty_matrix_has_no_pairs() -> None:
    assert maximum_weight_assignment([]) == []
    assert maximum_weight_assignment([[]]) == []
    assert maximum_weight_assignment(np.zeros((0, 3))) == []


def test_a_single_cell() -> None:
    assert maximum_weight_assignment([[0.7]]) == [(0, 0)]


def test_assignment_against_brute_force() -> None:
    """Every random matrix up to 6 x 6, every shape: the total equals the exhaustive optimum, no row or column twice."""
    generator = random.Random(20261028)
    checked = 0
    for rows in range(1, 7):
        for columns in range(1, 7):
            for _ in range(12):
                weights = [[round(generator.random(), 3) for _ in range(columns)] for _ in range(rows)]
                pairs = maximum_weight_assignment(weights)
                assert len({r for r, _ in pairs}) == len(pairs)
                assert len({c for _, c in pairs}) == len(pairs)
                assert all(0 <= r < rows and 0 <= c < columns for r, c in pairs)
                assert _total(weights, pairs) == pytest.approx(_best_total(weights), abs=1e-9)
                checked += 1
    assert checked == 6 * 6 * 12


def test_a_greedy_choice_would_lose_where_the_assignment_does_not() -> None:
    """The reason for the algorithm (``document_matching.py:76-78``): taking the best cell first is worse."""
    weights = [[0.9, 0.8], [0.8, 0.0]]
    assert sorted(maximum_weight_assignment(weights)) == [(0, 1), (1, 0)]
    assert _total(weights, maximum_weight_assignment(weights)) == pytest.approx(1.6)


def test_assignment_equals_the_original_pair_for_pair_including_ties() -> None:
    generator = random.Random(7)
    for rows, columns in [(1, 1), (2, 5), (5, 2), (7, 7), (12, 9), (9, 12), (30, 30)]:
        for levels in (2, 3, 11, 1000):
            weights = [[generator.randrange(levels) / levels for _ in range(columns)] for _ in range(rows)]
            assert maximum_weight_assignment(weights) == _original(weights), (rows, columns, levels)


def test_the_same_weights_give_the_same_pairs_twice() -> None:
    generator = random.Random(3)
    weights = [[generator.randrange(4) / 4 for _ in range(15)] for _ in range(15)]
    assert maximum_weight_assignment(weights) == maximum_weight_assignment([list(row) for row in weights])


def test_a_large_matrix_is_fast_enough() -> None:
    """A version has at most 500 pages: 500 x 500 must not take minutes."""
    import time

    generator = np.random.default_rng(1)
    weights = generator.random((300, 300))
    began = time.perf_counter()
    pairs = maximum_weight_assignment(weights)
    assert len(pairs) == 300
    assert time.perf_counter() - began < 20.0
