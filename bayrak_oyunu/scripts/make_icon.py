#!/usr/bin/env python3
"""Masaüstü kısayolu için ikon üretir (icon.png).

Ek bağımlılık yok: oyunun kendi bayrak çizimi kullanılıyor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from app.flags import draw_flag  # noqa: E402
from app.progress import PROJECT_ROOT  # noqa: E402

SIZE = 256


def build_icon(dest: Path = PROJECT_ROOT / "icon.png") -> Path:
    pygame.init()
    # Önce küçük çiz, sonra komşu-piksel ile büyüt: ikon da pixel art olsun
    small = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.rect(small, (26, 22, 44), (0, 0, 64, 64), border_radius=12)
    draw_flag(small, pygame.Rect(8, 18, 48, 32), "tr")
    # örümcek ağı köşesi: oyunun bekçisine gönderme
    for radius in (14, 22, 30):
        pygame.draw.circle(small, (236, 240, 248), (0, 0), radius, 1)
    for angle in range(0, 50, 12):
        pygame.draw.line(small, (236, 240, 248), (0, 0),
                         (34, angle), 1)
    icon = pygame.transform.scale(small, (SIZE, SIZE))
    pygame.image.save(icon, str(dest))
    pygame.quit()
    return dest


if __name__ == "__main__":
    print(build_icon())
