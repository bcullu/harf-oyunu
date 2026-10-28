"""Ses katmanı: önceden üretilmiş wav'ları belleğe alır ve çalar.

Çalışma anında TTS çağrılmaz; sesler kurulumda scripts/build_audio.py ile
üretilir. Dosya eksikse oyun sessiz devam eder, çökmez.

İki kanal kullanılır: konuşma (ülke adları, cümleler) ve efekt. Böylece
"şimdi koş" tıngırtısı konuşmayı kesmez.
"""

from __future__ import annotations

from pathlib import Path

from app.progress import PROJECT_ROOT

AUDIO_DIR = PROJECT_ROOT / "audio"
SPEECH_DIR = AUDIO_DIR / "tr"
SFX_DIR = AUDIO_DIR / "sfx"


def name_key(code: str) -> str:
    """Ülke adını söyleyen dosyanın anahtarı: 'tr' -> 'name_tr'."""
    return f"name_{code}"


def win_key(code: str) -> str:
    """'Aferin! Bu, Türkiye bayrağı.' cümlesinin anahtarı."""
    return f"win_{code}"


class Voice:
    """Tüm sesleri bellekte tutar (dosyalar küçük)."""

    def __init__(self, volume: float = 0.9):
        import pygame

        self._pygame = pygame
        self.volume = volume
        self.sounds: dict[str, "pygame.mixer.Sound"] = {}
        self.missing: list[str] = []
        self.enabled = pygame.mixer.get_init() is not None
        self._speech = pygame.mixer.Channel(0) if self.enabled else None
        self._sfx = pygame.mixer.Channel(1) if self.enabled else None
        self.load()

    def load(self) -> None:
        self.sounds.clear()
        self.missing.clear()
        if not self.enabled:
            return
        for directory in (SPEECH_DIR, SFX_DIR):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.wav")):
                try:
                    sound = self._pygame.mixer.Sound(str(path))
                except Exception:  # bozuk dosya oyunu durdurmasın
                    self.missing.append(path.stem)
                    continue
                sound.set_volume(self.volume)
                self.sounds[path.stem] = sound

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    # -- çalma -----------------------------------------------------------
    def _play_on(self, channel, key: str, interrupt: bool) -> bool:
        sound = self.sounds.get(key)
        if sound is None:
            if key not in self.missing:
                self.missing.append(key)
            return False
        if channel is None:
            sound.play()
            return True
        if interrupt:
            channel.stop()
        elif channel.get_busy():
            return False
        channel.play(sound)
        return True

    def say(self, key: str) -> bool:
        """Konuşma kanalı: yeni cümle öncekini keser."""
        return self._play_on(self._speech, key, interrupt=True)

    def sfx(self, key: str) -> bool:
        """Efekt kanalı: konuşmayı kesmez."""
        return self._play_on(self._sfx, key, interrupt=True)

    def say_name(self, code: str) -> bool:
        return self.say(name_key(code))

    def say_win(self, code: str) -> bool:
        return self.say(win_key(code))

    def speaking(self) -> bool:
        return bool(self._speech and self._speech.get_busy())

    def stop(self) -> None:
        for channel in (self._speech, self._sfx):
            if channel is not None:
                channel.stop()


def init_mixer() -> bool:
    """Mixer'ı başlatır. Ses aygıtı yoksa False döner (oyun sessiz çalışır)."""
    import pygame

    try:
        pygame.mixer.pre_init(22050, -16, 1, 1024)
        pygame.mixer.init()
        return True
    except Exception:
        return False
