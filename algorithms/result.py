"""Résultat commun d'une recherche."""
from __future__ import annotations

import time


class SearchResult:
    """chemin, coût, nombre de cases développées, temps, drapeaux. Les cases explorées ne sont converties en
    ensemble de (ligne, colonne) que si on les demande (affichage) : une recherche ne construit pas de tuples."""

    def __init__(self, path, cost, explored, time_ms, found, timed_out=False, ids=None, width=0):
        self.path = path
        self.cost = cost
        self.explored = explored
        self.time_ms = time_ms
        self.found = found
        self.timed_out = timed_out
        self._ids = ids
        self._w = width
        self._visited = None

    @property
    def visited(self) -> set:
        if self._visited is None:
            w = self._w
            self._visited = {(i // w - 1, i % w - 1) for i in self._ids} if self._ids is not None else set()
        return self._visited


def elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0
