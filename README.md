# Harf Oyunu

5 yaşındaki çocuklar için harf ve rakam tanıma oyunu. Klavyedeki bir tuşa
basıldığında harf ekranı kaplayacak kadar büyük görünür ve sesli okunur.

- Türkçe alfabenin 29 harfi (ğ, ı, İ, ö, ş, ü dahil) ve 0-9 rakamları
- Türkçe / İngilizce, F1 ile anında geçiş
- İki mod: **Serbest Mod** ve **Harfi Bul** (yıldızlı)
- İnternet gerekmez, çalışırken hiçbir sunucuya bağlanmaz
- Çocuk yanlışlıkla kapatamaz

Tek bağımlılık: `pygame-ce`. Linux ve macOS'ta çalışır.

---

## 1. Kurulum

Terminali açın ve proje klasörüne girip şunu çalıştırın:

```bash
bash install.sh
```

Betik sırayla şunları yapar:

1. Python 3.10+ var mı diye bakar
2. `.venv` adında bir sanal ortam kurar (sistem Python'ınıza dokunmaz)
3. `pygame-ce` kurar
4. Ses dosyalarını kontrol eder (hazır geldiği için yeniden üretmez)
5. Masaüstü ikonunu üretir
6. Kurulumu doğrular (`--self-check`)
7. Linux'ta uygulama menüsüne "Harf Oyunu" kısayolu ekler

Betik birden çok kez çalıştırılabilir, var olanı bozmaz.

### Python veya venv yoksa

```bash
sudo apt install python3 python3-venv
```

### Türkçe harfler kutu görünüyorsa

Sistemde Türkçe glif içeren bir font yok demektir:

```bash
sudo apt install fonts-dejavu
```

---

## 2. Çalıştırma

Uygulama menüsünden **Harf Oyunu**'na tıklayın, ya da:

```bash
.venv/bin/python main.py
```

Faydalı seçenekler:

| Komut | Ne yapar |
|---|---|
| `main.py` | Tam ekran başlatır (normal kullanım) |
| `main.py --windowed` | Pencerede başlatır (deneme için) |
| `main.py --lang en` | Bu seferlik İngilizce başlatır |
| `main.py --self-check` | Ekran açmadan kurulumu doğrular, çıkar |

---

## 3. Tuşlar

### Çocuk için

| Tuş | Ne olur |
|---|---|
| Herhangi bir harf/rakam | Ekranda büyük görünür ve sesi okunur |

### Ebeveyn için

| Tuş | İşlev |
|---|---|
| **F1** | Dil: Türkçe ↔ İngilizce |
| **F2** | Mod: Serbest Mod ↔ Harfi Bul |
| **F3** | Harf seti: sadece harfler → sadece rakamlar → ikisi |
| **F4** | Yazı boyutu: %45 → %62 → %80 |
| **+ / −** | Ses seviyesi (%10 adım) |
| **Ctrl+Q** | Anında çıkış |
| **ESC (2 saniye basılı)** | Çıkış — çubuk dolunca kapanır |

Her ayar değişikliği anında `config.json`'a yazılır, bir dahaki açılışta hatırlanır.

ESC'ye kısa basmak hiçbir şey yapmaz; çocuk yanlışlıkla kapatamasın diye
2 saniye basılı tutmak gerekir.

---

## 4. Oyun modları

**Serbest Mod** — Basılan harf ekranın ortasında dev olarak, rastgele canlı bir
renkte belirir; kısa bir büyüme animasyonundan sonra sesi okunur.

**Harfi Bul** — Ekran ikiye ayrılır: solda bulunması istenen harf ("BUNU BUL"),
sağda çocuğun bastığı harf ("SEN"). Doğru bilince çan sesi, "Aferin!" ve bir
yıldız kazanılır. Yanlışta ceza yoktur: yumuşak bir ses ve "Olsun, tekrar dene"
denir, aynı harf ekranda kalır. **5 yıldızda** kutlama ekranı gelir, sonra
yıldızlar sıfırlanıp yeni tur başlar.

---

## 5. Ayarlar (config.json)

Proje klasöründeki `config.json` elle de düzenlenebilir:

```json
{
  "language": "tr",
  "volume": 0.9,
  "char_set": "both",
  "font_scale": 0.62
}
```

| Alan | Değerler | Anlamı |
|---|---|---|
| `language` | `tr`, `en` | Arayüz ve ses dili |
| `volume` | 0.0 – 1.0 | Ses seviyesi |
| `char_set` | `letters`, `digits`, `both` | Hangi karakterler kabul edilsin |
| `font_scale` | 0.2 – 0.95 | Harfin ekran yüksekliğine oranı |

Dosya bozuksa veya bir alan eksikse oyun çökmez, o alan için varsayılana döner.

---

## 6. Sesler

Sesler **çalışma anında üretilmez**. Hepsi önceden `.wav` olarak hazırlanmıştır
(`audio/` klasörü, 85 dosya, ~3 MB) ve oyun açılışta bunları belleğe alır.
Böylece hem internet gerekmez hem de tuşa basınca gecikme olmaz.

Sesler bu depoya dahildir; **normalde yeniden üretmenize gerek yoktur.**

### Yeniden üretmek isterseniz

```bash
.venv/bin/python scripts/build_audio.py --force
```

Betik şu motorları sırayla dener, ilk bulduğunu kullanır:

1. **piper-tts** (`pip install piper-tts` + ses modeli)
2. **macOS `say`** (macOS'ta hazır gelir)
3. **espeak-ng** (`sudo apt install espeak-ng`)

Hiçbiri yoksa tek satırlık kurulum komutu gösterip durur, oyun yine de sessiz
çalışır.

Faydalı seçenekler: `--lang tr`, `--dry-run`, `--engine espeak-ng`, `--no-carrier`.

### Seslerin nasıl hazırlandığı

TTS motorları tek başına verilen "bı", "lı" gibi kısa heceleri bozuk okuyor.
Bu yüzden her harf `"Şu harf | bı | evet."` cümlesinin içinde seslendirilip
ortadaki parça kesiliyor (`scripts/wav_trim.py`). Motorlar belli bir hızın
altına da inmediği için sesler üretimden sonra perdesi bozulmadan 1.6 kat
uzatılıyor. Alkış ve yıldız sesleri TTS ile değil, saf Python ile sentezleniyor
(`audio/sfx/`).

Mevcut set macOS'un Yelda sesiyle üretildi. Linux'ta yeniden üretilirse
espeak-ng kullanılacağı için ses daha robotik olur — bu yüzden hazır wav'lar
depoda taşınıyor.

---

## 7. Masaüstü kısayolu (Linux)

`install.sh` şunu oluşturur:

```
~/.local/share/applications/harf-oyunu.desktop
```

Kısayol menüde görünmezse:

```bash
update-desktop-database ~/.local/share/applications
```

Kaldırmak için dosyayı silmeniz yeterlidir.

---

## 8. Sorun giderme

| Belirti | Çözüm |
|---|---|
| Harfler kutu görünüyor | `sudo apt install fonts-dejavu` |
| Hiç ses yok | `.venv/bin/python main.py --self-check` çıktısına bakın; "ses OK" yazmıyorsa `scripts/build_audio.py` çalıştırın |
| Türkçe harfler yanlış geliyor | Klavye düzeninin Türkçe Q olduğundan emin olun; oyun tuş kodunu değil karakteri okur |
| Tam ekrandan çıkamıyorum | Ctrl+Q, ya da ESC'yi 2 saniye basılı tutun |
| Wayland'de pencere açılmıyor | `SDL_VIDEODRIVER=x11 .venv/bin/python main.py` deneyin |

---

## 9. Geliştirici notları

```bash
.venv/bin/python -m pytest          # tüm testler (ekransız çalışır)
.venv/bin/python main.py --self-check
```

Testler `SDL_VIDEODRIVER=dummy` ile ekran açmadan çalışır.

### Dosya düzeni

```
main.py                # olay döngüsü, tuş yönetimi
app/config.py          # config.json + dil verisi yükleme
app/text_tr.py         # tr_upper/tr_lower (Türkçe i/ı kuralı)
app/render.py          # çizim, animasyon, yıldızlar, kutlama
app/audio.py           # wav yükleme ve çalma
app/game_modes.py      # Serbest Mod / Harfi Bul durum makinesi
data/tr.json           # alfabe, harf sesleri, ekran metinleri
data/en.json
scripts/build_audio.py # sesleri offline üretir
scripts/wav_trim.py    # taşıyıcı cümleden kesme, uzatma, efekt sentezi
scripts/make_icon.py   # masaüstü ikonu
audio/                 # üretilmiş wav'lar (depoya dahil)
tests/                 # 111 test
```

### Neden bu kadar az CPU kullanıyor?

Oyun sonsuz döngüde dönmez. `pygame.event.wait()` ile bloklanır ve olay
gelmediğinde işlemciyi meşgul etmez. Ekran yalnızca durum değiştiğinde yeniden
çizilir. 30 FPS'lik zamanlayıcı sadece animasyon ve ESC geri sayımı sırasında
açılır, biter bitmez kapanır. Ses kuyruğu için ayrı ve daha seyrek (120 ms)
bir zamanlayıcı vardır, kuyruk boşalınca o da kapanır.

### CPU ölçümü

```bash
.venv/bin/python main.py --windowed &
PID=$!; sleep 5; ps -o time= -p $PID; sleep 30; ps -o time= -p $PID
```

İki değerin farkı 30 saniyede harcanan CPU süresidir. Linux'ta canlı izlemek için:

```bash
top -b -n 5 -d 1 -p $(pgrep -f "main.py")
```

Ölçüm sonuçları için PLAN.md'ye bakın.
