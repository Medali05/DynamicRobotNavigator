"""
Notre algorithme : plus court chemin « Dijkstra guidé par une boussole » (A*), sur des entiers.

IDÉE EN 3 LIGNES
  - Dijkstra explore les cases par coût croissant depuis le départ : plus court chemin garanti, mais il explore
    dans toutes les directions, sans savoir où est la cible.
  - Une « boussole » h(case) estime la distance restante jusqu'à la cible (à vol d'oiseau).
  - On classe chaque case par  f = g + h  (g = chemin déjà parcouru, h = distance estimée restante) et on
    développe toujours la case de plus petit f : on va vers la cible sans perdre l'optimalité.

POURQUOI LE RÉSULTAT EST LE PLUS COURT
  La boussole ne surestime jamais la distance réelle : le premier chemin qui atteint la cible est optimal.

STRUCTURES DE DONNÉES (voir grid.py et file_a_seaux.py)
  cases = indices entiers dans un tableau plat avec bordure ; coûts entiers (10 et 14) ; tableaux de travail
  réutilisés grâce aux marques de génération ; file à seaux au lieu d'un tas de tuples.

POUR LES TESTS
  guided=False met la boussole à zéro (f = g) : on retrouve Dijkstra pur.
"""
from __future__ import annotations

import time
from array import array

from .file_a_seaux import FileASeaux
from .grid import DIAG, INF, STRAIGHT, Grid
from .result import SearchResult, elapsed_ms


def shortest_path(grid: Grid, start, goal, diagonals: bool = False, budget_ms=None,
                  guided: bool = True) -> SearchResult:
    t0 = time.perf_counter()
    deadline = None if budget_ms is None else t0 + budget_ms / 1000.0
    W, cells = grid.W, grid.cells
    ws = grid.workspace()
    g, parent, stamp = ws.g, ws.parent, ws.stamp
    OUVERT = ws.new_search()           # marque « vue » pour cette recherche
    FERME = OUVERT + 1                 # marque « déjà développée »
    depart, cible = grid.index(*start), grid.index(*goal)
    gr, gc = divmod(cible, W)          # coordonnées de la cible (avec bordure)

    # déplacements : (décalage d'indice, dr, dc) ; diagonales : (décalage, dr, dc, voisin horizontal, voisin vertical)
    droits = ((1, 0, 1), (-1, 0, -1), (W, 1, 0), (-W, -1, 0))
    diago = ((W + 1, 1, 1, 1, W), (W - 1, 1, -1, -1, W), (-W + 1, -1, 1, 1, -W), (-W - 1, -1, -1, -1, -W))

    sr, sc = divmod(depart, W)
    ax, ay = abs(sr - gr), abs(sc - gc)
    h_dep = 10 * (ax + ay) - (6 * min(ax, ay) if diagonals else 0)
    h0 = h_dep if guided else 0

    file = FileASeaux()                # cases à traiter, rangées par f = g + h
    stamp[depart] = OUVERT
    g[depart] = 0
    parent[depart] = -1
    file.push(h0, depart)
    explorees = array("i")             # cases développées, dans l'ordre (sert à l'affichage)
    nb = 0
    meilleure, h_min = depart, h_dep   # case la plus proche de la cible : plan de repli

    while file:
        i = file.pop()                 # la case de plus petit f
        if stamp[i] == FERME:
            continue
        stamp[i] = FERME
        explorees.append(i)
        nb += 1

        if i == cible:                 # arrivé : on remonte les parents
            chemin, k = [], i
            while k != -1:
                chemin.append((k // W - 1, k % W - 1))
                k = parent[k]
            chemin.reverse()
            return SearchResult(chemin, g[i] / 10.0, nb, elapsed_ms(t0), True, False, explorees, W)

        ri = i // W
        ci = i - ri * W
        if deadline is not None:       # budget de temps : vérifié toutes les 64 cases développées
            if (nb & 63) == 0 and time.perf_counter() > deadline:
                chemin, k = [], meilleure                 # plan de repli : chemin vers la case explorée
                while k != -1:                            # la plus proche de la cible
                    chemin.append((k // W - 1, k % W - 1))
                    k = parent[k]
                chemin.reverse()
                return SearchResult(chemin, g[meilleure] / 10.0, nb, elapsed_ms(t0), False, True, explorees, W)
            ax, ay = abs(ri - gr), abs(ci - gc)
            hi = 10 * (ax + ay) - (6 * min(ax, ay) if diagonals else 0)
            if hi < h_min:
                meilleure, h_min = i, hi

        gi = g[i]
        for off, dr, dc in droits:
            j = i + off
            if cells[j]:               # obstacle ou bordure
                continue
            sj = stamp[j]
            if sj == FERME:
                continue
            ng = gi + STRAIGHT
            if sj < OUVERT or ng < g[j]:                  # jamais vue, ou meilleur chemin trouvé
                stamp[j] = OUVERT
                g[j] = ng
                parent[j] = i
                if guided:
                    ax, ay = ri + dr - gr, ci + dc - gc
                    if ax < 0:
                        ax = -ax
                    if ay < 0:
                        ay = -ay
                    hn = 10 * (ax + ay) - (6 * (ax if ax < ay else ay) if diagonals else 0)
                else:
                    hn = 0
                file.push(ng + hn, j)
        if diagonals:
            for off, dr, dc, a, b in diago:
                j = i + off
                if cells[j] or cells[i + a] or cells[i + b]:   # obstacle, ou coin d'obstacle coupé
                    continue
                sj = stamp[j]
                if sj == FERME:
                    continue
                ng = gi + DIAG
                if sj < OUVERT or ng < g[j]:
                    stamp[j] = OUVERT
                    g[j] = ng
                    parent[j] = i
                    if guided:
                        ax, ay = ri + dr - gr, ci + dc - gc
                        if ax < 0:
                            ax = -ax
                        if ay < 0:
                            ay = -ay
                        hn = 10 * (ax + ay) - 6 * (ax if ax < ay else ay)
                    else:
                        hn = 0
                    file.push(ng + hn, j)

    return SearchResult([], INF, nb, elapsed_ms(t0), False, False, explorees, W)
