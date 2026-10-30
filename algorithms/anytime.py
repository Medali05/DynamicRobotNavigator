"""A* « anytime » : poids décroissant, on garde le dernier chemin terminé avant la fin du budget."""
from __future__ import annotations

import time

from .astar import astar
from .grid import INF, Grid
from .result import SearchResult, elapsed_ms


def anytime_astar(grid: Grid, start, goal, diagonals: bool = False, budget_ms: float = 50.0,
                  weights=(3.0, 2.0, 1.5, 1.0)) -> SearchResult:
    t0 = time.perf_counter()
    best = last = None
    explored = 0
    visited = set()
    for w in weights:
        remaining = budget_ms - elapsed_ms(t0)
        if remaining <= 0:
            break
        res = astar(grid, start, goal, diagonals, weight=w, budget_ms=remaining)
        explored += res.explored
        visited |= res.visited
        last = res
        if res.found:
            best = res
        else:
            break
    final = best if best is not None else last
    if final is None:  # budget nul
        return SearchResult([], INF, 0, elapsed_ms(t0), False, True)
    return SearchResult(final.path, final.cost, explored, elapsed_ms(t0), final.found,
                        (not final.found) and final.timed_out, visited)
