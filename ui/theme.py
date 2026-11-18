"""Couleurs, polices et petites fonctions de dessin communes."""
from __future__ import annotations

import math

import pygame

BG = (10, 13, 19)
PANEL = (17, 23, 36)
CARD = (27, 35, 53)
CARD_HOVER = (36, 47, 70)
LINE = (44, 57, 84)
TEXT = (232, 236, 244)
MUTE = (140, 151, 172)
ACCENT = (79, 140, 255)
ACCENT_HOVER = (110, 162, 255)
GOOD = (34, 197, 94)
WARN = (245, 158, 11)
BAD = (239, 68, 68)

DOOR_RGB = [(239, 68, 68), (59, 130, 246), (34, 197, 94), (250, 204, 21), (168, 85, 247)]
SHAPES = ["cercle", "carré", "triangle", "étoile", "hexagone"]

_fonts: dict = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("segoeui,helveticaneue,arial,dejavusans,freesans", size, bold=bold)
    return _fonts[key]


def draw_text(surf, text, pos, size=14, color=TEXT, bold=False, anchor="topleft"):
    img = font(size, bold).render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)
    return rect


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shape_points(kind: str, cx: float, cy: float, r: float):
    if kind == "triangle":
        return [(cx, cy - r), (cx + 0.95 * r, cy + 0.8 * r), (cx - 0.95 * r, cy + 0.8 * r)]
    if kind == "étoile":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        return pts
    if kind == "hexagone":
        return [(cx + r * math.cos(i * math.pi / 3), cy + r * math.sin(i * math.pi / 3)) for i in range(6)]
    return None


def draw_shape(surf, kind: str, center, r: float, color, outline=None, outline_w=0):
    cx, cy = center
    if kind == "cercle":
        pygame.draw.circle(surf, color, (cx, cy), r)
        if outline:
            pygame.draw.circle(surf, outline, (cx, cy), r, outline_w)
    elif kind == "carré":
        rect = pygame.Rect(0, 0, int(r * 1.7), int(r * 1.7))
        rect.center = (int(cx), int(cy))
        pygame.draw.rect(surf, color, rect, border_radius=max(1, int(r * 0.2)))
        if outline:
            pygame.draw.rect(surf, outline, rect, outline_w, border_radius=max(1, int(r * 0.2)))
    else:
        pts = shape_points(kind, cx, cy, r)
        pygame.draw.polygon(surf, color, pts)
        if outline:
            pygame.draw.polygon(surf, outline, pts, outline_w)


_grad_cache: dict = {}


def vgrad(w: int, h: int, top, bottom, radius: int = 10) -> pygame.Surface:
    """Rectangle arrondi avec un dégradé vertical (mis en cache)."""
    key = (w, h, top, bottom, radius)
    if key not in _grad_cache:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            pygame.draw.line(surf, mix(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        _grad_cache[key] = surf
    return _grad_cache[key]


def draw_icon(surf, name: str, center, s: float, color, w: int = 2):
    """Petites icônes dessinées en vectoriel. s = demi-taille en pixels."""
    x, y = center
    if name == "play":
        pygame.draw.polygon(surf, color, [(x - s * 0.6, y - s), (x - s * 0.6, y + s), (x + s, y)])
    elif name == "pause":
        for dx in (-0.55, 0.55):
            pygame.draw.rect(surf, color, (x + dx * s - s * 0.28, y - s, s * 0.56, 2 * s), border_radius=1)
    elif name == "step":
        pygame.draw.polygon(surf, color, [(x - s, y - s), (x - s, y + s), (x + s * 0.45, y)])
        pygame.draw.rect(surf, color, (x + s * 0.62, y - s, s * 0.4, 2 * s))
    elif name == "replan":
        pygame.draw.arc(surf, color, (x - s, y - s, 2 * s, 2 * s), 0.7, 5.6, w)
        pygame.draw.polygon(surf, color, [(x + s * 0.1, y - s * 1.35), (x + s * 1.15, y - s * 0.85),
                                          (x + s * 0.3, y - s * 0.3)])
    elif name == "home":
        pygame.draw.polygon(surf, color, [(x - s * 1.15, y - s * 0.05), (x, y - s), (x + s * 1.15, y - s * 0.05)])
        pygame.draw.rect(surf, color, (x - s * 0.75, y - s * 0.05, s * 1.5, s * 1.05))
    elif name == "dice":
        pygame.draw.rect(surf, color, (x - s, y - s, 2 * s, 2 * s), w, border_radius=3)
        for dx, dy in ((-0.45, -0.45), (0, 0), (0.45, 0.45)):
            pygame.draw.circle(surf, color, (x + dx * s, y + dy * s), max(1, s * 0.2))
    elif name == "maze":
        pygame.draw.rect(surf, color, (x - s, y - s, 2 * s, 2 * s), w, border_radius=2)
        pygame.draw.lines(surf, color, False, [(x - s, y - s * 0.2), (x + s * 0.25, y - s * 0.2),
                                               (x + s * 0.25, y + s * 0.55)], w)
        pygame.draw.line(surf, color, (x - s * 0.5, y + s * 0.3), (x - s * 0.5, y + s), w)
    elif name == "clear":
        pygame.draw.line(surf, color, (x - s * 0.8, y - s * 0.8), (x + s * 0.8, y + s * 0.8), w + 1)
        pygame.draw.line(surf, color, (x - s * 0.8, y + s * 0.8), (x + s * 0.8, y - s * 0.8), w + 1)
