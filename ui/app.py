"""
Application graphique (Pygame) : carte, robot animé, obstacles, chemin lumineux et panneau de commandes.
Toute la logique est dans simulation.py ; ce fichier ne fait que l'afficher et relayer les commandes.
"""
from __future__ import annotations

import math
import random
import sys

import pygame

from simulation import DOOR_COLORS, SIZES, Simulation

from . import theme
from .sprites import Sprites, build_arena
from .theme import draw_text
from .widgets import Button, Chips, Choice, Segmented, Slider, Toggle

W, H = 1280, 720            # taille MINIMALE de la fenêtre (la mise en page s'adapte au-delà)
PANEL_W, PANEL_H = 300, 688

if sys.platform == "win32":      # sinon Windows étire (et floute) la fenêtre sur les écrans réglés à 125 % / 150 %
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
PATH_BLUE = (79, 140, 255)
PATH_AMBER = (245, 158, 11)
STATUS = {"idle": ("Prêt", theme.MUTE), "running": ("En route", theme.GOOD),
          "arrived": ("Arrivé", theme.ACCENT_HOVER), "no_path": ("Aucun chemin", theme.BAD)}


DROP_T = 0.55   # durée de la chute d'un obstacle qui apparaît
OUT_T = 0.35    # durée de la disparition


