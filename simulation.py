"""
simulation.py - Logique de l'application (aucune dépendance à l'interface graphique).

La classe Simulation gère : la grille, le robot, la destination, le chemin, les niveaux 1 à 3,
les changements dynamiques et le mode « portes colorées ». ui/ ne fait que l'afficher.

Un seul algorithme de recherche est utilisé partout : shortest_path (algorithms/shortest_path.py).

Niveau 1 : le robot calcule le plus court chemin vers la cible et le suit (obstacles fixes, les clics
           sont ignorés pendant le déplacement).
Niveau 2 : des obstacles apparaissent et disparaissent, certains sur le trajet du robot, qui doit alors
           chercher un autre chemin (on recalcule seulement quand le chemin devient impraticable).
Niveau 3 : niveau 2 + calcul sous budget de temps (plan de repli si dépassé) + on recalcule aussi quand
           un obstacle disparaît et qu'un chemin plus court est possible.
"""
from __future__ import annotations

import random

from algorithms import SQRT2, Grid, heuristic_for, maze_grid, path_cost, shortest_path


DOOR_COLORS = ["rouge", "bleu", "vert", "jaune", "violet"]
DOOR_SHAPES = ["cercle", "carré", "triangle", "étoile", "hexagone"]  # lisible par un daltonien

SIZES = {"Petite (13×19)": (13, 19), "Moyenne (21×31)": (21, 31), "Grande (31×45)": (31, 45)}


