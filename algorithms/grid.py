"""
Grille 2D en tableau plat, avec bordure d'obstacles.

STRUCTURE DE DONNÉES (choix justifié)
  - Une case (ligne, colonne) est codée par UN entier : indice = (ligne + 1) * L + (colonne + 1), avec L = colonnes + 2.
  - Les obstacles sont dans un bytearray : 1 octet par case (une liste de listes de booléens en coûte 8).
  - Une bordure d'obstacles entoure la grille : le test « sortie de la carte » disparaît de la recherche
    (une case voisine hors carte est simplement un obstacle).
  - Les tableaux de travail de la recherche (coût, parent, marque) sont alloués UNE fois par grille et
    réutilisés à chaque recherche grâce à un numéro de génération : aucune réinitialisation en O(cases).

  grille.blocked[r][c] reste utilisable (lecture et écriture) : ce sont des vues sur le même bytearray.

COÛTS ENTIERS : un pas droit coûte 10 et une diagonale 14 (≈ 10·√2). Les coûts affichés sont divisés par 10
  (1,0 et 1,4). Des coûts entiers permettent la file à seaux et évitent toute erreur d'arrondi.
"""
from __future__ import annotations

import random
from array import array

STRAIGHT = 10          # coût entier d'un pas droit
DIAG = 14              # coût entier d'une diagonale
STRAIGHT_COST = 1.0
DIAG_COST = 1.4        # = DIAG / 10
INF = float("inf")
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS8 = DIRS4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class Workspace:
    """Tableaux de travail d'une recherche, réutilisés d'une recherche à l'autre.

    g[i]      coût du meilleur chemin connu jusqu'à la case i          (entier, 4 octets)
    parent[i] case d'où l'on vient                                      (entier, 4 octets)
    stamp[i]  marque : < ouvert = jamais vue ; ouvert = vue ; ouvert + 1 = déjà développée (4 octets)
    Chaque recherche utilise de nouvelles marques : pas besoin d'effacer les tableaux entre deux recherches.
    """
    __slots__ = ("g", "parent", "stamp", "gen")

    def __init__(self, n: int):
        self.g = array("i", [0]) * n
        self.parent = array("i", [0]) * n
        self.stamp = array("I", [0]) * n
        self.gen = 0

    def new_search(self) -> int:
        self.gen += 1
        if self.gen >= 2_000_000_000:                 # presque jamais : on repart de zéro
            self.stamp = array("I", [0]) * len(self.stamp)
            self.gen = 1
        return 2 * self.gen                           # marque « ouvert » ; marque « fermé » = ouvert + 1


class Grid:
    """Grille 2D. blocked[r][c] est vrai (non nul) pour un obstacle."""

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.W = cols + 2                              # largeur avec la bordure
        self.cells = bytearray(self.W * (rows + 2))
        W = self.W
        self.cells[0:W] = b"\x01" * W                  # bordure haute et basse
        self.cells[(rows + 1) * W:(rows + 2) * W] = b"\x01" * W
        for r in range(1, rows + 1):                   # bordure gauche et droite
            self.cells[r * W] = 1
            self.cells[r * W + W - 1] = 1
        mv = memoryview(self.cells)
        self.blocked = [mv[(r + 1) * W + 1:(r + 1) * W + 1 + cols] for r in range(rows)]
        self._ws = None

    def copy(self) -> "Grid":
        g = Grid(self.rows, self.cols)
        g.cells[:] = self.cells
        return g

    def index(self, r: int, c: int) -> int:
        return (r + 1) * self.W + c + 1

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def free(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols and not self.cells[(r + 1) * self.W + c + 1]

    def workspace(self) -> Workspace:
        if self._ws is None:
            self._ws = Workspace(len(self.cells))
        return self._ws

    def neighbors(self, r: int, c: int, diagonals: bool) -> list:
        """Voisins accessibles avec leur coût (utilisé par les tests ; la recherche travaille directement
        sur les indices). Une diagonale ne peut pas couper le coin d'un obstacle."""
        cells, W = self.cells, self.W
        i = (r + 1) * W + c + 1
        out = []
        for dr, dc in (DIRS8 if diagonals else DIRS4):
            if cells[i + dr * W + dc]:
                continue
            if dr and dc:
                if cells[i + dc] or cells[i + dr * W]:
                    continue
                out.append(((r + dr, c + dc), DIAG_COST))
            else:
                out.append(((r + dr, c + dc), STRAIGHT_COST))
        return out


def random_grid(rows: int, cols: int, density: float, rng: random.Random):
    """Obstacles au hasard. Départ en haut à gauche, arrivée en bas à droite (toujours libres)."""
    g = Grid(rows, cols)
    for r in range(rows):
        row = g.blocked[r]
        for c in range(cols):
            row[c] = rng.random() < density
    start, goal = (0, 0), (rows - 1, cols - 1)
    g.blocked[start[0]][start[1]] = False
    g.blocked[goal[0]][goal[1]] = False
    return g, start, goal


def maze_grid(rows: int, cols: int, rng: random.Random, loops: float = 0.04):
    """Labyrinthe (parcours en profondeur) avec quelques murs percés pour créer plusieurs chemins."""
    rows += 1 - rows % 2  # dimensions impaires
    cols += 1 - cols % 2
    g = Grid(rows, cols)
    g.cells[:] = b"\x01" * len(g.cells)
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
