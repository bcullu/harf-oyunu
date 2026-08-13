"""Ses üretimi ve yüklenmesi (SDL_AUDIODRIVER=dummy ile ekransız)."""

import wave

import pygame
import pytest

from app.audio import Voice, audio_dir_for, init_mixer, key_for, sound_key
from app.config import SUPPORTED_LANGUAGES, load_language
from scripts.build_audio import texts_for


def test_sound_key_is_filename_safe():
    assert sound_key("Ğ") == "char_011e"
    assert sound_key("İ") == "char_0130"
    assert sound_key("A") == "char_0041"
    assert sound_key("5") == "char_0035"
    # Türkçe I/İ ve i/ı farklı dosyalara gitmeli
    assert sound_key("I") != sound_key("İ")


def test_key_for_phrases():
    assert key_for("phrase.correct") == "phrase_correct"
    assert key_for("A") == "char_0041"


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_every_char_has_a_text(lang):
    data = load_language(lang)
    texts = texts_for(lang)
    for char in data.charset("both"):
        assert sound_key(char) in texts, f"{lang}: {char} için metin yok"
        assert texts[sound_key(char)].strip()


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_generated_wavs_exist_and_are_valid(lang):
    directory = audio_dir_for(lang)
    if not directory.is_dir():
        pytest.skip("Sesler henüz üretilmedi: python scripts/build_audio.py")
    for key in texts_for(lang):
        path = directory / f"{key}.wav"
        assert path.exists(), f"eksik ses: {path.name}"
        assert path.stat().st_size > 0
        with wave.open(str(path)) as wav:
            assert wav.getnframes() > 0, f"boş ses: {path.name}"


def test_voice_loads_into_memory():
    if not audio_dir_for("tr").is_dir():
        pytest.skip("Sesler henüz üretilmedi")
    init_mixer()
    pygame.init()
    try:
        voice = Voice("tr")
        data = load_language("tr")
        for char in data.charset("both"):
            assert voice.play_char(char), f"{char} çalınamadı"
        assert voice.play_phrase("correct")
    finally:
        pygame.quit()


def test_voice_without_audio_files_is_silent_not_crashing():
    init_mixer()
    pygame.init()
    try:
        voice = Voice("tr")
        assert voice.play("char_ffff") is False  # olmayan ses -> sessiz, hata yok
        voice.stop()
    finally:
        pygame.quit()
