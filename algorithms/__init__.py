"""
Dossier de l'algorithme : un seul algorithme de plus court chemin, appelé en une ligne.

    from algorithms import Grid, shortest_path

    grille = Grid(60, 60)
    grille.blocked[5][7] = True                                    # un obstacle
    res = shortest_path(grille, (0, 0), (59, 59))                  # 4 directions
    res = shortest_path(grille, (0, 0), (59, 59), diagonals=True)  # 8 directions
    res = shortest_path(grille, (0, 0), (59, 59), budget_ms=50)    # temps de calcul borné
    print(res.found, res.cost, res.explored, res.time_ms, res.path)

Fichiers : grid.py (grille plate), file_a_seaux.py (file de priorité à seaux), shortest_path.py (l'algorithme),
heuristics.py (la boussole), result.py (format de la réponse).
"""
from .file_a_seaux import FileASeaux
from .grid import DIAG_COST, INF, Grid, maze_grid, random_grid
from .heuristics import heuristic_for, manhattan, octile, path_cost
from .result import SearchResult
from .shortest_path import shortest_path

__all__ = ["Grid", "SearchResult", "FileASeaux", "shortest_path", "random_grid", "maze_grid", "manhattan",
           "octile", "heuristic_for", "path_cost", "DIAG_COST", "INF"]
