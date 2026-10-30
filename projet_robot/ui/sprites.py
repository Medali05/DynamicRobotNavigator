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


# --------------------------------------------------------------------------- obstacles
def crate(cs: int, wood=(184, 130, 76)) -> pygame.Surface:
    S = cs * SS
    big = _new(S, S)
    m = int(S * 0.11)
    box = pygame.Rect(m, m, S - 2 * m - int(S * 0.03), S - 2 * m - int(S * 0.03))
    pygame.draw.rect(big, (0, 0, 0, 90), box.move(int(S * 0.04), int(S * 0.05)), border_radius=int(S * 0.06))
    dark = theme.mix(wood, (0, 0, 0), 0.42)
    light = theme.mix(wood, (255, 255, 255), 0.22)
    pygame.draw.rect(big, wood, box, border_radius=int(S * 0.06))
    for i in range(1, 4):  # planches
        y = box.y + box.h * i // 4
        pygame.draw.line(big, dark, (box.x, y), (box.right, y), SS)
    pygame.draw.line(big, light, (box.x + SS * 2, box.y + SS * 2), (box.right - SS * 2, box.y + SS * 2), SS)
    inner = box.inflate(-int(S * 0.16), -int(S * 0.16))
    pygame.draw.line(big, dark, inner.topleft, inner.bottomright, int(SS * 2))
    pygame.draw.line(big, dark, inner.topright, inner.bottomleft, int(SS * 2))
    pygame.draw.rect(big, dark, box, int(SS * 1.6), border_radius=int(S * 0.06))
    pygame.draw.rect(big, dark, inner, int(SS * 1.5))
    for p in (inner.topleft, inner.topright, inner.bottomleft, inner.bottomright):
        pygame.draw.circle(big, (60, 40, 22), p, int(SS * 1.8))
    return _shrink(big, cs, cs)


def concrete(cs: int) -> pygame.Surface:
    """Bloc de béton avec bande de danger jaune et noire."""
    S = cs * SS
    big = _new(S, S)
    m = int(S * 0.10)
    box = pygame.Rect(m, m, S - 2 * m - int(S * 0.03), S - 2 * m - int(S * 0.03))
    pygame.draw.rect(big, (0, 0, 0, 90), box.move(int(S * 0.04), int(S * 0.05)), border_radius=int(S * 0.08))
    pygame.draw.rect(big, (116, 126, 142), box, border_radius=int(S * 0.08))
    pygame.draw.rect(big, (150, 160, 176), (box.x + SS, box.y + SS, box.w - 2 * SS, int(S * 0.10)),
                     border_radius=int(S * 0.05))
    band = pygame.Rect(box.x, box.y + int(box.h * 0.46), box.w, int(box.h * 0.26))
    layer = _new(band.w, band.h)
    layer.fill((26, 28, 34))
    step = int(S * 0.20)
    for x in range(-band.h, band.w + band.h, step):
        pygame.draw.polygon(layer, (250, 204, 21), [(x, band.h), (x + step // 2, band.h),
                                                    (x + step // 2 + band.h, 0), (x + band.h, 0)])
    big.blit(layer, band)
    pygame.draw.rect(big, (62, 70, 86), box, int(SS * 1.6), border_radius=int(S * 0.08))
    return _shrink(big, cs, cs)


def rock(cs: int, seed: int) -> pygame.Surface:
    S = cs * SS
    big = _new(S, S)
    rng = random.Random(seed)
    cx, cy = S * 0.5, S * 0.52
    n = 10
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n + rng.uniform(-0.12, 0.12)
        rad = S * rng.uniform(0.30, 0.40)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang) * 0.92))
    shadow = [(x + S * 0.04, y + S * 0.05) for x, y in pts]
    pygame.draw.polygon(big, (0, 0, 0, 90), shadow)
    pygame.draw.polygon(big, (104, 111, 124), pts)
    hi = [(cx + (x - cx) * 0.62 - S * 0.05, cy + (y - cy) * 0.62 - S * 0.06) for x, y in pts]
    pygame.draw.polygon(big, (146, 154, 168), hi)
    lo = [(cx + (x - cx) * 0.9, cy + (y - cy) * 0.9) for x, y in pts[n // 2:]]
    pygame.draw.lines(big, (74, 80, 92), False, lo, int(SS * 1.6))
    pygame.draw.polygon(big, (58, 64, 76), pts, int(SS * 1.6))
    a = pts[rng.randrange(n)]
    pygame.draw.line(big, (70, 76, 88), (cx, cy), (cx + (a[0] - cx) * 0.7, cy + (a[1] - cy) * 0.7), SS)
    return _shrink(big, cs, cs)


def barrel(cs: int, color=(205, 72, 52)) -> pygame.Surface:
    S = cs * SS
    big = _new(S, S)
    c = (S * 0.5, S * 0.5)
    R = S * 0.36
    pygame.draw.circle(big, (0, 0, 0, 90), (c[0] + S * 0.04, c[1] + S * 0.05), R)
    pygame.draw.circle(big, theme.mix(color, (0, 0, 0), 0.35), c, R)
    pygame.draw.circle(big, color, c, R * 0.92)
    pygame.draw.circle(big, theme.mix(color, (255, 255, 255), 0.25), c, R * 0.72, int(SS * 1.5))
    pygame.draw.circle(big, theme.mix(color, (0, 0, 0), 0.2), c, R * 0.60)
    pygame.draw.circle(big, theme.mix(color, (255, 255, 255), 0.35), (c[0] - R * 0.2, c[1] - R * 0.2), R * 0.2)
    pygame.draw.circle(big, (40, 40, 46), (c[0] + R * 0.28, c[1] + R * 0.1), R * 0.12)
    return _shrink(big, cs, cs)


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
def build_arena(cols: int, rows: int, cs: int) -> pygame.Surface:
    """Sol de la carte : dalles, joints, reflets, vignettage et coins arrondis."""
    w, h = cols * cs, rows * cs
    surf = pygame.Surface((w, h)).convert()
    rng = random.Random(11)
    for r in range(rows):
        for c in range(cols):
            base = (28, 36, 51) if (r + c) % 2 == 0 else (25, 32, 46)
            j = rng.randint(-2, 2)
            pygame.draw.rect(surf, (base[0] + j, base[1] + j, base[2] + j), (c * cs, r * cs, cs, cs))
    line = (37, 47, 66)
    for c in range(cols + 1):
        pygame.draw.line(surf, line, (c * cs, 0), (c * cs, h))
    for r in range(rows + 1):
        pygame.draw.line(surf, line, (0, r * cs), (w, r * cs))
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
            crate(cs), concrete(cs), rock(cs, 1), barrel(cs), crate(cs, (160, 112, 66)),
            rock(cs, 2), barrel(cs, (58, 112, 196)), concrete(cs), rock(cs, 3),
        ]
        self.wall = wall_block(cs)
        self.door_left = [door(cs, i, "L") for i in range(5)]
        self.door_right = [door(cs, i, "R") for i in range(5)]
        self.pad = pad(cs)
        self.dock = dock(cs)
        self.robot = robot(cs)

    def obstacle(self, r: int, c: int) -> pygame.Surface:
        return self.obstacles[(r * 7349 + c * 9151 + r * c) % len(self.obstacles)]
