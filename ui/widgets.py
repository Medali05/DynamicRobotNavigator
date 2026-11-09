"""Petits composants d'interface dessinés avec Pygame : bouton, sélecteurs, interrupteur, curseur."""
from __future__ import annotations

import pygame

from . import theme
from .theme import draw_text


class Widget:
    def __init__(self, rect, enabled_fn=None):
        self.rect = pygame.Rect(rect)
        self.enabled_fn = enabled_fn

    @property
    def enabled(self) -> bool:
        return self.enabled_fn() if self.enabled_fn else True

    def event(self, e) -> bool:
        return False

    def draw(self, surf, mouse):
        pass

    def hot(self, mouse) -> bool:
        return self.enabled and self.rect.collidepoint(mouse)


def _clicked(w: Widget, e) -> bool:
    return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and w.enabled and w.rect.collidepoint(e.pos)


class Button(Widget):
    def __init__(self, rect, text, on_click, style="ghost", text_fn=None, enabled_fn=None, icon=None, size=14):
        super().__init__(rect, enabled_fn)
        self.text, self.on_click, self.style, self.text_fn = text, on_click, style, text_fn
        self.icon, self.size = icon, size

    def event(self, e) -> bool:
        if _clicked(self, e):
            self.on_click()
            return True
        return False

    def draw(self, surf, mouse):
        hot, on = self.hot(mouse), self.enabled
        top, bot = {"primary": ((104, 160, 255), (62, 118, 238)),
                    "danger": ((250, 100, 100), (214, 60, 60))}.get(self.style, ((40, 52, 78), (29, 38, 58)))
        if hot:
            top, bot = theme.mix(top, (255, 255, 255), 0.12), theme.mix(bot, (255, 255, 255), 0.12)
        if not on:
            top, bot = theme.mix(top, theme.PANEL, 0.65), theme.mix(bot, theme.PANEL, 0.65)
        if self.style == "primary" and on:  # lueur sous le bouton principal
            glow = self.rect.inflate(8, 8)
            pygame.draw.rect(surf, theme.mix(theme.PANEL, theme.ACCENT, 0.28 if hot else 0.16), glow, border_radius=14)
        surf.blit(theme.vgrad(self.rect.w, self.rect.h, top, bot, 10), self.rect.topleft)
        edge = theme.mix(bot, (255, 255, 255), 0.25) if self.style != "ghost" else theme.LINE
        pygame.draw.rect(surf, edge, self.rect, 1, border_radius=10)
        color = theme.TEXT if on else theme.MUTE
        txt = self.text_fn() if self.text_fn else self.text
        img = theme.font(self.size, True).render(txt, True, color)
        if self.icon:
            s = max(5, self.size * 0.46)
            total = int(2 * s + 7 + img.get_width())
            x0 = self.rect.centerx - total // 2
            theme.draw_icon(surf, self.icon, (x0 + s, self.rect.centery), s, color)
            surf.blit(img, (x0 + 2 * s + 7, self.rect.centery - img.get_height() // 2))
        else:
            surf.blit(img, img.get_rect(center=self.rect.center))


class Segmented(Widget):
    def __init__(self, rect, options, get, set_, enabled_fn=None):
        super().__init__(rect, enabled_fn)
        self.options, self.get, self.set = options, get, set_

    def event(self, e) -> bool:
        if _clicked(self, e):
            self.set(min(len(self.options) - 1, (e.pos[0] - self.rect.x) * len(self.options) // self.rect.w))
            return True
        return False

    def draw(self, surf, mouse):
        on = self.enabled
        pygame.draw.rect(surf, theme.CARD, self.rect, border_radius=10)
        n, w = len(self.options), self.rect.w / len(self.options)
        for i, label in enumerate(self.options):
            seg = pygame.Rect(self.rect.x + i * w + 3, self.rect.y + 3, w - 6, self.rect.h - 6)
            sel = i == self.get()
            if sel:
                pygame.draw.rect(surf, theme.ACCENT if on else theme.LINE, seg, border_radius=8)
            elif self.hot(mouse) and seg.collidepoint(mouse):
                pygame.draw.rect(surf, theme.CARD_HOVER, seg, border_radius=8)
            draw_text(surf, label, seg.center, 13, theme.TEXT if (sel or on) else theme.MUTE, sel, "center")


class Choice(Widget):
    """Sélecteur à flèches : < valeur >."""

    def __init__(self, rect, label, options, get, set_, enabled_fn=None):
        super().__init__(rect, enabled_fn)
        self.label, self.options, self.get, self.set = label, options, get, set_

    def event(self, e) -> bool:
        if _clicked(self, e):
            i = self.options.index(self.get())
            step = -1 if e.pos[0] < self.rect.x + self.rect.w * 0.3 else 1
            self.set(self.options[(i + step) % len(self.options)])
            return True
        return False

    def draw(self, surf, mouse):
        on = self.enabled
        pygame.draw.rect(surf, theme.CARD_HOVER if self.hot(mouse) else theme.CARD, self.rect, border_radius=10)
        pygame.draw.rect(surf, theme.LINE, self.rect, 1, border_radius=10)
        draw_text(surf, self.label, (self.rect.centerx, self.rect.y + 4), 10, theme.MUTE, False, "midtop")
        draw_text(surf, self.get(), (self.rect.centerx, self.rect.bottom - 4), 14, theme.TEXT if on else theme.MUTE,
                  True, "midbottom")
        cy = self.rect.centery
        for sign, x in ((-1, self.rect.x + 16), (1, self.rect.right - 16)):
            pts = [(x - sign * 4, cy - 6), (x + sign * 4, cy), (x - sign * 4, cy + 6)]
            pygame.draw.lines(surf, theme.MUTE, False, pts, 2)


class Toggle(Widget):
    def __init__(self, rect, label, get, set_, enabled_fn=None):
        super().__init__(rect, enabled_fn)
        self.label, self.get, self.set = label, get, set_

    def event(self, e) -> bool:
        if _clicked(self, e):
            self.set(not self.get())
            return True
        return False

    def draw(self, surf, mouse):
        on, val = self.enabled, self.get()
        draw_text(surf, self.label, (self.rect.x + 2, self.rect.centery), 14, theme.TEXT if on else theme.MUTE,
                  False, "midleft")
        sw = pygame.Rect(0, 0, 38, 20)
        sw.midright = (self.rect.right - 2, self.rect.centery)
        pygame.draw.rect(surf, theme.ACCENT if (val and on) else theme.LINE, sw, border_radius=10)
        kx = sw.right - 11 if val else sw.x + 11
        pygame.draw.circle(surf, (255, 255, 255) if on else theme.MUTE, (kx, sw.centery), 7)


class Slider(Widget):
    def __init__(self, rect, label, vmin, vmax, get, set_, fmt, enabled_fn=None):
        super().__init__(rect, enabled_fn)
        self.label, self.vmin, self.vmax, self.get, self.set, self.fmt = label, vmin, vmax, get, set_, fmt
        self.drag = False

    def _track(self):
        return pygame.Rect(self.rect.x + 4, self.rect.bottom - 12, self.rect.w - 8, 4)

    def _set_from(self, x):
        t = (x - self._track().x) / self._track().w
        self.set(self.vmin + max(0.0, min(1.0, t)) * (self.vmax - self.vmin))

    def event(self, e) -> bool:
        if _clicked(self, e):
            self.drag = True
            self._set_from(e.pos[0])
            return True
        if e.type == pygame.MOUSEMOTION and self.drag:
            self._set_from(e.pos[0])
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.drag:
            self.drag = False
            return True
        return False

    def draw(self, surf, mouse):
        on = self.enabled
        draw_text(surf, self.label, (self.rect.x + 2, self.rect.y + 2), 13, theme.TEXT if on else theme.MUTE)
        draw_text(surf, self.fmt(self.get()), (self.rect.right - 2, self.rect.y + 2), 13,
                  theme.ACCENT_HOVER if on else theme.MUTE, True, "topright")
        tr = self._track()
        pygame.draw.rect(surf, theme.LINE, tr, border_radius=2)
        t = (self.get() - self.vmin) / (self.vmax - self.vmin)
        fill = pygame.Rect(tr.x, tr.y, int(tr.w * t), tr.h)
        pygame.draw.rect(surf, theme.ACCENT if on else theme.MUTE, fill, border_radius=2)
        pygame.draw.circle(surf, (255, 255, 255) if on else theme.MUTE, (tr.x + int(tr.w * t), tr.centery), 7)


class Chips(Widget):
    """Choix de la couleur de départ : cinq pastilles avec leur forme."""

    def __init__(self, rect, get, set_, enabled_fn=None):
        super().__init__(rect, enabled_fn)
        self.get, self.set = get, set_

    def _slot(self, i):
        w = self.rect.w / 5
        return pygame.Rect(self.rect.x + i * w + 2, self.rect.y, w - 4, self.rect.h)

    def event(self, e) -> bool:
        if _clicked(self, e):
            for i in range(5):
                if self._slot(i).collidepoint(e.pos):
                    self.set(i)
                    return True
        return False

    def draw(self, surf, mouse):
        on = self.enabled
        for i in range(5):
            slot = self._slot(i)
            pygame.draw.rect(surf, theme.CARD_HOVER if (on and slot.collidepoint(mouse)) else theme.CARD, slot,
                             border_radius=8)
            col = theme.DOOR_RGB[i] if on else theme.mix(theme.DOOR_RGB[i], theme.PANEL, 0.7)
            theme.draw_shape(surf, theme.SHAPES[i], slot.center, 8, col)
            if i == self.get() and on:
                pygame.draw.rect(surf, (255, 255, 255), slot, 2, border_radius=8)
