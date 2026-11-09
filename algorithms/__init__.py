"""
Dossier de l'algorithme : un seul algorithme de plus court chemin, appelé en une ligne.

    from algorithms import Grid, shortest_path

    grille = Grid(20, 30)
    grille.blocked[5][7] = True                                    # un obstacle
    res = shortest_path(grille, (0, 0), (19, 29))                  # 4 directions
    res = shortest_path(grille, (0, 0), (19, 29), diagonals=True)  # 8 directions
    res = shortest_path(grille, (0, 0), (19, 29), budget_ms=50)    # temps de calcul borné
    print(res.found, res.cost, res.explored, res.time_ms, res.path)
"""
from .grid import INF, SQRT2, Grid, maze_grid, random_grid
from .heuristics import heuristic_for, manhattan, octile, path_cost
from .result import SearchResult
from .shortest_path import shortest_path

__all__ = ["Grid", "SearchResult", "shortest_path", "random_grid", "maze_grid", "manhattan", "octile",
           "heuristic_for", "path_cost", "SQRT2", "INF"]
