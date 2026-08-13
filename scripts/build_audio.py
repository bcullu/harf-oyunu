#!/usr/bin/env python3
"""Tüm konuşma seslerini offline üretip audio/<dil>/*.wav olarak kaydeder.

Kurulumda BİR KEZ çalıştırılır. Oyun çalışırken TTS çağrılmaz.
Motor sırası: piper-tts -> macOS `say` -> espeak-ng.

Kullanım:
    python scripts/build_audio.py              # tüm diller
    python scripts/build_audio.py --lang tr
    python scripts/build_audio.py --dry-run    # sadece ne üretileceğini göster
    python scripts/build_audio.py --force      # var olan wav'ları yeniden üret
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio import audio_dir_for, key_for  # noqa: E402
from app.config import SUPPORTED_LANGUAGES, load_language  # noqa: E402
from scripts.wav_trim import (TrimError, extract_segment, read_wav,  # noqa: E402
                              time_stretch, write_wav)

# piper ses modellerinin aranacağı dizinler
PIPER_VOICE_DIRS = (
    os.environ.get("PIPER_VOICES", ""),
    "~/.local/share/piper-voices",
    "~/.local/share/piper",
    "~/piper-voices",
    "/usr/share/piper-voices",
    "/usr/local/share/piper-voices",
    "/opt/piper/voices",
)

# Her dil için piper model adı öneki ve espeak-ng ses kodu
LANG_HINTS = {
    "tr": {"piper": "tr_TR", "espeak": "tr", "say_locale": "tr_TR"},
    "en": {"piper": "en_US", "espeak": "en-us", "say_locale": "en_US"},
}

# macOS'ta tercih edilen sesler (aksi halde alfabetik ilk ses seçilir ve
# "Albert", "Bad News" gibi şaka sesleri gelebilir)
PREFERRED_SAY_VOICES = {
    "tr": ("Yelda",),
    "en": ("Samantha", "Ava", "Allison", "Alex", "Karen", "Daniel"),
}

INSTALL_HINT = {
    "Linux": "sudo apt install espeak-ng     # veya: pipx install piper-tts",
    "Darwin": "brew install espeak-ng        # (macOS'ta `say` zaten yeterlidir)",
}


# data/*.json içindeki metinlerde duraklama işareti. Her motor bunu kendi
# sözdizimine çevirir.
PAUSE_TOKEN = "|"
PAUSE_MS = 600

# TTS motorları tek başına verilen "bı", "lı" gibi heceleri bozuk okur. Harf
# sesleri bu cümlenin içinde sentezlenip virgül duraklamalarından kesilir.
# {text} iki yanı garantili sessizlikle (PAUSE_TOKEN) çevrelenir, sonra
# ortadaki parça kesilir. Sadece kesin süreli duraklama üretebilen motorlarda
# kullanılır; piper cümle içinde böyle bir sessizlik veremez.
CARRIER = {
    "tr": "Şu harf | {text} | evet.",
    "en": "The letter | {text} | yes.",
}

# Konuşma hızı: çocuk için normalden yavaş
SAY_RATE = 90           # kelime/dakika (macOS varsayılanı ~175), çocuk için yavaş
ESPEAK_SPEED = 115      # kelime/dakika (espeak varsayılanı 175)
ESPEAK_WORD_GAP = 12    # 10 ms'lik birimler, kelimeler arası ek boşluk
PIPER_LENGTH_SCALE = 1.15  # >1 = daha yavaş
PIPER_TRAILING_SILENCE = 0.2  # saniye, ses sonundaki sessizlik

# TTS motorları belli bir hızın altına inmiyor (say 25 wpm'de bile hece
# ~0.3 sn). Harf sesleri bu yüzden üretimden sonra perde bozulmadan
# uzatılır. 1.0 = germe yok.
STRETCH_FACTOR = 1.6


class EngineError(RuntimeError):
    pass


class Engine:
    name = "?"
    # Cümle içinde kesin süreli sessizlik üretebiliyor mu? (taşıyıcı cümle
    # tekniği buna bağlı: piper üretemez, say ve espeak-ng üretir)
    exact_pause = False

    def supports(self, lang: str) -> bool:
        raise NotImplementedError

    def render_pauses(self, text: str) -> str:
        """PAUSE_TOKEN'ı motorun anladığı duraklamaya çevirir."""
        raise NotImplementedError

    def synth(self, text: str, lang: str, out_path: Path) -> None:
        raise NotImplementedError


