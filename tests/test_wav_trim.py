"""Taşıyıcı cümleden parça kesme mantığı (sentetik wav ile)."""

import array
import math
import wave

import pytest

from scripts.wav_trim import (MIN_GAP_MS, TrimError, extract_segment,
                              find_segments, read_wav)

RATE = 22050


def tone(duration_ms: int, freq: int = 220, amp: int = 12000) -> array.array:
    count = RATE * duration_ms // 1000
    return array.array("h", (int(amp * math.sin(2 * math.pi * freq * i / RATE))
                             for i in range(count)))


def silence(duration_ms: int) -> array.array:
    return array.array("h", [0] * (RATE * duration_ms // 1000))


def write(path, *parts):
    samples = array.array("h")
    for part in parts:
        samples.extend(part)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(samples.tobytes())
    return path


def test_finds_three_segments(tmp_path):
    path = write(tmp_path / "c.wav",
                 tone(400), silence(600), tone(300, 330), silence(600), tone(500))
    _, samples = read_wav(path)
    segments = find_segments(samples, RATE)
    assert len(segments) == 3


def test_short_gaps_do_not_split(tmp_path):
    # Hece içindeki kısa duraklama parçayı bölmemeli
    gap = max(10, MIN_GAP_MS // 3)
    path = write(tmp_path / "c.wav", tone(200), silence(gap), tone(200))
    _, samples = read_wav(path)
    assert len(find_segments(samples, RATE)) == 1


def test_extract_middle_segment(tmp_path):
    src = write(tmp_path / "src.wav",
                tone(400), silence(600), tone(300, 330), silence(600), tone(500))
    dest = tmp_path / "out.wav"
    assert extract_segment(src, dest, index=1, expected=3) is True
    params, samples = read_wav(dest)
    duration = len(samples) / params.framerate
    # 300 ms hedef + iki uçta pay; taşıyıcının tamamından çok kısa olmalı
    assert 0.3 <= duration <= 0.5


def test_falls_back_when_segment_count_unexpected(tmp_path):
    src = write(tmp_path / "src.wav", tone(400), silence(600), tone(400))
    dest = tmp_path / "out.wav"
    assert extract_segment(src, dest, index=1, expected=3) is False
    # dosya yine de yazılmış olmalı (sessiz kalmaktansa tam cümle)
    assert dest.exists() and dest.stat().st_size > 0


def test_rejects_stereo(tmp_path):
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(tone(100).tobytes())
    with pytest.raises(TrimError):
        read_wav(path)


# --- zaman germe ------------------------------------------------------------

def test_time_stretch_lengthens_without_changing_format(tmp_path):
    from scripts.wav_trim import time_stretch
    samples = tone(400)
    stretched = time_stretch(samples, RATE, 1.6)
    ratio = len(stretched) / len(samples)
    assert 1.4 <= ratio <= 1.8, f"beklenen ~1.6 kat, gelen {ratio:.2f}"
    assert stretched.typecode == "h"
    assert max(abs(s) for s in stretched) <= 32767


def test_time_stretch_is_noop_for_factor_one():
    from scripts.wav_trim import time_stretch
    samples = tone(300)
    assert time_stretch(samples, RATE, 1.0) is samples


def test_time_stretch_skips_very_short_audio():
    from scripts.wav_trim import time_stretch
    samples = tone(20)  # 20 ms: germek anlamsız
    assert len(time_stretch(samples, RATE, 2.0)) == len(samples)
