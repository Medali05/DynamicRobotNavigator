"""
benchmark.py - Banc d'essai du projet de navigation de robot.

Utilisation :
    python benchmark.py            # banc complet (quelques minutes)
    python benchmark.py --quick    # version rapide pour tester
    python benchmark.py --out dossier

Sorties (dans le dossier resultats/ par défaut) :
    static.csv, dynamic.csv        données brutes (une ligne par mesure)
    summary.md                     tableaux moyenne +- IC95 % prêts pour le rapport
    fig_*.png                      graphiques

Protocole : mêmes instances pour toutes les méthodes (graines fixes), plusieurs instances par
configuration, plusieurs répétitions chronométrées, moyenne et intervalle de confiance à 95 %.
"""
from __future__ import annotations

import argparse
import os
import random
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from algorithms import (ALGORITHMS, SQRT2, Grid, astar, bfs, dijkstra, heuristic_for,
                        maze_grid, path_cost, random_grid)

SEED = 42
DYN_DENSITY = 0.30  # assez dense pour que le chemin optimal ne soit pas toujours la distance de Manhattan
COLORS = {
    "BFS": "#9aa5b1", "Dijkstra": "#e08a3c", "A*": "#2f6fed",
    "A* pondéré (w=2)": "#8e5bd6", "Anytime (50 ms)": "#2fa36b",
}
POLICY_COLORS = {"paresseux (niveau 2)": "#9aa5b1", "intelligent (niveau 3)": "#2f6fed",
                 "systématique": "#e08a3c"}


# =========================================================================== instances
def make_instance(kind: str, size: int, density: float, seed: int):
    """Instance résoluble en 4 directions (donc aussi en 8). On avance la graine jusqu'à en trouver une."""
    attempt = 0
    while True:
        rng = random.Random(SEED * 100003 + seed * 101 + attempt)
        if kind == "labyrinthe":
            grid, s, t = maze_grid(size, size, rng)
        else:
            grid, s, t = random_grid(size, size, density, rng)
        if bfs(grid, s, t, False).found:
            return grid, s, t
        attempt += 1


# =========================================================================== expériences statiques
def run_static(configs, n_instances: int, reps: int) -> pd.DataFrame:
    rows = []
    for cfg in configs:
        t_cfg = time.time()
        for i in range(n_instances):
            grid, s, t = make_instance(cfg["kind"], cfg["size"], cfg["density"], i)
            optimum = dijkstra(grid, s, t, cfg["diagonals"]).cost
            for name, fn in ALGORITHMS.items():
                times = []
                for _ in range(reps):
                    res = fn(grid, s, t, cfg["diagonals"])
                    times.append(res.time_ms)
                rows.append({
                    "experience": cfg["exp"], "environnement": cfg["kind"], "taille": cfg["size"],
                    "densite": cfg["density"], "diagonales": cfg["diagonals"], "instance": i,
                    "algorithme": name, "temps_ms": float(np.mean(times)), "cout": res.cost,
                    "explorees": res.explored, "trouve": res.found,
                    "ecart_optimal_pct": max(0.0, round((res.cost / optimum - 1.0) * 100.0, 6)) if res.found else np.nan,
                })
        print(f"  [{cfg['exp']}] {cfg['kind']} {cfg['size']}x{cfg['size']} d={cfg['density']} "
              f"{'8' if cfg['diagonals'] else '4'} dir : {time.time() - t_cfg:.1f} s")
    return pd.DataFrame(rows)


# =========================================================================== expérience dynamique
def _path_valid(grid: Grid, remaining: list, diagonals: bool) -> bool:
    for a, b in zip(remaining, remaining[1:]):
        if grid.blocked[b[0]][b[1]]:
            return False
        if diagonals and a[0] != b[0] and a[1] != b[1]:
            if grid.blocked[a[0]][b[1]] or grid.blocked[b[0]][a[1]]:
                return False
    return True


def _toggle_obstacles(grid: Grid, rate: float, pos, goal, rng: random.Random):
    """Applique des changements aléatoires : en moyenne `rate` cellules modifiées par pas.
    Autant d'apparitions que de disparitions en moyenne, pour garder une densité stable."""
    n = int(rate) + (1 if rng.random() < rate - int(rate) else 0)
    added = removed = 0
    for _ in range(n):
        want_block = rng.random() < 0.5
        for _try in range(80):
            r, c = rng.randrange(grid.rows), rng.randrange(grid.cols)
            if (r, c) == pos or (r, c) == goal:
                continue
            if want_block and not grid.blocked[r][c]:
                grid.blocked[r][c] = True
                added += 1
                break
            if (not want_block) and grid.blocked[r][c]:
                grid.blocked[r][c] = False
                removed += 1
                break
    return added, removed


