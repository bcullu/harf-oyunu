#!/usr/bin/env python3
"""Harf Oyunu — 5 yaş için harf ve rakam tanıma oyunu.

Olay güdümlü döngü: pygame.event.wait() ile bloklanır, olay yokken CPU ~%0.
Animasyon sırasında (ve yalnızca o sırada) 30 FPS'lik bir zamanlayıcı açılır.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# --self-check modunda pencere/ses açılmaması için sürücüleri pygame'den önce ayarla
if "--self-check" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from app.audio import Voice, init_mixer, phrase_key, sound_key  # noqa: E402
from app.config import VOLUME_STEP, Config, load_language  # noqa: E402
from app.game_modes import (CELEBRATE, CORRECT, PROMPT, SAY, SHOW,  # noqa: E402
                            STAR, STARS_TO_WIN, WRONG, Action,
                            build_modes)
from app.render import Renderer  # noqa: E402
from app.text_tr import upper_for_lang  # noqa: E402

TICK_EVENT = pygame.USEREVENT + 1
TICK_MS = 33  # ~30 FPS, sadece animasyon/geri sayım sırasında
AUDIO_EVENT = pygame.USEREVENT + 2
AUDIO_TICK_MS = 120  # ses kuyruğu yoklaması, sadece kuyrukta ses varken
ESC_HOLD_MS = 2000  # çocuk yanlışlıkla kapatmasın diye basılı tutma süresi

# Ses seviyesi tuşları (klavye üstü ve numpad)
VOLUME_UP_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
VOLUME_DOWN_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)


class App:
    def __init__(self, config: Config | None = None, lang_code: str | None = None,
                 fullscreen: bool = True, size: tuple[int, int] = (960, 600)):
        self.config = config if config is not None else Config()
        if lang_code:  # --lang, config.json'daki dili geçersiz kılar
            self.config.language = lang_code
        self.lang = load_language(self.config.language)
        self.allowed = set(self.lang.charset(self.config.char_set))

        flags = pygame.FULLSCREEN if fullscreen else 0
        screen_size = (0, 0) if fullscreen else size
        self.screen = pygame.display.set_mode(screen_size, flags)
        pygame.display.set_caption("Harf Oyunu")
        pygame.mouse.set_visible(False)

        self.renderer = Renderer(self.screen, font_scale=self.config.font_scale)
        self.renderer.set_hint(self._hint())

        # Sesler önceden üretilmiş wav'lardan gelir; yoksa oyun sessiz çalışır.
        # Diller arası geçiş hızlı olsun diye her dilin sesleri saklanır.
        self._voices: dict[str, Voice] = {}
        self.voice = self._voice_for(self.config.language)

        # Modlar F2 ile sırayla değişir; ilki serbest mod
        self.modes = build_modes(sorted(self.allowed))
        self.mode_index = 0
        self.mode = self.modes[0]

        self.running = True
        self.dirty = True
        self._esc_down_at: int | None = None
        self._timer_on = False
        self._audio_timer_on = False
        self._pending_sound: str | None = None   # animasyon bitince çalacak harf
        self._pending_prompt: str | None = None  # bulunması istenen harf
        self._sound_queue: list[str] = []

    # -- olay işleme -----------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        now = pygame.time.get_ticks()

        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == AUDIO_EVENT:
            self._pump_audio()

        elif event.type == TICK_EVENT:
            was_celebrating = self.renderer.celebrating
            was_animating = self.renderer.animating
            self.renderer.update(now)
            # Ses, giriş animasyonu bittikten sonra çalar (önce görüntü, sonra ses)
            if was_animating and not self.renderer.animating:
                self._flush_pending_sound()
            if was_celebrating and not self.renderer.celebrating:
                self._run(self.mode.on_celebration_end(), now)
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

        if self._handle_settings_key(event.key):
            return

        # Türkçe Q klavyede ğ/ü/ş/i/ö/ç doğru gelsin diye event.key değil unicode
        char = getattr(event, "unicode", "") or ""
        if not char or not char.isprintable() or char.isspace():
            return
        upper = upper_for_lang(char, self.lang.code)
        if upper in self.allowed:
            self._reset_audio()  # önceki ses kesilsin, üst üste binmesin
            self._run(self.mode.on_char(upper), now)

    # -- oyun modları -----------------------------------------------------
    def _run(self, actions: list[Action], now: int) -> None:
        """Modun ürettiği eylemleri ekrana ve sese uygular."""
        for action in actions:
            if action.kind == SHOW:
                self.renderer.show_char(action.value, now)
                self._pending_sound = None
            elif action.kind == SAY:
                # Ses, giriş animasyonu bitince çalar
                self._pending_sound = sound_key(action.value)
            elif action.kind == PROMPT:
                if self.renderer.target_char != action.value:
                    self.renderer.clear_char()  # yeni tur: sağ taraf boşalsın
                self.renderer.set_target(action.value)
                self._enqueue(phrase_key("find_letter"), sound_key(action.value))
            elif action.kind == CORRECT:
                self._enqueue("sfx_correct", phrase_key("correct"))
            elif action.kind == WRONG:
                self._enqueue("sfx_wrong", phrase_key("wrong"))
            elif action.kind == STAR:
                self.renderer.set_stars(action.value)
            elif action.kind == CELEBRATE:
                self.renderer.set_target(None)
                self.renderer.start_celebration(
                    self.lang.ui.get("celebrate", "★"), now)
                self._enqueue("sfx_celebrate", phrase_key("celebrate"))
        self.dirty = True

    def switch_mode(self, now: int) -> None:
        """F2: modlar arasında geçiş yapar."""
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.renderer.clear_char()
        self.renderer.set_layout(self.mode.shows_prompt, self._labels())
        self.renderer.set_stars(0, STARS_TO_WIN)
        self.renderer.set_status(self.lang.ui.get(self.mode.ui_key, self.mode.name))
        self._pending_sound = None
        self.mode.set_chars(sorted(self.allowed))
        self._run(self.mode.enter(), now)
        self.renderer.set_status(self.lang.ui.get(self.mode.ui_key, self.mode.name))

    # -- ebeveyn ayarları -------------------------------------------------
    def _handle_settings_key(self, key: int) -> bool:
        """Ayar tuşunu işler. İşlendiyse True döner. Her değişiklik diske yazılır."""
        if key == pygame.K_F1:
            self.set_language(self.config.toggle_language())
        elif key == pygame.K_F2:
            self.switch_mode(pygame.time.get_ticks())
        elif key == pygame.K_F3:
            value = self.config.cycle_char_set()
            self.allowed = set(self.lang.charset(value))
            actions = []
            for mode in self.modes:
                result = mode.set_chars(sorted(self.allowed))
                if mode is self.mode:  # yalnızca aktif modun eylemleri işlenir
                    actions = result
            self._run(actions, pygame.time.get_ticks())
            self._status("char_set_changed", self.lang.ui.get(f"set_{value}", value))
        elif key == pygame.K_F4:
            value = self.config.cycle_font_scale()
            self.renderer.set_font_scale(value)
            self._status("font_scale_changed", round(value * 100))
        elif key in VOLUME_UP_KEYS or key in VOLUME_DOWN_KEYS:
            step = VOLUME_STEP if key in VOLUME_UP_KEYS else -VOLUME_STEP
            value = self.config.change_volume(step)
            for voice in self._voices.values():
                voice.set_volume(value)
            self._status("volume_changed", round(value * 100))
        else:
            return False
        self.config.save()
        self.dirty = True
        return True

    def set_language(self, code: str) -> None:
        """Dili anında değiştirir: veri, sesler ve ekran metinleri yenilenir."""
        self.lang = load_language(code)
        self.allowed = set(self.lang.charset(self.config.char_set))
        self.voice.stop()
        self.voice = self._voice_for(code)
        self.renderer.set_hint(self._hint())
        self.renderer.set_status(self.lang.ui.get("language_changed", code))
        self._reset_audio()
        for mode in self.modes:
            mode.set_chars(sorted(self.allowed))

        self.renderer.set_layout(self.mode.shows_prompt, self._labels())
        self.renderer.set_stars(0, STARS_TO_WIN)
        self._enqueue(phrase_key("language_set"))
        if self.mode.shows_prompt:
            self._run(self.mode.enter(), pygame.time.get_ticks())

    def _voice_for(self, code: str) -> Voice:
        if code not in self._voices:
            self._voices[code] = Voice(code, volume=self.config.volume)
        return self._voices[code]

    def _labels(self) -> tuple[str, str]:
        """Bölünmüş ekranın sol/sağ başlıkları."""
        return (self.lang.ui.get("label_target", ""),
                self.lang.ui.get("label_you", ""))

    def _hint(self) -> str:
        """Alt satırdaki ebeveyn bilgisi: çıkış ve ayar kısayolları."""
        return "   ·   ".join(part for part in
                              (self.lang.ui.get("exit_hint", ""),
                               self.lang.ui.get("settings_hint", "")) if part)

    def _status(self, ui_key: str, value) -> None:
        template = self.lang.ui.get(ui_key, "{value}")
        self.renderer.set_status(template.format(value=value))

    # -- ses -------------------------------------------------------------
    def _reset_audio(self) -> None:
        """Bekleyen tüm sesleri iptal eder (yeni tuşa basıldığında)."""
        self._sound_queue.clear()
        self._pending_sound = None
        self.voice.stop()

    def _enqueue(self, *keys: str) -> None:
        self._sound_queue.extend(keys)
        self._pump_audio()

    def _pump_audio(self) -> None:
        """Sıradaki sesi, bir önceki bittiyse başlatır."""
        if self._sound_queue and not self.voice.busy():
            self.voice.play(self._sound_queue.pop(0))

    def _flush_pending_sound(self) -> None:
        if self._pending_sound is not None:
            self._enqueue(self._pending_sound)
            self._pending_sound = None

    # -- zamanlayıcı -----------------------------------------------------
    def _needs_tick(self) -> bool:
        return self.renderer.animating or self._esc_down_at is not None

    def _needs_audio_tick(self) -> bool:
        return bool(self._sound_queue)

    def _sync_timer(self) -> None:
        """Zamanlayıcıları yalnızca gerektiğinde açık tutar (boşta CPU ~%0)."""
        need = self._needs_tick()
        if need != self._timer_on:
            pygame.time.set_timer(TICK_EVENT, TICK_MS if need else 0)
            self._timer_on = need
        # Ses kuyruğu daha seyrek yoklanır; bir ses bitince sıradaki başlar
        need_audio = self._needs_audio_tick()
        if need_audio != self._audio_timer_on:
            pygame.time.set_timer(AUDIO_EVENT, AUDIO_TICK_MS if need_audio else 0)
            self._audio_timer_on = need_audio

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
    import tempfile

    init_mixer()
    pygame.init()
    # Gerçek config.json'a dokunmamak için geçici dosya kullanılır
    tmp_config = Path(tempfile.mkdtemp()) / "config.json"
    app = App(config=Config(path=tmp_config), lang_code="tr",
              fullscreen=False, size=(640, 480))
    cases = [("ğ", "Ğ"), ("i", "İ"), ("ı", "I"), ("5", "5"), ("ş", "Ş")]
    for typed, expected in cases:
        app.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=0, unicode=typed, mod=0))
        app.draw_if_dirty()
        if app.renderer.current_char != expected:
            print(f"HATA: '{typed}' -> {app.renderer.current_char!r}, "
                  f"beklenen {expected!r}")
            return 1

    # F1 ile dil değişimi ve ayarın diske yazılması
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1,
                                        unicode="", mod=0))
    if app.lang.code != "en" or not tmp_config.exists():
        print(f"HATA: F1 sonrası dil {app.lang.code!r}, "
              f"config yazıldı mı: {tmp_config.exists()}")
        return 1
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1,
                                        unicode="", mod=0))
    print(f"ayarlar OK: dil geçişi tr->en->{app.lang.code}, "
          f"{Config.load(tmp_config).as_dict()}")

    # "Harfi Bul": beş doğru cevap kutlamaya götürmeli
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2,
                                        unicode="", mod=0))
    if not app.mode.shows_prompt:
        print("HATA: F2 ile Harfi Bul moduna geçilmedi")
        return 1
    for _ in range(STARS_TO_WIN):
        target = app.mode.target
        app.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=0, unicode=target, mod=0))
    if not app.renderer.celebrating or app.renderer.stars != STARS_TO_WIN:
        print(f"HATA: {STARS_TO_WIN} doğru cevap sonrası kutlama yok "
              f"(yıldız: {app.renderer.stars})")
        return 1
    app.draw_if_dirty()
    print(f"oyun modu OK: {STARS_TO_WIN} yıldız -> kutlama")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2,
                                        unicode="", mod=0))

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
    parser.add_argument("--lang", default=None, choices=("tr", "en"),
                        help="config.json'daki dili geçersiz kılar")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_check:
        return self_check()

    config = Config.load()
    init_mixer()  # pygame.init()'ten önce: tampon boyutu gecikmeyi belirler
    pygame.init()
    try:
        App(config=config, lang_code=args.lang,
            fullscreen=not args.windowed).run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
