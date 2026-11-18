"""Fabrique des cartes. Séparé de Grid pour ne pas mélanger la carte et son remplissage."""
from __future__ import annotations

import random

from ..constants import DIRS4
from .grid import Grid


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
