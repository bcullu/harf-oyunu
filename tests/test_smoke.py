"""SDL_VIDEODRIVER=dummy ile ekransız duman testi (bkz. conftest.py)."""

import pygame
import pytest

import main as main_module
from main import TICK_EVENT, App


@pytest.fixture
def app():
    pygame.init()
    instance = App(lang_code="tr", fullscreen=False, size=(640, 480))
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


def test_self_check_passes():
    assert main_module.self_check() == 0
