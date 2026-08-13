"""SDL_VIDEODRIVER=dummy ile ekransız duman testi (bkz. conftest.py)."""

import pygame
import pytest

import main as main_module
from app.config import CHAR_SETS, Config
from app.game_modes import STARS_TO_WIN, FindLetterMode
from main import TICK_EVENT, App


@pytest.fixture
def app(tmp_path):
    pygame.init()
    config = Config(path=tmp_path / "config.json")
    instance = App(config=config, lang_code="tr", fullscreen=False, size=(640, 480))
    yield instance
    pygame.quit()


def key_event(unicode_char="", key=0, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode_char, mod=mod)


def test_window_opens(app):
    assert app.screen.get_size() == (640, 480)
    assert app.running is True


@pytest.mark.parametrize("typed,expected", [
    ("ğ", "Ğ"), ("i", "İ"), ("ı", "I"), ("ç", "Ç"), ("ş", "Ş"),
    ("ö", "Ö"), ("ü", "Ü"), ("a", "A"), ("7", "7"),
])
def test_keypress_shows_uppercase_char(app, typed, expected):
    app.handle_event(key_event(typed))
    assert app.renderer.current_char == expected
    app.draw_if_dirty()  # çizim hata vermemeli


def test_unknown_char_ignored(app):
    app.handle_event(key_event("A"))
    app.handle_event(key_event("@"))
    assert app.renderer.current_char == "A"


def test_ctrl_q_quits(app):
    app.handle_event(key_event("q", key=pygame.K_q, mod=pygame.KMOD_CTRL))
    assert app.running is False


def test_plain_q_does_not_quit(app):
    app.handle_event(key_event("q", key=pygame.K_q))
    assert app.running is True


def test_escape_requires_two_seconds(app, monkeypatch):
    now = [10_000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                        unicode="\x1b", mod=0))
    now[0] += 1000
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert app.running is True
    assert 0 < app.renderer.exit_progress < 1

    now[0] += 1100
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert app.running is False


def test_escape_release_cancels_exit(app, monkeypatch):
    now = [10_000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                        unicode="\x1b", mod=0))
    now[0] += 1500
    app.handle_event(pygame.event.Event(TICK_EVENT))
    app.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE, mod=0))
    assert app.renderer.exit_progress == 0.0

    now[0] += 5000
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert app.running is True


def test_timer_only_runs_during_animation(app, monkeypatch):
    calls = []
    monkeypatch.setattr(pygame.time, "set_timer",
                        lambda evt, ms, **kw: calls.append(ms))
    now = [5000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])

    app._sync_timer()
    assert calls == []  # boşta zamanlayıcı yok

    app.handle_event(key_event("a"))
    app._sync_timer()
    assert calls[-1] == 33  # animasyon başlayınca açıldı

    now[0] += 500  # animasyon süresi dolsun
    app.handle_event(pygame.event.Event(TICK_EVENT))
    app._sync_timer()
    assert calls[-1] == 0  # animasyon bitince kapandı


def test_sound_plays_after_animation(app, monkeypatch):
    played = []
    monkeypatch.setattr(app.voice, "play", lambda key: played.append(key) or True)
    now = [5000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])

    app.handle_event(key_event("ğ"))
    assert played == []  # animasyon sürerken ses yok
    assert app._pending_sound == "char_011e"

    now[0] += 500
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert played == ["char_011e"]  # animasyon bitince çaldı

    now[0] += 500
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert played == ["char_011e"]  # tekrar çalmaz


# --- ebeveyn ayarları (M3) ---------------------------------------------------

def fkey(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode="", mod=0)


def test_f1_switches_language_and_persists(app):
    assert app.lang.code == "tr"
    app.handle_event(fkey(pygame.K_F1))
    assert app.lang.code == "en"
    # ayar diske yazıldı mı
    assert Config.load(app.config.path).language == "en"
    # İngilizce harfler kabul edilmeli, Türkçeye özgü olanlar değil
    app.handle_event(key_event("w"))
    assert app.renderer.current_char == "W"
    app.handle_event(key_event("ğ"))
    assert app.renderer.current_char == "W"  # değişmedi


def test_language_switch_reloads_sounds(app):
    app.handle_event(fkey(pygame.K_F1))
    assert app.voice.lang_code == "en"
    app.handle_event(fkey(pygame.K_F1))
    assert app.voice.lang_code == "tr"


def test_english_uses_ascii_upper_not_turkish(app):
    app.handle_event(fkey(pygame.K_F1))  # -> en
    app.handle_event(key_event("i"))
    assert app.renderer.current_char == "I"  # Türkçede İ olurdu


def test_f3_cycles_char_set(app):
    seen = []
    for _ in CHAR_SETS:
        app.handle_event(fkey(pygame.K_F3))
        seen.append(app.config.char_set)
    assert set(seen) == set(CHAR_SETS)


def test_char_set_digits_only_rejects_letters(app):
    while app.config.char_set != "digits":
        app.handle_event(fkey(pygame.K_F3))
    app.handle_event(key_event("7"))
    assert app.renderer.current_char == "7"
    app.handle_event(key_event("a"))
    assert app.renderer.current_char == "7"  # harf kabul edilmedi


