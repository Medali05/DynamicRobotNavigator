"""
Image : la même grille, trois méthodes (cases explorées en bleu, chemin en orange).

Installation :  pip install matplotlib
Lancer depuis le dossier du projet :   py tests/figure_comparaison.py      ->  tests/figure_comparaison.png
"""
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
sys.path.insert(0, ICI)
from algorithms import path_cost, random_grid, shortest_path  # noqa: E402
from comparaison import glouton  # noqa: E402,F401  (réutilise le glouton du script de comparaison)

TAILLE, GRAINE = 30, 7
g, s, t = random_grid(TAILLE, TAILLE, 0.25, random.Random(GRAINE))

dij = shortest_path(g, s, t, False, guided=False)
nous = shortest_path(g, s, t, False)
chemin_g, n_g, _ = glouton(g, s, t, False)
# le glouton n'expose pas ses cases explorées : on les recalcule avec la même méthode
import heapq  # noqa: E402
from algorithms import heuristic_for  # noqa: E402
h = heuristic_for(False)
vues, parent, file, ordre, dev = {s}, {s: None}, [(h(s, t), 0, s)], 0, set()
while file:
    _, _, c = heapq.heappop(file)
    dev.add(c)
    if c == t:
        break
    for v, _ in g.neighbors(c[0], c[1], False):
        if v not in vues:
            vues.add(v); parent[v] = c; ordre += 1
            heapq.heappush(file, (h(v, t), ordre, v))

panneaux = [("Dijkstra pur", dij.visited, dij.path, dij.explored, dij.cost),
            ("Glouton", dev, chemin_g, n_g, path_cost(chemin_g)),
            ("Notre algorithme", nous.visited, nous.path, nous.explored, nous.cost)]
fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
for ax, (nom, vis, chemin, n, cout) in zip(axes, panneaux):
    img = np.zeros((TAILLE, TAILLE))
    for (r, c) in vis:
        img[r, c] = 1
    for r in range(TAILLE):
        for c in range(TAILLE):
            if g.blocked[r][c]:
                img[r, c] = 2
    ax.imshow(img, cmap=ListedColormap(["#f4f6fb", "#b9d0ff", "#3b4252"]), vmin=0, vmax=2, interpolation="nearest")
    ys, xs = zip(*chemin)
    ax.plot(xs, ys, color="#ff7a1a", linewidth=2.4)
    ax.scatter([s[1]], [s[0]], c="#1fa35c", s=70, zorder=3)
    ax.scatter([t[1]], [t[0]], c="#e5484d", s=70, zorder=3)
    ax.set_title(f"{nom}\n{n} cases explorées · longueur {cout:.0f}", fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("Même grille 30×30 (25 % d'obstacles) : cases explorées en bleu, chemin en orange", fontsize=12, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.94))
sortie = os.path.join(ICI, "figure_comparaison.png")
fig.savefig(sortie, dpi=140)
print("Image créée :", sortie)
for nom, _, _, n, cout in panneaux:
    print(f"  {nom:18s} {n:5d} cases, longueur {cout:.1f}")