def simulate(grid0: Grid, start, goal, policy: str, rate: float, rng: random.Random,
             diagonals: bool = False):
    """
    Le robot avance d'une case par pas pendant que l'environnement change.
    Politiques de replanification :
      paresseux (niveau 2)    : seulement si le chemin restant devient impraticable
      intelligent (niveau 3)  : idem + quand un obstacle disparaît ET que le chemin restant peut être
                                raccourci (coût restant > heuristique robot-cible)
      systématique            : à chaque changement, quel qu'il soit
    """
    grid = grid0.copy()
    h = heuristic_for(diagonals)
    max_steps = 6 * (grid.rows + grid.cols)
    first = astar(grid, start, goal, diagonals, 1.0)
    initial_cost = first.cost
    pos, path, idx = start, first.path, 0
    compute, replans, travelled, steps = first.time_ms, 1, 0.0, 0
    while pos != goal and steps < max_steps:
        steps += 1
        added, removed = _toggle_obstacles(grid, rate, pos, goal, rng)
        remaining = path[idx:]
        no_route = len(remaining) < 2
        invalid = (not no_route) and not _path_valid(grid, remaining, diagonals)
        need = no_route or invalid
        if policy == "intelligent (niveau 3)" and removed and not need:
            need = path_cost(remaining) > h(pos, goal) + 1e-9
        elif policy == "systématique" and (added or removed):
            need = True
        if need:
            res = astar(grid, pos, goal, diagonals, 1.0)
            compute += res.time_ms
            replans += 1
            path, idx = (res.path, 0) if res.found else ([pos], 0)
        if len(path) - idx > 1:
            nxt = path[idx + 1]
            travelled += SQRT2 if (nxt[0] != pos[0] and nxt[1] != pos[1]) else 1.0
            pos = nxt
            idx += 1
    ok = pos == goal
    return {"succes": ok, "pas": steps, "cout_parcouru": travelled, "replanifications": replans,
            "calcul_ms": compute, "etirement": travelled / initial_cost if ok else np.nan}


def run_dynamic(size: int, density: float, rates, policies, n_seeds: int) -> pd.DataFrame:
    rows = []
    for rate in rates:
        t_rate = time.time()
        for seed in range(n_seeds):
            grid, s, t = make_instance("aléatoire", size, density, 1000 + seed)
            for policy in policies:
                rng = random.Random(SEED * 7919 + seed * 31 + int(rate * 100))
                out = simulate(grid, s, t, policy, rate, rng)
                rows.append({"taux_changement": rate, "politique": policy, "graine": seed, **out})
        print(f"  [dynamique] taux {rate} : {time.time() - t_rate:.1f} s")
    return pd.DataFrame(rows)


# =========================================================================== statistiques et tableaux
def ci95(series: pd.Series) -> float:
    s = series.dropna()
    return 1.96 * s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else 0.0


def md_table(df: pd.DataFrame, group_cols, value_cols, labels) -> str:
    lines = ["| " + " | ".join(list(group_cols) + [labels[v] for v in value_cols]) + " |",
             "|" + "|".join(["---"] * (len(group_cols) + len(value_cols))) + "|"]
    for keys, sub in df.groupby(list(group_cols), sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        cells = [str(k) for k in keys]
        for v in value_cols:
            m, c = sub[v].mean(), ci95(sub[v])
            cells.append(f"{m:.2f} ± {c:.2f}" if v != "explorees" else f"{m:.0f} ± {c:.0f}")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# =========================================================================== graphiques
def grouped_bars(ax, df, x, hue, y, ylabel, log=False, colors=COLORS):
    xs = sorted(df[x].unique())
    hues = list(dict.fromkeys(df[hue]))
    w = 0.8 / len(hues)
    for i, hv in enumerate(hues):
        sub = df[df[hue] == hv].groupby(x)[y]
        m = sub.mean().reindex(xs)
        ci = sub.apply(ci95).reindex(xs)
        ax.bar(np.arange(len(xs)) + (i - (len(hues) - 1) / 2) * w, m, w, yerr=ci, capsize=2,
               label=hv, color=colors.get(hv), edgecolor="white", linewidth=0.5)
    ax.set_xticks(np.arange(len(xs)))
    ax.set_xticklabels([str(v) for v in xs])
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)


