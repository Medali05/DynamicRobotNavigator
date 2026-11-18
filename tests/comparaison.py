"""
Comparaison de trois méthodes sur les MÊMES grilles :
  - Dijkstra pur   : notre algorithme sans la boussole (guided=False)
  - Glouton        : classe les cases seulement selon la boussole h, sans compter le chemin déjà parcouru
  - Notre algorithme : f = g + h  (Dijkstra guidé par une boussole, c'est-à-dire A*)

Lancer depuis le dossier du projet :   py tests/comparaison.py

Le glouton est écrit ICI, uniquement pour cette comparaison : il n'est pas dans le projet
(le professeur demande un seul algorithme de plus court chemin).
"""
import heapq
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algorithms import heuristic_for, path_cost, random_grid, shortest_path  # noqa: E402

NB_GRILLES = 40
POURCENT_OBSTACLES = 0.25


def glouton(grille, depart, cible, diagonales):
    """Glouton : f = h seulement. Très rapide, mais le chemin n'est pas forcément le plus court."""
    t0 = time.perf_counter()
    h = heuristic_for(diagonales)
    parent, vues, ordre = {depart: None}, {depart}, 0
    file = [(h(depart, cible), 0, depart)]
    developpees = 0
    while file:
        _, _, case = heapq.heappop(file)
        developpees += 1
        if case == cible:
            chemin = []
            while case is not None:
                chemin.append(case)
                case = parent[case]
            return chemin[::-1], developpees, (time.perf_counter() - t0) * 1000
        for voisin, _ in grille.neighbors(case[0], case[1], diagonales):
            if voisin not in vues:
                vues.add(voisin)
                parent[voisin] = case
                ordre += 1
                heapq.heappush(file, (h(voisin, cible), ordre, voisin))
    return None, developpees, (time.perf_counter() - t0) * 1000


def moyenne_temps(fonction, repetitions=3):
    return sum(fonction() for _ in range(repetitions)) / repetitions


def main():
    print(f"Grilles aléatoires, {int(POURCENT_OBSTACLES * 100)} % d'obstacles, {NB_GRILLES} grilles par ligne "
          "(seules les grilles résolubles sont gardées), graine fixe, mêmes grilles pour les trois méthodes.\n")
    print(f"{'Grille':>8} {'Dir.':>4} | {'Dijkstra pur':^19} | {'Glouton':^38} | {'Notre algorithme':^19}")
    print(f"{'':>8} {'':>4} | {'cases':>8} {'ms':>8} | {'cases':>8} {'ms':>8} {'plus long':>9} {'max':>7} | {'cases':>8} {'ms':>8}")
    tout_plus_long = True
    for taille in (20, 50, 100):
        for diag in (False, True):
            dij, nous, glo, ecarts = [], [], [], []
            for i in range(NB_GRILLES):
                g, s, t = random_grid(taille, taille, POURCENT_OBSTACLES, random.Random(1000 + i))
                a = shortest_path(g, s, t, diag)
                if not a.found:
                    continue
                d = shortest_path(g, s, t, diag, guided=False)
                assert abs(a.cost - d.cost) < 1e-9, "notre algorithme et Dijkstra doivent donner la même longueur"
                chemin, n, _ = glouton(g, s, t, diag)
                dij.append((d.explored, moyenne_temps(lambda: shortest_path(g, s, t, diag, guided=False).time_ms)))
                nous.append((a.explored, moyenne_temps(lambda: shortest_path(g, s, t, diag).time_ms)))
                glo.append((n, moyenne_temps(lambda: glouton(g, s, t, diag)[2])))
                ecarts.append((path_cost(chemin) / a.cost - 1) * 100)
                tout_plus_long = tout_plus_long and path_cost(chemin) >= a.cost - 1e-9
            moy = lambda lst, k: sum(x[k] for x in lst) / len(lst)
            print(f"{taille:>3}x{taille:<4} {'8' if diag else '4':>4} | {moy(dij, 0):8.0f} {moy(dij, 1):8.2f} | "
                  f"{moy(glo, 0):8.0f} {moy(glo, 1):8.2f} {sum(ecarts) / len(ecarts):8.1f}% {max(ecarts):6.1f}% | "
                  f"{moy(nous, 0):8.0f} {moy(nous, 1):8.2f}")
    print("\nLecture :")
    print("  - Dijkstra pur et notre algorithme trouvent toujours exactement la même longueur (vérifié par assertion).")
    print("    Notre algorithme explore beaucoup moins de cases grâce à la boussole.")
    print("  - Le glouton est le plus rapide, mais son chemin est plus long que l'optimal"
          f" ({'dans tous les cas mesurés' if tout_plus_long else 'dans certains cas'}) : il ne répond pas à « plus court chemin ».")


if __name__ == "__main__":
    main()