def bounce(t: float) -> float:
    """Courbe de rebond : 0 -> 1 avec quelques rebonds."""
    t = max(0.0, min(1.0, t))
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Robot Navigator - navigation intelligente dans un environnement dynamique")
        self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)   # pas de SCALED : pixels réels, rendu net
        self.fullscreen = False
        self.windowed_size = (W, H)
        self.layout()
        self.clock = pygame.time.Clock()
        self.density = 20.0         # densité des obstacles (%)
        self.sim = Simulation(21, 31, seed=7)
        self.sim.random_obstacles(self.density / 100)
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
    def layout(self):
        """Calcule les zones selon la taille réelle de la fenêtre : le panneau reste à 1:1, l'arène prend la place."""
        sw, sh = self.screen.get_size()
        self.panel = pygame.Rect(sw - PANEL_W - 16, max(16, (sh - PANEL_H) // 2), PANEL_W, PANEL_H)
        self.arena_box = pygame.Rect(20, 20, self.panel.x - 40, sh - 84)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.screen.get_size()
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)           # résolution native de l'écran
        else:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.on_resize()

    def on_resize(self):
        self.screen = pygame.display.get_surface()
        sw, sh = self.screen.get_size()
        if (sw < W or sh < H) and not self.fullscreen:                    # taille minimale
            self.screen = pygame.display.set_mode((max(sw, W), max(sh, H)), pygame.RESIZABLE)
        self.layout()
        self.rebuild_arena(reset=False)
        self.build_ui()
        self.parts, self.stamps, self.sparks_due, self.last_stamp = [], [], [], None
        self.fxlayer = None

    def rebuild_arena(self, reset: bool = True):
        s = self.sim
        cs = max(12, min(self.arena_box.w // s.cols, self.arena_box.h // s.rows))
        if reset or cs != getattr(self, "cs", None):                      # sprites refaits à la bonne taille
            self.cs = cs
            self.sprites = Sprites(cs)
            self.floor = build_arena(s.cols, s.rows, cs)
            self.layer = pygame.Surface((s.cols * cs, s.rows * cs), pygame.SRCALPHA)
            self.explored_key = None
        self.arena_rect = pygame.Rect(0, 0, s.cols * self.cs, s.rows * self.cs)
        self.arena_rect.center = self.arena_box.center
        if reset:
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
        self.parts, self.stamps, self.sparks_due = [], [], []   # particules, traces de chenilles, étincelles
        self.last_stamp = None
        self.victory_done = False

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
        self.toast(["Niveau 1 : le robot suit le plus court chemin",
                    "Niveau 2 : obstacles qui apparaissent et disparaissent sur le trajet",
                    "Niveau 3 : plus court chemin sous budget de temps"][i])

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
        self.sim.random_obstacles(self.density / 100)
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
        self._edit(lambda: self.sim.random_obstacles(self.density / 100), f"Nouveaux obstacles ({self.density:.0f} %)")

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
        for cell in s.path_hits:                    # un obstacle tombe sur le trajet : étincelles à l'impact
            self.sparks_due.append((self.time + 0.364, cell))
        if s.status == "arrived" and not self.victory_done:
            self.victory_done = True
            gx, gy = self.cell_center(*s.goal)
            cs = self.cs
            self.burst(gx, gy, 70, theme.DOOR_RGB + [(255, 255, 255)], speed=cs * 7, life=1.5, rad=cs * 0.09,
                       gravity=cs * 8, angle=-math.pi / 2, spread=math.pi * 1.2, kind="confetti")
            for k in range(2):
                self.parts.append({"x": gx, "y": gy, "vx": 0, "vy": 0, "t0": self.time + k * 0.25, "life": 0.9,
                                   "c": theme.GOOD, "r": cs * 2.4, "g": 0, "kind": "ring"})
        self.sync_blocked()

    # ------------------------------------------------------------------ interface
    def build_ui(self):
        s, x, w = self.sim, self.panel.x + 16, self.panel.w - 32
        self.widgets, self.headers = [], []
        add = self.widgets.append
        lvl2 = lambda: s.level >= 2
        y = self.panel.y + 60
        self.headers.append((y, "NIVEAU"))
        y += 16
        add(Segmented((x, y, w, 32), ["Niveau 1", "Niveau 2", "Niveau 3"], lambda: s.level - 1, self.on_level))
        y += 36
        self.algo_card_y = y            # mention de l'algorithme (dessinée dans draw_panel)
        y += 40
        self.headers.append((y, "OPTIONS"))
        y += 16
        add(Toggle((x, y, w, 24), "Diagonales (8 directions)", lambda: s.diagonals, self.on_diag))
        y += 24
        add(Toggle((x, y, w, 24), "Portes colorées", lambda: s.doors_mode, self.on_doors))
        y += 24
        add(Toggle((x, y, w, 24), "Afficher la zone explorée", lambda: self.show_explored,
                   lambda v: setattr(self, "show_explored", v)))
        y += 26
        add(Chips((x, y, w, 26), lambda: s.start_color, self.on_color, lambda: s.doors_mode))
        y += 32
        self.headers.append((y, "RÉGLAGES"))
        y += 16
        add(Slider((x, y, w, 30), "Vitesse du robot", 1, 14, lambda: self.speed,
                   lambda v: setattr(self, "speed", v), lambda v: f"{v:.0f} cases/s"))
        y += 31
        add(Slider((x, y, w, 30), "Densité des obstacles", 5, 40, lambda: self.density,
                   lambda v: setattr(self, "density", v), lambda v: f"{v:.0f} %"))
        y += 31
        add(Slider((x, y, w, 30), "Obstacles qui apparaissent", 0, 2, lambda: s.change_rate,
                   lambda v: setattr(s, "change_rate", v), lambda v: f"{v:.1f} / pas", lvl2))
        y += 31
        add(Slider((x, y, w, 30), "Part tombant sur le trajet", 0, 100, lambda: s.block_bias * 100,
                   lambda v: setattr(s, "block_bias", v / 100), lambda v: f"{v:.0f} %", lvl2))
        y += 31
        add(Slider((x, y, w, 30), "Budget de calcul par recherche", 0, 1,
                   lambda: math.log(s.budget_ms / 0.1) / math.log(2000),      # échelle logarithmique :
                   lambda t: setattr(s, "budget_ms", 0.1 * 2000 ** t),         # de 0,1 ms à 200 ms
                   lambda t: (f"{0.1 * 2000 ** t:.1f} ms" if 0.1 * 2000 ** t < 10 else f"{0.1 * 2000 ** t:.0f} ms"),
                   lambda: s.level == 3))
        y += 31
        add(Slider((x, y, w, 30), "Changement des portes", 0, 20, lambda: s.door_rate * 100,
                   lambda v: setattr(s, "door_rate", v / 100), lambda v: f"{v:.0f} % / pas",
                   lambda: s.level >= 2 and s.doors_mode))
        y += 34
        self.headers.append((y, "CARTE"))
        y += 16
        add(Segmented((x, y, w, 30), ["Obstacle", "Robot", "Destination"], lambda: self.tool,
                      lambda i: setattr(self, "tool", i)))
        y += 34
        bw = (w - 8) // 3
        add(Button((x, y, bw, 28), "Aléatoire", self.on_random, icon="dice", size=12))
        add(Button((x + bw + 4, y, bw, 28), "Labyrinthe", self.on_maze, enabled_fn=lambda: not s.doors_mode,
                   icon="maze", size=12))
        add(Button((x + 2 * (bw + 4), y, bw, 28), "Effacer", self.on_clear, icon="clear", size=12))
        y += 32
        add(Choice((x, y, w, 38), "Taille de la carte", list(SIZES), lambda: self.size_label, self.on_size))
        y += 44
        add(Button((x, y, w // 2 - 3, 36), "Lancer", self.on_start, "primary", icon="play",
                   text_fn=lambda: "Relancer" if s.status == "arrived" else "Lancer"))
        add(Button((x + w // 2 + 3, y, w // 2 - 3, 36), "Pause", self.toggle_pause, icon="pause",
                   text_fn=lambda: "Reprendre" if self.paused else "Pause",
                   enabled_fn=lambda: s.status == "running"))
        y += 40
        add(Button((x, y, bw, 28), "Pas à pas", self.on_step, icon="step", size=12))
        add(Button((x + bw + 4, y, bw, 28), "Replanifier", self.on_replan, icon="replan", size=12))
        add(Button((x + 2 * (bw + 4), y, bw, 28), "Au départ", self.on_reset, icon="home", size=12))

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
        if e.type == pygame.VIDEORESIZE:
            self.on_resize()
            return True
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif e.key == pygame.K_SPACE:
                self.on_start() if self.sim.status != "running" else self.toggle_pause()
            elif e.key == pygame.K_r:
                self.on_reset()
            elif e.key == pygame.K_ESCAPE:
                if self.fullscreen:
                    self.toggle_fullscreen()
                else:
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
        self.fx = [f for f in self.fx if self.time - f["t0"] < 0.6]
        self.toasts = [t for t in self.toasts if self.time - t["t0"] < 3.6]
        self.update_effects(dt)

    def burst(self, x, y, n, colors, speed, life, rad, gravity=0.0, angle=0.0, spread=2 * math.pi, kind="dust"):
        for _ in range(n):
            a = angle + random.uniform(-spread / 2, spread / 2)
            v = random.uniform(0.25, 1.0) * speed
            self.parts.append({"x": x, "y": y, "vx": math.cos(a) * v, "vy": math.sin(a) * v, "t0": self.time,
                               "life": life * random.uniform(0.7, 1.2), "c": random.choice(colors),
                               "r": rad * random.uniform(0.6, 1.2), "g": gravity, "kind": kind})

    def update_effects(self, dt: float):
        cs, s = self.cs, self.sim
        for f in self.fx:                            # poussière quand un obstacle touche le sol
            if f["kind"] == "in" and not f.get("boom") and self.time - f["t0"] >= 0.364:
                f["boom"] = True
                x, y = self.cell_center(*f["cell"])
                self.burst(x, y + cs * 0.3, 8, [(150, 160, 176), (118, 128, 146)], speed=cs * 1.3, life=0.7,
                           rad=cs * 0.12, kind="dust")
        due = [d for d in self.sparks_due if d[0] <= self.time]
        self.sparks_due = [d for d in self.sparks_due if d[0] > self.time]
        for _, cell in due:                          # étincelles : un obstacle vient de bloquer le chemin
            x, y = self.cell_center(*cell)
            self.burst(x, y + cs * 0.1, 26, [(255, 214, 90), (255, 150, 40), (255, 250, 210)], speed=cs * 5.5,
                       life=0.55, rad=cs * 0.055, gravity=cs * 10, angle=-math.pi / 2, spread=math.pi * 1.3,
                       kind="spark")
        rr, rc = self.robot_cell_pos()               # traces de chenilles et poussière derrière le robot
        px, py = self.cell_center(rr, rc)
        if self.anim_t < 1.0 and self.anim_from != self.anim_to:
            if self.last_stamp is None or math.hypot(px - self.last_stamp[0], py - self.last_stamp[1]) >= 0.24 * cs:
                self.stamps.append((px, py, self.heading, self.time))
                self.last_stamp = (px, py)
                bx, by = px - math.cos(self.heading) * cs * 0.36, py - math.sin(self.heading) * cs * 0.36
                self.burst(bx, by, 1, [(128, 138, 156)], speed=cs * 0.6, life=0.55, rad=cs * 0.07,
                           angle=self.heading + math.pi, spread=1.3, kind="dust")
        self.stamps = [st for st in self.stamps if self.time - st[3] < 7.0][-220:]
        for p in self.parts:
            if self.time >= p["t0"]:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += p["g"] * dt
        self.parts = [p for p in self.parts if self.time - p["t0"] < p["life"]]

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

    def draw_robot(self, scr, px, py):
        """Robot : faisceau des phares, balayage du lidar, sprite et voyant d'état clignotant."""
        s, cs = self.sim, self.cs
        R = int(cs * 2.6)
        tmp = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        h = self.heading
        for L, half, al in ((cs * 1.9, 0.42, 30), (cs * 1.35, 0.22, 30)):          # phares
            pts = [(R, R)] + [(R + L * math.cos(h + d), R + L * math.sin(h + d)) for d in
                              (-half, -half / 2, 0, half / 2, half)]
            pygame.draw.polygon(tmp, (255, 244, 200, al), pts)
        sweep = self.time * 4.2                                                      # lidar
        for i in range(6):
            a = sweep - i * 0.11
            pts = [(R, R)] + [(R + R * 0.95 * math.cos(a + d), R + R * 0.95 * math.sin(a + d)) for d in (-0.09, 0, 0.09)]
            pygame.draw.polygon(tmp, (110, 205, 255, int(64 * (1 - i / 6))), pts)
        ring = (self.time * 0.9) % 1.0
        pygame.draw.circle(tmp, (110, 205, 255, int(70 * (1 - ring))), (R, R), int(cs * (0.5 + 1.8 * ring)), 2)
        scr.blit(tmp, (px - R, py - R))
        img = pygame.transform.rotozoom(self.sprites.robot, -math.degrees(h), 1.0)
        scr.blit(img, img.get_rect(center=(px, py)))
        # voyant d'état : vert en route, orange en pause ou repli, rouge sans chemin, bleu à l'arrivée
        if s.status == "running":
            col = theme.WARN if (self.paused or s.fallback) else theme.GOOD
            if len(s.path) - s.idx < 2 and s.pos != s.goal:
                col = theme.BAD
        elif s.status == "arrived":
            col = theme.ACCENT_HOVER
        elif s.status == "no_path":
            col = theme.BAD
        else:
            col = theme.MUTE
        on = int(self.time * 3) % 2 == 0 or s.status == "arrived"
        bx, by = px - math.cos(h) * cs * 0.26, py - math.sin(h) * cs * 0.26
        if on:
            self.glow(scr, (bx, by), cs * 0.5, col, 150)
        pygame.draw.circle(scr, col if on else theme.mix(col, (0, 0, 0), 0.6), (bx, by), max(2, int(cs * 0.07)))

    def draw_particles(self, scr):
        if not self.parts:
            return
        ar = self.arena_rect
        if getattr(self, "fxlayer", None) is None or self.fxlayer.get_size() != ar.size:
            self.fxlayer = pygame.Surface(ar.size, pygame.SRCALPHA)
        fl = self.fxlayer
        fl.fill((0, 0, 0, 0))
        for p in self.parts:
            u = (self.time - p["t0"]) / p["life"]
            if u < 0:
                continue
            x, y, c, k = p["x"] - ar.x, p["y"] - ar.y, p["c"], p["kind"]
            if k == "dust":
                pygame.draw.circle(fl, (*c, int(120 * (1 - u))), (x, y), max(1, int(p["r"] * (1 + 1.6 * u))))
            elif k == "spark":
                pygame.draw.line(fl, (*c, int(255 * (1 - u))), (x, y), (x - p["vx"] * 0.03, y - p["vy"] * 0.03), 2)
            elif k == "confetti":
                pygame.draw.rect(fl, (*c, int(255 * (1 - u) ** 0.7)), (x, y, p["r"] * 1.7, p["r"] * 0.9))
            elif k == "ring":
                pygame.draw.circle(fl, (*c, int(210 * (1 - u))), (x, y), max(2, int(p["r"] * (0.2 + u))), 3)
        scr.blit(fl, ar.topleft)

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
        for (sx, sy, sh, st0) in self.stamps:        # traces de chenilles qui s'estompent
            al = int(80 * (1 - (self.time - st0) / 7.0))
            nx, ny = -math.sin(sh), math.cos(sh)
            for sg in (-1, 1):
                pygame.draw.circle(layer, (4, 6, 10, al), (sx - ar.x + sg * 0.21 * cs * nx, sy - ar.y + sg * 0.21 * cs * ny),
                                   max(1, int(cs * 0.06)))
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

        # obstacles en relief, triés par rangée avec le robot (le robot passe devant ou derrière)
        rr, rc = self.robot_cell_pos()
        split = int(rr + 0.5) + 1
        self.draw_obstacle_rows(scr, 0, split)
        px, py = self.cell_center(rr, rc)
        self.draw_robot(scr, px, py)
        self.draw_obstacle_rows(scr, split, s.rows)
        self.draw_particles(scr)

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

    def draw_obstacle_rows(self, scr, r0: int, r1: int):
        s, cs, sp, ar = self.sim, self.cs, self.sprites, self.arena_rect
        walls = s.wall_cells() if s.doors_mode else set()
        fx_in = {f["cell"]: f for f in self.fx if f["kind"] == "in"}
        for r in range(r0, r1):
            row = s.grid.blocked[r]
            for c in range(s.cols):
                if not row[c] or (r, c) in walls:
                    continue
                spr = sp.obstacle(r, c)
                x, y = ar.x + c * cs, ar.y + (r + 1) * cs - sp.obs_h
                f = fx_in.get((r, c))
                if not f:
                    scr.blit(spr, (x, y))
                    continue
                t = (self.time - f["t0"]) / DROP_T
                off = -(1 - bounce(t)) * cs * 3.2           # chute avec rebonds
                a = min(1.0, t / 0.15)
                if a < 1:
                    tmp = spr.copy()
                    tmp.set_alpha(int(255 * a))
                    scr.blit(tmp, (x, y + off))
                else:
                    scr.blit(spr, (x, y + off))
                if 0.364 <= t < 0.75:                         # onde de choc à l'impact
                    u = (t - 0.364) / 0.386
                    rx = int(cs * (0.35 + 0.55 * u))
                    ring = pygame.Surface((2 * rx + 4, rx + 4), pygame.SRCALPHA)
                    pygame.draw.ellipse(ring, (210, 220, 240, int(150 * (1 - u))), ring.get_rect(), 2)
                    scr.blit(ring, ring.get_rect(center=(x + cs // 2, ar.y + (r + 1) * cs - cs * 0.15)))
        for f in self.fx:
            if f["kind"] != "out" or not (r0 <= f["cell"][0] < r1):
                continue
            k = (self.time - f["t0"]) / OUT_T
            if k < 1:
                r, c = f["cell"]
                tmp = sp.obstacle(r, c).copy()
                tmp.set_alpha(int(255 * (1 - k)))
                scr.blit(tmp, (ar.x + c * cs, ar.y + (r + 1) * cs - sp.obs_h - k * cs * 0.6))

    def draw_panel(self, scr):
        scr.blit(theme.vgrad(self.panel.w, self.panel.h, (24, 32, 52), (13, 18, 30), 18), self.panel.topleft)
        pygame.draw.rect(scr, theme.LINE, self.panel, 1, border_radius=18)
        # logo : petit robot sur une pastille
        logo = pygame.Rect(self.panel.x + 16, self.panel.y + 14, 30, 30)
        scr.blit(theme.vgrad(30, 30, (110, 165, 255), (60, 114, 235), 9), logo.topleft)
        pygame.draw.rect(scr, (240, 245, 255), (logo.x + 7, logo.y + 10, 16, 11), border_radius=3)
        for dx in (10, 18):
            pygame.draw.circle(scr, (40, 70, 160), (logo.x + dx, logo.y + 15), 2)
        pygame.draw.line(scr, (240, 245, 255), (logo.centerx, logo.y + 10), (logo.centerx, logo.y + 6), 2)
        pygame.draw.circle(scr, (240, 245, 255), (logo.centerx, logo.y + 5), 2)
        draw_text(scr, "ROBOT NAVIGATOR", (self.panel.x + 56, self.panel.y + 12), 18, theme.TEXT, True)
        draw_text(scr, "Navigation intelligente", (self.panel.x + 56, self.panel.y + 33), 11, theme.MUTE)
        for (hy, label) in self.headers:                       # titres de sections
            r = draw_text(scr, label, (self.panel.x + 18, hy), 10, theme.MUTE, True)
            pygame.draw.line(scr, theme.LINE, (r.right + 8, hy + 6), (self.panel.right - 16, hy + 6))
        card = pygame.Rect(self.panel.x + 16, self.algo_card_y, self.panel.w - 32, 34)
        scr.blit(theme.vgrad(card.w, card.h, (34, 46, 74), (27, 37, 60), 10), card.topleft)
        pygame.draw.rect(scr, theme.LINE, card, 1, border_radius=10)
        draw_text(scr, "Algorithme", (card.x + 12, card.centery), 11, theme.MUTE, False, "midleft")
        draw_text(scr, "Plus court chemin guidé", (card.right - 12, card.centery), 13, theme.TEXT, True, "midright")
        for w in self.widgets:
            w.draw(scr, self.mouse)

    def draw_hud(self, scr):
        s = self.sim
        label, col = STATUS.get(s.status, ("", theme.MUTE))
        if s.status == "running" and self.paused:
            label, col = "En pause", theme.WARN
        if s.status == "running" and s.fallback:
            label, col = "Plan de repli (budget dépassé)", theme.WARN
        y = self.arena_box.bottom + 10
        pill = pygame.Rect(self.arena_box.x, y, 12, 12)
        pygame.draw.circle(scr, col, (pill.x + 6, y + 14), 6)
        r = draw_text(scr, label, (self.arena_box.x + 20, y + 14), 14, theme.TEXT, True, "midleft")
        left = max(0, len(s.path) - s.idx - 1)
        calc = f"Dernier calcul : {s.last_ms:.2f} ms"
        if s.level == 3:
            calc += f" / budget {s.budget_ms:.1f} ms"
        info = f"Chemin : {left} pas   |   Calculs : {s.replans}   |   {calc}"
        draw_text(scr, info, (r.right + 22, y + 14), 13, theme.MUTE, False, "midleft")
        draw_text(scr, "Clic : obstacle   Clic droit : effacer   Espace : lancer / pause   R : au départ   F11 : plein écran",
                  (self.arena_box.right, y + 14), 12, theme.MUTE, False, "midright")