#!/usr/bin/env bash
# Harf Oyunu kurulumu: sanal ortam, bağımlılık, sesler, masaüstü kısayolu.
# Tekrar tekrar çalıştırılabilir; var olanı bozmaz.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$INSTALL_DIR/.venv"
cd "$INSTALL_DIR"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m[!]\033[0m %s\n' "$1"; }
error() { printf '\033[1;31m[HATA]\033[0m %s\n' "$1" >&2; }

# 1. Python sürümü -----------------------------------------------------------
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    error "python3 bulunamadı. Kurmak için:"
    echo "    sudo apt install python3 python3-venv    # Debian/Ubuntu"
    exit 1
fi
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    error "Python 3.10 veya üstü gerekli (bulunan: $("$PYTHON" -V))"
    exit 1
fi
info "Python: $("$PYTHON" -V)"

# 2. Sanal ortam -------------------------------------------------------------
# Yalnızca .venv/bin/python'a bakmak yetmez: python3-venv kurulu değilken
# ortam yarım kalıyor (python var, pip yok). pip'i de sınayıp gerekirse
# ortamı baştan kuruyoruz.
venv_ok() {
    [ -x "$VENV/bin/python" ] \
        && "$VENV/bin/python" -m pip --version >/dev/null 2>&1
}

apt_hint() {
    error "$1"
    echo "    sudo apt install python3-venv python3-pip     # Debian/Ubuntu"
    echo "    sudo dnf install python3-virtualenv python3-pip  # Fedora"
}

if venv_ok; then
    info "Sanal ortam zaten var, kullanılıyor"
else
    if [ -e "$VENV" ]; then
        warn "Sanal ortam eksik ya da bozuk, yeniden kuruluyor"
        rm -rf "$VENV"
    fi
    info "Sanal ortam oluşturuluyor: .venv"
    if ! "$PYTHON" -m venv "$VENV"; then
        apt_hint "venv oluşturulamadı. Eksik paketi kurup tekrar deneyin:"
        exit 1
    fi
    # Bazı dağıtımlarda venv pip'siz kurulabiliyor; kurtarmayı deneyelim
    venv_ok || "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
    if ! venv_ok; then
        apt_hint "Sanal ortamda pip yok. Eksik paketi kurup tekrar deneyin:"
        exit 1
    fi
fi

info "pygame-ce kuruluyor"
# 'pip' betiği yerine 'python -m pip': yolu bozuk ortamlarda da çalışır
"$VENV/bin/python" -m pip install --quiet --upgrade pip
if ! "$VENV/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"; then
    error "pygame-ce kurulamadı. İnternet bağlantısını kontrol edin."
    echo "    Derleme hatası alıyorsanız: sudo apt install python3-dev build-essential"
    exit 1
fi

# 3. Sesler ------------------------------------------------------------------
# Sesler depoyla birlikte geldiği için normalde üretim gerekmez.
WAV_COUNT=$(find "$INSTALL_DIR/audio" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
if [ "$WAV_COUNT" -gt 0 ]; then
    info "Sesler hazır ($WAV_COUNT dosya), yeniden üretilmiyor"
else
    warn "Ses dosyaları yok, üretiliyor (bir kerelik, internet gerekmez)"
    if ! "$VENV/bin/python" "$INSTALL_DIR/scripts/build_audio.py"; then
        warn "Sesler üretilemedi. Oyun sessiz çalışır; yukarıdaki komutu"
        warn "çalıştırıp 'bash install.sh' ile tekrar deneyebilirsiniz."
    fi
fi

# 4. İkon --------------------------------------------------------------------
if [ ! -f "$INSTALL_DIR/icon.png" ]; then
    info "İkon üretiliyor"
    "$VENV/bin/python" "$INSTALL_DIR/scripts/make_icon.py" >/dev/null
fi

# 5. Doğrulama ---------------------------------------------------------------
info "Kurulum doğrulanıyor"
if ! "$VENV/bin/python" "$INSTALL_DIR/main.py" --self-check; then
    error "Doğrulama başarısız. Yukarıdaki çıktıyı paylaşın."
    exit 1
fi

# 6. Kısayollar (yalnızca Linux) ---------------------------------------------
desktop_dir() {
    # Masaüstü klasörü dile göre değişir (Desktop / Masaüstü)
    if command -v xdg-user-dir >/dev/null 2>&1; then
        xdg-user-dir DESKTOP 2>/dev/null && return 0
    fi
    for candidate in "$HOME/Desktop" "$HOME/Masaüstü"; do
        [ -d "$candidate" ] && echo "$candidate" && return 0
    done
    return 1
}

if [ "$(uname -s)" = "Linux" ]; then
    ENTRY="$(mktemp)"
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
        "$INSTALL_DIR/harf-oyunu.desktop.in" > "$ENTRY"
    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$ENTRY" && info "Kısayol dosyası doğrulandı"
    fi

    # a) Uygulama menüsü
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"
    install -m 755 "$ENTRY" "$APPS_DIR/harf-oyunu.desktop"
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$APPS_DIR" 2>/dev/null || true
    info "Uygulama menüsüne eklendi: 'Harf Oyunu'"

    # b) Masaüstü ikonu (çocuk terminale girmeden çift tıklayabilsin)
    if DESK="$(desktop_dir)" && [ -n "$DESK" ] && [ -d "$DESK" ]; then
        install -m 755 "$ENTRY" "$DESK/harf-oyunu.desktop"
        # Cinnamon/GNOME masaüstündeki kısayolu "güvenilir" işaretlemeden
        # çalıştırmıyor; işaretlenmezse çift tıklayınca uyarı çıkıyor
        if command -v gio >/dev/null 2>&1; then
            gio set "$DESK/harf-oyunu.desktop" metadata::trusted true 2>/dev/null \
                || gio set "$DESK/harf-oyunu.desktop" \
                       -t string metadata::trusted yes 2>/dev/null || true
        fi
        # Nemo/Nautilus ikonu hemen yenilesin diye dosyaya dokun
        touch "$DESK/harf-oyunu.desktop"
        info "Masaüstü ikonu kuruldu: $DESK/harf-oyunu.desktop"
    else
        warn "Masaüstü klasörü bulunamadı, yalnızca menü girdisi eklendi"
    fi
    rm -f "$ENTRY"
else
    info "macOS: kısayollar atlandı (menü/masaüstü girdisi Linux'a özgü)"
fi

echo
info "Kurulum tamam. Başlatmak için:"
echo "    $VENV/bin/python $INSTALL_DIR/main.py"
