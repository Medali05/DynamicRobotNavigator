"""A* : une seule recherche de plus court chemin, deux façons de ranger la file ouverte.

COMPLEXITÉ
  V = nombre de cases libres (au plus lignes × colonnes)
  E = nombre d'arêtes. Sur une grille, E ≤ 4V (4 directions) ou E ≤ 8V (8 directions).
  n = nombre d'entrées présentes dans la file ouverte au moment d'une extraction.

  Les deux versions calculent le même f = g + h, avec la même heuristique admissible.
  Si la recherche atteint la cible, la longueur du chemin est donc la même.
  Ce qui change, c'est le coût de « prendre la case de plus petit f ».

  Version « list » — A* classique
    Extraire le minimum parcourt toute la file : Θ(n), puis le retrait au milieu est encore Θ(n).
    Chaque arête peut insérer une entrée : O(E) insertions.
    Pire cas : O(V²) sur une grille (E = Θ(V), et n peut valoir Θ(V)).
    Mémoire : O(V) Node (un par case atteinte) + O(E) doublons laissés dans la liste.

  Version « heap » — A* avec tas binaire (celle de l'application)
    heappush et heappop : O(log n), avec n = O(E).
    Pire cas : O(E log V). Sur une grille 4 directions, E = Θ(V), donc O(V log V).
    Mémoire : O(V) Node + O(E) doublons dans le tas.
    Python n'a pas de decrease-key : quand un meilleur g est trouvé, on empile une
    nouvelle entrée et l'ancienne est ignorée au moment où elle sort (case déjà fermée).
    On échange un peu de mémoire contre un code simple. Le nombre de cases ouvertes, lui, ne change pas.

  Heuristique
    h est O(1). Elle ne change pas le pire cas ci-dessus.
    Elle réduit le nombre pratique de cases ouvertes : on ne développe pas tout le disque autour du départ.
    Manhattan (4 directions) et octile (8 directions) sont admissibles et cohérentes :
    la première fois qu'une case est ouverte, son g est définitif. D'où l'ensemble fermé.

NIVEAU 3, TEMPS RÉEL
  Le budget est un temps en millisecondes, pas un nombre de cases.
  Le test d'horloge est fait toutes les 64 ouvertures : O(1) amorti, il ne domine pas le calcul.
  Dans un même budget T, le nombre de cases qu'on a le temps d'ouvrir est environ
      T / (coût d'une ouverture).
  Une ouverture coûte le parcours des voisins (≤ 8) plus une insertion dans la file.
  Avec la liste, l'extraction est chère : peu de cases tiennent dans T, le repli se déclenche souvent.
  Avec le tas, l'extraction est bon marché : la cible est atteinte plus souvent avant l'échéance.
  Le repli n'est pas le plus court chemin jusqu'à la cible. C'est le plus court chemin jusqu'à la
  case déjà ouverte la plus proche de la cible (plus petit h). L'optimisation ne change pas cette
  règle : elle change la probabilité qu'on n'en ait pas besoin.

  Donc :
    - la longueur optimale, quand le calcul finit, ne dépend pas de la file (liste ou tas) ;
    - le temps et le nombre de cases explorées en dépendent ;
    - au niveau 3, ce temps décide si le robot reçoit le chemin optimal ou un préfixe orange.
"""
from __future__ import annotations

import heapq
import time

from ..constants import INF
from ..world.grid import Grid
from ..world.node import Node
from .heuristic import Heuristic
from .path_manager import PathManager
from .result import SearchResult, elapsed_ms


class AStar:
    """Recherche A*. structure = \"heap\" (application) ou \"list\" (comparaison seulement)."""

    def __init__(self, structure: str = "heap"):
        if structure not in ("heap", "list"):
            raise ValueError("structure doit être 'heap' ou 'list'")
        self.structure = structure

    def search(self, grid: Grid, start, goal, diagonals: bool = False, budget_ms=None,
               guided: bool = True) -> SearchResult:
        t0 = time.perf_counter()
        deadline = None if budget_ms is None else t0 + budget_ms / 1000.0
        boussole = Heuristic(diagonals, guided)
        nodes: dict[tuple, Node] = {}

        def touch(cell) -> Node:
            """O(1) amorti. Un seul Node par case : g et parent vivent sur l'objet."""
            node = nodes.get(cell)
            if node is None:
                node = Node(cell[0], cell[1])
                nodes[cell] = node
            return node

        depart = touch(start)
        depart.g = 0.0
        h0 = boussole(depart, goal)
        ordre = 0
        ouvert = [(h0, h0, ordre, depart)]
        pushes = 1
        fermees: set[Node] = set()
        plus_proche, h_min = depart, h0

        while ouvert:
            # Liste : Θ(n) pour trouver et retirer le minimum. Tas : O(log n).
            if self.structure == "heap":
                _, _, _, case = heapq.heappop(ouvert)
            else:
                _, _, _, case = _pop_list(ouvert)
            if case in fermees:
                continue
            fermees.add(case)

            if case.pos == goal:
                return self._result(case, case.g, fermees, t0, True, False, nodes, pushes)

            if deadline is not None:
                if len(fermees) % 64 == 0 and time.perf_counter() > deadline:
                    return self._result(plus_proche, plus_proche.g, fermees, t0, False, True, nodes, pushes)
                h = boussole(case, goal)
                if h < h_min:
                    plus_proche, h_min = case, h

            for voisin_pos, pas in grid.neighbors(case.r, case.c, diagonals):
                voisin = touch(voisin_pos)
                if voisin in fermees:
                    continue
                nouveau = case.g + pas
                if nouveau < voisin.g:
                    voisin.g = nouveau
                    voisin.parent = case
                    ordre += 1
                    h = boussole(voisin, goal)
                    pushes += 1
                    entree = (nouveau + h, h, ordre, voisin)
                    if self.structure == "heap":
                        heapq.heappush(ouvert, entree)   # O(log n)
                    else:
                        ouvert.append(entree)            # O(1), le coût est payé à l'extraction

        return self._result(None, INF, fermees, t0, False, False, nodes, pushes)

    @staticmethod
    def _result(node, cost, fermees, t0, found, timed_out, nodes, pushes) -> SearchResult:
        chemin = PathManager.reconstruct(node) if node is not None else []
        return SearchResult(
            chemin, cost, len(fermees), elapsed_ms(t0), found, timed_out,
            {n.pos for n in fermees}, len(nodes), pushes,
        )


def _pop_list(ouvert: list):
    """Θ(n) comparaisons, puis Θ(n) pour retirer l'élément au milieu de la liste."""
    meilleur = 0
    for i in range(1, len(ouvert)):
        if ouvert[i] < ouvert[meilleur]:
            meilleur = i
    return ouvert.pop(meilleur)
