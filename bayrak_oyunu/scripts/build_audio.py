#!/usr/bin/env python3
"""Türkçe konuşma seslerini ve efektleri offline üretir.

Kurulumda BİR KEZ çalıştırılır; oyun çalışırken TTS çağrılmaz.
Konuşma motoru sırası: macOS `say` (Yelda) -> espeak-ng.
Efektler dış araç olmadan, saf Python ile sentezlenir.

Kullanım:
    python scripts/build_audio.py
    python scripts/build_audio.py --force      # var olanları yeniden üret
    python scripts/build_audio.py --dry-run
    python scripts/build_audio.py --check      # eksik dosya var mı
"""

from __future__ import annotations

import argparse
import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio import SFX_DIR, SPEECH_DIR  # noqa: E402
from app.speech import speech_table  # noqa: E402

RATE = 22050

# Çocuk için normalden yavaş konuşma
SAY_VOICE = "Yelda"
SAY_RATE = 130          # kelime/dakika (varsayılan ~175)
ESPEAK_SPEED = 130


class EngineError(RuntimeError):
    pass


class SayEngine:
    """macOS yerleşik `say` komutu."""

    name = "say"

    def __init__(self):
        self.binary = shutil.which("say")
        self.voice = None
        if self.binary:
            self.voice = self._pick_voice()

    def _pick_voice(self) -> str | None:
        try:
            out = subprocess.run([self.binary, "-v", "?"], capture_output=True,
                                 text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        names = [line.split()[0] for line in out.splitlines()
                 if "tr_TR" in line and line.split()]
        if not names:
            return None
        return SAY_VOICE if SAY_VOICE in names else names[0]

    def available(self) -> bool:
        return bool(self.binary and self.voice)

    def synth(self, text: str, out_path: Path) -> None:
        cmd = [self.binary, "-v", self.voice, "-r", str(SAY_RATE),
               "--file-format=WAVE", f"--data-format=LEI16@{RATE}",
               "-o", str(out_path), text]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise EngineError(result.stderr.decode("utf-8", "replace").strip())


class EspeakEngine:
    """espeak-ng: Linux'ta kurulumu kolay, sesi daha robotik."""

    name = "espeak-ng"

    def __init__(self):
        self.binary = shutil.which("espeak-ng") or shutil.which("espeak")

    def available(self) -> bool:
        return bool(self.binary)

    def synth(self, text: str, out_path: Path) -> None:
        cmd = [self.binary, "-v", "tr", "-s", str(ESPEAK_SPEED),
               "-w", str(out_path), text]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise EngineError(result.stderr.decode("utf-8", "replace").strip())


def pick_engine():
    for engine in (SayEngine(), EspeakEngine()):
        if engine.available():
            return engine
    return None


# -- efektler --------------------------------------------------------------
def _write_wav(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for value in samples:
        clipped = max(-1.0, min(1.0, value))
        frames += struct.pack("<h", int(clipped * 32000))
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(RATE)
        fh.writeframes(bytes(frames))


def _tone(freq: float, ms: int, volume: float = 0.5, decay: float = 4.0,
          wave_form: str = "sine") -> list[float]:
    count = int(RATE * ms / 1000)
    out = []
    for i in range(count):
        t = i / RATE
        phase = 2 * math.pi * freq * t
        if wave_form == "square":
            value = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_form == "tri":
            value = 2 / math.pi * math.asin(math.sin(phase))
        else:
            value = math.sin(phase)
        envelope = math.exp(-decay * t) * min(1.0, i / (RATE * 0.004) + 0.01)
        out.append(value * volume * envelope)
    return out


def _sequence(parts: list[list[float]]) -> list[float]:
    out: list[float] = []
    for part in parts:
        out.extend(part)
    return out


def _mix(a: list[float], b: list[float]) -> list[float]:
    length = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0.0) + (b[i] if i < len(b) else 0.0)
            for i in range(length)]


