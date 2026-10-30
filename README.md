# Banc d'essai - navigation de robot (thème 2)

## Lancer
    pip install numpy pandas matplotlib
    python algorithms.py            # mini démonstration (60x60, graine 42)
    python benchmark.py --quick     # test rapide (quelques secondes)
    python benchmark.py             # banc complet (environ 1 minute)

Sur Windows : `py benchmark.py`.

## Fichiers
- `algorithms.py` : grille, générateurs (aléatoire, labyrinthe), heuristiques Manhattan et octile, BFS, Dijkstra,
  A*, A* pondéré, A* anytime avec budget de temps. Registre `ALGORITHMS` : ajouter une méthode = une ligne.
- `benchmark.py` : expériences, statistiques (moyenne et IC95 %), CSV, graphiques, `summary.md`.
- `resultats/` : sorties du dernier lancement (graine 42).

## Expériences
1. Taille de la grille (20, 50, 100), 4 et 8 directions.
2. Densité d'obstacles (10, 25, 40 %).
3. Environnement aléatoire contre labyrinthe.
4. Dynamique : le robot avance pendant que des obstacles apparaissent et disparaissent ; comparaison de trois
   politiques de replanification (paresseuse = niveau 2, intelligente = niveau 3, systématique).

## Mesures
Temps de calcul (ms), coût du chemin, cases explorées, écart à l'optimal (%), nombre de replanifications,
temps de calcul cumulé, chemin parcouru / chemin initial optimal, taux de réussite.

## Limites connues (à écrire dans le rapport)
- Les temps dépendent de la machine et de Python ; seuls les ordres de grandeur et les comparaisons relatives comptent.
- Dans l'expérience dynamique, les changements sont aléatoires et la cible reste fixe. Le cas des portes de
  droite qui bougent (cible mobile) n'est pas encore simulé.
- Le budget de temps n'est testé que via l'approche anytime ; le plan de repli « case explorée la plus proche »
  existe dans `astar(budget_ms=...)` mais n'a pas encore d'expérience dédiée.