class Simulation:
    def __init__(self, rows: int = 21, cols: int = 31, seed=None):
        self.rng = random.Random(seed)
        # paramètres réglables depuis l'interface
        self.level = 1
        self.diagonals = False
        self.block_bias = 0.6       # part des nouveaux obstacles qui tombent sur le trajet du robot
        self.budget_ms = 50.0
        self.change_rate = 0.3      # cellules modifiées par pas (niveaux 2 et 3)
        self.door_rate = 0.03       # probabilité par pas que les portes de droite changent
        self.doors_mode = False
        self.start_color = 0
        # état
        self.new_grid(rows, cols)

    # ------------------------------------------------------------------ grille
    def new_grid(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.grid = Grid(rows, cols)
        self.doors_mode = False
        self.start = (rows // 2, 1)
        self.goal = (rows // 2, cols - 2)
        self.left_rows = self.right_rows = []
        self.right_colors = list(range(5))
        self.reset_robot()

    def clear(self):
        keep = self.wall_cells() if self.doors_mode else set()
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid.blocked[r][c] = (r, c) in keep
        self.reset_robot()

    def random_obstacles(self, density: float):
        protected = {self.start, self.goal}
        if self.doors_mode:
            for r in self.left_rows:
                protected.add((r, 1))
            for r in self.right_rows:
                protected.add((r, self.cols - 2))
        walls = self.wall_cells() if self.doors_mode else set()
        lo, hi = (1, self.cols - 1) if self.doors_mode else (0, self.cols)
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in walls:
                    self.grid.blocked[r][c] = True
                elif c < lo or c >= hi or (r, c) in protected:
                    self.grid.blocked[r][c] = False
                else:
                    self.grid.blocked[r][c] = self.rng.random() < density
        self.reset_robot()

    def maze(self):
        """Labyrinthe sur la grille courante (désactivé en mode portes)."""
        if self.doors_mode:
            return
        g, s, t = maze_grid(self.rows, self.cols, self.rng)
        self.grid = g
        self.rows, self.cols = g.rows, g.cols
        self.start, self.goal = s, t
        self.reset_robot()

    def set_obstacle(self, r: int, c: int, value: bool) -> bool:
        """Pose ou retire un obstacle. Renvoie True si la grille a changé."""
        cell = (r, c)
        if not self.grid.in_bounds(r, c) or cell in (self.pos, self.goal, self.start):
            return False
        if self.doors_mode and (cell in self.wall_cells() or cell in self.door_cells()):
            return False
        if self.level == 1 and self.status == "running":
            return False  # niveau 1 : édition ignorée pendant le déplacement
        if self.grid.blocked[r][c] == value:
            return False
        self.grid.blocked[r][c] = value
        if value:
            self._pending_added += 1
        else:
            self._pending_removed += 1
        if self.status != "running":
            self.plan_preview()
        return True

    def set_start(self, cell) -> bool:
        if self.doors_mode or not self.grid.free(*cell) or cell == self.goal:
            return False
        self.start = cell
        self.reset_robot()
        return True

    def set_goal(self, cell) -> bool:
        if self.doors_mode or not self.grid.free(*cell) or cell == self.start:
            return False
        self.goal = cell
        self.reset_robot()
        return True

    # ------------------------------------------------------------------ portes colorées
    def _door_rows(self):
        return [int((i + 0.5) * self.rows / 5) for i in range(5)]

    def door_cells(self):
        cells = {(r, 0) for r in self.left_rows}
        cells |= {(r, self.cols - 1) for r in self.right_rows}
        return cells

    def wall_cells(self):
        walls = set()
        for r in range(self.rows):
            if r not in self.left_rows:
                walls.add((r, 0))
            if r not in self.right_rows:
                walls.add((r, self.cols - 1))
        return walls

    def enable_doors(self, on: bool):
        """Active le mode portes : 5 portes colorées à gauche (fixes) et à droite (leurs couleurs changent)."""
        self.doors_mode = on
        if on:
            self.left_rows = self.right_rows = self._door_rows()
            self.right_colors = list(range(5))
            self.right_colors = self.rng.sample(range(5), 5)
            for r in range(self.rows):
                self.grid.blocked[r][0] = r not in self.left_rows
                self.grid.blocked[r][self.cols - 1] = r not in self.right_rows
            for r in self.left_rows:  # l'entrée de chaque porte reste dégagée
                self.grid.blocked[r][1] = False
            for r in self.right_rows:
                self.grid.blocked[r][self.cols - 2] = False
            self._place_robot_at_door()
        else:
            for r in range(self.rows):
                self.grid.blocked[r][0] = False
                self.grid.blocked[r][self.cols - 1] = False
            self.left_rows = self.right_rows = []
            self.start = (self.rows // 2, 1)
            self.goal = (self.rows // 2, self.cols - 2)
            self.reset_robot()

    def set_start_color(self, color_index: int):
        self.start_color = color_index
        if self.doors_mode:
            self._place_robot_at_door()

    def _target_row(self) -> int:
        slot = self.right_colors.index(self.start_color)
        return self.right_rows[slot]

    def _place_robot_at_door(self):
        self.start = (self.left_rows[self.start_color], 0)
        self.goal = (self._target_row(), self.cols - 1)
        self.reset_robot()

    def _shuffle_right_doors(self) -> str:
        """Échange les couleurs de deux portes de droite : les couleurs restent une permutation des 5."""
        i, j = self.rng.sample(range(5), 2)
        self.right_colors[i], self.right_colors[j] = self.right_colors[j], self.right_colors[i]
        self.goal = (self._target_row(), self.cols - 1)
        return f"Les portes de droite ont changé : la porte {DOOR_COLORS[self.start_color]} est maintenant en ligne {self.goal[0]}"

    # ------------------------------------------------------------------ robot
    def reset_robot(self):
        self.pos = self.start
        self.path = []
        self.idx = 0
        self.visited = set()
        self.status = "idle"      # idle | running | arrived | no_path
        self.replans = 0
        self.steps = 0
        self.travelled = 0.0
        self.last_ms = 0.0
        self.last_explored = 0
        self.last_cost = 0.0
        self.total_ms = 0.0
        self.fallback = False
        self.path_hits = []        # obstacles tombés sur le trajet pendant le dernier pas (pour l'affichage)
        self._pending_added = 0
        self._pending_removed = 0
        self.plan_preview()

    @property
    def use_diagonals(self) -> bool:
        return self.diagonals

    def _budget(self):
        return self.budget_ms if self.level == 3 else None

    def plan(self, count: bool = True):
        """Calcule un chemin depuis la position actuelle du robot vers la destination."""
        res = shortest_path(self.grid, self.pos, self.goal, self.use_diagonals, self._budget())
        self.last_ms, self.last_explored, self.last_cost = res.time_ms, res.explored, res.cost
        self.total_ms += res.time_ms
        self.visited = res.visited
        self.fallback = False
        if count:
            self.replans += 1
        if res.found:
            self.path, self.idx = res.path, 0
        elif res.timed_out and len(res.path) > 1:  # plan de repli : avancer vers la case explorée la plus proche
            self.path, self.idx, self.fallback = res.path, 0, True
        else:
            self.path, self.idx = [self.pos], 0
        return res

    def plan_preview(self):
        """Affiche le chemin prévu sans le compter comme une replanification."""
        if self.status == "running":
            return
        res = self.plan(count=False)
        self.status = "idle" if (res.found or self.fallback) else "no_path"

    def start_run(self):
        if self.status in ("arrived",):
            self.reset_robot()
        self.status = "running"
        self.replans = 0
        self.total_ms = 0.0
        self.plan(count=True)
        if len(self.path) < 2 and self.pos != self.goal:
            self.status = "no_path" if self.level == 1 else "running"

    def _valid(self, remaining) -> bool:
        for a, b in zip(remaining, remaining[1:]):
            if self.grid.blocked[b[0]][b[1]]:
                return False
            if self.use_diagonals and a[0] != b[0] and a[1] != b[1]:
                if self.grid.blocked[a[0]][b[1]] or self.grid.blocked[b[0]][a[1]]:
                    return False
        return True

    def _free_to_change(self, cell) -> bool:
        if cell in (self.pos, self.goal):
            return False
        if self.doors_mode:
            if cell in self.wall_cells() or cell in self.door_cells():
                return False
            if cell in {(r, 1) for r in self.left_rows} | {(r, self.cols - 2) for r in self.right_rows}:
                return False
        return True

    def _drop_on_path(self):
        """Fait tomber un obstacle sur le chemin restant (pas juste devant le robot). Refusé s'il coupe
        toute route vers la destination : le robot doit pouvoir se détourner."""
        ahead = [c for c in self.path[self.idx + 2:-1] if self._free_to_change(c)]
        self.rng.shuffle(ahead)
        for r, c in ahead[:6]:
            if self.grid.blocked[r][c]:
                continue
            self.grid.blocked[r][c] = True
            if shortest_path(self.grid, self.pos, self.goal, self.use_diagonals).found:
                return (r, c)
            self.grid.blocked[r][c] = False
        return None

    def _clear_near_path(self) -> bool:
        """Retire un obstacle voisin du chemin : un raccourci peut apparaître."""
        near = set()
        for (pr, pc) in self.path[self.idx:]:
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    near.add((pr + dr, pc + dc))
        cands = [(r, c) for (r, c) in near if self.grid.in_bounds(r, c) and self.grid.blocked[r][c]
                 and self._free_to_change((r, c))]
        if not cands:
            return False
        r, c = self.rng.choice(cands)
        self.grid.blocked[r][c] = False
        return True

    def _random_changes(self):
        rate = self.change_rate
        n = int(rate) + (1 if self.rng.random() < rate - int(rate) else 0)
        added = removed = 0
        for _ in range(n):
            want_block = self.rng.random() < 0.5
            targeted = self.rng.random() < self.block_bias and len(self.path) - self.idx > 3
            if want_block and targeted:
                cell = self._drop_on_path()
                if cell:
                    self.path_hits.append(cell)
                    added += 1
                    continue
            if (not want_block) and targeted and self._clear_near_path():
                removed += 1
                continue
            for _try in range(80):
                r, c = self.rng.randrange(self.rows), self.rng.randrange(self.cols)
                if not self._free_to_change((r, c)):
                    continue
                if want_block and not self.grid.blocked[r][c]:
                    self.grid.blocked[r][c] = True
                    added += 1
                    break
                if (not want_block) and self.grid.blocked[r][c]:
                    self.grid.blocked[r][c] = False
                    removed += 1
                    break
        return added, removed

    def step(self):
        """Un pas de simulation. Renvoie la liste des événements à afficher dans le journal."""
        events = []
        if self.status not in ("running", "no_path") or self.pos == self.goal:
            return events
        if self.status == "no_path" and self.level == 1:
            return events
        self.status = "running"
        self.path_hits = []
        added, removed = self._pending_added, self._pending_removed
        self._pending_added = self._pending_removed = 0
        target_moved = False
        if self.level >= 2:
            a, r = self._random_changes()
            added += a
            removed += r
            if self.doors_mode and self.rng.random() < self.door_rate:
                events.append(self._shuffle_right_doors())
                target_moved = True
        remaining = self.path[self.idx:]
        reason = None
        if self.pos != self.goal and len(remaining) < 2:
            reason = "aucun chemin utilisable : nouvelle recherche"
        elif target_moved:
            reason = "la porte cible a changé de place"
        elif not self._valid(remaining):
            reason = "le chemin prévu est bloqué"
        elif self.fallback:
            reason = "plan de repli : on poursuit la recherche"
        elif self.level == 3 and removed:
            h = heuristic_for(self.use_diagonals)
            if path_cost(remaining) > h(self.pos, self.goal) + 1e-9:
                reason = "un obstacle a disparu : chemin plus court possible"
        if reason:
            res = self.plan(count=True)
            tag = "plan de repli, budget dépassé" if self.fallback else (
                "chemin trouvé" if res.found else "aucun chemin")
            events.append(f"Replanification ({reason}) → {tag}, {res.time_ms:.1f} ms, {res.explored} cases explorées")
            if not res.found and not self.fallback and self.level == 1:
                self.status = "no_path"
                return events
        if len(self.path) - self.idx > 1:
            nxt = self.path[self.idx + 1]
            self.travelled += SQRT2 if (nxt[0] != self.pos[0] and nxt[1] != self.pos[1]) else 1.0
            self.pos = nxt
            self.idx += 1
            self.steps += 1
        else:
            self.steps += 1  # le robot attend
        if self.pos == self.goal:
            self.status = "arrived"
            if self.doors_mode:
                events.append(f"Arrivé : sortie par la porte {DOOR_COLORS[self.start_color]} de droite")
            else:
                events.append("Arrivé à la destination")
        return events