def sfx_table() -> dict[str, list[float]]:
    """Efektler: kısa, yumuşak ve birbirinden kolay ayırt edilir."""
    return {
        # Örümcek sırtını döndü: "şimdi!" sinyali, yükselen iki nota
        "sfx_safe": _sequence([_tone(880, 90, 0.45, 6), _tone(1320, 140, 0.45, 5)]),
        # Tehlike geri geldi
        "sfx_danger": _tone(180, 160, 0.30, 5, "tri"),
        # Başarılı sıçrama
        "sfx_hop": _sequence([_tone(620, 60, 0.4, 10), _tone(930, 90, 0.4, 8)]),
        # Yakalandın
        "sfx_caught": _sequence([_tone(420, 110, 0.4, 5, "square"),
                                 _tone(260, 220, 0.35, 4, "square")]),
        # Bayrağı aldın
        "sfx_win": _sequence([_tone(660, 110, 0.4, 5), _tone(880, 110, 0.4, 5),
                              _tone(1100, 110, 0.4, 5),
                              _mix(_tone(1320, 420, 0.35, 3),
                                   _tone(1760, 420, 0.2, 3))]),
        # Panoya yeni bayrak düştü
        "sfx_pop": _sequence([_tone(1500, 50, 0.35, 14), _tone(2000, 70, 0.3, 12)]),
        # Panoda seçim hareketi
        "sfx_move": _tone(1200, 40, 0.22, 18),
    }


# -- üretim ----------------------------------------------------------------
def build(force: bool = False, dry_run: bool = False) -> int:
    speech = speech_table()
    effects = sfx_table()

    todo_speech = {k: v for k, v in speech.items()
                   if force or not (SPEECH_DIR / f"{k}.wav").exists()}
    todo_sfx = {k: v for k, v in effects.items()
                if force or not (SFX_DIR / f"{k}.wav").exists()}

    print(f"Konuşma: {len(speech)} dosyanın {len(todo_speech)} tanesi üretilecek")
    print(f"Efekt:   {len(effects)} dosyanın {len(todo_sfx)} tanesi üretilecek")
    if dry_run:
        for key in sorted(todo_speech):
            print(f"  {key}.wav  <- {todo_speech[key]!r}")
        for key in sorted(todo_sfx):
            print(f"  {key}.wav  <- sentez")
        return 0

    for key, samples in sorted(todo_sfx.items()):
        _write_wav(SFX_DIR / f"{key}.wav", samples)
        print(f"  efekt  {key}.wav")

    if not todo_speech:
        return 0

    engine = pick_engine()
    if engine is None:
        print("\nTürkçe konuşabilen bir TTS motoru bulunamadı.", file=sys.stderr)
        print("  macOS : `say` zaten kuruludur, Türkçe ses (Yelda) "
              "Sistem Ayarları > Erişilebilirlik > Konuşulan İçerik "
              "bölümünden indirilebilir.", file=sys.stderr)
        print("  Linux : sudo apt install espeak-ng", file=sys.stderr)
        print("Oyun seslersiz de çalışır ama ülke adları duyulmaz.",
              file=sys.stderr)
        return 1

    print(f"Motor: {engine.name}"
          + (f" ({engine.voice})" if getattr(engine, "voice", None) else ""))
    SPEECH_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for key, text in sorted(todo_speech.items()):
        out = SPEECH_DIR / f"{key}.wav"
        try:
            engine.synth(text, out)
        except EngineError as exc:
            failed += 1
            print(f"  HATA {key}: {exc}", file=sys.stderr)
            continue
        print(f"  ses    {key}.wav  {text!r}")
    return 1 if failed else 0


def check() -> int:
    missing = [f"{k}.wav" for k in speech_table()
               if not (SPEECH_DIR / f"{k}.wav").exists()]
    missing += [f"{k}.wav" for k in sfx_table()
                if not (SFX_DIR / f"{k}.wav").exists()]
    if missing:
        print(f"Eksik {len(missing)} ses dosyası: "
              + ", ".join(missing[:6]) + (" ..." if len(missing) > 6 else ""))
        return 1
    print("Bütün ses dosyaları yerinde.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    return build(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
