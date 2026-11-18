"""Nombres et directions partagés par la carte et par la recherche."""
from __future__ import annotations

import math

SQRT2 = math.sqrt(2.0)   # coût d'un pas diagonal
INF = float("inf")        # « pas encore de chemin » pour g
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS8 = DIRS4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
