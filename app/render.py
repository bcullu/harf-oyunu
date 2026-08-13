"""Ekran çizimi: dev harf, yumuşama animasyonu, yıldızlar, kutlama.

Metinler pygame.font ile değil pygame.freetype ile çizilir: pygame.font,
Ğ/İ/Ö gibi şapkalı büyük harflerin üstünü kırpıyor (G ile Ğ aynı yükseklikte
çıkıyor). freetype glifin gerçek sınırlarını verir.

Çizim yalnızca durum değiştiğinde çağrılır (bkz. main.py olay döngüsü).

İki yerleşim var:
  - tek (serbest mod): basılan harf ekranın ortasında
  - bölünmüş ("Harfi Bul"): solda bulunacak harf, sağda çocuğun bastığı harf
"""

from __future__ import annotations

import math
import random

import pygame
import pygame.freetype

BACKGROUND = (16, 16, 24)
HINT_COLOR = (90, 90, 110)
STATUS_COLOR = (170, 170, 200)
LABEL_COLOR = (120, 120, 145)
TARGET_COLOR = (235, 235, 245)
DIVIDER_COLOR = (48, 48, 62)
STAR_COLOR = (255, 205, 60)
STAR_EMPTY_COLOR = (58, 58, 74)
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
CELEBRATE_MS = 3200  # kutlama ekranının süresi
DEFAULT_STAR_TOTAL = 5


def find_font_path() -> str | None:
    """Sistemde Türkçe destekleyen bir font arar; bulamazsa None döner."""
    if not pygame.font.get_init():
        pygame.font.init()
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


def star_points(center: tuple[float, float], radius: float) -> list[tuple[float, float]]:
    """Beş köşeli yıldızın köşe noktaları.

    Yıldız fontla değil elle çizilir: sistem fontlarında ★ (U+2605) glifi
    çoğu zaman yok ve boş kutu görünüyor.
    """
    cx, cy = center
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5  # tepe noktası yukarı baksın
        r = radius if i % 2 == 0 else radius * 0.42
        points.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    return points


