"""
Mesure du gain des structures de données personnalisées (grille plate + file à seaux + tableaux réutilisés)
par rapport à une version classique (dictionnaires, tuples, heapq).

Lancer depuis le dossier du projet :   py tests/benchmark_structures.py
Vérifie aussi, sur chaque grille, que les deux versions trouvent exactement la même longueur de chemin.
"""
import os
import random
import sys
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algorithms import maze_grid, random_grid, shortest_path  # noqa: E402
from reference_heapq import astar_reference  # noqa: E402

REPS = 3


def mesure(grille, s, t, diag):
    """Renvoie (cas) pour la référence et pour notre version : temps ms, cases, pic mémoire en Mo, coût."""
    ref_cost, ref_n, _ = astar_reference(grille, s, t, diag)
    ref_ms = sum(astar_reference(grille, s, t, diag)[2] for _ in range(REPS)) / REPS
    tracemalloc.start()
    astar_reference(grille, s, t, diag)
    ref_mem = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    r = shortest_path(grille, s, t, diag)                       # crée l'espace de travail (une seule fois)
    new_ms = sum(shortest_path(grille, s, t, diag).time_ms for _ in range(REPS)) / REPS
    tracemalloc.start()
    r2 = shortest_path(grille, s, t, diag)
    new_mem = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    assert abs(ref_cost - r.cost) < 1e-6, f"longueurs différentes : {ref_cost} contre {r.cost}"
    return (ref_ms, ref_n, ref_mem), (new_ms, r.explored, new_mem)


def main():
    print("Gain des structures personnalisées (moyennes ; temps en ms, mémoire en Mo = pic pendant UNE recherche)\n")
    print(f"{'Environnement':<22} {'Dir.':>4} | {'Classique (dict + heapq)':^25} | {'Notre version (plat + seaux)':^25} | {'gain':>11}")
    print(f"{'':<22} {'':>4} | {'ms':>8} {'Mo':>7} {'cases':>8} | {'ms':>8} {'Mo':>7} {'cases':>8} | {'temps':>5} {'mém.':>5}")
    cas = [("aléatoire 60x60", "a", 60, 8), ("aléatoire 100x100", "a", 100, 8), ("aléatoire 200x200", "a", 200, 5),
           ("aléatoire 300x300", "a", 300, 4), ("aléatoire 500x500", "a", 500, 3),
           ("labyrinthe 61x61", "m", 61, 5), ("labyrinthe 201x201", "m", 201, 4), ("labyrinthe 301x301", "m", 301, 3)]
    for nom, kind, taille, nb in cas:
        for diag in (False, True):
            if taille >= 500 and diag:
                continue
            A, B = [], []
            for i in range(60):
                if len(A) >= nb:
                    break
                rng = random.Random(1000 + i)
                g, s, t = random_grid(taille, taille, 0.25, rng) if kind == "a" else maze_grid(taille, taille, rng)
                if not shortest_path(g, s, t, diag).found:
                    continue
                a, b = mesure(g, s, t, diag)
                A.append(a)
                B.append(b)
            m = lambda L, k: sum(x[k] for x in L) / len(L)
            print(f"{nom:<22} {'8' if diag else '4':>4} | {m(A, 0):8.1f} {m(A, 2):7.2f} {m(A, 1):8.0f} | "
                  f"{m(B, 0):8.1f} {m(B, 2):7.2f} {m(B, 1):8.0f} | x{m(A, 0) / m(B, 0):4.1f} x{m(A, 2) / max(m(B, 2), 1e-9):5.0f}")
    print("\nMémoire de l'espace de travail (allouée UNE fois par grille, puis réutilisée) : 12 octets par case,")
    for n in (60, 100, 200, 500, 1000):
        print(f"  grille {n}x{n} : {12 * (n + 2) * (n + 2) / 1e6:.2f} Mo", end=";")
    print("\nVérifié : sur chaque grille, les deux versions trouvent exactement la même longueur de chemin.")


if __name__ == "__main__":
    main()
