"""Algorithme du projet. L'application n'importe que ce fichier.

    from algorithms import Grid, shortest_path

Deux dossiers, deux rôles :

    world/     la carte
        node.py          une case pendant la recherche (g, parent)
        grid.py          obstacles et voisins
        maps.py          cartes aléatoires et labyrinthes
    search/    le calcul
        heuristic.py     boussole Manhattan ou octile
        astar.py         A* (tas pour l'application, liste pour la comparaison)
        path_manager.py  reconstruit le chemin et son coût
        result.py        ce que la recherche renvoie
        shortest_path.py la fonction appelée par simulation.py
    constants.py         √2, infini, directions 4 et 8

Un seul algorithme est utilisé par le robot : shortest_path(), c'est-à-dire A* avec tas.
"""
from .constants import INF, SQRT2
from .search import (AStar, Heuristic, PathManager, SearchResult, heuristic_for, manhattan, octile,
                     path_cost, shortest_path)
from .world import Grid, Node, maze_grid, random_grid

__all__ = ["Grid", "Node", "Heuristic", "PathManager", "AStar", "SearchResult", "shortest_path",
           "random_grid", "maze_grid", "manhattan", "octile", "heuristic_for", "path_cost", "SQRT2", "INF"]
