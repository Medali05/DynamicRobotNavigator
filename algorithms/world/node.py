"""Une case pendant une recherche. La grille, elle, reste un tableau de booléens."""
from __future__ import annotations


class Node:
    """Case atteinte par A*. Une seule instance par coordonnée (voir AStar).

    g      coût réel déjà payé depuis le départ
    parent case précédente sur le meilleur chemin connu
    L'identité de la case est (r, c) : deux Node de mêmes coordonnées sont égaux.
    """

    __slots__ = ("r", "c", "g", "parent")

    def __init__(self, r: int, c: int):
        self.r = r
        self.c = c
        self.g = float("inf")
        self.parent = None

    @property
    def pos(self) -> tuple:
        return (self.r, self.c)

    def __getitem__(self, index: int) -> int:
        return (self.r, self.c)[index]

    def __eq__(self, other) -> bool:
        return isinstance(other, Node) and self.r == other.r and self.c == other.c

    def __hash__(self) -> int:
        return hash((self.r, self.c))

    def __lt__(self, other) -> bool:
        return (self.r, self.c) < (other.r, other.c)

    def __repr__(self) -> str:
        return f"Node({self.r}, {self.c}, g={self.g})"
