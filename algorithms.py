"""
algorithms.py - Noyau algorithmique du projet (sans dépendance à l'interface).

Contenu :
  - Grid                : grille 2D (obstacles), voisinage 4 ou 8 directions, interdiction de couper les coins
  - random_grid / maze_grid : générateurs d'environnements reproductibles (graine)
  - manhattan / octile  : heuristiques admissibles
  - bfs, dijkstra, astar, anytime_astar : méthodes de recherche, toutes avec les mêmes mesures
Chaque méthode renvoie un SearchResult : chemin, coût, cases explorées, temps (ms), drapeaux.
"""
from __future__ import annotations

import heapq
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field

SQRT2 = math.sqrt(2.0)
INF = float("inf")
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS8 = DIRS4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]

Cell = tuple  # (ligne, colonne)


# --------------------------------------------------------------------------- grille
class Grid:
    """Grille 2D. blocked[r][c] vaut True pour un obstacle."""

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.blocked = [[False] * cols for _ in range(rows)]

    def copy(self) -> "Grid":
        g = Grid(self.rows, self.cols)
        g.blocked = [row[:] for row in self.blocked]
        return g

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def free(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols and not self.blocked[r][c]

    def neighbors(self, r: int, c: int, diagonals: bool):
        """Voisins accessibles avec leur coût. Une diagonale ne peut pas couper le coin d'un obstacle."""
        for dr, dc in (DIRS8 if diagonals else DIRS4):
            nr, nc = r + dr, c + dc
            if not self.free(nr, nc):
                continue
            if dr and dc:
                if self.blocked[r + dr][c] or self.blocked[r][c + dc]:
                    continue
                yield (nr, nc), SQRT2
            else:
                yield (nr, nc), 1.0

    def obstacle_count(self) -> int:
        return sum(sum(row) for row in self.blocked)


def random_grid(rows: int, cols: int, density: float, rng: random.Random):
    """Obstacles tirés au hasard. Départ en haut à gauche, arrivée en bas à droite (toujours libres)."""
    g = Grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            g.blocked[r][c] = rng.random() < density
    start, goal = (0, 0), (rows - 1, cols - 1)
    g.blocked[start[0]][start[1]] = False
    g.blocked[goal[0]][goal[1]] = False
    return g, start, goal


def maze_grid(rows: int, cols: int, rng: random.Random, loops: float = 0.04):
    """Labyrinthe (parcours en profondeur) auquel on perce quelques murs pour créer plusieurs chemins."""
    rows += 1 - rows % 2  # dimensions impaires
    cols += 1 - cols % 2
    g = Grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            g.blocked[r][c] = True
    g.blocked[1][1] = False
    stack = [(1, 1)]
    while stack:
        r, c = stack[-1]
        options = [
            (r + 2 * dr, c + 2 * dc, dr, dc)
            for dr, dc in DIRS4
            if 1 <= r + 2 * dr < rows - 1 and 1 <= c + 2 * dc < cols - 1 and g.blocked[r + 2 * dr][c + 2 * dc]
        ]
        if options:
            nr, nc, dr, dc = rng.choice(options)
            g.blocked[r + dr][c + dc] = False
            g.blocked[nr][nc] = False
            stack.append((nr, nc))
        else:
            stack.pop()
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if g.blocked[r][c] and rng.random() < loops:
                g.blocked[r][c] = False
    return g, (1, 1), (rows - 2, cols - 2)


# --------------------------------------------------------------------------- heuristiques
def manhattan(a: Cell, b: Cell) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def octile(a: Cell, b: Cell) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2.0) * min(dx, dy)


def heuristic_for(diagonals: bool):
    return octile if diagonals else manhattan


def path_cost(path: list) -> float:
    return sum(SQRT2 if (a[0] != b[0] and a[1] != b[1]) else 1.0 for a, b in zip(path, path[1:]))


# --------------------------------------------------------------------------- résultat
@dataclass
class SearchResult:
    path: list
    cost: float
    explored: int          # nombre de cases développées (sorties de la file)
    time_ms: float
    found: bool            # le but a été atteint
    timed_out: bool = False  # le budget de temps a coupé la recherche (chemin partiel éventuel)
    visited: set = field(default_factory=set, repr=False)


