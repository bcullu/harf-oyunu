"""Ses katmanı: önceden üretilmiş wav'ları belleğe alır ve çalar.

Çalışma anında TTS ÇAĞRILMAZ. Sesler kurulumda scripts/build_audio.py ile
üretilir. Dosya eksikse oyun sessiz devam eder, çökmez.
"""

from __future__ import annotations

from pathlib import Path

from app.config import PROJECT_ROOT

AUDIO_DIR = PROJECT_ROOT / "audio"


def sound_key(char: str) -> str:
    """Bir karakterin ses anahtarı. Dosya adında Ğ/İ gibi harfler sorun
    çıkarmasın diye kod noktası kullanılır: 'Ğ' -> 'char_011e'."""
    return "char_" + "_".join(f"{ord(c):04x}" for c in char)


def phrase_key(name: str) -> str:
    return f"phrase_{name}"


def key_for(name: str) -> str:
    """data/*.json içindeki anahtarı ses anahtarına çevirir.

    'A' gibi karakter anahtarları char_*, 'phrase.correct' ise phrase_* olur.
    """
    if name.startswith("phrase."):
        return phrase_key(name.split(".", 1)[1])
    return sound_key(name)


def audio_dir_for(lang_code: str) -> Path:
    return AUDIO_DIR / lang_code


class Voice:
    """Bir dilin tüm seslerini bellekte tutar (dosyalar küçük)."""

    def __init__(self, lang_code: str, volume: float = 0.9):
        import pygame

        self._pygame = pygame
        self.lang_code = lang_code
        self.volume = volume
        self.sounds: dict[str, "pygame.mixer.Sound"] = {}
        self.missing: list[str] = []
        self.enabled = pygame.mixer.get_init() is not None
        self._channel = None
        if self.enabled:
            self._channel = pygame.mixer.Channel(0)
        self.load()

    def load(self) -> None:
        """Dile ait wav'ları ve dilden bağımsız efektleri belleğe alır."""
        self.sounds.clear()
        self.missing.clear()
        for directory in (audio_dir_for(self.lang_code), AUDIO_DIR / "sfx"):
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

    def play(self, key: str) -> bool:
        """Sesi çalar. Önceki ses kesilir (çocuk tuşlara hızlı basabilir)."""
        sound = self.sounds.get(key)
        if sound is None:
            if key not in self.missing:
                self.missing.append(key)
            return False
        if self._channel is not None:
            self._channel.stop()
            self._channel.play(sound)
        else:
            sound.play()
        return True

    def play_char(self, char: str) -> bool:
        return self.play(sound_key(char))

    def play_phrase(self, name: str) -> bool:
        return self.play(phrase_key(name))

    def busy(self) -> bool:
        """Kanalda hâlâ çalan bir ses var mı? (ses kuyruğu bunu yoklar)"""
        if self._channel is None:
            return False
        return bool(self._channel.get_busy())

    def stop(self) -> None:
        if self._channel is not None:
            self._channel.stop()


def init_mixer() -> bool:
    """Mixer'ı başlatır. Ses aygıtı yoksa False döner (oyun sessiz çalışır)."""
    import pygame

    try:
        # Tampon büyüdükçe ses geri çağırması seyrekleşir ve CPU düşer
        # (512 -> 1024 ölçümde ~%0.4 kazandırdı). 1024 örnek = ~46 ms gecikme,
        # harf sesi zaten animasyondan sonra çaldığı için fark edilmez.
        pygame.mixer.pre_init(22050, -16, 1, 1024)
        pygame.mixer.init()
        return True
    except Exception:
        return False
