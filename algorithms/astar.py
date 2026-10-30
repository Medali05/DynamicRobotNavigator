"""A* (et A* pondéré). Dijkstra est le cas particulier weight = 0."""
from __future__ import annotations

import heapq
import time

from .grid import INF, Grid
from .heuristics import heuristic_for
from .result import SearchResult, build_path, elapsed_ms


def astar(grid: Grid, start, goal, diagonals: bool = False, weight: float = 1.0,
          budget_ms=None) -> SearchResult:
    """
    f = g + weight * h
      weight = 0  -> Dijkstra        weight = 1 -> A* optimal (heuristique admissible)
      weight > 1  -> A* pondéré : plus rapide, optimalité non garantie.
    budget_ms : si le temps est dépassé (vérifié toutes les 64 extractions), la recherche s'arrête et
    renvoie le chemin vers la case explorée la plus proche du but (plan de repli), avec timed_out=True.
    """
    t0 = time.perf_counter()
    deadline = None if budget_ms is None else t0 + budget_ms / 1000.0
    h = heuristic_for(diagonals)
    g = {start: 0.0}
    parent = {start: None}
    counter = 0
    h0 = h(start, goal)
    heap = [(weight * h0, h0 if weight > 0 else 0.0, counter, start)]
    closed = set()
    best, best_h = start, h0
    pops = 0
    while heap:
        _, hcur, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        if cur == goal:
            path = build_path(parent, cur)
            return SearchResult(path, g[cur], len(closed), elapsed_ms(t0), True, False, closed)
        pops += 1
        if deadline is not None and pops % 64 == 0 and time.perf_counter() > deadline:
            path = build_path(parent, best)
            return SearchResult(path, g[best], len(closed), elapsed_ms(t0), False, True, closed)
        if deadline is not None:  # suivi de la case la plus proche du but (plan de repli)
            hc = hcur if weight > 0 else h(cur, goal)
            if hc < best_h:
                best, best_h = cur, hc
        gc = g[cur]
        for nb, step in grid.neighbors(cur[0], cur[1], diagonals):
            if nb in closed:
                continue
            ng = gc + step
            if ng < g.get(nb, INF):
                g[nb] = ng
                parent[nb] = cur
                counter += 1
                hn = h(nb, goal)
                heapq.heappush(heap, (ng + weight * hn, hn if weight > 0 else 0.0, counter, nb))
    return SearchResult([], INF, len(closed), elapsed_ms(t0), False, False, closed)
