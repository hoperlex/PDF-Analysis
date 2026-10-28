"""Maximum-weight one-to-one assignment over ``numpy`` (no ``scipy``).

`CMP-MATRIX-01`. The original assigns the pages of the next version to those of the previous one with an O(n^3)
Hungarian algorithm over the page score (``document_matching.py:73-133``, used by ``lineage.py:343-392``). This
module is the same algorithm -- the shortest-augmenting-path form with potentials, on the cost ``1 - weight``, the
matrix padded with zeros to a square -- with its inner loop over the columns vectorised. The operations on every
float are the original's, in the original's order, and the choice among equal minima is the first column, so it
returns the original's pairs on every input, ties included (a test holds the two equal on random matrices with
heavy ties). That is also what makes the build deterministic: the same weights give the same pairs.

The result is checked against exhaustive search on small random matrices (``test_assignment_against_brute_force``):
its total weight equals the best total weight over every one-to-one assignment.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

__all__ = ["maximum_weight_assignment"]


def maximum_weight_assignment(weights: Sequence[Sequence[float]] | np.ndarray) -> list[tuple[int, int]]:
    """Pairs ``(row, column)`` of a one-to-one assignment of maximum total weight.

    ``weights`` is ``rows x columns``; the matrix is padded with zero weights to a square, so a row or a column
    may stay unmatched (its partner is a pad and is not returned). Pairs come ordered by column, as the original
    returns them. A pair of weight zero may be returned (a pad of zero weight is not distinguishable from a real
    zero): the caller filters by its own threshold.
    """
    matrix = np.asarray(weights, dtype=np.float64)
    if matrix.ndim != 2 or matrix.size == 0:
        return []
    rows, columns = matrix.shape
    size = max(rows, columns)
    padded = np.zeros((size, size), dtype=np.float64)
    padded[:rows, :columns] = matrix
    cost = 1.0 - padded
    u = np.zeros(size + 1, dtype=np.float64)
    v = np.zeros(size + 1, dtype=np.float64)
    matched_row = np.zeros(size + 1, dtype=np.int64)
    previous_column = np.zeros(size + 1, dtype=np.int64)
    infinity = float("inf")
    for row in range(1, size + 1):
        matched_row[0] = row
        column0 = 0
        min_value = np.full(size + 1, infinity, dtype=np.float64)
        used = np.zeros(size + 1, dtype=bool)
        while True:
            used[column0] = True
            row0 = int(matched_row[column0])
            free = ~used[1:]
            current = cost[row0 - 1] - u[row0] - v[1:]
            better = free & (current < min_value[1:])
            min_value[1:][better] = current[better]
            previous_column[1:][better] = column0
            candidates = np.where(free, min_value[1:], infinity)
            chosen = int(np.argmin(candidates))
            delta = float(candidates[chosen])
            column1 = chosen + 1
            u[matched_row[used]] += delta
            v[used] -= delta
            min_value[~used] -= delta
            column0 = column1
            if matched_row[column0] == 0:
                break
        while True:
            column1 = int(previous_column[column0])
            matched_row[column0] = matched_row[column1]
            column0 = column1
            if column0 == 0:
                break
    pairs: list[tuple[int, int]] = []
    for column in range(1, size + 1):
        row = int(matched_row[column]) - 1
        if 0 <= row < rows and column - 1 < columns:
            pairs.append((row, column - 1))
    return pairs
