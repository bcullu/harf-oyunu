"""config.json doğrulama, kaydetme ve ebeveyn ayarı geçişleri."""

import json

import pytest

from app.config import (CHAR_SETS, DEFAULTS, FONT_SCALES, SUPPORTED_LANGUAGES,
                        Config, validate)


def test_defaults_when_file_missing(tmp_path):
    config = Config.load(tmp_path / "yok.json")
    assert config.as_dict() == DEFAULTS


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bozuk json", encoding="utf-8")
    assert Config.load(path).as_dict() == DEFAULTS


def test_non_object_json_falls_back(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert Config.load(path).as_dict() == DEFAULTS


@pytest.mark.parametrize("raw,field,expected", [
    ({"language": "de"}, "language", DEFAULTS["language"]),      # desteklenmeyen dil
    ({"char_set": "hepsi"}, "char_set", DEFAULTS["char_set"]),   # geçersiz set
    ({"volume": "yüksek"}, "volume", DEFAULTS["volume"]),        # sayı değil
    ({"volume": 5}, "volume", 1.0),                              # üst sınıra kırpılır
    ({"volume": -3}, "volume", 0.0),                             # alt sınıra kırpılır
    ({"font_scale": 9}, "font_scale", 0.95),                     # üst sınır
    ({"font_scale": 0.01}, "font_scale", 0.2),                   # alt sınır
    ({"font_scale": None}, "font_scale", DEFAULTS["font_scale"]),
])
def test_validation(raw, field, expected):
    assert validate(raw)[field] == expected


def test_unknown_keys_are_dropped():
    assert "sifre" not in validate({"sifre": "gizli"})


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    config = Config(path=path)
    config.language = "en"
    config.volume = 0.4
    config.char_set = "digits"
    config.font_scale = 0.8
    assert config.save() is True

    again = Config.load(path)
    assert (again.language, again.volume, again.char_set, again.font_scale) == \
           ("en", 0.4, "digits", 0.8)
    # dosya okunabilir JSON olmalı (ebeveyn elle düzenleyebilsin)
    assert json.loads(path.read_text(encoding="utf-8"))["language"] == "en"


def test_invalid_assignments_are_ignored(tmp_path):
    config = Config(path=tmp_path / "c.json")
    config.language = "de"
    config.char_set = "yok"
    assert config.language == DEFAULTS["language"]
    assert config.char_set == DEFAULTS["char_set"]


def test_toggle_language_cycles_all():
    config = Config()
    seen = [config.language]
    for _ in SUPPORTED_LANGUAGES:
        seen.append(config.toggle_language())
    assert set(seen) == set(SUPPORTED_LANGUAGES)
    assert seen[0] == seen[-1]  # tur başa döner


def test_cycle_char_set_visits_every_option():
    config = Config()
    seen = {config.cycle_char_set() for _ in CHAR_SETS}
    assert seen == set(CHAR_SETS)


def test_cycle_font_scale_visits_every_step():
    config = Config()
    seen = {config.cycle_font_scale() for _ in FONT_SCALES}
    assert seen == set(FONT_SCALES)


def test_cycle_font_scale_from_custom_value():
    # Ebeveyn dosyayı elle düzenlemiş olabilir: en yakın kademeden devam etsin
    config = Config({"font_scale": 0.61})
    assert config.cycle_font_scale() == 0.80


def test_volume_steps_stay_in_range():
    config = Config({"volume": 0.95})
    for _ in range(5):
        config.change_volume(0.1)
    assert config.volume == 1.0
    for _ in range(20):
        config.change_volume(-0.1)
    assert config.volume == 0.0


def test_save_failure_does_not_raise(tmp_path):
    # Yazılamayan yol: oyun çökmemeli, sadece False dönmeli
    config = Config(path=tmp_path / "olmayan.txt" / "config.json")
    (tmp_path / "olmayan.txt").write_text("dosya", encoding="utf-8")
    assert config.save() is False
