#!/usr/bin/env python3
"""Bayrak Hırsızı — 5 yaş için bayrak öğrenme oyunu.

Örümcek bekçi bayrağı koruyor. Sırtını döndüğü anda boşluk tuşuna basarak
bir sonraki saklanma noktasına geç; beş doğru basışta bayrak senin olur.
Kazanılan bayrak Türkçe seslendirilir ve panoya eklenir; bir sonraki
oyunda o bayrak çıkmaz. Amaç 50 bayrağın hepsini toplamak.

Tek tuş: BOŞLUK. Okuma yazma gerekmez.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if "--self-check" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from app import game as G  # noqa: E402
from app.audio import Voice, init_mixer  # noqa: E402
from app.flags import CODES  # noqa: E402
from app.progress import Progress  # noqa: E402
from app.render import Renderer  # noqa: E402
from app.speech import PRAISE_KEYS  # noqa: E402

FPS = 30
ESC_HOLD_MS = 2000      # çocuk yanlışlıkla kapatamasın
VOLUME_STEP = 0.1
BOARD_COLUMNS = 10

VOLUME_UP_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
VOLUME_DOWN_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)

# Oyun olayı -> çalınacak ses
SFX_FOR_EVENT = {
    G.EV_SAFE: "sfx_safe",
    G.EV_DANGER: "sfx_danger",
    G.EV_HOP: "sfx_hop",
    G.EV_CAUGHT: "sfx_caught",
    G.EV_GRAB: "sfx_win",
    G.EV_BOARD: "sfx_pop",
}


def open_screen(fullscreen: bool, size=(1280, 720)) -> "pygame.Surface":
    """Pencereyi açar; açamazsa daha güvenli bir kipe düşer.

    SCALED kullanılmıyor: ölçeklemeyi Renderer.present() zaten tam sayı
    katıyla kendisi yapıyor ve bazı SDL/pygame sürümleri SCALED ile (0, 0)
    boyutunu reddedip "Cannot set 0 size SCALED display mode" diyor.
    """
    if not fullscreen:
        return pygame.display.set_mode(size)
    try:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    except pygame.error:
        pass
    info = pygame.display.Info()          # masaüstü çözünürlüğünü açıkça ver
    desktop = (info.current_w, info.current_h)
    if desktop[0] > 0 and desktop[1] > 0:
        try:
            return pygame.display.set_mode(desktop, pygame.FULLSCREEN)
        except pygame.error:
            pass
    return pygame.display.set_mode(size)  # son çare: pencerede çalış


class App:
    def __init__(self, fullscreen: bool = True, size=(1280, 720),
                 seed: int | None = None):
        self.progress = Progress.load()
        self.screen = open_screen(fullscreen, size)
        pygame.display.set_caption("Bayrak Hırsızı")
        pygame.mouse.set_visible(False)

        self.renderer = Renderer(self.screen)
        self.voice = Voice(volume=self.progress.volume)
        self.rng = random.Random(seed)
        self.game = G.Game(self.progress, self.rng, pygame.time.get_ticks())

        self.running = True
        self._esc_down_at: int | None = None
        self._praise_turn = 0
        self.voice.say("phrase_intro")

    # -- olaylar ---------------------------------------------------------
    def handle_event(self, event, now: int) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            self._keydown(event, now)
        elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
            self._esc_down_at = None

    def _keydown(self, event, now: int) -> None:
        if event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
            self.running = False
            return
        if event.key == pygame.K_ESCAPE:
            if self._esc_down_at is None:
                self._esc_down_at = now
            return
        if event.key in VOLUME_UP_KEYS:
            self.voice.set_volume(self.progress.change_volume(VOLUME_STEP))
            self.voice.sfx("sfx_move")
            return
        if event.key in VOLUME_DOWN_KEYS:
            self.voice.set_volume(self.progress.change_volume(-VOLUME_STEP))
            self.voice.sfx("sfx_move")
            return

        if event.key == pygame.K_SPACE:
            before = self.game.state
            self._play_events(self.game.press_space(now))
            if before != self.game.state:
                self._on_state_change(before, self.game.state)
            return

        if event.key == pygame.K_b and self.game.state in (G.TITLE, G.WIN):
            self.renderer.reset_confetti()
            self._play_events(self.game.show_board())
            return

        if self.game.state == G.BOARD:
            delta = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                     pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}.get(event.key)
            if delta and self.game.move_board(*delta, columns=BOARD_COLUMNS):
                code = self.game.board_code()
                if self.progress.has(code):
                    self.voice.say_name(code)   # bayrağa bakarken adını duy
                else:
                    self.voice.sfx("sfx_move")

    def _on_state_change(self, before: str, after: str) -> None:
        if after == G.TITLE:
            self.voice.say("phrase_intro")
        elif after == G.BOARD:
            self.renderer.reset_confetti()

    # -- ses -------------------------------------------------------------
    def _play_events(self, events) -> None:
        for name in events:
            sfx = SFX_FOR_EVENT.get(name)
            if sfx:
                self.voice.sfx(sfx)
            if name == G.EV_START:
                self.voice.say("phrase_watch")
            elif name == G.EV_HOP:
                self._praise_turn += 1
                if self.game.step < G.STEPS_TO_WIN - 1 and self._praise_turn % 2:
                    key = PRAISE_KEYS[self._praise_turn % len(PRAISE_KEYS)]
                    self.voice.say(f"phrase_{key}")
            elif name == G.EV_NEAR:
                self.voice.say("phrase_near")
            elif name == G.EV_CAUGHT:
                self.voice.say("phrase_caught")
            elif name == G.EV_WIN:
                self.voice.say_win(self.game.code)
            elif name == G.EV_BOARD:
                self.voice.say("phrase_board")
            elif name == G.EV_ALL_DONE:
                self.voice.say("phrase_all_done")

    # -- döngü -----------------------------------------------------------
    def run(self) -> None:
        clock = pygame.time.Clock()
        while self.running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                self.handle_event(event, now)
            if self._esc_down_at is not None and now - self._esc_down_at >= ESC_HOLD_MS:
                self.running = False
            self._play_events(self.game.update(now))
            self.renderer.draw(self.game, now)
            self._draw_exit_bar(now)
            self.renderer.present()
            clock.tick(FPS)

    def _draw_exit_bar(self, now: int) -> None:
        """ESC basılı tutulurken ilerleyen çubuk (ebeveyn çıkışı)."""
        if self._esc_down_at is None:
            return
        ratio = min(1.0, (now - self._esc_down_at) / ESC_HOLD_MS)
        width = int(self.screen.get_width() * ratio)
        pygame.draw.rect(self.screen, (230, 90, 90),
                         (0, self.screen.get_height() - 4, width, 4))
        pygame.display.update((0, self.screen.get_height() - 4,
                               self.screen.get_width(), 4))


def self_check() -> int:
    """Pencere açmadan her ekranı bir kez çizer ve sesleri sayar."""
    pygame.init()
    init_mixer()
    screen = pygame.display.set_mode((640, 360))
    progress = Progress(collected=CODES[:3], path=Path(os.devnull))
    renderer = Renderer(screen)
    game = G.Game(progress, random.Random(1), 0)
    voice = Voice(volume=0.5)

    problems: list[str] = []
    now = 0
    for state in (G.TITLE, G.PLAY, G.WIN, G.BOARD, G.DONE):
        game.state = state
        try:
            renderer.draw(game, now)
        except Exception as exc:  # çizim hatası kuruluma takılsın
            problems.append(f"{state} çizilemedi: {exc}")
        now += 500

    from app.speech import speech_table
    from scripts.build_audio import sfx_table
    missing = [k for k in list(speech_table()) + list(sfx_table())
               if k not in voice.sounds]
    if missing and voice.enabled:
        problems.append(f"{len(missing)} ses dosyası eksik "
                        f"(scripts/build_audio.py çalıştırın)")

    # beş doğru basışta kazanılıyor mu
    game = G.Game(progress, random.Random(2), 0)
    t = 0
    game.start_run(t)
    for _ in range(G.STEPS_TO_WIN):
        game.update(t)
        moment = game.cycle_start + G.DANGER_MS + 50   # güvenli pencerenin içi
        if moment <= t:                                # bu turun penceresi geçti
            moment += game.cycle_ms
        t = moment
        game.press_space(t)
        t += G.HOP_MS + G.GRAB_MS + 50
        game.update(t)
    if game.state != G.WIN:
        problems.append(f"beş doğru basışta kazanılmadı (durum={game.state})")

    pygame.quit()
    for line in problems:
        print("SORUN:", line)
    if not problems:
        print("Her şey yolunda: 50 bayrak, çizim ve zamanlama çalışıyor.")
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windowed", action="store_true",
                        help="tam ekran yerine pencerede çalıştır")
    parser.add_argument("--self-check", action="store_true",
                        help="kurulumu doğrula, pencere açma")
    parser.add_argument("--reset", action="store_true",
                        help="toplanan bayrakları sıfırla")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    if args.self_check:
        return self_check()
    if args.reset:
        progress = Progress.load()
        progress.reset()
        print("Bayrak panosu sıfırlandı.")
        return 0

    pygame.init()
    init_mixer()
    app = App(fullscreen=not args.windowed, seed=args.seed)
    try:
        app.run()
    finally:
        app.progress.save()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
