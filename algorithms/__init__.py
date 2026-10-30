"""
Dossier des algorithmes : chaque méthode s'appelle en une ligne.

    from algorithms import Grid, astar, bfs, dijkstra, anytime_astar

    grille = Grid(20, 30)
    grille.blocked[5][7] = True                          # un obstacle
    res = astar(grille, (0, 0), (19, 29))                # 4 directions
    res = astar(grille, (0, 0), (19, 29), diagonals=True)
    res = astar(grille, (0, 0), (19, 29), budget_ms=50)  # temps de calcul borné
    print(res.found, res.cost, res.explored, res.time_ms, res.path)

Méthodes : bfs, dijkstra, astar (weight=1 optimal, weight>1 pondéré), anytime_astar.
"""
from .anytime import anytime_astar
from .astar import astar
from .bfs import bfs
from .dijkstra import dijkstra
from .grid import INF, SQRT2, Grid, maze_grid, random_grid
from .heuristics import heuristic_for, manhattan, octile, path_cost
from .result import SearchResult

__all__ = ["Grid", "SearchResult", "bfs", "dijkstra", "astar", "anytime_astar", "random_grid", "maze_grid",
           "manhattan", "octile", "heuristic_for", "path_cost", "SQRT2", "INF"]