def test_f4_changes_font_scale(app):
    before = app.config.font_scale
    app.handle_event(fkey(pygame.K_F4))
    assert app.config.font_scale != before
    assert app.renderer.font_scale == app.config.font_scale
    app.draw_if_dirty()  # yeni boyutla çizim hata vermemeli


def test_volume_keys_change_and_persist(app, monkeypatch):
    app.config.volume = 0.5
    app.handle_event(fkey(pygame.K_PLUS))
    assert app.config.volume == 0.6
    app.handle_event(fkey(pygame.K_MINUS))
    app.handle_event(fkey(pygame.K_MINUS))
    assert app.config.volume == 0.4
    assert Config.load(app.config.path).volume == 0.4


def test_settings_show_status_and_clear_on_next_letter(app):
    app.handle_event(fkey(pygame.K_F4))
    assert app.renderer.status_text
    app.handle_event(key_event("a"))
    assert app.renderer.status_text == ""


def test_settings_keys_do_not_start_animation_timer(app, monkeypatch):
    # Ayar tuşları harf göstermez, dolayısıyla zamanlayıcı da açılmamalı
    calls = []
    monkeypatch.setattr(pygame.time, "set_timer", lambda evt, ms, **kw: calls.append(ms))
    app.handle_event(fkey(pygame.K_F3))
    app._sync_timer()
    assert calls == []


def test_config_survives_restart(app, tmp_path):
    app.handle_event(fkey(pygame.K_F1))
    app.handle_event(fkey(pygame.K_F3))
    saved = app.config.as_dict()
    restarted = App(config=Config.load(app.config.path), fullscreen=False,
                    size=(320, 240))
    assert restarted.config.as_dict() == saved
    assert restarted.lang.code == saved["language"]


# --- oyun modu (M4) ----------------------------------------------------------

def enter_find_mode(app):
    """F2 ile 'Harfi Bul' moduna geçer."""
    while not isinstance(app.mode, FindLetterMode):
        app.handle_event(fkey(pygame.K_F2))
    return app.mode


def test_f2_switches_between_modes(app):
    assert app.mode.name == "free"
    app.handle_event(fkey(pygame.K_F2))
    assert app.mode.name == "find"
    app.handle_event(fkey(pygame.K_F2))
    assert app.mode.name == "free"


def test_entering_find_mode_asks_for_a_letter(app):
    mode = enter_find_mode(app)
    assert mode.target in app.allowed
    assert mode.target in app.renderer.prompt_text
    app.draw_if_dirty()


def test_correct_answer_awards_star(app):
    mode = enter_find_mode(app)
    app.handle_event(key_event(mode.target))
    assert app.renderer.stars == 1


def test_wrong_answer_costs_nothing(app):
    mode = enter_find_mode(app)
    target = mode.target
    wrong = next(c for c in app.allowed if c != target and c.isalpha())
    app.handle_event(key_event(wrong))
    assert app.renderer.stars == 0
    assert app.mode.target == target        # hedef korunur
    assert app.renderer.current_char == wrong  # basılan harf yine de görünür


def test_five_stars_show_celebration_then_reset(app, monkeypatch):
    now = [1000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
    mode = enter_find_mode(app)
    for _ in range(STARS_TO_WIN):
        app.handle_event(key_event(mode.target))
    assert app.renderer.celebrating
    assert app.renderer.stars == STARS_TO_WIN
    app.draw_if_dirty()  # kutlama ekranı çizilebilmeli

    now[0] += 5000  # kutlama süresi dolsun
    app.handle_event(pygame.event.Event(TICK_EVENT))
    assert not app.renderer.celebrating
    assert app.renderer.stars == 0
    assert app.mode.target in app.allowed  # yeni tur başladı


def test_keys_ignored_during_celebration(app, monkeypatch):
    now = [1000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
    mode = enter_find_mode(app)
    for _ in range(STARS_TO_WIN):
        app.handle_event(key_event(mode.target))
    app.handle_event(key_event("a"))
    assert app.renderer.celebrating  # kutlama bozulmadı


def test_celebration_keeps_timer_running(app, monkeypatch):
    now = [1000]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
    mode = enter_find_mode(app)
    for _ in range(STARS_TO_WIN):
        app.handle_event(key_event(mode.target))
    assert app._needs_tick() is True


def test_free_mode_has_no_prompt_or_stars(app):
    app.handle_event(key_event("a"))
    assert app.renderer.prompt_text == ""
    assert app.renderer.stars == 0


def test_switching_mode_clears_game_state(app):
    mode = enter_find_mode(app)
    app.handle_event(key_event(mode.target))
    app.handle_event(fkey(pygame.K_F2))  # serbest moda dön
    assert app.renderer.stars == 0
    assert app.renderer.prompt_text == ""


def test_char_set_change_gives_target_from_new_set(app):
    enter_find_mode(app)
    while app.config.char_set != "digits":
        app.handle_event(fkey(pygame.K_F3))
    assert app.mode.target in set("0123456789")


def test_sound_queue_runs_dry_and_stops_its_timer(app):
    enter_find_mode(app)
    assert app._needs_audio_tick() is True   # hedef anonsu kuyrukta
    app._sound_queue.clear()
    assert app._needs_audio_tick() is False  # kuyruk boşalınca zamanlayıcı kapanır


def test_self_check_passes():
    assert main_module.self_check() == 0
