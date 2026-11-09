"""
Justification du choix de l'algorithme : avec ou sans « boussole » (même code, guided=True / False).

Lancer depuis le dossier du projet :   py tests/comparaison.py
Le script vérifie aussi que les deux versions trouvent toujours un chemin de MÊME longueur (le plus court).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algorithms import random_grid, shortest_path  # noqa: E402

NB_GRILLES = 30
print(f"{NB_GRILLES} grilles aléatoires par configuration, 25 % d'obstacles, graine fixe, mêmes grilles pour les deux.\n")
print(f"{'Taille':>8} {'Directions':>10} | {'Dijkstra pur':^28} | {'Notre algorithme':^28}")
print(f"{'':>8} {'':>10} | {'cases':>8} {'ms':>8} {'longueur':>9} | {'cases':>8} {'ms':>8} {'longueur':>9}")
for taille in (20, 50, 100):
    for diag in (False, True):
        pur, guide = [], []
        for i in range(NB_GRILLES):
            g, s, t = random_grid(taille, taille, 0.25, random.Random(1000 + i))
            a = shortest_path(g, s, t, diag, guided=False)
            if not a.found:
                continue
            b = shortest_path(g, s, t, diag, guided=True)
            assert abs(a.cost - b.cost) < 1e-9, "les deux longueurs devraient être identiques"
            pur.append(a)
            guide.append(b)
        moy = lambda lst, attr: sum(getattr(r, attr) for r in lst) / len(lst)
        print(f"{taille:>3}x{taille:<4} {'8' if diag else '4':>10} | "
              f"{moy(pur, 'explored'):8.0f} {moy(pur, 'time_ms'):8.2f} {moy(pur, 'cost'):9.1f} | "
              f"{moy(guide, 'explored'):8.0f} {moy(guide, 'time_ms'):8.2f} {moy(guide, 'cost'):9.1f}")
print("\nVérifié : sur toutes les grilles, les deux versions trouvent exactement la même longueur (le plus court).")
