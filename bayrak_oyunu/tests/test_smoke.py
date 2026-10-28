"""Ekransız duman testi: her ekran çizilebiliyor mu, sesler yerinde mi."""

import os
import random

import pygame
import pytest

import app.game as G
from app.audio import SFX_DIR, SPEECH_DIR
from app.flags import CODES
from app.progress import Progress
from app.render import VIRTUAL, Renderer
from app.speech import PHRASES, speech_table
from scripts.build_audio import sfx_table


@pytest.fixture(scope="module")
def screen():
    pygame.init()
    surface = pygame.display.set_mode((640, 360))
    yield surface
    pygame.quit()


def make_game(tmp_path, collected=None):
    progress = Progress(collected=collected or ["tr", "jp"],
                        path=tmp_path / "p.json")
    return G.Game(progress, random.Random(3), now=0)


@pytest.mark.parametrize("state", [G.TITLE, G.PLAY, G.WIN, G.BOARD, G.DONE])
def test_her_ekran_cizilir(screen, tmp_path, state):
    renderer = Renderer(screen)
    game = make_game(tmp_path)
    game.state = state
    renderer.draw(game, 1234)
    assert renderer.canvas.get_size() == VIRTUAL


def test_oyun_boyunca_cizim_cokmez(screen, tmp_path):
    renderer = Renderer(screen)
    game = make_game(tmp_path)
    now = 0
    game.start_run(now)
    for _ in range(400):
        now += 33
        game.update(now)
        renderer.draw(game, now)
        if game.is_safe(now):
            game.press_space(now)
    assert game.step >= 1


def test_bos_panoda_da_cizilir(screen, tmp_path):
    renderer = Renderer(screen)
    game = make_game(tmp_path, collected=[])
    for state in (G.TITLE, G.BOARD):
        game.state = state
        renderer.draw(game, 10)


def test_dolu_panoda_da_cizilir(screen, tmp_path):
    renderer = Renderer(screen)
    game = make_game(tmp_path, collected=list(CODES))
    game.state = G.BOARD
    renderer.draw(game, 10)


def test_butun_konusma_dosyalari_uretilmis():
    missing = [key for key in speech_table()
               if not (SPEECH_DIR / f"{key}.wav").exists()]
    assert missing == [], f"eksik ses: {missing[:5]}"


def test_butun_efektler_uretilmis():
    missing = [key for key in sfx_table()
               if not (SFX_DIR / f"{key}.wav").exists()]
    assert missing == []


def test_her_ulkenin_adi_ve_cumlesi_var():
    table = speech_table()
    for code in CODES:
        assert f"name_{code}" in table
        assert f"win_{code}" in table
    assert len(table) == 2 * len(CODES) + len(PHRASES)


def test_self_check_gecer():
    import main
    assert main.self_check() == 0


def test_ses_dosyalari_okunabilir(screen):
    """Mixer dummy sürücüde de wav'ları yükleyebilmeli."""
    from app.audio import Voice, init_mixer
    if not init_mixer():
        pytest.skip("ses aygıtı yok")
    voice = Voice(volume=0.1)
    assert len(voice.sounds) >= len(speech_table())
    assert voice.say_name("tr")
    assert voice.sfx("sfx_hop")
    assert voice.say("yok_boyle_bir_ses") is False


def test_progress_dosyasi_yazilamazsa_cokmez(tmp_path):
    progress = Progress(path=tmp_path / "olmayan" / "alt" / "p.json")
    assert progress.add("tr") is True
    engelli = Progress(path=os.devnull + "/p.json")
    assert engelli.save() is False


def test_main_in_istedigi_her_ses_uretiliyor():
    """main.py'nin çaldığı anahtarlar ses tablolarıyla birebir uyuşmalı.

    Önek unutmak (phrase_praise_1 yerine praise_1) sessizce sessizliğe yol
    açıyordu; bu test onu yakalar.
    """
    import main
    from app.speech import PRAISE_KEYS

    speech = speech_table()
    effects = sfx_table()
    for key in PRAISE_KEYS:
        assert f"phrase_{key}" in speech
    for key in ("intro", "watch", "near", "caught", "board", "all_done"):
        assert f"phrase_{key}" in speech
    for key in main.SFX_FOR_EVENT.values():
        assert key in effects
    assert "sfx_move" in effects


def test_tam_ekran_scaled_istemez(screen):
    """SCALED + (0, 0) bazı SDL sürümlerinde hata veriyordu.

    "Cannot set 0 size SCALED display mode": ölçeklemeyi present() zaten
    kendisi yaptığı için SCALED'a hiç gerek yok.
    """
    import pathlib

    import main

    kaynak = pathlib.Path(main.__file__).read_text(encoding="utf-8")
    assert "pygame.SCALED" not in kaynak
    pencere = main.open_screen(fullscreen=False, size=(640, 360))
    assert pencere.get_size() == (640, 360)
    assert main.open_screen(fullscreen=True, size=(640, 360)) is not None


def test_kucuk_ekranda_da_basilir(screen):
    """Oyun alanından küçük bir ekranda ölçek 1'in altına düşmemeli."""
    kucuk = pygame.display.set_mode((240, 140))
    renderer = Renderer(kucuk)
    game = G.Game(Progress(collected=[], path=os.devnull), random.Random(1), 0)
    renderer.draw(game, 10)
    renderer.present()
    pygame.display.set_mode((640, 360))
