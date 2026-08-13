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


# --- zaman germe (perde bozulmadan uzatma) ---------------------------------
# say/espeak belirli bir hızın altına inmiyor. Kesilen hece bu yüzden üretim
# sonrası WSOLA ile uzatılır: ses tizleşmez, sadece yavaşlar.

STRETCH_FRAME_MS = 30    # analiz penceresi
STRETCH_SEARCH_MS = 6    # en iyi örtüşmenin arandığı bölge
CORRELATION_STEP = 4     # benzerlik hesabında örnek atlama (hız için)


def _hann(size: int) -> list[float]:
    import math
    return [0.5 - 0.5 * math.cos(2 * math.pi * i / (size - 1)) for i in range(size)]


def _best_offset(samples: array.array, target: array.array,
                 center: int, search: int, length: int) -> int:
    """Hedef parçaya en çok benzeyen konumu ±search içinde arar."""
    best_score, best = None, 0
    for delta in range(-search, search + 1):
        start = center + delta
        if start < 0 or start + length > len(samples):
            continue
        score = sum(samples[start + i] * target[i]
                    for i in range(0, length, CORRELATION_STEP))
        if best_score is None or score > best_score:
            best_score, best = score, delta
    return best


def time_stretch(samples: array.array, rate: int, factor: float) -> array.array:
    """Sesi `factor` katı uzatır (factor > 1 = daha yavaş). Perde değişmez."""
    if factor <= 1.0 or len(samples) < rate // 20:
        return samples
    frame = max(64, rate * STRETCH_FRAME_MS // 1000)
    hop_out = frame // 2
    hop_in = max(1, int(hop_out / factor))
    search = rate * STRETCH_SEARCH_MS // 1000
    window = _hann(frame)

    out = [0.0] * (int(len(samples) * factor) + frame)
    out_pos = 0
    read_pos = 0
    index = 0
    while read_pos + frame + search < len(samples):
        if index > 0:
            # önceki karenin doğal devamına en çok benzeyen yeri bul
            target = samples[read_pos + hop_out:read_pos + hop_out + hop_out]
            nominal = index * hop_in
            offset = _best_offset(samples, target, nominal, search, len(target))
            read_pos = max(0, nominal + offset)
            if read_pos + frame >= len(samples):
                break
        for i in range(frame):
            out[out_pos + i] += samples[read_pos + i] * window[i]
        out_pos += hop_out
        index += 1

    result = array.array("h")
    for value in out[:out_pos + hop_out]:
        result.append(max(-32768, min(32767, int(value))))
    return result
