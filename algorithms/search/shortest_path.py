"""Point d'entrée unique du projet : A* avec tas binaire.

L'application (niveaux 1, 2 et 3) appelle shortest_path(). La version « liste »
n'est là que pour la comparaison de complexité, dans tests/comparaison.py.
"""
from __future__ import annotations

from ..world.grid import Grid
from .astar import AStar
from .result import SearchResult


def shortest_path(grid: Grid, start, goal, diagonals: bool = False, budget_ms=None,
                  guided: bool = True, structure: str = "heap") -> SearchResult:
    """Plus court chemin de start à goal.

    structure=\"heap\" : O(E log V), utilisé par la simulation.
    structure=\"list\" : O(V²), même chemin si le calcul va au bout, plus lent.
    budget_ms : niveau 3. None : on va jusqu'à la cible (niveaux 1 et 2).
    guided=False : h = 0, on retrouve Dijkstra, pour la comparaison seulement.
    """
    return AStar(structure).search(grid, start, goal, diagonals, budget_ms, guided)
