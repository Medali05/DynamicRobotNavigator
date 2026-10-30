"""
Application graphique (Pygame) : carte, robot animé, obstacles, chemin lumineux et panneau de commandes.
Toute la logique est dans simulation.py ; ce fichier ne fait que l'afficher et relayer les commandes.
"""
from __future__ import annotations

import math

import pygame

from simulation import ALGO_NAMES, DOOR_COLORS, SIZES, Simulation

from . import theme
from .sprites import Sprites, build_arena
from .theme import draw_text
from .widgets import Button, Chips, Choice, Segmented, Slider, Toggle

W, H = 1280, 720
ARENA_BOX = pygame.Rect(20, 20, 924, 636)
PANEL = pygame.Rect(964, 16, 300, 688)
PATH_BLUE = (79, 140, 255)
PATH_AMBER = (245, 158, 11)
STATUS = {"idle": ("Prêt", theme.MUTE), "running": ("En route", theme.GOOD),
          "arrived": ("Arrivé", theme.ACCENT_HOVER), "no_path": ("Aucun chemin", theme.BAD)}


def ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1 = 1.9
    return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Robot Navigator - navigation intelligente dans un environnement dynamique")
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE | pygame.SCALED)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.sim = Simulation(21, 31, seed=7)
        self.sim.random_obstacles(0.20)
        self.size_label = "Moyenne (21×31)"
        self.paused = False
        self.show_explored = False
        self.tool = 0
        self.speed = 6.0            # cases par seconde
        self.time = 0.0
        self.step_timer = 0.0
        self.toasts: list = []
        self.fx: list = []
        self.prev_blocked = None
        self.door_flash = -10.0
        self.painting = False
        self.paint_value = True
        self.mouse = (0, 0)
        self.explored_key = None
        self.explored_surf = None
        self.rebuild_arena()
        self.build_ui()
        self.sync_blocked(initial=True)

    # ------------------------------------------------------------------ carte
    def rebuild_arena(self):
        s = self.sim
        self.cs = max(12, min(ARENA_BOX.w // s.cols, ARENA_BOX.h // s.rows))
        self.sprites = Sprites(self.cs)
        self.floor = build_arena(s.cols, s.rows, self.cs)
        aw, ah = s.cols * self.cs, s.rows * self.cs
        self.arena_rect = pygame.Rect(0, 0, aw, ah)
        self.arena_rect.center = ARENA_BOX.center
        self.layer = pygame.Surface((aw, ah), pygame.SRCALPHA)
        self.explored_key = None
        self.reset_visual()

    def reset_visual(self):
        s = self.sim
        self.trail = [s.pos]
        self.anim_from = self.anim_to = s.pos
        self.anim_t = 1.0
        self.step_timer = 0.0
        self.heading = math.atan2(s.goal[0] - s.pos[0], s.goal[1] - s.pos[1])
        self.heading_target = self.heading
        self.paused = False

    def cell_center(self, r: float, c: float):
        return (self.arena_rect.x + (c + 0.5) * self.cs, self.arena_rect.y + (r + 0.5) * self.cs)

    def local_center(self, r: float, c: float):
        return ((c + 0.5) * self.cs, (r + 0.5) * self.cs)

    def sync_blocked(self, initial: bool = False):
        """Détecte les obstacles qui apparaissent ou disparaissent pour les animer."""
        s = self.sim
        walls = s.wall_cells() if s.doors_mode else set()
        cur = {(r, c) for r in range(s.rows) for c in range(s.cols)
               if s.grid.blocked[r][c] and (r, c) not in walls}
        if self.prev_blocked is not None and not initial:
            added, removed = cur - self.prev_blocked, self.prev_blocked - cur
            if len(added) + len(removed) <= 40:
                for cell in added:
                    self.fx.append({"cell": cell, "kind": "in", "t0": self.time})
                for cell in removed:
                    self.fx.append({"cell": cell, "kind": "out", "t0": self.time})
        self.prev_blocked = cur

    def toast(self, text: str, kind: str = "info"):
        if self.toasts and self.toasts[-1]["text"] == text and self.time - self.toasts[-1]["t0"] < 1.5:
            return
        self.toasts.append({"text": text, "t0": self.time, "kind": kind})
        self.toasts = self.toasts[-3:]

    # ------------------------------------------------------------------ commandes
    def after_reset(self):
        self.reset_visual()
        self.sync_blocked(initial=True)

    def on_level(self, i: int):
        self.sim.level = i + 1
        if self.sim.status != "running":
            self.sim.reset_robot()
            self.after_reset()
        self.toast(["Niveau 1 : trouver un chemin", "Niveau 2 : obstacles en temps réel",
                    "Niveau 3 : plus court chemin, temps borné"][i])

    def on_algo(self, name: str):
        self.sim.algo = name
        self.refresh_plan()

    def on_diag(self, v: bool):
        self.sim.diagonals = v
        self.refresh_plan()

    def refresh_plan(self):
        s = self.sim
        if s.status == "running":
            s.plan(count=True)
        else:
            s.reset_robot()
            self.after_reset()

    def on_doors(self, v: bool):
        if self.sim.status == "running":
            self.toast("Remets le robot au départ avant de changer de mode")
            return
        self.sim.enable_doors(v)
        self.after_reset()
        if v:
            self.toast(f"Le robot part de la porte {DOOR_COLORS[self.sim.start_color]} de gauche")

    def on_color(self, i: int):
        if self.sim.status == "running":
            self.toast("Remets le robot au départ avant de changer de porte")
            return
        self.sim.set_start_color(i)
        self.after_reset()

    def on_size(self, label: str):
        rows, cols = SIZES[label]
        self.size_label = label
        self.sim.new_grid(rows, cols)
        self.sim.random_obstacles(0.20)
        self.prev_blocked = None
        self.fx.clear()
        self.rebuild_arena()
        self.sync_blocked(initial=True)

    def _edit(self, fn, msg: str):
        if self.sim.status == "running":
            self.toast("Remets le robot au départ avant de modifier la carte")
            return
        fn()
        self.after_reset()
        self.toast(msg)

    def on_random(self):
        self._edit(lambda: self.sim.random_obstacles(0.20), "Nouveaux obstacles")

    def on_maze(self):
        self._edit(self.sim.maze, "Labyrinthe généré")

    def on_clear(self):
        self._edit(self.sim.clear, "Carte dégagée")

    def on_start(self):
        s = self.sim
        if s.status == "running":
            self.paused = False
            return
        if s.status == "arrived":
            s.reset_robot()
            self.after_reset()
        s.start_run()
        self.reset_visual()
        if s.status == "no_path":
            self.toast("Aucun chemin entre le robot et la destination", "bad")

    def toggle_pause(self):
        if self.sim.status == "running":
            self.paused = not self.paused

    def on_step(self):
        s = self.sim
        if s.status in ("idle", "arrived"):
            self.on_start()
        if s.status == "running":
            self.paused = True
            self.do_step()

    def on_replan(self):
        s = self.sim
        res = s.plan(count=s.status == "running")
        if res.found or s.fallback:
            if s.status == "no_path":
                s.status = "idle"
            self.toast(f"Nouveau chemin calculé en {res.time_ms:.1f} ms")
        else:
            if s.status == "idle":
                s.status = "no_path"
            self.toast("Aucun chemin vers la destination", "bad")

    def on_reset(self):
        self.sim.reset_robot()
        self.after_reset()
        self.toast("Robot remis au départ")

    def do_step(self):
        s = self.sim
        before = s.pos
        events = s.step()
        for e in events:
            if "portes de droite" in e:
                self.door_flash = self.time
                self.toast("Les portes de droite ont changé !", "warn")
            elif e.startswith("Replanification"):
                self.toast(e.split(" → ")[0].replace("Replanification (", "Nouveau calcul : ").rstrip(") "))
            elif e.startswith("Arrivé"):
                self.toast(e, "good")
            else:
                self.toast(e)
        if s.pos != before:
            self.anim_from, self.anim_to, self.anim_t = before, s.pos, 0.0
            self.heading_target = math.atan2(s.pos[0] - before[0], s.pos[1] - before[1])
            self.trail.append(s.pos)
        else:
            self.anim_from = self.anim_to = s.pos
        if s.status == "no_path" and s.level == 1:
            self.toast("Aucun chemin : la destination est inaccessible", "bad")
        self.sync_blocked()

    # ------------------------------------------------------------------ interface
    def build_ui(self):
        s, x, w = self.sim, PANEL.x + 16, PANEL.w - 32
        self.widgets = []
        add = self.widgets.append
        y = PANEL.y + 62
        add(Segmented((x, y, w, 36), ["Niveau 1", "Niveau 2", "Niveau 3"], lambda: s.level - 1, self.on_level))
        y += 44
        add(Choice((x, y, w, 46), "Algorithme", ALGO_NAMES, lambda: s.algo, self.on_algo))
        y += 54
        add(Toggle((x, y, w, 26), "Diagonales (8 directions)", lambda: s.diagonals, self.on_diag))
        y += 28
        add(Toggle((x, y, w, 26), "Portes colorées", lambda: s.doors_mode, self.on_doors))
        y += 28
        add(Toggle((x, y, w, 26), "Afficher la zone explorée", lambda: self.show_explored,
                   lambda v: setattr(self, "show_explored", v)))
        y += 32
        add(Chips((x, y, w, 30), lambda: s.start_color, self.on_color, lambda: s.doors_mode))
        y += 38
        add(Slider((x, y, w, 34), "Vitesse du robot", 1, 14, lambda: self.speed,
                   lambda v: setattr(self, "speed", v), lambda v: f"{v:.0f} cases/s"))
        y += 36
        add(Slider((x, y, w, 34), "Budget de calcul", 1, 200, lambda: s.budget_ms,
                   lambda v: setattr(s, "budget_ms", v), lambda v: f"{v:.0f} ms", lambda: s.level == 3))
        y += 36
        add(Slider((x, y, w, 34), "Changements de la carte", 0, 2, lambda: s.change_rate,
                   lambda v: setattr(s, "change_rate", v), lambda v: f"{v:.1f} / pas", lambda: s.level >= 2))
        y += 36
        add(Slider((x, y, w, 34), "Changement des portes", 0, 20, lambda: s.door_rate * 100,
                   lambda v: setattr(s, "door_rate", v / 100), lambda v: f"{v:.0f} % / pas",
                   lambda: s.level >= 2 and s.doors_mode))
        y += 42
        add(Segmented((x, y, w, 34), ["Obstacle", "Robot", "Destination"], lambda: self.tool,
                      lambda i: setattr(self, "tool", i)))
        y += 42
        bw = (w - 8) // 3
        add(Button((x, y, bw, 32), "Aléatoire", self.on_random))
        add(Button((x + bw + 4, y, bw, 32), "Labyrinthe", self.on_maze, enabled_fn=lambda: not s.doors_mode))
        add(Button((x + 2 * (bw + 4), y, bw, 32), "Effacer", self.on_clear))
        y += 38
        add(Choice((x, y, w, 40), "Taille de la carte", list(SIZES), lambda: self.size_label, self.on_size))
        y += 50
        add(Button((x, y, w // 2 - 3, 40), "Lancer", self.on_start, "primary",
                   text_fn=lambda: "Relancer" if s.status == "arrived" else "Lancer"))
        add(Button((x + w // 2 + 3, y, w // 2 - 3, 40), "Pause", self.toggle_pause,
                   text_fn=lambda: "Reprendre" if self.paused else "Pause",
                   enabled_fn=lambda: s.status == "running"))
        y += 46
        tw = (w - 8) // 3
        add(Button((x, y, tw, 32), "Pas à pas", self.on_step))
        add(Button((x + tw + 4, y, tw, 32), "Replanifier", self.on_replan))
        add(Button((x + 2 * (tw + 4), y, tw, 32), "Au départ", self.on_reset))

    # ------------------------------------------------------------------ boucle
    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for e in pygame.event.get():
                if not self.handle(e):
                    pygame.quit()
                    return
            self.update(dt)
            self.render()
            pygame.display.flip()

    def handle(self, e) -> bool:
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self.on_start() if self.sim.status != "running" else self.toggle_pause()
            elif e.key == pygame.K_r:
                self.on_reset()
            elif e.key == pygame.K_ESCAPE:
                return False
        for w in self.widgets:
            if w.event(e):
                return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3) and self.arena_rect.collidepoint(e.pos):
            self.arena_click(e.pos, erase=e.button == 3)
        elif e.type == pygame.MOUSEMOTION and self.painting and self.arena_rect.collidepoint(e.pos):
            self.paint(self.cell_at(e.pos))
        elif e.type == pygame.MOUSEBUTTONUP:
            self.painting = False
        return True

    def cell_at(self, pos):
        return ((pos[1] - self.arena_rect.y) // self.cs, (pos[0] - self.arena_rect.x) // self.cs)

    def arena_click(self, pos, erase: bool):
        s, cell = self.sim, self.cell_at(pos)
        if self.tool in (1, 2) and not erase:
            if s.status == "running":
                self.toast("Remets le robot au départ avant de le déplacer")
                return
            ok = s.set_start(cell) if self.tool == 1 else s.set_goal(cell)
            if ok:
                self.after_reset()
            elif s.doors_mode:
                self.toast("En mode portes, le départ et la destination suivent la couleur choisie")
            return
        self.paint_value = False if erase else not s.grid.blocked[cell[0]][cell[1]]
        self.painting = True
        self.paint(cell)

    def paint(self, cell):
        s = self.sim
        if s.level == 1 and s.status == "running":
            self.toast("Niveau 1 : la carte ne peut pas être modifiée pendant le déplacement")
            return
        if s.set_obstacle(cell[0], cell[1], self.paint_value):
            self.sync_blocked()

    def update(self, dt: float):
        self.time += dt
        s = self.sim
        if s.status == "running" and not self.paused:
            self.step_timer += dt
            interval = 1.0 / self.speed
            while self.step_timer >= interval and s.status == "running":
                self.step_timer -= interval
                self.do_step()
        self.anim_t = min(1.0, self.anim_t + dt * self.speed)
        diff = (self.heading_target - self.heading + math.pi) % (2 * math.pi) - math.pi
        self.heading += diff * min(1.0, dt * 14)
        self.fx = [f for f in self.fx if self.time - f["t0"] < 0.35]
        self.toasts = [t for t in self.toasts if self.time - t["t0"] < 3.6]

    # ------------------------------------------------------------------ dessin
    def render(self):
        scr = self.screen
        scr.fill(theme.BG)
        self.draw_arena(scr)
        self.draw_panel(scr)
        self.draw_hud(scr)

    def glow(self, scr, center, radius, color, alpha):
        r = int(radius)
        tmp = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            pygame.draw.circle(tmp, (*color, int(alpha * (1 - i / 7))), (r, r), int(r * i / 6))
        scr.blit(tmp, (center[0] - r, center[1] - r))

    def explored_overlay(self):
        s = self.sim
        key = (id(s.visited), len(s.visited), self.cs)
        if key != self.explored_key:
            surf = pygame.Surface(self.arena_rect.size, pygame.SRCALPHA)
            for (r, c) in s.visited:
                pygame.draw.rect(surf, (79, 140, 255, 42), (c * self.cs + 1, r * self.cs + 1, self.cs - 1, self.cs - 1))
            self.explored_surf, self.explored_key = surf, key
        return self.explored_surf

    def robot_cell_pos(self):
        e = self.anim_t
        r = self.anim_from[0] + (self.anim_to[0] - self.anim_from[0]) * e
        c = self.anim_from[1] + (self.anim_to[1] - self.anim_from[1]) * e
        return r, c

    def draw_arena(self, scr):
        s, cs, sp, ar = self.sim, self.cs, self.sprites, self.arena_rect
        pygame.draw.rect(scr, (0, 0, 0), ar.inflate(10, 10).move(0, 6), border_radius=22)
        pygame.draw.rect(scr, theme.LINE, ar.inflate(6, 6), border_radius=19)
        scr.blit(self.floor, ar.topleft)
        if self.show_explored:
            scr.blit(self.explored_overlay(), ar.topleft)

        # chemin et trace (couche translucide)
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        if len(self.trail) > 1:
            for i, (r, c) in enumerate(self.trail[:-1]):
                if i % 2 == 0:
                    pygame.draw.circle(layer, (60, 200, 140, 120), self.local_center(r, c), max(2, cs // 9))
        rr, rc = self.robot_cell_pos()
        remaining = s.path[s.idx + 1:] if s.path else []
        if remaining and s.pos != s.goal:
            pts = [self.local_center(rr, rc)] + [self.local_center(r, c) for r, c in remaining]
            col = PATH_AMBER if s.fallback else PATH_BLUE
            pulse = 0.5 + 0.5 * math.sin(self.time * 4)
            if len(pts) > 1:
                pygame.draw.lines(layer, (*col, 50), False, pts, max(6, int(cs * 0.62)))
                pygame.draw.lines(layer, (*col, 120), False, pts, max(4, int(cs * 0.30)))
                pygame.draw.lines(layer, (200, 225, 255, 235), False, pts, max(2, int(cs * 0.11)))
                for p in pts[1:]:
                    pygame.draw.circle(layer, (200, 225, 255, 235), p, max(1, int(cs * 0.055)))
                dot = int(self.time * 6) % max(1, len(pts) - 1)
                pygame.draw.circle(layer, (255, 255, 255, int(150 + 100 * pulse)), pts[dot + 1], max(3, int(cs * 0.14)))
        scr.blit(layer, ar.topleft)

        # marqueurs
        if not s.doors_mode:
            scr.blit(sp.dock, sp.dock.get_rect(center=self.cell_center(*s.start)))
        gx, gy = self.cell_center(*s.goal)
        pulse = 0.5 + 0.5 * math.sin(self.time * 3)
        goal_col = theme.DOOR_RGB[s.start_color] if s.doors_mode else theme.BAD
        self.glow(scr, (gx, gy), cs * (1.0 + 0.35 * pulse), goal_col, 110)
        if not s.doors_mode:
            scr.blit(sp.pad, sp.pad.get_rect(center=(gx, gy)))

        # murs et portes
        if s.doors_mode:
            for (r, c) in s.wall_cells():
                scr.blit(sp.wall, (ar.x + c * cs, ar.y + r * cs))
            flash = max(0.0, 1.0 - (self.time - self.door_flash) / 0.8)
            for slot, r in enumerate(s.left_rows):
                scr.blit(sp.door_left[slot], (ar.x, ar.y + r * cs))
            for slot, r in enumerate(s.right_rows):
                scr.blit(sp.door_right[s.right_colors[slot]], (ar.x + (s.cols - 1) * cs, ar.y + r * cs))
                if flash > 0:
                    f = pygame.Surface((cs, cs), pygame.SRCALPHA)
                    f.fill((255, 255, 255, int(160 * flash)))
                    scr.blit(f, (ar.x + (s.cols - 1) * cs, ar.y + r * cs))

        # obstacles (avec apparition et disparition animées)
        fx_in = {f["cell"]: f for f in self.fx if f["kind"] == "in"}
        walls = s.wall_cells() if s.doors_mode else set()
        for r in range(s.rows):
            row = s.grid.blocked[r]
            for c in range(s.cols):
                if not row[c] or (r, c) in walls:
                    continue
                spr = sp.obstacle(r, c)
                f = fx_in.get((r, c))
                if f:
                    k = ease_out_back((self.time - f["t0"]) / 0.3)
                    big = pygame.transform.rotozoom(spr, 0, max(0.05, k))
                    scr.blit(big, big.get_rect(center=self.cell_center(r, c)))
                else:
                    scr.blit(spr, (ar.x + c * cs, ar.y + r * cs))
        for f in self.fx:
            if f["kind"] == "out":
                k = (self.time - f["t0"]) / 0.3
                if k < 1:
                    spr = sp.obstacle(*f["cell"]).copy()
                    spr.set_alpha(int(255 * (1 - k)))
                    big = pygame.transform.rotozoom(spr, 0, 1 + 0.25 * k)
                    big.set_alpha(int(255 * (1 - k)))
                    scr.blit(big, big.get_rect(center=self.cell_center(*f["cell"])))

        # robot
        px, py = self.cell_center(rr, rc)
        ring = (self.time * 0.9) % 1.0
        self.glow(scr, (px, py), cs * (0.6 + 1.1 * ring), (110, 205, 255), int(70 * (1 - ring)))
        img = pygame.transform.rotozoom(sp.robot, -math.degrees(self.heading), 1.0)
        scr.blit(img, img.get_rect(center=(px, py)))

        # bannière : aucun chemin
        if s.pos != s.goal and len(s.path) - s.idx < 2 and s.status in ("no_path", "running"):
            box = pygame.Rect(0, 0, 400, 56)
            box.center = ar.center
            pygame.draw.rect(scr, (60, 18, 24), box, border_radius=14)
            pygame.draw.rect(scr, theme.BAD, box, 2, border_radius=14)
            draw_text(scr, "Aucun chemin vers la destination", box.center, 20, (255, 255, 255), True, "center")

        # notifications
        ty = ar.y + 14
        for t in reversed(self.toasts):
            age = self.time - t["t0"]
            a = max(0.0, min(1.0, min(age / 0.2, (3.6 - age) / 0.6)))
            col = {"good": theme.GOOD, "bad": theme.BAD, "warn": theme.WARN}.get(t["kind"], theme.ACCENT)
            img = theme.font(14, True).render(t["text"], True, (240, 244, 252))
            box = pygame.Rect(0, ty, img.get_width() + 34, 30)
            box.centerx = ar.centerx
            tmp = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(tmp, (14, 19, 30, int(225 * a)), tmp.get_rect(), border_radius=15)
            pygame.draw.circle(tmp, (*col, int(255 * a)), (15, 15), 5)
            img.set_alpha(int(255 * a))
            tmp.blit(img, (28, 15 - img.get_height() // 2))
            scr.blit(tmp, box.topleft)
            ty += 36

    def draw_panel(self, scr):
        pygame.draw.rect(scr, theme.PANEL, PANEL, border_radius=18)
        pygame.draw.rect(scr, theme.LINE, PANEL, 1, border_radius=18)
        draw_text(scr, "ROBOT NAVIGATOR", (PANEL.x + 18, PANEL.y + 14), 20, theme.TEXT, True)
        draw_text(scr, "Navigation intelligente", (PANEL.x + 18, PANEL.y + 38), 12, theme.MUTE)
        for w in self.widgets:
            w.draw(scr, self.mouse)

    def draw_hud(self, scr):
        s = self.sim
        label, col = STATUS.get(s.status, ("", theme.MUTE))
        if s.status == "running" and self.paused:
            label, col = "En pause", theme.WARN
        if s.status == "running" and s.fallback:
            label, col = "Plan de repli (budget dépassé)", theme.WARN
        y = ARENA_BOX.bottom + 10
        pill = pygame.Rect(ARENA_BOX.x, y, 12, 12)
        pygame.draw.circle(scr, col, (pill.x + 6, y + 14), 6)
        r = draw_text(scr, label, (ARENA_BOX.x + 20, y + 14), 14, theme.TEXT, True, "midleft")
        left = max(0, len(s.path) - s.idx - 1)
        info = f"Chemin : {left} pas   |   Calculs : {s.replans}   |   Dernier calcul : {s.last_ms:.1f} ms"
        draw_text(scr, info, (r.right + 22, y + 14), 13, theme.MUTE, False, "midleft")
        draw_text(scr, "Clic : obstacle   Clic droit : effacer   Espace : lancer / pause   R : au départ",
                  (ARENA_BOX.right, y + 14), 12, theme.MUTE, False, "midright")
