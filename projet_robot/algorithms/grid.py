"""Grille 2D, voisinage (4 ou 8 directions) et générateurs d'environnements."""
from __future__ import annotations

import math
import random

SQRT2 = math.sqrt(2.0)
INF = float("inf")
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS8 = DIRS4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]


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

    def neighbors(self, r: int, c: int, diagonals: bool) -> list:
        """Voisins accessibles avec leur coût. Une diagonale ne peut pas couper le coin d'un obstacle."""
        blocked, rows, cols = self.blocked, self.rows, self.cols
        out = []
        for dr, dc in (DIRS8 if diagonals else DIRS4):
            nr, nc = r + dr, c + dc
            if nr < 0 or nc < 0 or nr >= rows or nc >= cols or blocked[nr][nc]:
                continue
            if dr and dc:
                if blocked[nr][c] or blocked[r][nc]:
                    continue
                out.append(((nr, nc), SQRT2))
            else:
                out.append(((nr, nc), 1.0))
        return out


def random_grid(rows: int, cols: int, density: float, rng: random.Random):
    """Obstacles au hasard. Départ en haut à gauche, arrivée en bas à droite (toujours libres)."""
    g = Grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            g.blocked[r][c] = rng.random() < density
    start, goal = (0, 0), (rows - 1, cols - 1)
    g.blocked[start[0]][start[1]] = False
    g.blocked[goal[0]][goal[1]] = False
    return g, start, goal


def maze_grid(rows: int, cols: int, rng: random.Random, loops: float = 0.04):
    """Labyrinthe (parcours en profondeur) avec quelques murs percés pour créer plusieurs chemins."""
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
