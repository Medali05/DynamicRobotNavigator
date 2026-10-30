"""Dijkstra : chemin de coût minimal, sans heuristique."""
from __future__ import annotations

from .astar import astar
from .grid import Grid
from .result import SearchResult


def dijkstra(grid: Grid, start, goal, diagonals: bool = False, budget_ms=None) -> SearchResult:
    return astar(grid, start, goal, diagonals, weight=0.0, budget_ms=budget_ms)
