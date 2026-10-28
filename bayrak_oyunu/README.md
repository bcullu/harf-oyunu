# Bayrak Hırsızı

5 yaşındaki çocuklar için bayrak öğrenme oyunu. Okuma yazma gerekmez:
her şey resim, renk ve **Türkçe ses** ile anlatılır, tek tuşla oynanır.

Örümcek bekçi bir müze odasında bayrağı koruyor. Bekçi sırtını döndüğü anda
**boşluk tuşuna** basarak bir sonraki saklanma yerine geç. Beş doğru basışta
bayrak senin olur: ülkenin adı Türkçe söylenir ve bayrak panoya eklenir.
Kazanılan bayrak bir daha karşına çıkmaz; amaç 50 ülkenin hepsini toplamak.

- İzometrik, 2D pixel art (320x180 iç çözünürlük, tam sayı katıyla büyütülür)
- Tek tuş: **BOŞLUK**. Yanlış zamanda basmak oyunu bitirmez, bir adım geri atar
- 50 ülke bayrağı koda gömülü olarak çizilir, hiçbir görsel dosyası yoktur
- Türkçe seslendirme önceden üretilmiş wav'lardan gelir; oyun internete çıkmaz
- Çocuk yanlışlıkla kapatamaz (ESC iki saniye basılı tutulur)

Tek bağımlılık: `pygame-ce`. Linux ve macOS'ta çalışır; Python 3.8 ve üstü
yeter (eski dağıtımlar için kodda 3.9+ sözdizimi kullanılmadı).

---

## 1. Kurulum

```bash
bash install.sh
```

Betik sırayla şunları yapar:

1. Python 3.8+ var mı diye bakar
2. `.venv` adında bir sanal ortam kurar (sistem Python'ınıza dokunmaz)
3. `pygame-ce` kurar
4. Ses dosyalarını kontrol eder (hazır geldiği için yeniden üretmez)
5. Masaüstü ikonunu üretir
6. Kurulumu doğrular (`--self-check`)
7. Linux'ta uygulama menüsüne ve masaüstüne "Bayrak Hırsızı" kısayolu ekler

Betik birden çok kez çalıştırılabilir, var olanı bozmaz.

## 2. Çalıştırma

```bash
.venv/bin/python main.py
```

| Seçenek | Ne yapar |
| --- | --- |
| `--windowed` | Tam ekran yerine pencerede açar |
| `--self-check` | Pencere açmadan kurulumu doğrular |
| `--reset` | Toplanan bayrakları sıfırlar |
| `--seed 7` | Bayrak sırasını sabitler (test için) |

## 3. Nasıl oynanır

| Ekran | Boşluk tuşu ne yapar |
| --- | --- |
| Başlangıç | Çalınacak bayrağı gösterir, oyunu başlatır |
| Oyun | Güvenli anda bir sonraki saklanma yerine geçer |
| Kazanma | Bayrak panosunu açar |
| Pano | Yeni oyuna başlar |

Panoda **yön tuşlarıyla** bayraklar arasında gezilir; seçilen bayrağın adı
Türkçe söylenir. Başlangıç ve kazanma ekranında **B** tuşu da panoyu açar.

### Çocuk neye bakacak?

Üç işaret aynı anda değişir, hepsi tek şeyi söyler:

| Örümcek | Zemindeki ışık | Alttaki boşluk tuşu |
| --- | --- | --- |
| Bize bakıyor (beyaz gözler) | Sarı koni bizim tarafa dönük | Gri, üstünde iki kırmızı çizgi: **bekle** |
| Sırtı dönük (siyah örümcek) | Yeşil koni duvara dönük | Yeşil, yukarı ok ve "ding" sesi: **bas** |

Ayrıca gidilecek saklanma yeri yeşil parlar ve üstünde zıplayan bir ok belirir.

### Ebeveyn tuşları

| Tuş | Ne yapar |
| --- | --- |
| `+` / `-` | Ses seviyesi (kalıcı olarak kaydedilir) |
| `ESC` (2 sn basılı) | Oyundan çıkar |
| `Ctrl+Q` | Anında çıkar |

## 4. Zorluk

Güvenli pencere oyun ilerledikçe kısalır ama asla 1,15 saniyenin altına
inmez:

```
pencere = 2100 ms - 130 ms x adım - 8 ms x toplanan bayrak     (en az 1150 ms)
```

Yani ilk adımlar rahat, bayrağa yaklaştıkça heyecan artar; pano doldukça
oyun bir miktar hızlanır.

## 5. Dosyalar

```
main.py                oyun döngüsü, tuşlar, olay -> ses eşlemesi
app/game.py            devriye ritmi ve zamanlama (pygame içermez, test edilir)
app/render.py          izometrik oda, karakterler, ekranlar
app/flags.py           50 ülkenin adı ve kodla çizimi
app/progress.py        progress.json: toplanan bayraklar ve ses seviyesi
app/audio.py           wav'ları belleğe alır, konuşma ve efekt kanalları
app/speech.py          seslendirilecek Türkçe metinler
scripts/build_audio.py sesleri offline üretir (macOS `say` / espeak-ng)
scripts/make_icon.py   masaüstü ikonu
audio/tr/*.wav         110 konuşma dosyası (50 ülke adı + 50 cümle + 10 anlatım)
audio/sfx/*.wav        7 efekt (saf Python ile sentezlenir)
```

## 6. Sesleri yeniden üretmek

Sesler depoyla birlikte gelir. Başka bir sesle üretmek isterseniz:

```bash
.venv/bin/python scripts/build_audio.py --force
```

Motor sırası: macOS `say` (Türkçe ses **Yelda**) → `espeak-ng`. Linux'ta:

```bash
sudo apt install espeak-ng
```

Ses dosyası eksikse oyun sessiz çalışır, çökmez.

## 7. Testler

```bash
.venv/bin/python -m pytest -q
```

47 test: bayrak çizimleri, pano kaydı, devriye zamanlaması, yakalanma ve
kazanma yolu, her ekranın ekransız çizilmesi.
