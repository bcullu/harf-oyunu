"""Bayrak panosunun diske yazılması ve bir sonraki bayrağın seçilmesi."""

import json
import random

from app.flags import CODES
from app.progress import Progress


def test_bos_baslangic(tmp_path):
    progress = Progress(path=tmp_path / "p.json")
    assert progress.collected == []
    assert len(progress.remaining()) == len(CODES)
    assert not progress.complete()


def test_ekle_ve_diske_yaz(tmp_path):
    path = tmp_path / "p.json"
    progress = Progress(path=path)
    assert progress.add("tr") is True
    assert progress.add("tr") is False        # aynı bayrak iki kez eklenmez
    assert json.loads(path.read_text(encoding="utf-8"))["collected"] == ["tr"]


def test_bilinmeyen_kod_eklenmez(tmp_path):
    progress = Progress(path=tmp_path / "p.json")
    assert progress.add("zz") is False
    assert progress.collected == []


def test_kazanilan_bayrak_bir_daha_cikmaz(tmp_path):
    progress = Progress(path=tmp_path / "p.json")
    rng = random.Random(0)
    for _ in range(len(CODES)):
        code = progress.pick_next(rng)
        assert not progress.has(code)
        progress.add(code)
    assert progress.complete()
    # hepsi toplanınca oyun durmaz, rastgele biri gelir
    assert progress.pick_next(rng) in CODES


def test_bozuk_dosya_varsayilana_doner(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{bu json değil", encoding="utf-8")
    progress = Progress.load(path)
    assert progress.collected == []
    assert progress.volume == 0.9


def test_bilinmeyen_kodlar_dosyadan_temizlenir(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"collected": ["tr", "zz", "tr", "jp"]}),
                    encoding="utf-8")
    progress = Progress.load(path)
    assert progress.collected == ["tr", "jp"]


def test_ses_seviyesi_sinirli(tmp_path):
    progress = Progress(path=tmp_path / "p.json")
    for _ in range(20):
        progress.change_volume(0.1)
    assert progress.volume == 1.0
    for _ in range(30):
        progress.change_volume(-0.1)
    assert progress.volume == 0.0


def test_sifirla(tmp_path):
    progress = Progress(path=tmp_path / "p.json")
    progress.add("tr")
    progress.reset()
    assert progress.collected == []
