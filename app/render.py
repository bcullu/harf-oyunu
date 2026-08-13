"""Ekran çizimi: dev harf, yumuşama animasyonu, çıkış göstergesi.

Çizim yalnızca durum değiştiğinde çağrılır (bkz. main.py olay döngüsü).
"""

from __future__ import annotations

import random

import pygame

BACKGROUND = (16, 16, 24)
HINT_COLOR = (90, 90, 110)
EXIT_BAR_COLOR = (220, 80, 80)

# Türkçe glifleri (ğ, İ, ş, ...) içermesi muhtemel font adayları
FONT_CANDIDATES = (
    "DejaVu Sans",
    "Liberation Sans",
    "Noto Sans",
    "FreeSans",
    "Arial Unicode MS",
    "Helvetica",
    "Arial",
)

# Çocuk için canlı ama okunabilir renkler
PALETTE = (
    (255, 87, 87),
    (255, 159, 28),
    (255, 214, 10),
    (106, 217, 111),
    (56, 199, 199),
    (77, 155, 255),
    (168, 124, 255),
    (255, 122, 190),
)

ANIM_DURATION_MS = 300


def find_font_path() -> str | None:
    """Sistemde Türkçe destekleyen bir font arar; bulamazsa None döner."""
    for name in FONT_CANDIDATES:
        path = pygame.font.match_font(name)
        if path:
            return path
    return None


def _ease_out_back(t: float) -> float:
    """Hafif taşmalı yumuşama (0 -> 1)."""
    c1, c3 = 1.70158, 2.70158
    t -= 1.0
    return 1.0 + c3 * t * t * t + c1 * t * t


class Renderer:
    def __init__(self, screen: pygame.Surface, font_scale: float = 0.62):
        self.screen = screen
        self.font_scale = font_scale
        self._font_path = find_font_path()
        self._glyph_font = self._make_font(int(screen.get_height() * font_scale))
        self._hint_font = self._make_font(max(14, screen.get_height() // 32))

        self.current_char: str | None = None
        self._color = PALETTE[0]
        self._glyph: pygame.Surface | None = None
        self._anim_start_ms = 0
        self._anim_active = False
        self.exit_progress = 0.0  # ESC basılı tutma göstergesi (0..1)

    # -- font ------------------------------------------------------------
    def _make_font(self, size: int) -> pygame.font.Font:
        if self._font_path:
            return pygame.font.Font(self._font_path, size)
        return pygame.font.Font(None, size)

    def set_font_scale(self, scale: float) -> None:
        self.font_scale = scale
        self._glyph_font = self._make_font(int(self.screen.get_height() * scale))
        if self.current_char:
            self._render_glyph()

    # -- içerik ----------------------------------------------------------
    def show_char(self, char: str, now_ms: int) -> None:
        """Yeni karakteri gösterir ve giriş animasyonunu başlatır."""
        self.current_char = char
        new_color = random.choice([c for c in PALETTE if c != self._color])
        self._color = new_color
        self._render_glyph()
        self._anim_start_ms = now_ms
        self._anim_active = True

    def _render_glyph(self) -> None:
        assert self.current_char is not None
        self._glyph = self._glyph_font.render(self.current_char, True, self._color)

    # -- animasyon -------------------------------------------------------
    @property
    def animating(self) -> bool:
        return self._anim_active

    def update(self, now_ms: int) -> bool:
        """Animasyon durumunu ilerletir. Hâlâ animasyon varsa True döner."""
        if self._anim_active and now_ms - self._anim_start_ms >= ANIM_DURATION_MS:
            self._anim_active = False
        return self._anim_active

    def _anim_progress(self, now_ms: int) -> float:
        if not self._anim_active:
            return 1.0
        elapsed = now_ms - self._anim_start_ms
        return min(1.0, max(0.0, elapsed / ANIM_DURATION_MS))

    # -- çizim -----------------------------------------------------------
    def draw(self, now_ms: int) -> None:
        self.screen.fill(BACKGROUND)

        if self._glyph is not None:
            t = self._anim_progress(now_ms)
            scale = 0.45 + 0.55 * _ease_out_back(t)
            alpha = int(255 * min(1.0, t * 2.5))
            w = max(1, int(self._glyph.get_width() * scale))
            h = max(1, int(self._glyph.get_height() * scale))
            surf = pygame.transform.smoothscale(self._glyph, (w, h))
            if alpha < 255:
                surf = surf.copy()
                surf.set_alpha(alpha)
            rect = surf.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(surf, rect)

        self._draw_hint()
        if self.exit_progress > 0:
            self._draw_exit_bar()

        pygame.display.flip()

    def _draw_hint(self) -> None:
        text = self._hint_font.render(self._hint_text, True, HINT_COLOR)
        rect = text.get_rect(midbottom=(self.screen.get_width() // 2,
                                        self.screen.get_height() - 12))
        self.screen.blit(text, rect)

    _hint_text = "ESC (2 sn) veya Ctrl+Q ile çıkış"

    def set_hint(self, text: str) -> None:
        self._hint_text = text

    def _draw_exit_bar(self) -> None:
        width = int(self.screen.get_width() * 0.4 * self.exit_progress)
        height = max(6, self.screen.get_height() // 90)
        rect = pygame.Rect(0, 0, width, height)
        rect.midbottom = (self.screen.get_width() // 2,
                          self.screen.get_height() - 12 - self._hint_font.get_height())
        pygame.draw.rect(self.screen, EXIT_BAR_COLOR, rect, border_radius=height // 2)