class Renderer:
    def __init__(self, screen: pygame.Surface, font_scale: float = 0.62):
        self.screen = screen
        self.font_scale = font_scale
        self._font_path = find_font_path()
        self._glyph_font = self._make_font(int(screen.get_height() * font_scale))
        self._hint_font = self._make_font(max(14, screen.get_height() // 32))
        self._label_font = self._make_font(max(16, screen.get_height() // 22))

        self.current_char: str | None = None
        self.target_char: str | None = None
        self.split = False           # "Harfi Bul" modunda ekran ikiye ayrılır
        self.labels = ("", "")       # (sol, sağ) başlıklar
        self.status_text = ""        # ayar değişince üstte görünen kısa bilgi
        self.stars = 0
        self.star_total = DEFAULT_STAR_TOTAL
        self.celebrate_text = ""
        self._celebrate_start: int | None = None

        self._color = PALETTE[0]
        self._glyph: pygame.Surface | None = None
        self._target_glyph: pygame.Surface | None = None
        self._anim_start_ms = 0
        self._anim_active = False
        self.exit_progress = 0.0  # ESC basılı tutma göstergesi (0..1)

    # -- font ------------------------------------------------------------
    def _make_font(self, size: int) -> "pygame.freetype.Font":
        if not pygame.freetype.get_init():
            pygame.freetype.init()
        return pygame.freetype.Font(self._font_path, size)

    def set_font_scale(self, scale: float) -> None:
        self.font_scale = scale
        self._glyph_font = self._make_font(int(self.screen.get_height() * scale))
        if self.current_char:
            self._glyph = self._render(self.current_char, self._color)
        if self.target_char:
            self._target_glyph = self._render(self.target_char, TARGET_COLOR)

    def _render(self, char: str, color) -> pygame.Surface:
        return self._glyph_font.render(char, color)[0]

    # -- içerik ----------------------------------------------------------
    def set_status(self, text: str) -> None:
        """Ayar değişikliğini üstte gösterir; sonraki harfte kendiliğinden silinir."""
        self.status_text = text

    def show_char(self, char: str, now_ms: int) -> None:
        """Çocuğun bastığı karakteri gösterir ve giriş animasyonunu başlatır."""
        self.current_char = char
        self.status_text = ""
        self._color = random.choice([c for c in PALETTE if c != self._color])
        self._glyph = self._render(char, self._color)
        self._anim_start_ms = now_ms
        self._anim_active = True

    def clear_char(self) -> None:
        self.current_char = None
        self._glyph = None

    # -- oyun modu göstergeleri ------------------------------------------
    def set_layout(self, split: bool, labels: tuple[str, str] = ("", "")) -> None:
        """Bölünmüş yerleşimi açar/kapatır (Harfi Bul modu)."""
        self.split = split
        self.labels = labels
        if not split:
            self.set_target(None)

    def set_target(self, char: str | None) -> None:
        """Bulunması istenen karakter (solda gösterilir)."""
        self.target_char = char
        self._target_glyph = self._render(char, TARGET_COLOR) if char else None

    def set_stars(self, count: int, total: int | None = None) -> None:
        self.stars = count
        if total:
            self.star_total = total

    def start_celebration(self, text: str, now_ms: int) -> None:
        self.celebrate_text = text
        self._celebrate_start = now_ms

    @property
    def celebrating(self) -> bool:
        return self._celebrate_start is not None

    # -- animasyon -------------------------------------------------------
    @property
    def animating(self) -> bool:
        return self._anim_active or self.celebrating

    def update(self, now_ms: int) -> bool:
        """Animasyon durumunu ilerletir. Hâlâ animasyon varsa True döner."""
        if self._anim_active and now_ms - self._anim_start_ms >= ANIM_DURATION_MS:
            self._anim_active = False
        if (self._celebrate_start is not None
                and now_ms - self._celebrate_start >= CELEBRATE_MS):
            self._celebrate_start = None
            self.celebrate_text = ""
        return self.animating

    def _anim_progress(self, now_ms: int) -> float:
        if not self._anim_active:
            return 1.0
        return min(1.0, max(0.0, (now_ms - self._anim_start_ms) / ANIM_DURATION_MS))

    # -- çizim -----------------------------------------------------------
    def draw(self, now_ms: int) -> None:
        self.screen.fill(BACKGROUND)

        if self.celebrating:
            self._draw_celebration(now_ms)
            pygame.display.flip()
            return

        if self.split:
            self._draw_split(now_ms)
        elif self._glyph is not None:
            self._blit_fitted(self._glyph, self.screen.get_rect(),
                              *self._anim_transform(now_ms))

        self._draw_hint()
        if self.status_text:
            self._draw_status()
        if self.split:
            self._draw_stars()
        if self.exit_progress > 0:
            self._draw_exit_bar()

        pygame.display.flip()

    def _anim_transform(self, now_ms: int) -> tuple[float, int]:
        """Giriş animasyonunun (ölçek, saydamlık) değerleri."""
        t = self._anim_progress(now_ms)
        return 0.45 + 0.55 * _ease_out_back(t), int(255 * min(1.0, t * 2.5))

    def _blit_fitted(self, glyph: pygame.Surface, area: pygame.Rect,
                     scale: float = 1.0, alpha: int = 255,
                     fill: float = 0.75) -> None:
        """Glifi verilen alana sığdırarak ortalar."""
        limit = min(area.width * fill / max(1, glyph.get_width()),
                    area.height * fill / max(1, glyph.get_height()), 1.0)
        size = (max(1, int(glyph.get_width() * limit * scale)),
                max(1, int(glyph.get_height() * limit * scale)))
        surface = pygame.transform.smoothscale(glyph, size)
        if alpha < 255:
            surface = surface.copy()
            surface.set_alpha(alpha)
        self.screen.blit(surface, surface.get_rect(center=area.center))

    def _draw_split(self, now_ms: int) -> None:
        width, height = self.screen.get_size()
        middle = width // 2
        # Harf alanları; alt şerit yıldızlara ve ipucuna ayrılır
        top = int(height * 0.12)
        bottom = int(height * 0.80)
        left_area = pygame.Rect(0, top, middle, bottom - top)
        right_area = pygame.Rect(middle, top, width - middle, bottom - top)

        pygame.draw.line(self.screen, DIVIDER_COLOR,
                         (middle, int(height * 0.08)),
                         (middle, int(height * 0.84)), 2)

        for area, text in zip((left_area, right_area), self.labels):
            if text:
                label = self._label_font.render(text, LABEL_COLOR)[0]
                self.screen.blit(label, label.get_rect(
                    midtop=(area.centerx, int(height * 0.05))))

        if self._target_glyph is not None:
            self._blit_fitted(self._target_glyph, left_area)
        if self._glyph is not None:
            self._blit_fitted(self._glyph, right_area, *self._anim_transform(now_ms))

    def _draw_stars(self) -> None:
        """Kazanılan yıldızlar dolu, kalanlar soluk çizilir."""
        width, height = self.screen.get_size()
        radius = max(10, height // 26)
        gap = radius * 2.6
        total = self.star_total
        start_x = width / 2 - gap * (total - 1) / 2
        y = height - radius - max(34, height // 14)
        for index in range(total):
            center = (start_x + index * gap, y)
            points = star_points(center, radius)
            if index < self.stars:
                pygame.draw.polygon(self.screen, STAR_COLOR, points)
            else:
                pygame.draw.polygon(self.screen, STAR_EMPTY_COLOR, points, 2)

    def _draw_celebration(self, now_ms: int) -> None:
        elapsed = now_ms - (self._celebrate_start or now_ms)
        # Yavaşça nefes alan bir büyüme; ekran sakin kalsın diye küçük genlik
        pulse = 1.0 + 0.06 * math.sin(elapsed / 160.0)
        color = PALETTE[(elapsed // 220) % len(PALETTE)]
        width, height = self.screen.get_size()

        text = self._glyph_font.render(self.celebrate_text, color)[0]
        self._blit_fitted(text, pygame.Rect(0, 0, width, int(height * 0.62)),
                          scale=pulse, fill=0.85)

        radius = max(14, height // 14)
        gap = radius * 2.6
        start_x = width / 2 - gap * (self.stars - 1) / 2
        y = height * 0.78
        for index in range(self.stars):
            pygame.draw.polygon(self.screen, STAR_COLOR,
                                star_points((start_x + index * gap, y),
                                            radius * pulse))

    def _draw_hint(self) -> None:
        text = self._hint_font.render(self._hint_text, HINT_COLOR)[0]
        rect = text.get_rect(midbottom=(self.screen.get_width() // 2,
                                        self.screen.get_height() - 12))
        self.screen.blit(text, rect)

    _hint_text = "ESC (2 sn) veya Ctrl+Q ile çıkış"

    def set_hint(self, text: str) -> None:
        self._hint_text = text

    def _draw_status(self) -> None:
        text = self._hint_font.render(self.status_text, STATUS_COLOR)[0]
        rect = text.get_rect(midtop=(self.screen.get_width() // 2, 12))
        self.screen.blit(text, rect)

    def _draw_exit_bar(self) -> None:
        width = int(self.screen.get_width() * 0.4 * self.exit_progress)
        height = max(6, self.screen.get_height() // 90)
        rect = pygame.Rect(0, 0, width, height)
        rect.midbottom = (self.screen.get_width() // 2,
                          self.screen.get_height() - 12 - self._hint_font.get_sized_height())
        pygame.draw.rect(self.screen, EXIT_BAR_COLOR, rect, border_radius=height // 2)
