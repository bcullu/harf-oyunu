#!/usr/bin/env python3
"""Masaüstü kısayolu için basit bir ikon üretir (icon.png).

Ek bağımlılık yok: zaten kurulu olan pygame kullanılıyor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pygame.freetype  # noqa: E402

from app.config import PROJECT_ROOT  # noqa: E402
from app.render import BACKGROUND, PALETTE, find_font_path  # noqa: E402

SIZE = 256


def build_icon(dest: Path = PROJECT_ROOT / "icon.png") -> Path:
    pygame.init()
    pygame.freetype.init()
    surface = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pygame.draw.rect(surface, BACKGROUND, (0, 0, SIZE, SIZE), border_radius=48)

    font = pygame.freetype.Font(find_font_path(), int(SIZE * 0.62))
    # "Aa" yerine tek harf: küçük boyutta da okunur kalsın
    glyph, _ = font.render("A", PALETTE[3])
    surface.blit(glyph, glyph.get_rect(center=(SIZE // 2, SIZE // 2)))

    pygame.image.save(surface, str(dest))
    pygame.quit()
    return dest


if __name__ == "__main__":
    print(build_icon())
