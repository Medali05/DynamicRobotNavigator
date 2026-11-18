"""
Version de RÉFÉRENCE (sert uniquement aux tests) : A* « classique » avec dictionnaires, ensembles de tuples
et tas binaire (heapq). Même métrique que notre version (pas droit 1,0 ; diagonale 1,4).
On l'utilise pour (1) vérifier que notre version trouve toujours la même longueur, (2) mesurer le gain.
"""
import heapq
import time

from algorithms import DIAG_COST, INF, heuristic_for


def astar_reference(grid, start, goal, diagonals=False):
    t0 = time.perf_counter()
    h = heuristic_for(diagonals)
    g, parent, closed, counter = {start: 0.0}, {start: None}, set(), 0
    h0 = h(start, goal)
    heap = [(h0, h0, counter, start)]
    while heap:
        _, _, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        if cur == goal:
            return g[cur], len(closed), (time.perf_counter() - t0) * 1000.0
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
                heapq.heappush(heap, (ng + hn, hn, counter, nb))
    return INF, len(closed), (time.perf_counter() - t0) * 1000.0
