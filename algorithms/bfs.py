"""BFS : parcours en largeur."""
from __future__ import annotations

import time
from collections import deque

from .grid import INF, Grid
from .heuristics import path_cost
from .result import SearchResult, build_path, elapsed_ms


def bfs(grid: Grid, start, goal, diagonals: bool = False) -> SearchResult:
    """Minimise le nombre de pas (pas le coût réel quand les diagonales sont permises)."""
    t0 = time.perf_counter()
    parent = {start: None}
    queue = deque([start])
    visited = set()
    while queue:
        cur = queue.popleft()
        visited.add(cur)
        if cur == goal:
            path = build_path(parent, cur)
            return SearchResult(path, path_cost(path), len(visited), elapsed_ms(t0), True, False, visited)
        for nb, _ in grid.neighbors(cur[0], cur[1], diagonals):
            if nb not in parent:
                parent[nb] = cur
                queue.append(nb)
    return SearchResult([], INF, len(visited), elapsed_ms(t0), False, False, visited)
