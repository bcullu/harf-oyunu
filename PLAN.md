# PLAN — Harf Oyunu

5 yaş için harf/rakam tanıma oyunu. Python 3.10+, tek runtime bağımlılığı: `pygame-ce`.

## 1. Mimari kararlar

**K1 — Olay güdümlü döngü (CPU ~%0).**
`pygame.event.wait()` ile blokla. Animasyon gerektiğinde `pygame.time.set_timer(TICK, 33)`
(≈30 FPS) ile timer aç, animasyon bitince timer'ı kapat (`set_timer(TICK, 0)`).
Böylece boştayken hiç olay gelmez, süreç uyur. Çizim yalnızca `dirty=True` iken.

**K2 — Ses tamamen önceden üretilir.**
Çalışma anında TTS yok. `scripts/build_audio.py` tüm metinleri `audio/<lang>/<key>.wav`
olarak üretir. Motor sırası: piper-tts → macOS `say` → espeak-ng. Hiçbiri yoksa
tek satırlık kurulum komutu yazıp `exit(1)` (oyun çökmüyor, sadece build script'i).
Oyun açılışta tüm wav'ları `pygame.mixer.Sound` olarak belleğe alır (~birkaç MB).
Ses dosyası eksikse oyun sessiz devam eder, çökmez.

**K3 — Türkçe metin katmanı.**
Girdi `event.unicode` ile okunur (Türkçe Q klavyede ğ/ü/ş/i/ö/ç doğru gelsin).
`app/text_tr.py` içinde `tr_upper()` / `tr_lower()`: i→İ, ı→I, ğ/ü/ş/ö/ç eşlemesi.
Alfabe ve fonetik metinler kodda değil `data/tr.json` / `data/en.json` içinde.

**K4 — Font.**
Sistem fontu `pygame.font.match_font` ile aranır (DejaVu Sans / Arial Unicode);
Türkçe glif garantisi için aday listesi denenir, bulunamazsa `pygame.font.Font(None)`
fallback. Font boyutu ekran yüksekliğinin oranı olarak hesaplanır (config'te `font_scale`).

**K5 — Konfig.**
`config.json` kullanıcı dizininde değil, proje kökünde (tek kullanıcı, taşınabilir).
Alanlar: `language`, `volume`, `char_set` (letters|digits|both), `font_scale`.
Eksik/bozuk alanlar varsayılanla doldurulur (şema doğrulama, çökme yok).

**K6 — Çıkış güvenliği.**
Ctrl+Q anında çıkar. ESC basılı tutma: `KEYDOWN`'da zaman damgası + 2100 ms'lik
tek seferlik timer; `KEYUP` gelirse iptal. Ekranda ilerleme çubuğu (animasyon
timer'ı zaten açık olduğundan ek maliyet yok). `pygame.display.set_mode(FULLSCREEN)`.

**K7 — Modlar.**
`app/game_modes.py` içinde küçük durum makinesi: `FreeMode` ve `FindLetterMode`.
Her mod `handle_key(char) -> list[Event]` döndürür; main.py sesi/çizimi tetikler.
F2 mod değiştirir, F1 dil değiştirir.

**K8 — Test edilebilirlik.**
Saf mantık (tr_upper, config, mod durum makinesi, veri dosyaları) pygame'siz test edilir.
Görsel katman `SDL_VIDEODRIVER=dummy` + `SDL_AUDIODRIVER=dummy` ile smoke test edilir.
`python main.py --self-check` : başlat, sentetik olay besle, çık, 0 döndür.

## 2. Dosya listesi

```
main.py                  # giriş, olay döngüsü, --self-check
app/__init__.py
app/config.py            # config.json yükle/kaydet/varsayılan
app/text_tr.py           # tr_upper/tr_lower, alfabe yardımcıları
app/render.py            # ekran çizimi, animasyon, font seçimi
app/audio.py             # wav yükleme + çalma (mixer)
app/game_modes.py        # FreeMode, FindLetterMode, yıldız sistemi
data/tr.json             # alfabe, rakamlar, fonetik metinler, UI metinleri
data/en.json
scripts/build_audio.py   # TTS motor tespiti + wav üretimi
audio/                   # üretilen wav'lar (git'e girmez)
tests/test_text_tr.py
tests/test_config.py
tests/test_game_modes.py
tests/test_smoke.py      # dummy driver ile pencere+tuş
install.sh
harf-oyunu.desktop
README.md
requirements.txt
.gitignore
```

## 3. Kilometre taşları

| # | Kapsam | Nasıl test edilecek |
|---|--------|---------------------|
| **M1** | Pencere (tam ekran), `event.unicode` ile tuş okuma, dev harf/rakam çizimi, rastgele renk, yumuşama animasyonu, Ctrl+Q / ESC-2sn çıkış. Ses yok. | `pytest tests/test_text_tr.py tests/test_smoke.py` — dummy driver'da pencere açılır, sentetik `ğ`/`i`/`5` olayları beslenir, ekranda çizilen karakter `tr_upper` sonucuna eşit mi diye modelden doğrulanır. `python main.py --self-check`. Elle: tam ekran açılıp Türkçe harflerin göründüğü. CPU: `top` ile boşta ölçüm. |
| **M2** | `scripts/build_audio.py` (piper→say→espeak-ng), `app/audio.py`, harf/rakam seslendirme, fonetik metinler `data/*.json`'dan. | `python scripts/build_audio.py --lang tr` çalıştır → `audio/tr/*.wav` sayısı = 29 harf + 10 rakam + UI sesleri. Test: her JSON anahtarı için wav var mı; wav'lar >0 byte. Oyun tarafı `SDL_AUDIODRIVER=dummy` ile Sound yüklemesini doğrular. Elle: A'ya bas, "A, araba gibi" duyulmalı. |
| **M3** | `config.json`, F1 ile anlık dil değişimi (İngilizce veri + wav seti), ebeveyn ayarları: ses seviyesi (+/-), harf seti (letters/digits/both), font boyutu. Ayar diske yazılır. | `tests/test_config.py`: bozuk/eksik JSON → varsayılan; kaydet→yükle round-trip. Smoke: F1 gönder → aktif dil değişti, config.json güncellendi. Elle: F1'e bas, çık, tekrar aç — dil hatırlanıyor mu. |
| **M4** | "Harfi Bul" modu: hedef harf sesli+yazılı istenir, doğru → alkış + yıldız, yanlış → nazik "tekrar dene", 5 yıldızda kutlama ekranı. F2 ile mod değişimi. | `tests/test_game_modes.py`: doğru/yanlış tuş → beklenen event dizisi; 5 doğru → `CELEBRATE`; hedef seçimi `char_set` ayarına uyuyor mu; aynı hedef üst üste gelmiyor mu. Smoke: sentetik doğru cevap dizisiyle kutlamaya ulaşma. Elle: F2, istenen harfe bas. |
| **M5** | `install.sh` (venv + pygame-ce + build_audio), `README.md` (Türkçe, adım adım), `harf-oyunu.desktop`, boştaki CPU ölçümü `top` ile raporlanır. | `bash -n install.sh`, temiz venv'de install.sh çalıştır → `python main.py --self-check` geçer. `.desktop` dosyası `desktop-file-validate` (varsa) ile kontrol. CPU: uygulama açıkken 60 sn boşta `top -l 5`/`top -b -n 5` çıktısı raporlanır (hedef <%1). |

## 4. Riskler / varsayımlar

- **Geliştirme makinesi macOS**, hedef Linux. `say` ile wav üretilecek (`say -o x.aiff` →
  `afconvert` ile wav). Linux'ta piper/espeak-ng yolu ayrıca kodlanacak ama burada
  fiilen test edilemez — sadece kuru testi (`--dry-run`) yapılacak. **Onayın gerekli:
  bu kabul edilebilir mi, yoksa Linux tarafını sen mi test edeceksin?**
- Wayland'de tam ekran + klavye SDL3/SDL2 üzerinden sorunsuz; `SDL_VIDEODRIVER`
  otomatik seçilecek, zorlanmayacak.
- Türkçe glif içeren sistem fontu yoksa harfler kutu görünür — README'de
  `fonts-dejavu` notu olacak.
- Git deposu yok; M1'den önce `git init` atılacak (onayınla).

## 5. Çalışma kuralı

Her taş için: kod → dummy-driver smoke test → `pytest` + `--self-check` → commit →
"M<n> tamam, şunu test et: ..." deyip DUR.
