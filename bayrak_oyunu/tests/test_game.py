"""Oyun mantığı: devriye ritmi, zamanlama, yakalanma ve kazanma."""

import random

import app.game as G
from app.progress import Progress


def make_game(tmp_path, collected=None, seed=1):
    progress = Progress(collected=collected or [], path=tmp_path / "p.json")
    return G.Game(progress, random.Random(seed), now=0)


def test_bes_adimda_kazanilir(tmp_path):
    assert G.STEPS_TO_WIN == 5


def test_devriye_once_tehlike_sonra_guvenli(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    assert not game.is_safe(0)
    assert not game.is_safe(G.DANGER_MS - 1)
    assert game.is_safe(G.DANGER_MS)
    assert game.is_safe(G.DANGER_MS + game.safe_ms - 1)


def test_devriye_dongusu_tekrar_eder(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    cycle = game.cycle_ms
    game.update(cycle + 10)
    assert not game.is_safe(cycle + 10)      # yeni tur yine tehlikeyle başlar
    assert game.direction == -1              # örümcek ters yöne yürür


def test_guvenli_anda_basinca_bir_adim_ilerler(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    events = game.press_space(G.DANGER_MS + 100)
    assert G.EV_HOP in events
    assert game.step == 1


def test_tehlikede_basinca_yakalanir(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    game.press_space(G.DANGER_MS + 100)                  # 1. adım
    now = game.cycle_ms + 100                            # yeni turun tehlikesi
    game.update(now)
    events = game.press_space(now)
    assert G.EV_CAUGHT in events
    assert game.step == 0                                 # bir adım geri


def test_baslangicta_yakalanmak_geri_atmaz(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    game.press_space(100)
    assert game.step == 0


def test_animasyon_sirasinda_tus_yok_sayilir(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    game.press_space(G.DANGER_MS + 50)
    assert game.press_space(G.DANGER_MS + 100) == []      # sıçrama sürüyor
    assert game.step == 1


def next_safe_moment(game, now: int) -> int:
    """Şu andan sonraki ilk güvenli pencerenin ortasına atlar."""
    game.update(now)
    moment = game.cycle_start + G.DANGER_MS + 50
    if moment <= now:
        moment = game.cycle_start + game.cycle_ms + G.DANGER_MS + 50
    return moment


def play_until_win(game):
    now = 0
    game.start_run(now)
    while game.step < G.STEPS_TO_WIN:
        now = next_safe_moment(game, now)
        game.press_space(now)
        now += G.HOP_MS + 50
        game.update(now)
    now += G.GRAB_MS + 50
    return now, game.update(now)


def test_bes_dogru_basista_kazanir(tmp_path):
    game = make_game(tmp_path)
    _, events = play_until_win(game)
    assert G.EV_WIN in events
    assert game.state == G.WIN


def test_kazanilan_bayrak_panoya_eklenir(tmp_path):
    game = make_game(tmp_path)
    code = game.code
    play_until_win(game)
    assert game.progress.has(code)
    assert game.new_code == code


def test_sonraki_oyun_farkli_bayrak_verir(tmp_path):
    game = make_game(tmp_path)
    first = game.code
    now, _ = play_until_win(game)
    game.show_board()
    game.next_round(now)
    assert game.state == G.TITLE
    assert game.code != first


def test_son_bayraktan_sonra_kutlama(tmp_path):
    from app.flags import CODES
    game = make_game(tmp_path, collected=CODES[:-1])
    now, _ = play_until_win(game)
    game.show_board()
    events = game.next_round(now)
    assert G.EV_ALL_DONE in events
    assert game.state == G.DONE


def test_guvenli_pencere_adimla_daralir_ama_tabani_var(tmp_path):
    from app.flags import CODES
    game = make_game(tmp_path)
    game.start_run(0)
    first = game.safe_ms
    game.step = 4
    game.safe_ms = game._safe_window()
    assert game.safe_ms < first
    game.progress.collected = list(CODES)
    assert game._safe_window() >= G.SAFE_MIN


def test_oyuncu_sicrama_sirasinda_iki_nokta_arasinda(tmp_path):
    game = make_game(tmp_path)
    game.start_run(0)
    game.press_space(G.DANGER_MS + 100)
    mid = G.DANGER_MS + 100 + G.HOP_MS // 2
    tx, ty, lift = game.player_pos(mid)
    ax, ay, _ = G.SPOTS[0]
    bx, by, _ = G.SPOTS[1]
    assert min(ax, bx) <= tx <= max(ax, bx)
    assert min(ay, by) <= ty <= max(ay, by)
    assert lift > 0.5                       # havada


def test_bosluk_ekranlar_arasinda_dolastirir(tmp_path):
    game = make_game(tmp_path)
    assert game.state == G.TITLE
    game.press_space(0)
    assert game.state == G.PLAY
    now, _ = play_until_win(game)
    game.press_space(now)
    assert game.state == G.BOARD
    game.press_space(now)
    assert game.state == G.TITLE


def test_pano_secimi_sinirlar_icinde(tmp_path):
    from app.flags import CODES
    game = make_game(tmp_path)
    game.show_board()
    game.board_index = 0
    assert game.move_board(-1, 0) is False
    game.board_index = len(CODES) - 1
    assert game.move_board(1, 0) is False
    assert game.board_code() == CODES[-1]