class PiperEngine(Engine):
    """piper-tts: en doğal sonuç, çevrimdışı çalışır."""

    name = "piper"
    exact_pause = False

    def __init__(self):
        # venv içine kurulmuşsa PATH'te olmayabilir; yorumlayıcının yanına da bak
        venv_piper = Path(sys.executable).parent / "piper"
        self.binary = (shutil.which("piper") or shutil.which("piper-tts")
                       or (str(venv_piper) if venv_piper.exists() else None))
        self.models: dict[str, Path] = {}
        if self.binary:
            self._find_models()

    def _find_models(self) -> None:
        for raw in PIPER_VOICE_DIRS:
            if not raw:
                continue
            directory = Path(raw).expanduser()
            if not directory.is_dir():
                continue
            for lang, hints in LANG_HINTS.items():
                if lang in self.models:
                    continue
                matches = sorted(directory.rglob(f"{hints['piper']}*.onnx"))
                if matches:
                    self.models[lang] = matches[0]

    def supports(self, lang: str) -> bool:
        return bool(self.binary) and lang in self.models

    def render_pauses(self, text: str) -> str:
        # piper SSML desteklemez; noktalama ile duraklama sağlanır
        return text.replace(PAUSE_TOKEN, "...")

    def synth(self, text: str, lang: str, out_path: Path) -> None:
        cmd = [self.binary, "--model", str(self.models[lang]),
               "--length_scale", str(PIPER_LENGTH_SCALE),
               "--sentence_silence", str(PIPER_TRAILING_SILENCE),
               "--output_file", str(out_path)]
        result = subprocess.run(cmd, input=text.encode("utf-8"),
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise EngineError(result.stderr.decode("utf-8", "replace").strip())


class SayEngine(Engine):
    """macOS yerleşik `say` komutu."""

    name = "say"
    exact_pause = True

    def __init__(self):
        self.binary = shutil.which("say") if platform.system() == "Darwin" else None
        self.voices: dict[str, str] = {}
        if self.binary:
            self._find_voices()

    def _find_voices(self) -> None:
        try:
            output = subprocess.run([self.binary, "-v", "?"],
                                    capture_output=True, text=True).stdout
        except OSError:
            return
        # dil -> o dilde bulunan tüm ses adları
        found: dict[str, list[str]] = {lang: [] for lang in LANG_HINTS}
        for line in output.splitlines():
            # "Yelda               tr_TR    # Merhaba..."  -> ad birden çok kelime olabilir
            parts = line.split()
            locale = next((p for p in parts if "_" in p and len(p) == 5), None)
            if locale is None:
                continue
            voice_name = line.split(locale)[0].strip()
            for lang, hints in LANG_HINTS.items():
                if locale == hints["say_locale"]:
                    found[lang].append(voice_name)
        for lang, names in found.items():
            if not names:
                continue
            preferred = next((v for v in PREFERRED_SAY_VOICES.get(lang, ())
                              if v in names), None)
            self.voices[lang] = preferred or names[0]

    def supports(self, lang: str) -> bool:
        return bool(self.binary) and lang in self.voices

    def render_pauses(self, text: str) -> str:
        # say'in gömülü konuşma komutu: [[slnc <ms>]]
        return text.replace(PAUSE_TOKEN, f"[[slnc {PAUSE_MS}]]")

    def synth(self, text: str, lang: str, out_path: Path) -> None:
        cmd = [self.binary, "-v", self.voices[lang], "-r", str(SAY_RATE),
               "--file-format=WAVE", "--data-format=LEI16@22050",
               "-o", str(out_path), text]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise EngineError(result.stderr.decode("utf-8", "replace").strip())


class EspeakEngine(Engine):
    """espeak-ng: her yerde bulunur, sesi robotik ama iş görür."""

    name = "espeak-ng"
    exact_pause = True

    def __init__(self):
        self.binary = shutil.which("espeak-ng") or shutil.which("espeak")

    def supports(self, lang: str) -> bool:
        return bool(self.binary) and lang in LANG_HINTS

    def render_pauses(self, text: str) -> str:
        # espeak-ng SSML modunda (-m) break etiketini anlar
        return text.replace(PAUSE_TOKEN, f'<break time="{PAUSE_MS}ms"/>')

    def synth(self, text: str, lang: str, out_path: Path) -> None:
        cmd = [self.binary, "-m", "-v", LANG_HINTS[lang]["espeak"],
               "-s", str(ESPEAK_SPEED), "-g", str(ESPEAK_WORD_GAP),
               "-p", "60", "-w", str(out_path), text]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise EngineError(result.stderr.decode("utf-8", "replace").strip())


def pick_engine(languages: list[str], forced: str | None = None) -> Engine | None:
    """İstenen dilleri destekleyen ilk motoru döndürür."""
    engines = [PiperEngine(), SayEngine(), EspeakEngine()]
    for engine in engines:
        if forced and engine.name != forced:
            continue
        if all(engine.supports(lang) for lang in languages):
            return engine
    return None


def carrier_keys(lang_code: str) -> set[str]:
    """Taşıyıcı cümle içinde üretilecek anahtarlar (harfler ve rakamlar)."""
    data = load_language(lang_code)
    return {key_for(char) for char in data.charset("both")}


def texts_for(lang_code: str) -> dict[str, str]:
    """Ses anahtarı -> seslendirilecek metin."""
    data = load_language(lang_code)
    items = {key_for(char): text for char, text in data.phonetics.items()}
    for name, text in data.phrases.items():
        # {char} yer tutucusu olan cümleler oyunda parça parça çalınır,
        # burada yer tutucusuz kısmı üretilir.
        items[key_for(f"phrase.{name}")] = text.replace("{char}", "").strip()
    return items


def build(lang_code: str, engine: Engine, force: bool, dry_run: bool,
          use_carrier: bool = True) -> tuple[int, int]:
    """(üretilen, atlanan) sayısını döndürür."""
    out_dir = audio_dir_for(lang_code)
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    items = texts_for(lang_code)
    char_keys = carrier_keys(lang_code)
    carriers = char_keys if use_carrier and engine.exact_pause else set()
    for index, (key, text) in enumerate(sorted(items.items()), start=1):
        path = out_dir / f"{key}.wav"
        if path.exists() and path.stat().st_size > 0 and not force:
            skipped += 1
            continue
        spoken = text
        if key in carriers:
            spoken = CARRIER[lang_code].format(text=text)
        if dry_run:
            print(f"  [{index}/{len(items)}] üretilecek: {path.name}  <- {spoken!r}")
            made += 1
            continue

        if key in carriers:
            raw = path.with_suffix(".raw.wav")
            engine.synth(engine.render_pauses(spoken), lang_code, raw)
            _check_produced(raw, engine)
            try:
                trimmed = extract_segment(raw, path, index=1, expected=3)
            except TrimError as exc:
                raise EngineError(f"{path.name}: {exc}") from exc
            raw.unlink()
            note = "" if trimmed else "  (UYARI: parça bulunamadı, tam cümle)"
        else:
            engine.synth(engine.render_pauses(spoken), lang_code, path)
            note = ""
        _check_produced(path, engine)

        # Harf/rakam sesleri çocuğun ayırt edebilmesi için yavaşlatılır
        if key in char_keys and STRETCH_FACTOR > 1.0:
            params, samples = read_wav(path)
            write_wav(path, params, time_stretch(samples, params.framerate,
                                                 STRETCH_FACTOR))
        made += 1
        print(f"  [{index}/{len(items)}] {path.name}{note}")
    return made, skipped


def _check_produced(path: Path, engine: Engine) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise EngineError(f"{path.name} üretilemedi (motor: {engine.name})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Oyun seslerini offline üret")
    parser.add_argument("--lang", default="all",
                        choices=("all",) + SUPPORTED_LANGUAGES)
    parser.add_argument("--engine", choices=("piper", "say", "espeak-ng"),
                        help="Motoru elle seç (varsayılan: sırayla otomatik)")
    parser.add_argument("--force", action="store_true",
                        help="Var olan wav'ları yeniden üret")
    parser.add_argument("--dry-run", action="store_true",
                        help="Üretme, sadece listele")
    parser.add_argument("--no-carrier", action="store_true",
                        help="Taşıyıcı cümle kullanma, sesi doğrudan üret")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    languages = list(SUPPORTED_LANGUAGES) if args.lang == "all" else [args.lang]

    engine = pick_engine(languages, args.engine)
    if engine is None:
        hint = INSTALL_HINT.get(platform.system(), INSTALL_HINT["Linux"])
        print("Ses üretici (TTS) bulunamadı. Şu komutu çalıştırıp tekrar deneyin:",
              file=sys.stderr)
        print(f"    {hint}", file=sys.stderr)
        return 1

    print(f"Motor: {engine.name}")
    total_made = total_skipped = 0
    for lang in languages:
        print(f"[{lang}]")
        try:
            made, skipped = build(lang, engine, args.force, args.dry_run,
                                  use_carrier=not args.no_carrier)
        except EngineError as exc:
            print(f"Ses üretimi başarısız ({engine.name}): {exc}", file=sys.stderr)
            return 1
        total_made += made
        total_skipped += skipped
    action = "üretilecek" if args.dry_run else "üretildi"
    print(f"Toplam: {total_made} {action}, {total_skipped} atlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
