"""
Notre algorithme unique : plus court chemin « Dijkstra guidé par une boussole ».

IDÉE EN 3 LIGNES
  - Dijkstra explore les cases par coût croissant depuis le départ : il trouve le plus court chemin,
    mais il explore dans toutes les directions, sans savoir où est la cible.
  - Une « boussole » h(case) estime la distance restante jusqu'à la cible (distance à vol d'oiseau).
  - On classe donc chaque case par  f = g + h   (g = chemin déjà parcouru, h = distance estimée restante).
    On développe toujours la case de plus petit f : on va vers la cible, sans jamais perdre l'optimalité.

POURQUOI LE RÉSULTAT EST LE PLUS COURT
  La boussole ne surestime jamais la distance réelle (la ligne droite est toujours <= un chemin réel).
  Une heuristique de ce type est dite « admissible » : le premier chemin qui atteint la cible est optimal.

POUR LES TESTS
  guided=False met la boussole à zéro (f = g) : on retrouve Dijkstra pur. Cela sert uniquement à montrer,
  chiffres à l'appui, ce que la boussole apporte (même longueur, beaucoup moins de cases explorées).
"""
from __future__ import annotations

import heapq
import time

from .grid import INF, Grid
from .heuristics import heuristic_for
from .result import SearchResult, build_path, elapsed_ms


def shortest_path(grid: Grid, start, goal, diagonals: bool = False, budget_ms=None,
                  guided: bool = True) -> SearchResult:
    t0 = time.perf_counter()
    deadline = None if budget_ms is None else t0 + budget_ms / 1000.0
    boussole = heuristic_for(diagonals) if guided else (lambda a, b: 0.0)

    cout = {start: 0.0}        # g : meilleur coût connu pour atteindre chaque case depuis le départ
    parent = {start: None}     # d'où l'on vient : sert à reconstruire le chemin à la fin
    fermees = set()            # cases déjà développées (leur coût est définitif)
    ordre = 0                  # numéro d'insertion, pour départager deux cases identiques
    h0 = boussole(start, goal)
    a_traiter = [(h0, h0, ordre, start)]   # file de priorité : (f, h, ordre, case)
    plus_proche, h_min = start, h0          # sert au plan de repli si le temps est dépassé

    while a_traiter:
        _, _, _, case = heapq.heappop(a_traiter)        # la case de plus petit f
        if case in fermees:
            continue
        fermees.add(case)

        if case == goal:                                # arrivé : on remonte les parents
            chemin = build_path(parent, case)
            return SearchResult(chemin, cout[case], len(fermees), elapsed_ms(t0), True, False, fermees)

        # Budget de temps (niveau 3) : vérifié toutes les 64 cases pour ne pas ralentir la recherche.
        if deadline is not None:
            if len(fermees) % 64 == 0 and time.perf_counter() > deadline:
                chemin = build_path(parent, plus_proche)    # plan de repli : aller vers la case explorée
                return SearchResult(chemin, cout[plus_proche], len(fermees),  # la plus proche de la cible
                                    elapsed_ms(t0), False, True, fermees)
            h = boussole(case, goal)
            if h < h_min:
                plus_proche, h_min = case, h

        for voisin, pas in grid.neighbors(case[0], case[1], diagonals):
            if voisin in fermees:
                continue
            nouveau_cout = cout[case] + pas
            if nouveau_cout < cout.get(voisin, INF):    # un chemin plus court vers ce voisin
                cout[voisin] = nouveau_cout
                parent[voisin] = case
                ordre += 1
                h = boussole(voisin, goal)
                heapq.heappush(a_traiter, (nouveau_cout + h, h, ordre, voisin))

    return SearchResult([], INF, len(fermees), elapsed_ms(t0), False, False, fermees)
