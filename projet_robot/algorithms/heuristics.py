"""Heuristiques admissibles et coût d'un chemin."""
from __future__ import annotations

from .grid import SQRT2


def manhattan(a, b) -> float:
    """Heuristique pour 4 directions."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def octile(a, b) -> float:
    """Heuristique pour 8 directions."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2.0) * min(dx, dy)


def heuristic_for(diagonals: bool):
    return octile if diagonals else manhattan


def path_cost(path: list) -> float:
    return sum(SQRT2 if (a[0] != b[0] and a[1] != b[1]) else 1.0 for a, b in zip(path, path[1:]))
