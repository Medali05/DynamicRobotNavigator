"""Distance estimée jusqu'à la cible. Un appel est O(1).

Admissible : h n'est jamais plus grand que le vrai coût restant.
Si la recherche va jusqu'à la cible, le chemin est donc le plus court.
Octile, plus serrée que Manhattan quand les diagonales sont autorisées,
ne change pas le pire cas O(E log V) : elle réduit le nombre de cases ouvertes.
C'est ce nombre qui décide si le budget du niveau 3 suffit.
"""
from __future__ import annotations

from ..constants import SQRT2


def manhattan(a, b) -> float:
    """4 directions. h = |Δligne| + |Δcolonne|. Admissible et cohérente."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def octile(a, b) -> float:
    """8 directions. Compte les diagonales à √2. Plus serrée que Manhattan, toujours admissible."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2.0) * min(dx, dy)


def heuristic_for(diagonals: bool):
    return octile if diagonals else manhattan


class Heuristic:
    """Boussole utilisée par A*. guided=False donne h = 0 (Dijkstra pur)."""

    def __init__(self, diagonals: bool = False, guided: bool = True):
        self.diagonals = diagonals
        self.guided = guided
        if guided:
            self._fn = octile if diagonals else manhattan
        else:
            self._fn = lambda a, b: 0.0

    def __call__(self, a, b) -> float:
        return self._fn(a, b)
