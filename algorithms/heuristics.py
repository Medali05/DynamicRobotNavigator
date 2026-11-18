"""Heuristiques admissibles (la boussole) et coût d'un chemin, avec la même métrique que la recherche."""
from __future__ import annotations

from .grid import DIAG_COST


def manhattan(a, b) -> float:
    """Distance pour 4 directions."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def octile(a, b) -> float:
    """Distance pour 8 directions (diagonale = 1,4)."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (DIAG_COST - 2.0) * min(dx, dy)


def heuristic_for(diagonals: bool):
    return octile if diagonals else manhattan


def path_cost(path: list) -> float:
    return sum(DIAG_COST if (a[0] != b[0] and a[1] != b[1]) else 1.0 for a, b in zip(path, path[1:]))