def _build_path(parent: dict, node: Cell) -> list:
    out = []
    while node is not None:
        out.append(node)
        node = parent[node]
    out.reverse()
    return out


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


# --------------------------------------------------------------------------- méthodes
def bfs(grid: Grid, start: Cell, goal: Cell, diagonals: bool = False, budget_ms=None) -> SearchResult:
    """Parcours en largeur : minimise le nombre de pas (pas le coût réel quand les diagonales sont permises)."""
    t0 = time.perf_counter()
    parent = {start: None}
    queue = deque([start])
    visited = set()
    while queue:
        cur = queue.popleft()
        visited.add(cur)
        if cur == goal:
            path = _build_path(parent, cur)
            return SearchResult(path, path_cost(path), len(visited), _ms(t0), True, False, visited)
        for nb, _ in grid.neighbors(cur[0], cur[1], diagonals):
            if nb not in parent:
                parent[nb] = cur
                queue.append(nb)
    return SearchResult([], INF, len(visited), _ms(t0), False, False, visited)


def astar(grid: Grid, start: Cell, goal: Cell, diagonals: bool = False,
          weight: float = 1.0, budget_ms=None) -> SearchResult:
    """
    A* générique : f = g + weight * h.
      weight = 0  -> Dijkstra         weight = 1 -> A* optimal (heuristique admissible)
      weight > 1  -> A* pondéré (plus rapide, optimalité non garantie, coût <= weight * optimal)
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
        _, _, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        if cur == goal:
            path = _build_path(parent, cur)
            return SearchResult(path, g[cur], len(closed), _ms(t0), True, False, closed)
        pops += 1
        if deadline is not None and pops % 64 == 0 and time.perf_counter() > deadline:
            path = _build_path(parent, best)
            return SearchResult(path, g[best], len(closed), _ms(t0), False, True, closed)
        hc = h(cur, goal)
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
    return SearchResult([], INF, len(closed), _ms(t0), False, False, closed)


def dijkstra(grid: Grid, start: Cell, goal: Cell, diagonals: bool = False, budget_ms=None) -> SearchResult:
    return astar(grid, start, goal, diagonals, weight=0.0, budget_ms=budget_ms)


def anytime_astar(grid: Grid, start: Cell, goal: Cell, diagonals: bool = False,
                  budget_ms: float = 50.0, weights=(3.0, 2.0, 1.5, 1.0)) -> SearchResult:
    """
    Approche « anytime » : A* pondéré avec un poids décroissant. On garde le dernier chemin terminé
    avant la fin du budget. Le premier chemin arrive vite, les suivants l'améliorent.
    """
    t0 = time.perf_counter()
    best = None
    explored = 0
    visited = set()
    last = None
    for w in weights:
        remaining = budget_ms - _ms(t0)
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
        return SearchResult([], INF, 0, _ms(t0), False, True)
    return SearchResult(final.path, final.cost, explored, _ms(t0), final.found,
                        (not final.found) and final.timed_out, visited)


# Registre : ajouter une méthode = une ligne ici, le banc d'essai la prend en compte automatiquement.
ALGORITHMS = {
    "BFS": lambda g, s, t, d, b=None: bfs(g, s, t, d),
    "Dijkstra": lambda g, s, t, d, b=None: dijkstra(g, s, t, d),
    "A*": lambda g, s, t, d, b=None: astar(g, s, t, d, 1.0),
    "A* pondéré (w=2)": lambda g, s, t, d, b=None: astar(g, s, t, d, 2.0),
    "Anytime (50 ms)": lambda g, s, t, d, b=None: anytime_astar(g, s, t, d, 50.0),
}


if __name__ == "__main__":
    rng = random.Random(42)
    grid, s, t = random_grid(60, 60, 0.25, rng)
    for diag in (False, True):
        print(f"--- {'8' if diag else '4'} directions, grille 60x60, 25 % d'obstacles, graine 42")
        for name, fn in ALGORITHMS.items():
            r = fn(grid, s, t, diag)
            print(f"{name:20s} coût={r.cost:8.2f}  explorées={r.explored:5d}  {r.time_ms:7.2f} ms  trouvé={r.found}")
