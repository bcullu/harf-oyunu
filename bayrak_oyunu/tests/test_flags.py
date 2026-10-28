"""Bayrak verisi ve çizimi."""

import pygame
import pytest

from app import flags


def test_elli_bayrak_var():
    assert len(flags.FLAGS) == 50


def test_kodlar_benzersiz():
    assert len(set(flags.CODES)) == len(flags.CODES)


def test_adlar_turkce_ve_dolu():
    for code, name, _ in flags.FLAGS:
        assert name.strip(), code
        assert name[0].isupper() or name[0] in "İÇŞÖÜĞ", name


def test_her_bayrak_cizilebiliyor():
    pygame.init()
    surf = pygame.Surface((64, 44))
    for code in flags.CODES:
        surf.fill((0, 0, 0))
        flags.draw_flag(surf, pygame.Rect(2, 2, 60, 40), code)
        # en az birkaç piksel boyanmış olmalı
        assert surf.get_at((30, 20))[:3] != (0, 0, 0), code


def test_cok_kucuk_kutuda_cokmez():
    pygame.init()
    surf = pygame.Surface((8, 8))
    for code in flags.CODES:
        flags.draw_flag(surf, pygame.Rect(0, 0, 6, 4), code)


def test_bilinmeyen_kod_gri_kutu():
    pygame.init()
    surf = pygame.Surface((20, 20))
    flags.draw_flag(surf, pygame.Rect(0, 0, 20, 14), "zz")
    assert surf.get_at((10, 7))[:3] == flags.GREY


def test_cizim_kutunun_disina_tasmaz():
    pygame.init()
    surf = pygame.Surface((60, 60))
    surf.fill((0, 0, 0))
    flags.draw_flag(surf, pygame.Rect(20, 20, 24, 16), "au")
    assert surf.get_at((2, 2))[:3] == (0, 0, 0)
    assert surf.get_at((55, 55))[:3] == (0, 0, 0)


@pytest.mark.parametrize("code", ["tr", "jp", "us"])
def test_flag_surface_boyutu(code):
    pygame.init()
    surf = flags.flag_surface(code, (30, 20))
    assert surf.get_size() == (30, 20)
