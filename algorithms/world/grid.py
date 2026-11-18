"""La carte et ses obstacles. Rien ici ne calcule un chemin."""
from __future__ import annotations

from ..constants import DIRS4, DIRS8, SQRT2


class Grid:
    """Carte. blocked[r][c] vaut True pour un obstacle.

    Les coordonnées restent des couples (ligne, colonne). L'objet Node n'existe
    que le temps d'une recherche, pour porter g et le parent.
    neighbors est O(1) : au plus 4 ou 8 voisins, test de coin coupé compris.
    """

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
