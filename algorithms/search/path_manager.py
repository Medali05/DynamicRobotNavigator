"""Reconstruction du chemin à partir des parents, et coût de ce chemin."""
from __future__ import annotations

from ..constants import SQRT2
from ..world.node import Node


def path_cost(path: list) -> float:
    """O(L). Un pas droit coûte 1, une diagonale √2."""
    return sum(SQRT2 if (a[0] != b[0] and a[1] != b[1]) else 1.0 for a, b in zip(path, path[1:]))


class PathManager:
    """Transforme la chaîne de parents en liste de cases (ligne, colonne).

    Complexité : O(L) où L est le nombre de cases du chemin (L ≤ cases explorées).
    On ne stocke pas tous les chemins possibles : un parent par case suffit,
    parce que le parent pointe déjà vers le meilleur prédécesseur connu.
    """

    @staticmethod
    def reconstruct(node: Node | None) -> list:
        out = []
        while node is not None:
            out.append(node.pos)
            node = node.parent
        out.reverse()
        return out

    @staticmethod
    def cost(path: list) -> float:
        return path_cost(path)
