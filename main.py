#!/usr/bin/env python3
"""Harf Oyunu — 5 yaş için harf ve rakam tanıma oyunu.

Olay güdümlü döngü: pygame.event.wait() ile bloklanır, olay yokken CPU ~%0.
Animasyon sırasında (ve yalnızca o sırada) 30 FPS'lik bir zamanlayıcı açılır.
"""

from __future__ import annotations

import argparse
import os
import sys

# --self-check modunda pencere/ses açılmaması için sürücüleri pygame'den önce ayarla
if "--self-check" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from app.audio import Voice, init_mixer, sound_key  # noqa: E402
from app.config import load_language  # noqa: E402
from app.render import Renderer  # noqa: E402
from app.text_tr import upper_for_lang  # noqa: E402

TICK_EVENT = pygame.USEREVENT + 1
TICK_MS = 33  # ~30 FPS, sadece animasyon/geri sayım sırasında
ESC_HOLD_MS = 2000  # çocuk yanlışlıkla kapatmasın diye basılı tutma süresi


class App:
    def __init__(self, lang_code: str = "tr", fullscreen: bool = True,
                 char_set: str = "both", size: tuple[int, int] = (960, 600),
                 volume: float = 0.9):
        self.lang = load_language(lang_code)
        self.char_set = char_set
        self.allowed = set(self.lang.charset(char_set))

        flags = pygame.FULLSCREEN if fullscreen else 0
        screen_size = (0, 0) if fullscreen else size
        self.screen = pygame.display.set_mode(screen_size, flags)
        pygame.display.set_caption("Harf Oyunu")
        pygame.mouse.set_visible(False)

        self.renderer = Renderer(self.screen)
        self.renderer.set_hint(self.lang.ui.get("exit_hint", ""))

        # Sesler önceden üretilmiş wav'lardan gelir; yoksa oyun sessiz çalışır
        self.voice = Voice(lang_code, volume=volume)

        self.running = True
        self.dirty = True
        self._esc_down_at: int | None = None
        self._timer_on = False
        self._pending_sound: str | None = None

    # -- olay işleme -----------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        now = pygame.time.get_ticks()

        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == TICK_EVENT:
            was_animating = self.renderer.animating
            self.renderer.update(now)
            # Ses, giriş animasyonu bittikten sonra çalar (önce görüntü, sonra ses)
            if was_animating and not self.renderer.animating:
                self._flush_pending_sound()
            if self._esc_down_at is not None:
                held = now - self._esc_down_at
                self.renderer.exit_progress = min(1.0, held / ESC_HOLD_MS)
                if held >= ESC_HOLD_MS:
                    self.running = False
            self.dirty = True

        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event, now)

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_ESCAPE:
                self._esc_down_at = None
                self.renderer.exit_progress = 0.0
                self.dirty = True

    def _handle_keydown(self, event: pygame.event.Event, now: int) -> None:
        # Ctrl+Q: ebeveyn için anında çıkış
        if event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
            self.running = False
            return

        if event.key == pygame.K_ESCAPE:
            if self._esc_down_at is None:
                self._esc_down_at = now
                self.dirty = True
            return

        # Türkçe Q klavyede ğ/ü/ş/i/ö/ç doğru gelsin diye event.key değil unicode
        char = getattr(event, "unicode", "") or ""
        if not char or not char.isprintable() or char.isspace():
            return
        upper = upper_for_lang(char, self.lang.code)
        if upper in self.allowed:
            self.voice.stop()  # önceki ses kesilsin, üst üste binmesin
            self.renderer.show_char(upper, now)
            self._pending_sound = sound_key(upper)
            self.dirty = True

    # -- ses -------------------------------------------------------------
    def _flush_pending_sound(self) -> None:
        if self._pending_sound is not None:
            self.voice.play(self._pending_sound)
            self._pending_sound = None

    # -- zamanlayıcı -----------------------------------------------------
    def _needs_tick(self) -> bool:
        return self.renderer.animating or self._esc_down_at is not None

    def _sync_timer(self) -> None:
        """Zamanlayıcıyı yalnızca gerektiğinde açık tutar (boşta CPU ~%0)."""
        need = self._needs_tick()
        if need != self._timer_on:
            pygame.time.set_timer(TICK_EVENT, TICK_MS if need else 0)
            self._timer_on = need

    # -- döngü -----------------------------------------------------------
    def draw_if_dirty(self) -> None:
        if self.dirty:
            self.renderer.draw(pygame.time.get_ticks())
            self.dirty = False

    def run(self) -> None:
        self.draw_if_dirty()
        self._sync_timer()
        while self.running:
            event = pygame.event.wait()  # olay yokken uyur, CPU harcamaz
            self.handle_event(event)
            self.draw_if_dirty()
            self._sync_timer()


def self_check() -> int:
    """Başlatma + sentetik tuş olaylarıyla temel akışı doğrular."""
    init_mixer()
    pygame.init()
    app = App(lang_code="tr", fullscreen=False, size=(640, 480))
    cases = [("ğ", "Ğ"), ("i", "İ"), ("ı", "I"), ("5", "5"), ("ş", "Ş")]
    for typed, expected in cases:
        app.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=0, unicode=typed, mod=0))
        app.draw_if_dirty()
        if app.renderer.current_char != expected:
            print(f"HATA: '{typed}' -> {app.renderer.current_char!r}, "
                  f"beklenen {expected!r}")
            return 1

    # Ctrl+Q çıkışı
    app.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_q, unicode="q", mod=pygame.KMOD_CTRL))
    if app.running:
        print("HATA: Ctrl+Q ile çıkılmadı")
        return 1

    # Ses varlığı: eksikse uyar ama başarısız sayma (sesler ayrı üretiliyor)
    missing = [ch for ch in app.lang.charset("both")
               if sound_key(ch) not in app.voice.sounds]
    if missing:
        print(f"UYARI: {len(missing)} karakterin sesi yok "
              f"(ör. {' '.join(missing[:5])}). Çözüm: "
              f"python scripts/build_audio.py")
    else:
        print(f"ses OK: {len(app.voice.sounds)} wav yüklendi ({app.lang.code})")

    pygame.quit()
    print("self-check OK: " + ", ".join(f"{t}->{e}" for t, e in cases))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harf Oyunu")
    parser.add_argument("--self-check", action="store_true",
                        help="Ekransız doğrulama çalıştır ve çık")
    parser.add_argument("--windowed", action="store_true",
                        help="Tam ekran yerine pencerede aç (geliştirme için)")
    parser.add_argument("--lang", default="tr", choices=("tr", "en"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_check:
        return self_check()

    init_mixer()  # pygame.init()'ten önce: tampon boyutu gecikmeyi belirler
    pygame.init()
    try:
        App(lang_code=args.lang, fullscreen=not args.windowed).run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
