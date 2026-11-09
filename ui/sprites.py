"""
Sprites dessinés par le code (aucune image à fournir) : robot, caisses, blocs de béton, rochers, barils,
portes colorées, murs, plateforme de destination et sol de la carte. Chaque sprite est dessiné en grand
puis réduit (anti-crénelage) et mis en cache pour la taille de case courante.
"""
from __future__ import annotations

import math
import random

import pygame

from . import theme

SS = 4  # facteur de sur-échantillonnage


def _new(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _shrink(big: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(big, (w, h))


def _r(*vals):
    return [int(v) for v in vals]


# --------------------------------------------------------------------------- obstacles en relief
EXT = 0.30  # hauteur supplémentaire du sprite (les objets « montent » au-dessus de leur case)


def _canvas(cs: int):
    ext = int(round(cs * EXT))
    return ext, _new(cs * SS, (cs + ext) * SS)


def _finish(big: pygame.Surface, cs: int, ext: int) -> pygame.Surface:
    return _shrink(big, cs, cs + ext)


def _box(big, cs, ext, x0, x1, y0, y1, h, top, front, lift=0.0, shadow=True, radius=0.04):
    """Boîte vue de trois quarts. x0..x1, y0..y1 : emprise au sol (fractions de la case), h : hauteur."""
    S = cs * SS
    gx0, gx1 = int(x0 * S), int(x1 * S)
    gy0 = int(y0 * S) + ext * SS - int(lift * S)
    gy1 = int(y1 * S) + ext * SS - int(lift * S)
    hh, rad = int(h * S), int(radius * S)
    if shadow:
        sh = pygame.Rect(gx0 + int(S * 0.07), gy0 + int(S * 0.04), gx1 - gx0, gy1 - gy0)
        pygame.draw.rect(big, (0, 0, 0, 135), sh, border_radius=rad)
    fr = pygame.Rect(gx0, gy1 - hh, gx1 - gx0, hh)
    tp = pygame.Rect(gx0, gy0 - hh, gx1 - gx0, gy1 - gy0)
    pygame.draw.rect(big, front, fr, border_bottom_left_radius=rad, border_bottom_right_radius=rad)
    pygame.draw.rect(big, top, tp, border_top_left_radius=rad, border_top_right_radius=rad)
    return tp, fr


def _crate_details(big, tp, fr, wood):
    dark = theme.mix(wood, (0, 0, 0), 0.45)
    light = theme.mix(wood, (255, 255, 255), 0.25)
    for i in range(1, 4):  # planches du dessus
        x = tp.x + tp.w * i // 4
        pygame.draw.line(big, dark, (x, tp.y + SS), (x, tp.bottom - SS), SS)
    pygame.draw.rect(big, light, (tp.x + SS, tp.y + SS, tp.w - 2 * SS, SS * 2))
    for i in range(1, 3):  # planches de face
        y = fr.y + fr.h * i // 3
        pygame.draw.line(big, dark, (fr.x + SS, y), (fr.right - SS, y), SS)
    pygame.draw.line(big, dark, (fr.x + SS * 3, fr.y + SS * 2), (fr.right - SS * 3, fr.bottom - SS * 2), SS * 2)
    pygame.draw.line(big, dark, (fr.right - SS * 3, fr.y + SS * 2), (fr.x + SS * 3, fr.bottom - SS * 2), SS * 2)
    pygame.draw.rect(big, dark, fr, SS, border_radius=SS * 2)
    pygame.draw.rect(big, dark, tp, SS, border_radius=SS * 2)
    for p in (fr.topleft, fr.topright, fr.bottomleft, fr.bottomright):
        pygame.draw.circle(big, (50, 34, 20), (p[0] + (SS * 3 if p[0] == fr.x else -SS * 3),
                                               p[1] + (SS * 3 if p[1] == fr.y else -SS * 3)), SS * 1.5)


def crate(cs: int, wood=(184, 130, 76)) -> pygame.Surface:
    ext, big = _canvas(cs)
    tp, fr = _box(big, cs, ext, 0.11, 0.89, 0.30, 0.88, 0.34, theme.mix(wood, (255, 255, 255), 0.18), wood)
    _crate_details(big, tp, fr, wood)
    return _finish(big, cs, ext)


def stacked_crates(cs: int) -> pygame.Surface:
    ext, big = _canvas(cs)
    low, up = (170, 118, 68), (196, 144, 86)
    tp, fr = _box(big, cs, ext, 0.10, 0.90, 0.34, 0.88, 0.26, theme.mix(low, (255, 255, 255), 0.15), low)
    _crate_details(big, tp, fr, low)
    tp2, fr2 = _box(big, cs, ext, 0.22, 0.78, 0.40, 0.80, 0.26, theme.mix(up, (255, 255, 255), 0.2), up,
                    lift=0.26, shadow=False)
    _crate_details(big, tp2, fr2, up)
    return _finish(big, cs, ext)


def container(cs: int, color=(178, 58, 50)) -> pygame.Surface:
    """Conteneur métallique ondulé."""
    ext, big = _canvas(cs)
    top_c = theme.mix(color, (255, 255, 255), 0.18)
    tp, fr = _box(big, cs, ext, 0.07, 0.93, 0.32, 0.88, 0.32, top_c, color, radius=0.03)
    dark = theme.mix(color, (0, 0, 0), 0.38)
    light = theme.mix(color, (255, 255, 255), 0.30)
    for i in range(1, 11):  # ondulations
        x = tp.x + tp.w * i // 11
        pygame.draw.line(big, theme.mix(top_c, (0, 0, 0), 0.22), (x, tp.y + SS * 2), (x, tp.bottom - SS * 2), SS)
        x = fr.x + fr.w * i // 11
        pygame.draw.line(big, dark, (x, fr.y + SS), (x, fr.bottom - SS), SS)
        pygame.draw.line(big, light, (x + SS, fr.y + SS), (x + SS, fr.bottom - SS), SS)
    pygame.draw.line(big, dark, (fr.centerx, fr.y), (fr.centerx, fr.bottom), SS * 2)
    for dx in (-0.10, 0.10):
        bx = fr.centerx + int(cs * SS * dx)
        pygame.draw.rect(big, (206, 212, 224), (bx - SS, fr.y + SS * 2, SS * 2, fr.h - SS * 4))
    pygame.draw.rect(big, (240, 242, 248), (fr.x + int(fr.w * 0.1), fr.y + int(fr.h * 0.28), int(fr.w * 0.14),
                                            int(fr.h * 0.22)))
    pygame.draw.rect(big, dark, fr, SS, border_radius=SS * 2)
    pygame.draw.rect(big, dark, tp, SS, border_radius=SS * 2)
    return _finish(big, cs, ext)


def barrier(cs: int) -> pygame.Surface:
    """Barrière en béton à bande de danger."""
    ext, big = _canvas(cs)
    tp, fr = _box(big, cs, ext, 0.06, 0.94, 0.40, 0.86, 0.36, (176, 184, 198), (122, 131, 147), radius=0.05)
    band = pygame.Rect(fr.x, fr.y + int(fr.h * 0.30), fr.w, int(fr.h * 0.42))
    layer = _new(band.w, band.h)
    layer.fill((26, 28, 34))
    step = int(cs * SS * 0.22)
    for x in range(-band.h, band.w + band.h, step):
        pygame.draw.polygon(layer, (250, 204, 21), [(x, band.h), (x + step // 2, band.h),
                                                    (x + step // 2 + band.h, 0), (x + band.h, 0)])
    big.blit(layer, band)
    pygame.draw.rect(big, (206, 214, 226), (tp.x + SS * 2, tp.y + SS, tp.w - SS * 4, SS * 2), border_radius=SS)
    pygame.draw.line(big, (86, 94, 110), (fr.x, fr.y), (fr.right, fr.y), SS)
    pygame.draw.rect(big, (70, 78, 94), fr, SS, border_radius=SS * 2)
    return _finish(big, cs, ext)


def barrel(cs: int, color=(205, 72, 52)) -> pygame.Surface:
    """Baril métallique (cylindre)."""
    ext, big = _canvas(cs)
    S = cs * SS
    R = int(S * 0.27)
    cx = S // 2
    gy = int(S * 0.64) + ext * SS
    h = int(S * 0.34)
    pygame.draw.ellipse(big, (0, 0, 0, 135), (cx - R + int(S * 0.06), gy - R // 2 + int(S * 0.06), 2 * R, R + R // 2))
    dark, mid = theme.mix(color, (0, 0, 0), 0.40), theme.mix(color, (0, 0, 0), 0.15)
    pygame.draw.circle(big, dark, (cx, gy), R)
    pygame.draw.rect(big, mid, (cx - R, gy - h, 2 * R, h))
    pygame.draw.rect(big, theme.mix(color, (255, 255, 255), 0.18), (cx - R + SS * 2, gy - h, R // 2, h))
    for k in (0.28, 0.68):
        y = gy - int(h * k)
        pygame.draw.line(big, dark, (cx - R, y), (cx + R, y), SS * 2)
    ty = gy - h
    pygame.draw.circle(big, theme.mix(color, (255, 255, 255), 0.10), (cx, ty), R)
    pygame.draw.circle(big, dark, (cx, ty), R, SS * 2)
    pygame.draw.circle(big, theme.mix(color, (0, 0, 0), 0.2), (cx, ty), int(R * 0.68), SS)
    pygame.draw.circle(big, (46, 46, 54), (cx + int(R * 0.30), ty - int(R * 0.15)), int(R * 0.14))
    pygame.draw.circle(big, (230, 232, 238), (cx - int(R * 0.30), ty + int(R * 0.12)), int(R * 0.10))
    return _finish(big, cs, ext)


def boulder(cs: int, seed: int) -> pygame.Surface:
    """Rocher avec mousse, construit par couches pour donner du volume."""
    ext, big = _canvas(cs)
    S = cs * SS
    rng = random.Random(seed)
    cx, cy = S * 0.5, S * 0.62 + ext * SS
    n = 11
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n + rng.uniform(-0.10, 0.10)
        rad = S * rng.uniform(0.28, 0.37)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang) * 0.78))
    height = S * 0.30
    pygame.draw.polygon(big, (0, 0, 0, 135), [(x + S * 0.06, y + S * 0.04) for x, y in pts])
    layers = 9
    for i in range(layers + 1):
        t = i / layers
        col = theme.mix((70, 76, 90), (132, 140, 156), t)
        k = 1.0 - 0.12 * t
        poly = [(cx + (x - cx) * k, cy + (y - cy) * k - height * t) for x, y in pts]
        pygame.draw.polygon(big, col, poly)
    top = [(cx + (x - cx) * 0.88, cy + (y - cy) * 0.88 - height) for x, y in pts]
    pygame.draw.polygon(big, (150, 158, 174), top)
    hi = [(cx + (x - cx) * 0.52 - S * 0.04, cy + (y - cy) * 0.52 - height - S * 0.03) for x, y in pts]
    pygame.draw.polygon(big, (176, 184, 198), hi)
    pygame.draw.polygon(big, (52, 58, 72), top, SS)
    for _ in range(4):  # touffes de mousse
        a = rng.uniform(math.pi, 2 * math.pi)
        mx, my = cx + math.cos(a) * S * 0.18, cy - height + math.sin(a) * S * 0.07
        pygame.draw.circle(big, (74, 132, 76), (mx, my), S * rng.uniform(0.035, 0.06))
        pygame.draw.circle(big, (104, 168, 98), (mx - S * 0.01, my - S * 0.01), S * 0.022)
    for _ in range(2):
        a = pts[rng.randrange(n)]
        pygame.draw.line(big, (60, 66, 80), (cx, cy - height * 0.4),
                         (cx + (a[0] - cx) * 0.8, cy + (a[1] - cy) * 0.8 - height * 0.4), SS)
    return _finish(big, cs, ext)


def pallet(cs: int) -> pygame.Surface:
    """Palette en bois chargée de deux cartons."""
    ext, big = _canvas(cs)
    wood = (172, 126, 72)
    tp, fr = _box(big, cs, ext, 0.07, 0.93, 0.50, 0.88, 0.07, theme.mix(wood, (255, 255, 255), 0.12), wood, radius=0.015)
    for i in range(1, 5):
        x = tp.x + tp.w * i // 5
        pygame.draw.line(big, theme.mix(wood, (0, 0, 0), 0.4), (x, tp.y), (x, tp.bottom), SS)
    for x0, x1, tone in ((0.11, 0.49, (204, 164, 108)), (0.51, 0.89, (196, 154, 98))):
        t, f = _box(big, cs, ext, x0, x1, 0.52, 0.84, 0.30, theme.mix(tone, (255, 255, 255), 0.18), tone,
                    lift=0.07, radius=0.03)
        pygame.draw.rect(big, (226, 206, 160), (t.centerx - SS * 2, t.y, SS * 4, t.h))
        pygame.draw.rect(big, (226, 206, 160), (f.centerx - SS * 2, f.y, SS * 4, f.h))
        pygame.draw.rect(big, theme.mix(tone, (0, 0, 0), 0.4), f, SS, border_radius=SS)
        pygame.draw.rect(big, theme.mix(tone, (0, 0, 0), 0.4), t, SS, border_radius=SS)
    return _finish(big, cs, ext)


def cones(cs: int) -> pygame.Surface:
    """Deux cônes de signalisation."""
    ext, big = _canvas(cs)
    S = cs * SS
    for cx, scale in ((0.30, 0.92), (0.70, 1.0)):
        x = int(S * cx)
        base_y = int(S * 0.82) + ext * SS
        w, hgt = int(S * 0.16 * scale), int(S * 0.52 * scale)
        pygame.draw.ellipse(big, (0, 0, 0, 90), (x - w - int(S * 0.02), base_y - int(S * 0.05) + int(S * 0.04),
                                                 2 * w + int(S * 0.10), int(S * 0.12)))
        pygame.draw.rect(big, (38, 40, 48), (x - w - int(S * 0.04), base_y - int(S * 0.06), 2 * w + int(S * 0.08),
                                             int(S * 0.08)), border_radius=int(S * 0.02))
        body = [(x - w, base_y - int(S * 0.05)), (x + w, base_y - int(S * 0.05)), (x, base_y - hgt)]
        pygame.draw.polygon(big, (255, 118, 28), body)
        pygame.draw.polygon(big, (214, 88, 14), [(x, base_y - hgt), (x + w, base_y - int(S * 0.05)),
                                                 (x + int(w * 0.1), base_y - int(S * 0.05))])
        y1, y2 = base_y - int(hgt * 0.62), base_y - int(hgt * 0.38)
        wd = lambda y: int(w * (base_y - y) / hgt)
        pygame.draw.polygon(big, (246, 246, 250), [(x - wd(y1), y1), (x + wd(y1), y1), (x + wd(y2), y2), (x - wd(y2), y2)])
        pygame.draw.circle(big, (40, 40, 46), (x, base_y - hgt), int(S * 0.025))
    return _finish(big, cs, ext)


def wall_block(cs: int) -> pygame.Surface:
    S = cs * SS
    big = _new(S, S)
    big.fill((43, 51, 68))
    pygame.draw.rect(big, (58, 68, 90), (0, 0, S, int(S * 0.08)))
    pygame.draw.rect(big, (30, 36, 50), (0, S - int(S * 0.08), S, int(S * 0.08)))
    pygame.draw.line(big, (30, 36, 50), (S // 2, 0), (S // 2, S), SS)
    for p in ((0.18, 0.2), (0.82, 0.2), (0.18, 0.8), (0.82, 0.8)):
        pygame.draw.circle(big, (82, 94, 120), (S * p[0], S * p[1]), int(SS * 1.6))
    return _shrink(big, cs, cs)


# --------------------------------------------------------------------------- portes
def door(cs: int, color_index: int, side: str) -> pygame.Surface:
    """Porte colorée avec sa forme gravée (lisible par un daltonien). side : 'L' (mur gauche) ou 'R'."""
    S = cs * SS
    big = _new(S, S)
    col = theme.DOOR_RGB[color_index]
    pygame.draw.rect(big, (24, 29, 41), (0, 0, S, S))
    frame = pygame.Rect(int(S * 0.08), int(S * 0.08), int(S * 0.84), int(S * 0.84))
    pygame.draw.rect(big, (78, 90, 116), frame, border_radius=int(S * 0.12))
    panel = frame.inflate(-int(S * 0.14), -int(S * 0.14))
    pygame.draw.rect(big, theme.mix(col, (0, 0, 0), 0.30), panel, border_radius=int(S * 0.08))
    top = pygame.Rect(panel.x, panel.y, panel.w, panel.h // 2)
    pygame.draw.rect(big, col, top, border_top_left_radius=int(S * 0.08), border_top_right_radius=int(S * 0.08))
    pygame.draw.line(big, theme.mix(col, (255, 255, 255), 0.35), (panel.x + SS * 2, panel.y + SS * 2),
                     (panel.right - SS * 2, panel.y + SS * 2), SS)
    theme.draw_shape(big, theme.SHAPES[color_index], panel.center, S * 0.17, (250, 250, 252),
                     theme.mix(col, (0, 0, 0), 0.5), SS)
    hx = panel.right + int(S * 0.0) - int(S * 0.04) if side == "L" else panel.x + int(S * 0.04)
    pygame.draw.circle(big, (210, 216, 228), (hx, panel.centery), int(S * 0.045))
    pygame.draw.circle(big, (34, 197, 94), (S // 2, int(S * 0.14)), int(S * 0.03))
    return _shrink(big, cs, cs)


# --------------------------------------------------------------------------- marqueurs
def pad(cs: int) -> pygame.Surface:
    """Plateforme de destination."""
    S = cs * SS
    big = _new(S, S)
    c = (S // 2, S // 2)
    pygame.draw.circle(big, (0, 0, 0, 80), (c[0] + S * 0.03, c[1] + S * 0.04), S * 0.40)
    pygame.draw.circle(big, (30, 38, 58), c, S * 0.40)
    pygame.draw.circle(big, theme.BAD, c, S * 0.40, int(SS * 2.2))
    pygame.draw.circle(big, (251, 146, 60), c, S * 0.26, int(SS * 1.6))
    pygame.draw.circle(big, theme.BAD, c, S * 0.11)
    pygame.draw.circle(big, (255, 255, 255), (c[0] - S * 0.03, c[1] - S * 0.03), S * 0.035)
    return _shrink(big, cs, cs)


def dock(cs: int) -> pygame.Surface:
    S = cs * SS
    big = _new(S, S)
    c = (S // 2, S // 2)
    pygame.draw.circle(big, (34, 197, 94, 40), c, S * 0.40)
    pygame.draw.circle(big, (34, 197, 94, 190), c, S * 0.40, int(SS * 1.6))
    for i in range(8):
        ang = i * math.pi / 4
        p1 = (c[0] + S * 0.34 * math.cos(ang), c[1] + S * 0.34 * math.sin(ang))
        p2 = (c[0] + S * 0.44 * math.cos(ang), c[1] + S * 0.44 * math.sin(ang))
        pygame.draw.line(big, (34, 197, 94, 200), p1, p2, int(SS * 1.6))
    return _shrink(big, cs, cs)


# --------------------------------------------------------------------------- robot
def robot(cs: int) -> pygame.Surface:
    """Mini robot à chenilles vu de dessus, tourné vers la droite (angle 0)."""
    S = cs * SS
    big = _new(S, S)

    def P(x, y):
        return (int(S * x), int(S * y))

    def R(x0, y0, x1, y1):
        return pygame.Rect(int(S * x0), int(S * y0), int(S * (x1 - x0)), int(S * (y1 - y0)))

    pygame.draw.ellipse(big, (0, 0, 0, 95), R(0.10, 0.20, 0.92, 0.88))
    for y0 in (0.12, 0.68):  # chenilles
        tr = R(0.10, y0, 0.90, y0 + 0.20)
        pygame.draw.rect(big, (30, 34, 44), tr, border_radius=int(S * 0.08))
        for i in range(10):
            x = tr.x + int(tr.w * (0.06 + i * 0.095))
            pygame.draw.line(big, (66, 73, 90), (x, tr.y + SS * 2), (x, tr.bottom - SS * 2), int(SS * 1.5))
        pygame.draw.rect(big, (16, 18, 24), tr, int(SS * 1.2), border_radius=int(S * 0.08))
    body = R(0.17, 0.24, 0.83, 0.76)
    pygame.draw.rect(big, (205, 213, 228), body, border_radius=int(S * 0.10))
    pygame.draw.rect(big, (238, 242, 250), (body.x, body.y, body.w, body.h // 2),
                     border_top_left_radius=int(S * 0.10), border_top_right_radius=int(S * 0.10))
    pygame.draw.rect(big, (130, 142, 165), body, int(SS * 1.4), border_radius=int(S * 0.10))
    pygame.draw.rect(big, theme.ACCENT, R(0.23, 0.465, 0.64, 0.535), border_radius=int(S * 0.03))
    pygame.draw.rect(big, (40, 52, 82), R(0.23, 0.31, 0.50, 0.42), border_radius=int(S * 0.03))
    pygame.draw.rect(big, (40, 52, 82), R(0.23, 0.58, 0.50, 0.69), border_radius=int(S * 0.03))
    pygame.draw.circle(big, (28, 32, 42), P(0.40, 0.5), int(S * 0.095))  # lidar
    pygame.draw.circle(big, (110, 205, 255), P(0.40, 0.5), int(S * 0.095), int(SS * 1.4))
    pygame.draw.circle(big, (255, 90, 90), P(0.40, 0.5), int(S * 0.03))
    pygame.draw.rect(big, (26, 30, 42), R(0.73, 0.33, 0.84, 0.67), border_radius=int(S * 0.04))  # capteur avant
    for y in (0.40, 0.60):
        pygame.draw.circle(big, (80, 232, 255), P(0.785, y), int(S * 0.04))
        pygame.draw.circle(big, (190, 250, 255), P(0.785, y), int(S * 0.018))
    return _shrink(big, cs, cs)


# --------------------------------------------------------------------------- sol de la carte
def _blob(w: int, h: int, rng: random.Random, cx: float, cy: float, rad: float, color) -> pygame.Surface:
    """Zone organique (union de cercles) pour le gravier ou l'herbe."""
    z = _new(w, h)
    for _ in range(4):
        pygame.draw.circle(z, color, (cx + rng.uniform(-0.7, 0.7) * rad, cy + rng.uniform(-0.5, 0.5) * rad),
                           rad * rng.uniform(0.55, 0.9))
    return z


def build_arena(cols: int, rows: int, cs: int) -> pygame.Surface:
    """Sol de la carte : dalles de béton, route avec marquage, gravier, herbe, lignes jaunes, vignettage."""
    w, h = cols * cs, rows * cs
    rng = random.Random(11)
    surf = pygame.Surface((w, h)).convert()
    for r in range(rows):  # dalles de béton de 4 x 4 cases, en damier
        for c in range(cols):
            base = (31, 39, 55) if ((r // 4) + (c // 4)) % 2 == 0 else (27, 34, 49)
            j = rng.randint(-2, 2)
            pygame.draw.rect(surf, (base[0] + j, base[1] + j, base[2] + j), (c * cs, r * cs, cs, cs))
    # route (asphalte) avec ligne centrale jaune pointillée
    road_row = max(2, min(rows - 4, int(rows * 0.58)))
    road = pygame.Rect(0, road_row * cs, w, 2 * cs)
    pygame.draw.rect(surf, (22, 26, 35), road)
    for _ in range(int(w * 2 * cs / 180)):
        pygame.draw.circle(surf, (30, 35, 46), (rng.randint(0, w), rng.randint(road.y, road.bottom)), 1)
    y = road.centery
    for x in range(int(cs * 0.4), w, int(cs * 1.6)):
        pygame.draw.line(surf, (176, 140, 40), (x, y), (min(w, x + int(cs * 0.8)), y), max(2, cs // 14))
    # gravier et herbe
    zones = _new(w, h)
    for kind, n in (("gravel", 2), ("grass", 2)):
        for _ in range(n):
            cx, cy = rng.uniform(0.1, 0.9) * w, rng.uniform(0.08, 0.92) * h
            if abs(cy - road.centery) < cs * 3:
                cy = (cy + h * 0.45) % h
            rad = cs * rng.uniform(1.6, 2.6)
            col = (44, 50, 62, 255) if kind == "gravel" else (28, 54, 42, 255)
            blob = _blob(w, h, rng, cx, cy, rad, col)
            for _ in range(int(rad * rad / 6)):
                px, py = rng.uniform(cx - rad * 1.5, cx + rad * 1.5), rng.uniform(cy - rad * 1.2, cy + rad * 1.2)
                if 0 <= px < w and 0 <= py < h and blob.get_at((int(px), int(py))).a > 0:
                    if kind == "gravel":
                        t = rng.randint(-14, 20)
                        pygame.draw.circle(blob, (60 + t, 66 + t, 78 + t, 255), (px, py), max(1, cs // 14))
                    else:
                        pygame.draw.line(blob, (62 + rng.randint(0, 30), 112 + rng.randint(0, 30), 70, 255),
                                         (px, py), (px + rng.uniform(-2, 2), py - rng.uniform(2, cs * 0.2)), 1)
            zones.blit(blob, (0, 0))
    surf.blit(zones, (0, 0))
    # places de stationnement : contours jaunes pointillés
    for _ in range(2):
        bx = rng.randint(1, max(1, cols - 5)) * cs
        by = rng.choice([rng.randint(1, max(1, road_row - 3)), min(rows - 3, road_row + 3)]) * cs
        rect = pygame.Rect(bx, by, 3 * cs, 2 * cs)
        for x in range(rect.x, rect.right, max(4, cs // 3)):
            pygame.draw.line(surf, (150, 120, 36), (x, rect.y), (x + cs // 6, rect.y), 2)
            pygame.draw.line(surf, (150, 120, 36), (x, rect.bottom), (x + cs // 6, rect.bottom), 2)
        for yy in range(rect.y, rect.bottom, max(4, cs // 3)):
            pygame.draw.line(surf, (150, 120, 36), (rect.x, yy), (rect.x, yy + cs // 6), 2)
            pygame.draw.line(surf, (150, 120, 36), (rect.right, yy), (rect.right, yy + cs // 6), 2)
    # joints : traits fins entre cases, joints marqués entre dalles
    for c in range(cols + 1):
        pygame.draw.line(surf, (22, 28, 40) if c % 4 == 0 else (37, 47, 66), (c * cs, 0), (c * cs, h))
    for r in range(rows + 1):
        pygame.draw.line(surf, (22, 28, 40) if r % 4 == 0 else (37, 47, 66), (0, r * cs), (w, r * cs))
    shine = _new(w, h)
    for i in range(0, h, 3):  # reflet diagonal léger
        a = int(14 * max(0.0, 1 - i / h))
        pygame.draw.line(shine, (140, 170, 255, a), (0, i), (min(w, i + w // 3), 0))
    surf.blit(shine, (0, 0))
    vig = _new(w, h)
    n = max(10, min(w, h) // 14)
    for i in range(n):
        a = int(150 * (1 - i / n) ** 2)
        pygame.draw.rect(vig, (0, 0, 0, a), (i, i, w - 2 * i, h - 2 * i), 1)
    surf.blit(vig, (0, 0))
    out = _new(w, h)
    out.blit(surf, (0, 0))
    mask = _new(w, h)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=16)
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return out


class Sprites:
    """Tous les sprites pour une taille de case donnée."""

    def __init__(self, cs: int):
        self.cs = cs
        self.obstacles = [
            crate(cs), container(cs, (178, 58, 50)), barrier(cs), barrel(cs), boulder(cs, 1), stacked_crates(cs),
            pallet(cs), container(cs, (46, 100, 164)), barrel(cs, (58, 112, 196)), crate(cs, (160, 112, 66)),
            boulder(cs, 2), cones(cs), barrier(cs), container(cs, (54, 134, 92)), stacked_crates(cs),
        ]
        self.obs_h = self.obstacles[0].get_height()  # hauteur d'un sprite d'obstacle (case + relief)
        self.wall = wall_block(cs)
        self.door_left = [door(cs, i, "L") for i in range(5)]
        self.door_right = [door(cs, i, "R") for i in range(5)]
        self.pad = pad(cs)
        self.dock = dock(cs)
        self.robot = robot(cs)

    def obstacle(self, r: int, c: int) -> pygame.Surface:
        return self.obstacles[(r * 7349 + c * 9151 + r * c) % len(self.obstacles)]
