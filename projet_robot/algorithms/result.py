"""Résultat commun à tous les algorithmes de recherche."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    path: list              # liste de cases (ligne, colonne) du départ à l'arrivée
    cost: float             # coût du chemin
    explored: int           # nombre de cases développées
    time_ms: float          # temps de calcul
    found: bool             # le but a été atteint
    timed_out: bool = False  # le budget de temps a coupé la recherche (chemin partiel éventuel)
    visited: set = field(default_factory=set, repr=False)


def build_path(parent: dict, node) -> list:
    out = []
    while node is not None:
        out.append(node)
        node = parent[node]
    out.reverse()
    return out


def elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0
