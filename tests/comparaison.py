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

print("""
--------------------------------------------------------------------------------
Même A*, deux files ouvertes. La longueur ne doit pas changer.
  liste : extraire le min est O(n)  →  pire cas O(V²)
  tas   : extraire le min est O(log n)  →  pire cas O(V log V) sur une grille
La liste est limitée à de petites cartes : sur 100×100 elle devient très lente,
c'est justement ce que la complexité annonce.
""")
print(f"{'Taille':>8} | {'A* liste':^32} | {'A* tas (projet)':^32}")
print(f"{'':>8} | {'cases':>8} {'ms':>8} {'noeuds':>8} {'insert':>8} | {'cases':>8} {'ms':>8} {'noeuds':>8} {'insert':>8}")
for taille in (20, 40):
    liste, tas = [], []
    for i in range(12):
        g, s, t = random_grid(taille, taille, 0.25, random.Random(2000 + i))
        a = shortest_path(g, s, t, False, structure="list")
        if not a.found:
            continue
        b = shortest_path(g, s, t, False, structure="heap")
        assert abs(a.cost - b.cost) < 1e-9, "liste et tas doivent trouver la même longueur"
        assert a.explored == b.explored, "même heuristique : le même nombre de cases ouvertes"
        liste.append(a)
        tas.append(b)
    moy = lambda lst, attr: sum(getattr(r, attr) for r in lst) / len(lst)
    print(f"{taille:>3}x{taille:<4} | "
          f"{moy(liste, 'explored'):8.0f} {moy(liste, 'time_ms'):8.2f} {moy(liste, 'nodes'):8.0f} {moy(liste, 'pushes'):8.0f} | "
          f"{moy(tas, 'explored'):8.0f} {moy(tas, 'time_ms'):8.2f} {moy(tas, 'nodes'):8.0f} {moy(tas, 'pushes'):8.0f}")

print("""
Niveau 3 : même carte, budget très court. Le tas finit plus souvent avant l'échéance.
Un timeout n'est pas un chemin jusqu'à la cible : c'est le plan de repli.
""")
for budget in (0.05, 0.2, 1.0):
    fin_liste = fin_tas = 0
    essais = 0
    for i in range(10):
        g, s, t = random_grid(50, 50, 0.25, random.Random(3000 + i))
        a = shortest_path(g, s, t, False, budget_ms=budget, structure="list")
        b = shortest_path(g, s, t, False, budget_ms=budget, structure="heap")
        if not (a.found or a.timed_out):
            continue
        essais += 1
        fin_liste += int(a.found)
        fin_tas += int(b.found)
    print(f"  budget {budget:>4} ms, {essais} grilles 50×50 : "
          f"cible atteinte  liste {fin_liste}/{essais}   tas {fin_tas}/{essais}")

