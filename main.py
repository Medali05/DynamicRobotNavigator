"""
main.py - Interface graphique du projet « Navigation intelligente d'un robot ».

Lancer :  py main.py        (Windows)      |      python3 main.py   (macOS / Linux)

L'interface affiche la grille, le robot, la destination, les obstacles et le chemin calculé sous la forme
d'une ligne reliant le robot à la destination. Toute la logique est dans simulation.py et algorithms.py.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from simulation import ALGO_NAMES, DOOR_COLORS, DOOR_SHAPES, SIZES, Simulation

# --------------------------------------------------------------------------- couleurs
BG = "#0f1219"
GRID_LINE = "#1a2030"
OBSTACLE = "#4b5468"
WALL = "#262c3a"
EXPLORED = "#1d3159"
PATH = "#4f9bff"
PATH_FALLBACK = "#f59e0b"
TRAIL = "#2f7a5c"
ROBOT = "#22c55e"
GOAL = "#ef4444"
DOOR_RGB = ["#ef4444", "#3b82f6", "#22c55e", "#facc15", "#a855f7"]

STATUS_TEXT = {"idle": "Prêt", "running": "En route", "arrived": "Arrivé",
               "no_path": "Aucun chemin"}


def shape_points(kind: str, cx: float, cy: float, r: float):
    if kind == "triangle":
        return [cx, cy - r, cx + 0.9 * r, cy + 0.8 * r, cx - 0.9 * r, cy + 0.8 * r]
    if kind == "étoile":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r if i % 2 == 0 else r * 0.45
            pts += [cx + rad * math.cos(ang), cy + rad * math.sin(ang)]
        return pts
    if kind == "hexagone":
        pts = []
        for i in range(6):
            ang = i * math.pi / 3
            pts += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
        return pts
    return None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Navigation intelligente d'un robot dans un environnement dynamique")
        self.configure(bg="#e9ecf2")
        self.sim = Simulation(21, 31, seed=7)
        self.sim.random_obstacles(0.20)
        self.trail = [self.sim.pos]
        self.paused = False
        self.loop_id = None
        self.paint_value = True
        self.last_hint = ""

        self._build_vars()
        self._build_layout()
        self._apply_level_state()
        self.refresh()
        self.bind("<space>", lambda e: self.toggle_pause())

    # ------------------------------------------------------------------ variables Tk
    def _build_vars(self):
        s = self.sim
        self.v_level = tk.IntVar(value=s.level)
        self.v_algo = tk.StringVar(value=s.algo)
        self.v_diag = tk.BooleanVar(value=s.diagonals)
        self.v_budget = tk.DoubleVar(value=s.budget_ms)
        self.v_rate = tk.DoubleVar(value=s.change_rate)
        self.v_density = tk.DoubleVar(value=20)
        self.v_size = tk.StringVar(value="Moyenne (21×31)")
        self.v_doors = tk.BooleanVar(value=False)
        self.v_color = tk.StringVar(value=self._color_label(0))
        self.v_doorrate = tk.DoubleVar(value=s.door_rate * 100)
        self.v_tool = tk.StringVar(value="obstacle")
        self.v_speed = tk.DoubleVar(value=70)
        self.v_explored = tk.BooleanVar(value=True)

    @staticmethod
    def _color_label(i: int) -> str:
        return f"{DOOR_COLORS[i]} ({DOOR_SHAPES[i]})"

    # ------------------------------------------------------------------ mise en page
    def _compute_cell(self) -> int:
        avail_h = max(300, min(560, self.winfo_screenheight() - 360))
        return max(10, min(860 // self.sim.cols, avail_h // self.sim.rows))

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, rowspan=2, sticky="ns")
        self._build_controls(left)

        self.cell = self._compute_cell()
        self.canvas = tk.Canvas(self, width=self.sim.cols * self.cell, height=self.sim.rows * self.cell,
                                bg=BG, highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=1, padx=8, pady=8, sticky="n")
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", lambda e: self.on_press(e, erase=True))
        self.canvas.bind("<B3-Motion>", lambda e: self.on_drag(e, erase=True))

        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.grid(row=1, column=1, sticky="nsew")
        bottom.columnconfigure(1, weight=1)
        self._build_stats(bottom)

    def _build_controls(self, parent):
        # --- niveau
        f = ttk.LabelFrame(parent, text="Niveau", padding=6)
        f.pack(fill="x", pady=(0, 6))
        for val, txt in ((1, "1 – Trouver un chemin"), (2, "2 – Obstacles en temps réel"),
                         (3, "3 – Plus court chemin, temps borné")):
            ttk.Radiobutton(f, text=txt, value=val, variable=self.v_level,
                            command=self.on_level).pack(anchor="w")

        # --- algorithme
        f = ttk.LabelFrame(parent, text="Algorithme", padding=6)
        f.pack(fill="x", pady=(0, 6))
        cb = ttk.Combobox(f, textvariable=self.v_algo, values=ALGO_NAMES, state="readonly")
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_algo())
        ttk.Checkbutton(f, text="Diagonales (8 directions)", variable=self.v_diag,
                        command=self.on_algo).pack(anchor="w", pady=(4, 0))
        self.lbl_budget = ttk.Label(f)
        self.lbl_budget.pack(anchor="w")
        self.sc_budget = ttk.Scale(f, from_=1, to=200, variable=self.v_budget, command=self.on_budget)
        self.sc_budget.pack(fill="x")

        # --- environnement
        f = ttk.LabelFrame(parent, text="Environnement", padding=6)
        f.pack(fill="x", pady=(0, 6))
        cb = ttk.Combobox(f, textvariable=self.v_size, values=list(SIZES), state="readonly")
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_size())
        self.lbl_density = ttk.Label(f)
        self.lbl_density.pack(anchor="w", pady=(4, 0))
        ttk.Scale(f, from_=5, to=40, variable=self.v_density,
                  command=lambda v: self.lbl_density.config(text=f"Densité d'obstacles : {float(v):.0f} %")
                  ).pack(fill="x")
        self.lbl_density.config(text=f"Densité d'obstacles : {self.v_density.get():.0f} %")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(4, 0))
        ttk.Button(row, text="Obstacles aléatoires", command=self.on_random).pack(side="left", fill="x", expand=True)
        self.btn_maze = ttk.Button(row, text="Labyrinthe", command=self.on_maze)
        self.btn_maze.pack(side="left", padx=(4, 0))
        ttk.Button(f, text="Tout effacer", command=self.on_clear).pack(fill="x", pady=(4, 0))
        self.lbl_rate = ttk.Label(f)
        self.lbl_rate.pack(anchor="w", pady=(6, 0))
        self.sc_rate = ttk.Scale(f, from_=0, to=2, variable=self.v_rate, command=self.on_rate)
        self.sc_rate.pack(fill="x")

        # --- portes colorées
        f = ttk.LabelFrame(parent, text="Portes colorées", padding=6)
        f.pack(fill="x", pady=(0, 6))
        ttk.Checkbutton(f, text="Activer (gauche fixe, droite mobile)", variable=self.v_doors,
                        command=self.on_doors).pack(anchor="w")
        self.cb_color = ttk.Combobox(f, textvariable=self.v_color, state="disabled",
                                     values=[self._color_label(i) for i in range(5)])
        self.cb_color.pack(fill="x", pady=(4, 0))
        self.cb_color.bind("<<ComboboxSelected>>", lambda e: self.on_color())
        self.lbl_door = ttk.Label(f)
        self.lbl_door.pack(anchor="w")
        self.sc_door = ttk.Scale(f, from_=0, to=20, variable=self.v_doorrate, command=self.on_doorrate)
        self.sc_door.pack(fill="x")

        # --- édition
        f = ttk.LabelFrame(parent, text="Clic sur la grille", padding=6)
        f.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.rb_tools = []
        for val, txt in (("obstacle", "Obstacle"), ("start", "Robot"), ("goal", "Destination")):
            rb = ttk.Radiobutton(row, text=txt, value=val, variable=self.v_tool)
            rb.pack(side="left", padx=(0, 6))
            self.rb_tools.append(rb)
        ttk.Label(f, text="Clic droit : effacer un obstacle", foreground="#666").pack(anchor="w")

        # --- commandes
        f = ttk.LabelFrame(parent, text="Commandes", padding=6)
        f.pack(fill="x", pady=(0, 6))
        f.columnconfigure((0, 1), weight=1)
        self.btn_start = ttk.Button(f, text="Lancer", command=self.on_start)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=1)
        self.btn_pause = ttk.Button(f, text="Pause", command=self.toggle_pause)
        self.btn_pause.grid(row=0, column=1, sticky="ew", padx=(2, 0), pady=1)
        ttk.Button(f, text="Pas à pas", command=self.on_step).grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=1)
        ttk.Button(f, text="Replanifier", command=self.on_replan).grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=1)
        ttk.Button(f, text="Remettre le robot au départ", command=self.on_reset).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=1)
        ttk.Button(f, text="Comparer les algorithmes", command=self.on_compare).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=1)
        self.lbl_speed = ttk.Label(f)
        self.lbl_speed.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Scale(f, from_=10, to=400, variable=self.v_speed, command=self.on_speed).grid(
            row=5, column=0, columnspan=2, sticky="ew")
        ttk.Checkbutton(f, text="Afficher les cases explorées", variable=self.v_explored,
                        command=self.refresh).grid(row=6, column=0, columnspan=2, sticky="w")
        self.on_budget()
        self.on_rate()
        self.on_doorrate()
        self.on_speed()

    def _build_stats(self, parent):
        st = ttk.LabelFrame(parent, text="Statistiques", padding=6)
        st.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        self.stat = {}
        for i, (key, label) in enumerate((("status", "Statut"), ("length", "Longueur du chemin prévu"),
                                          ("explored", "Cases explorées (dernier calcul)"),
                                          ("time", "Temps de calcul (dernier / total)"),
                                          ("replans", "Calculs de chemin"), ("steps", "Pas effectués"),
                                          ("travelled", "Distance parcourue"))):
            ttk.Label(st, text=label + " :").grid(row=i, column=0, sticky="w")
            lbl = ttk.Label(st, text="-", font=("TkDefaultFont", 9, "bold"))
            lbl.grid(row=i, column=1, sticky="w", padx=(8, 0))
            self.stat[key] = lbl

        lg = ttk.LabelFrame(parent, text="Journal", padding=4)
        lg.grid(row=0, column=1, sticky="nsew")
        lg.columnconfigure(0, weight=1)
        self.log_box = tk.Text(lg, height=7, width=60, state="disabled", wrap="word", font=("TkDefaultFont", 9))
        sb = ttk.Scrollbar(lg, command=self.log_box.yview)
        self.log_box.config(yscrollcommand=sb.set)
        self.log_box.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

    # ------------------------------------------------------------------ journal et statistiques
    def log(self, msg: str):
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[pas {self.sim.steps}] {msg}\n")
        lines = int(self.log_box.index("end-1c").split(".")[0])
        if lines > 300:
            self.log_box.delete("1.0", f"{lines - 300}.0")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def hint(self, msg: str):
        if msg != self.last_hint:
            self.last_hint = msg
            self.log(msg)

    def update_stats(self):
        s = self.sim
        txt = STATUS_TEXT.get(s.status, s.status)
        if s.status == "running" and self.paused:
            txt = "En pause"
        if s.status == "running" and s.fallback:
            txt = "En route (plan de repli : budget dépassé)"
        self.stat["status"].config(text=txt, foreground="#c0392b" if s.status == "no_path" else "#000")
        remaining = max(0, len(s.path) - s.idx - 1)
        if s.path and len(s.path) > 1:
            self.stat["length"].config(text=f"{remaining} pas" + (f" (coût {s.last_cost:.1f})" if s.idx == 0 else ""))
        else:
            self.stat["length"].config(text="-")
        self.stat["explored"].config(text=str(s.last_explored))
        self.stat["time"].config(text=f"{s.last_ms:.2f} ms / {s.total_ms:.1f} ms")
        self.stat["replans"].config(text=str(s.replans))
        self.stat["steps"].config(text=str(s.steps))
        self.stat["travelled"].config(text=f"{s.travelled:.1f}")

    # ------------------------------------------------------------------ dessin
    def center(self, r: int, c: int):
        cs = self.cell
        return c * cs + cs / 2, r * cs + cs / 2

    def refresh(self):
        cv, s, cs = self.canvas, self.sim, self.cell
        cv.delete("all")
        walls = s._wall_cells() if s.doors_mode else set()
        # cases explorées
        if self.v_explored.get():
            for (r, c) in s.visited:
                cv.create_rectangle(c * cs, r * cs, (c + 1) * cs, (r + 1) * cs, fill=EXPLORED, outline="")
        # grille
        for i in range(s.cols + 1):
            cv.create_line(i * cs, 0, i * cs, s.rows * cs, fill=GRID_LINE)
        for j in range(s.rows + 1):
            cv.create_line(0, j * cs, s.cols * cs, j * cs, fill=GRID_LINE)
        # obstacles et murs
        pad = max(1, cs // 12)
        for r in range(s.rows):
            for c in range(s.cols):
                if s.grid.blocked[r][c]:
                    col = WALL if (r, c) in walls else OBSTACLE
                    cv.create_rectangle(c * cs + pad, r * cs + pad, (c + 1) * cs - pad, (r + 1) * cs - pad,
                                        fill=col, outline="")
        # portes
        if s.doors_mode:
            for slot, r in enumerate(s.left_rows):
                self.draw_door(r, 0, slot)
            for slot, r in enumerate(s.right_rows):
                self.draw_door(r, s.cols - 1, s.right_colors[slot])
        # trace parcourue
        if len(self.trail) > 1:
            cv.create_line(*[v for p in self.trail for v in self.center(*p)], fill=TRAIL,
                           width=max(2, cs // 8), capstyle="round", joinstyle="round")
        # chemin restant (ligne reliant le robot à la destination)
        remaining = s.path[s.idx:]
        if len(remaining) > 1:
            cv.create_line(*[v for p in remaining for v in self.center(*p)],
                           fill=PATH_FALLBACK if s.fallback else PATH, width=max(3, cs // 5),
                           capstyle="round", joinstyle="round", dash=(6, 4) if s.fallback else None)
        # destination
        gx, gy = self.center(*s.goal)
        rr = cs * 0.38
        cv.create_oval(gx - rr, gy - rr, gx + rr, gy + rr, outline=GOAL, width=max(2, cs // 8), fill=BG if not s.doors_mode else "")
        if not s.doors_mode:
            cv.create_oval(gx - rr / 3, gy - rr / 3, gx + rr / 3, gy + rr / 3, fill=GOAL, outline="")
        # robot
        rx, ry = self.center(*s.pos)
        rr = cs * 0.34
        cv.create_oval(rx - rr, ry - rr, rx + rr, ry + rr, fill=ROBOT, outline="white", width=2)
        cv.create_oval(rx - rr / 3, ry - rr / 3, rx + rr / 3, ry + rr / 3, fill=BG, outline="")
        # message clair quand aucun chemin n'existe
        if s.status == "no_path":
            w, h = s.cols * cs, s.rows * cs
            cv.create_rectangle(w / 2 - 190, h / 2 - 28, w / 2 + 190, h / 2 + 28, fill="#3b1218", outline=GOAL, width=2)
            cv.create_text(w / 2, h / 2, text="Aucun chemin vers la destination", fill="white",
                           font=("TkDefaultFont", 14, "bold"))
        self.update_stats()

    def draw_door(self, r: int, c: int, color_index: int):
        cv, cs = self.canvas, self.cell
        cx, cy = self.center(r, c)
        rad = cs * 0.38
        color = DOOR_RGB[color_index]
        cv.create_rectangle(c * cs + 1, r * cs + 1, (c + 1) * cs - 1, (r + 1) * cs - 1, fill="#151a26", outline="")
        kind = DOOR_SHAPES[color_index]
        pts = shape_points(kind, cx, cy, rad)
        if kind == "cercle":
            cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill=color, outline="white")
        elif kind == "carré":
            cv.create_rectangle(cx - rad, cy - rad, cx + rad, cy + rad, fill=color, outline="white")
        else:
            cv.create_polygon(*pts, fill=color, outline="white")

    # ------------------------------------------------------------------ boucle d'animation
    def schedule(self):
        if self.loop_id is None:
            self.loop_id = self.after(int(self.v_speed.get()), self._tick)

    def stop_loop(self):
        if self.loop_id is not None:
            self.after_cancel(self.loop_id)
            self.loop_id = None

    def _tick(self):
        self.loop_id = None
        s = self.sim
        if s.status != "running" or self.paused:
            self.refresh()
            return
        self.advance()
        if s.status == "running":
            self.schedule()

    def advance(self):
        s = self.sim
        before = s.pos
        for e in s.step():
            self.log(e)
        if s.pos != before:
            self.trail.append(s.pos)
        if s.status == "no_path" and s.level == 1:
            self.log("Aucun chemin : la destination est inaccessible")
        self.refresh()

    # ------------------------------------------------------------------ commandes
    def on_start(self):
        s = self.sim
        if s.status == "running":
            self.paused = False
            self.btn_pause.config(text="Pause")
            self.schedule()
            return
        if s.status == "arrived":
            self.trail = [s.start]
        s.start_run()
        self.trail = [s.pos]
        self.paused = False
        self.btn_pause.config(text="Pause")
        self.log(f"Départ - niveau {s.level}, {s.algo}, {'8' if s.diagonals else '4'} directions"
                 + (f", budget {s.budget_ms:.0f} ms" if s.level == 3 else ""))
        if s.status == "no_path":
            self.log("Aucun chemin entre le robot et la destination")
        self.refresh()
        if s.status == "running":
            self.schedule()

    def toggle_pause(self):
        if self.sim.status != "running":
            return
        self.paused = not self.paused
        self.btn_pause.config(text="Reprendre" if self.paused else "Pause")
        if not self.paused:
            self.schedule()
        self.refresh()

    def on_step(self):
        s = self.sim
        if s.status in ("idle", "arrived"):
            if s.status == "arrived":
                self.trail = [s.start]
            s.start_run()
            self.trail = [s.pos]
        if s.status == "running":
            self.paused = True
            self.btn_pause.config(text="Reprendre")
            self.advance()
        else:
            self.refresh()

    def on_replan(self):
        s = self.sim
        res = s.plan(count=s.status == "running")
        self.log(f"Replanification manuelle → {'chemin trouvé' if res.found else 'aucun chemin'}, "
                 f"{res.time_ms:.1f} ms, {res.explored} cases explorées")
        if not res.found and not s.fallback and s.status == "idle":
            s.status = "no_path"
        elif s.status == "no_path" and res.found:
            s.status = "idle"
        self.refresh()

    def on_reset(self):
        self.stop_loop()
        self.paused = False
        self.btn_pause.config(text="Pause")
        self.sim.reset_robot()
        self.trail = [self.sim.pos]
        self.log("Robot remis au départ")
        self.refresh()

    def on_compare(self):
        rows = self.sim.compare()
        win = tk.Toplevel(self)
        win.title("Comparaison des algorithmes")
        ttk.Label(win, text="Même position, même destination, grille actuelle (moyenne de 3 mesures).",
                  padding=8).pack(anchor="w")
        cols = ("algo", "trouve", "cout", "explorees", "temps")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=len(rows))
        for col, txt, w in (("algo", "Algorithme", 160), ("trouve", "Chemin trouvé", 100),
                            ("cout", "Longueur (coût)", 110), ("explorees", "Cases explorées", 110),
                            ("temps", "Temps (ms)", 90)):
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="center")
        best = min((r["cout"] for r in rows if r["trouve"]), default=None)
        for r in rows:
            gap = ""
            if r["trouve"] and best and r["cout"] > best + 1e-9:
                gap = f"  (+{(r['cout'] / best - 1) * 100:.1f} %)"
            tree.insert("", "end", values=(r["algorithme"], "oui" if r["trouve"] else "non",
                                           f"{r['cout']:.2f}{gap}" if r["trouve"] else "-",
                                           r["explorees"], f"{r['temps_ms']:.3f}"))
        tree.pack(padx=8, pady=(0, 8))
        self.log("Comparaison des algorithmes affichée")

    # ------------------------------------------------------------------ réglages
    def _stop_if_running_for_edit(self) -> bool:
        if self.sim.status == "running":
            self.hint("Mettez en pause ou remettez le robot au départ avant de modifier la grille ainsi")
            return False
        return True

    def on_level(self):
        self.sim.level = self.v_level.get()
        self._apply_level_state()
        self.log(f"Niveau {self.sim.level}")
        if self.sim.status != "running":
            self.sim.reset_robot()
            self.trail = [self.sim.pos]
        self.refresh()

    def _apply_level_state(self):
        lvl = self.sim.level
        self.sc_rate.state(["!disabled"] if lvl >= 2 else ["disabled"])
        self.sc_budget.state(["!disabled"] if lvl == 3 else ["disabled"])
        self.sc_door.state(["!disabled"] if (lvl >= 2 and self.sim.doors_mode) else ["disabled"])

    def on_algo(self):
        s = self.sim
        s.algo, s.diagonals = self.v_algo.get(), self.v_diag.get()
        if s.status == "running":
            s.plan(count=True)
            self.log(f"Algorithme changé : {s.algo}, {'8' if s.diagonals else '4'} directions")
        else:
            s.reset_robot()
            self.trail = [s.pos]
        self.refresh()

    def on_budget(self, *_):
        v = float(self.v_budget.get())
        self.sim.budget_ms = v
        self.lbl_budget.config(text=f"Budget de calcul (niveau 3) : {v:.0f} ms")

    def on_rate(self, *_):
        v = float(self.v_rate.get())
        self.sim.change_rate = v
        self.lbl_rate.config(text=f"Changements : {v:.1f} cellule(s) par pas (niveaux 2-3)")

    def on_doorrate(self, *_):
        v = float(self.v_doorrate.get())
        self.sim.door_rate = v / 100.0
        self.lbl_door.config(text=f"Changement des portes de droite : {v:.0f} % par pas")

    def on_speed(self, *_):
        self.lbl_speed.config(text=f"Vitesse : {float(self.v_speed.get()):.0f} ms par pas")

    def on_size(self):
        self.stop_loop()
        rows, cols = SIZES[self.v_size.get()]
        self.sim.new_grid(rows, cols)
        self.sim.random_obstacles(self.v_density.get() / 100.0)
        self.v_doors.set(False)
        self.cb_color.config(state="disabled")
        self.btn_maze.state(["!disabled"])
        self.cell = self._compute_cell()
        self.canvas.config(width=cols * self.cell, height=rows * self.cell)
        self.trail = [self.sim.pos]
        self.paused = False
        self.btn_pause.config(text="Pause")
        self._apply_level_state()
        self.log(f"Nouvelle grille {rows}×{cols}")
        self.refresh()

    def on_random(self):
        if not self._stop_if_running_for_edit():
            return
        self.sim.random_obstacles(self.v_density.get() / 100.0)
        self.trail = [self.sim.pos]
        self.log(f"Obstacles aléatoires ({self.v_density.get():.0f} %)")
        self.refresh()

    def on_maze(self):
        if not self._stop_if_running_for_edit():
            return
        self.sim.maze()
        self.trail = [self.sim.pos]
        self.log("Labyrinthe généré")
        self.refresh()

    def on_clear(self):
        if not self._stop_if_running_for_edit():
            return
        self.sim.clear()
        self.trail = [self.sim.pos]
        self.log("Grille effacée")
        self.refresh()

    def on_doors(self):
        if not self._stop_if_running_for_edit():
            self.v_doors.set(self.sim.doors_mode)
            return
        on = self.v_doors.get()
        self.sim.enable_doors(on)
        self.cb_color.config(state="readonly" if on else "disabled")
        self.btn_maze.state(["disabled"] if on else ["!disabled"])
        self._apply_level_state()
        self.trail = [self.sim.pos]
        if on:
            self.log(f"Portes colorées : le robot part de la porte {DOOR_COLORS[self.sim.start_color]} de gauche "
                     "et doit sortir par la porte de même couleur à droite")
        self.refresh()

    def on_color(self):
        if not self._stop_if_running_for_edit():
            return
        idx = [self._color_label(i) for i in range(5)].index(self.v_color.get())
        self.sim.set_start_color(idx)
        self.trail = [self.sim.pos]
        self.log(f"Porte de départ : {DOOR_COLORS[idx]}")
        self.refresh()

    # ------------------------------------------------------------------ souris
    def cell_at(self, event):
        r, c = event.y // self.cell, event.x // self.cell
        return (r, c) if self.sim.grid.in_bounds(r, c) else None

    def on_press(self, event, erase: bool = False):
        cell = self.cell_at(event)
        if cell is None:
            return
        s = self.sim
        tool = self.v_tool.get()
        if tool in ("start", "goal") and not erase:
            if not self._stop_if_running_for_edit():
                return
            ok = s.set_start(cell) if tool == "start" else s.set_goal(cell)
            if ok:
                self.trail = [s.pos]
            elif s.doors_mode:
                self.hint("En mode portes colorées, le départ et la destination suivent la couleur choisie")
            self.refresh()
            return
        self.paint_value = False if erase else (not s.grid.blocked[cell[0]][cell[1]])
        self.paint(cell)

    def on_drag(self, event, erase: bool = False):
        cell = self.cell_at(event)
        if cell is not None and self.v_tool.get() == "obstacle":
            self.paint(cell)

    def paint(self, cell):
        s = self.sim
        if s.level == 1 and s.status == "running":
            self.hint("Niveau 1 : les clics sont ignorés pendant le déplacement")
            return
        if s.set_obstacle(cell[0], cell[1], self.paint_value):
            self.refresh()


if __name__ == "__main__":
    App().mainloop()