def fig_static(df, exp, x, xlabel, title, path):
    sub = df[df.experience == exp]
    dirs = sorted(sub.diagonales.unique())
    fig, axes = plt.subplots(len(dirs), 3, figsize=(15, 4.2 * len(dirs)), squeeze=False)
    for r, d in enumerate(dirs):
        data = sub[sub.diagonales == d]
        lab = "8 directions" if d else "4 directions"
        grouped_bars(axes[r][0], data, x, "algorithme", "temps_ms", "Temps de calcul (ms)", log=True)
        grouped_bars(axes[r][1], data, x, "algorithme", "explorees", "Cases explorées", log=True)
        ok = data[data.algorithme != "BFS"] if not d else data
        grouped_bars(axes[r][2], ok, x, "algorithme", "ecart_optimal_pct", "Écart à l'optimal (%)")
        axes[r][0].set_title(f"{lab} - temps")
        axes[r][1].set_title(f"{lab} - cases explorées")
        axes[r][2].set_title(f"{lab} - écart à l'optimal")
        for c in range(3):
            axes[r][c].set_xlabel(xlabel)
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=len(l), frameon=False)
    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_exploration(path, size=40, density=0.25, diagonals=False):
    grid, s, t = make_instance("aléatoire", size, density, 7)
    names = ["BFS", "Dijkstra", "A*", "A* pondéré (w=2)"]
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.6))
    for ax, name in zip(axes, names):
        res = ALGORITHMS[name](grid, s, t, diagonals)
        img = np.zeros((grid.rows, grid.cols))
        for (r, c) in res.visited:
            img[r, c] = 1
        for r in range(grid.rows):
            for c in range(grid.cols):
                if grid.blocked[r][c]:
                    img[r, c] = 2
        ax.imshow(img, cmap=matplotlib.colors.ListedColormap(["#101319", "#9db8f5", "#4a5163"]),
                  vmin=0, vmax=2, interpolation="nearest")
        ys, xs = zip(*res.path)
        ax.plot(xs, ys, color="#ff7a45", linewidth=2)
        ax.scatter([s[1]], [s[0]], c="#2fa36b", s=60, zorder=3)
        ax.scatter([t[1]], [t[0]], c="#e5484d", s=60, zorder=3)
        ax.set_title(f"{name}\ncoût {res.cost:.1f} - {res.explored} cases - {res.time_ms:.1f} ms", fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"Cases explorées (bleu clair) sur la même grille {size}x{size}, {int(density*100)} % d'obstacles",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_dynamic(df, path):
    """Taux de réussite sur toutes les exécutions ; les autres mesures sur les parcours réussis seulement
    (un robot bloqué replanifie à chaque pas, ce qui fausserait les moyennes)."""
    panels = [("replanifications", "Nombre de replanifications (parcours réussis)", None),
              ("calcul_ms", "Temps de calcul cumulé (ms, parcours réussis)", None),
              ("etirement", "Chemin parcouru / chemin initial optimal", None),
              ("succes", "Taux de réussite", (0.8, 1.02))]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    for ax, (col, label, ylim) in zip(axes.ravel(), panels):
        for pol, sub in df.groupby("politique", sort=False):
            if col != "succes":
                sub = sub[sub.succes]
            g = sub.groupby("taux_changement")[col]
            m, ci = g.mean(), g.apply(ci95)
            lo, hi = (m - ci).clip(lower=0), m + ci
            if col == "succes":
                hi = hi.clip(upper=1.0)
            ax.plot(m.index, m.values, marker="o", label=pol, color=POLICY_COLORS.get(pol))
            ax.fill_between(m.index, lo, hi, alpha=0.18, color=POLICY_COLORS.get(pol))
        ax.set_xlabel("Fréquence des changements (cellules modifiées par pas)")
        ax.set_ylabel(label)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(alpha=0.25)
    axes[0][0].legend(frameon=False)
    fig.suptitle(f"Environnement dynamique : politiques de replanification avec A* "
                 f"(40x40, {int(DYN_DENSITY * 100)} % d'obstacles)", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=140)
    plt.close(fig)


# =========================================================================== programme principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="version rapide")
    ap.add_argument("--out", default="resultats")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    if args.quick:
        n_inst, reps, sizes, seeds, rates = 4, 1, (20, 40), 5, (0.0, 0.5, 2.0)
    else:
        n_inst, reps, sizes, seeds, rates = 30, 3, (20, 50, 100), 60, (0.0, 0.1, 0.3, 0.6, 1.0, 2.0)
    mid = sizes[1]

    print("Expériences statiques")
    configs = []
    for d in (False, True):
        for sz in sizes:
            configs.append(dict(exp="taille", kind="aléatoire", size=sz, density=0.25, diagonals=d))
    for dens in (0.10, 0.25, 0.40):
        configs.append(dict(exp="densité", kind="aléatoire", size=mid, density=dens, diagonals=True))
    for kind in ("aléatoire", "labyrinthe"):
        configs.append(dict(exp="environnement", kind=kind, size=mid + (1 - mid % 2), density=0.25, diagonals=False))
    static = run_static(configs, n_inst, reps)
    static.to_csv(os.path.join(args.out, "static.csv"), index=False)

    print("Expérience dynamique")
    policies = ["paresseux (niveau 2)", "intelligent (niveau 3)", "systématique"]
    dyn = run_dynamic(40 if not args.quick else 25, DYN_DENSITY, rates, policies, seeds)
    dyn.to_csv(os.path.join(args.out, "dynamic.csv"), index=False)

    print("Graphiques")
    fig_static(static, "taille", "taille", "Côté de la grille (cases)",
               "Passage à l'échelle : 25 % d'obstacles", os.path.join(args.out, "fig_taille.png"))
    d = static[static.experience == "densité"].copy()
    d["densite_pct"] = (d.densite * 100).round().astype(int)
    d["experience"] = "densité"
    fig_static(d, "densité", "densite_pct", "Densité d'obstacles (%)",
               f"Influence de la densité d'obstacles ({mid}x{mid}, 8 directions)",
               os.path.join(args.out, "fig_densite.png"))
    e = static[static.experience == "environnement"].copy()
    e["env"] = e.environnement
    fig_static(e, "environnement", "env", "Type d'environnement",
               "Environnement aléatoire contre labyrinthe (4 directions)",
               os.path.join(args.out, "fig_environnement.png"))
    fig_exploration(os.path.join(args.out, "fig_exploration.png"))
    fig_dynamic(dyn, os.path.join(args.out, "fig_dynamique.png"))

    labels = {"temps_ms": "Temps (ms)", "explorees": "Cases explorées", "cout": "Coût du chemin",
              "ecart_optimal_pct": "Écart à l'optimal (%)", "replanifications": "Replanifications",
              "calcul_ms": "Calcul cumulé (ms)", "etirement": "Parcouru / optimal initial",
              "succes": "Taux de réussite"}
    md = [f"# Résultats du banc d'essai (graine {SEED}, {n_inst} instances x {reps} répétitions)\n",
          "Valeurs : moyenne ± intervalle de confiance à 95 %.\n"]
    for exp, title in (("taille", "Taille de la grille (25 % d'obstacles)"),
                       ("densité", "Densité d'obstacles (8 directions)"),
                       ("environnement", "Type d'environnement (4 directions)")):
        sub = static[static.experience == exp].copy()
        sub["direction"] = np.where(sub.diagonales, "8 dir.", "4 dir.")
        key = {"taille": "taille", "densité": "densite", "environnement": "environnement"}[exp]
        sub = sub.sort_values([ "direction", key], kind="stable")
        md.append(f"\n## {title}\n")
        md.append(md_table(sub, ["direction", key, "algorithme"],
                           ["temps_ms", "explorees", "cout", "ecart_optimal_pct"], labels))
    md.append(f"\n## Environnement dynamique (A*, 40x40, {int(DYN_DENSITY * 100)} % d'obstacles)\n")
    md.append("Taux de réussite sur toutes les exécutions ; autres colonnes sur les parcours réussis.\n")
    md.append(md_table(dyn[dyn.succes], ["taux_changement", "politique"],
                       ["replanifications", "calcul_ms", "etirement"], labels))
    md.append("\n### Taux de réussite\n")
    md.append(md_table(dyn, ["taux_changement", "politique"], ["succes"], labels))
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"Terminé. Résultats dans {args.out}/")


if __name__ == "__main__":
    main()
