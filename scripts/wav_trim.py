"""Taşıyıcı cümleden hedef parçayı kesmek için wav yardımcıları.

TTS motorları tek başına verilen "bı", "lı" gibi kısa heceleri bozuk okur.
Bu yüzden harf, "Şu harf, bı, evet." gibi bir cümlenin içinde sentezlenir;
virgüller sessizlik yaratır ve ortadaki parça buradan kesilir.

Yalnızca standart kütüphane kullanılır (16-bit mono PCM wav).
"""

from __future__ import annotations

import array
import wave
from pathlib import Path

WINDOW_MS = 10          # enerji penceresi
MIN_SEGMENT_MS = 60     # bundan kısa gürültü parçası sayılmaz
MIN_GAP_MS = 300     # taşıyıcıdaki sessizlik en az 600 ms, bu eşik güvenli
SILENCE_RATIO = 0.05  # en yüksek pencere enerjisinin bu oranı altı = sessizlik
PAD_MS = 40           # kesilen parçanın iki ucuna bırakılan pay


class TrimError(RuntimeError):
    pass


def read_wav(path: Path) -> tuple[wave._wave_params, array.array]:
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        if params.sampwidth != 2 or params.nchannels != 1:
            raise TrimError(f"16-bit mono bekleniyordu: {path.name}")
        samples = array.array("h")
        samples.frombytes(wav.readframes(params.nframes))
    return params, samples


def write_wav(path: Path, params: wave._wave_params, samples: array.array) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(params.nchannels)
        wav.setsampwidth(params.sampwidth)
        wav.setframerate(params.framerate)
        wav.writeframes(samples.tobytes())


def _window_energies(samples: array.array, rate: int) -> tuple[list[float], int]:
    """Pencere başına ortalama mutlak genlik (audioop olmadan, saf Python)."""
    size = max(1, rate * WINDOW_MS // 1000)
    energies = []
    for start in range(0, len(samples), size):
        chunk = samples[start:start + size]
        energies.append(sum(abs(s) for s in chunk) / len(chunk) if chunk else 0.0)
    return energies, size


def find_segments(samples: array.array, rate: int) -> list[tuple[int, int]]:
    """Konuşma parçalarını (başlangıç, bitiş) örnek indeksi olarak döndürür."""
    energies, size = _window_energies(samples, rate)
    if not energies:
        return []
    threshold = max(energies) * SILENCE_RATIO
    loud = [e > threshold for e in energies]

    # Kısa sessizlikleri doldur (aynı hecenin içindeki duraklamalar bölmesin)
    min_gap = max(1, MIN_GAP_MS // WINDOW_MS)
    index = 0
    while index < len(loud):
        if not loud[index]:
            end = index
            while end < len(loud) and not loud[end]:
                end += 1
            if 0 < index and end < len(loud) and (end - index) < min_gap:
                for k in range(index, end):
                    loud[k] = True
            index = end
        else:
            index += 1

    segments = []
    min_len = max(1, MIN_SEGMENT_MS // WINDOW_MS)
    index = 0
    while index < len(loud):
        if loud[index]:
            start = index
            while index < len(loud) and loud[index]:
                index += 1
            if index - start >= min_len:
                segments.append((start * size, min(len(samples), index * size)))
        else:
            index += 1
    return segments


def extract_segment(src: Path, dest: Path, index: int = 1,
                    expected: int = 3) -> bool:
    """Taşıyıcı cümleden `index` numaralı parçayı keser.

    Beklenen sayıda parça bulunamazsa dosyayı olduğu gibi kopyalar ve
    False döner (çağıran uyarı gösterebilir).
    """
    params, samples = read_wav(src)
    segments = find_segments(samples, params.framerate)
    if len(segments) != expected or index >= len(segments):
        write_wav(dest, params, samples)
        return False
    pad = params.framerate * PAD_MS // 1000
    start, end = segments[index]
    start = max(0, start - pad)
    end = min(len(samples), end + pad)
    write_wav(dest, params, samples[start:end])
    return True
