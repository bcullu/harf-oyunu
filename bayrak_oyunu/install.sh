#!/usr/bin/env bash
# Bayrak Hırsızı kurulumu: sanal ortam, bağımlılık, sesler, masaüstü kısayolu.
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
# Eski dağıtımlar için taban 3.8: kodda 3.9+ sözdizimi ya da stdlib çağrısı
# yok (tip ipuçları __future__ ile metin olarak tutuluyor).
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
    error "Python 3.8 veya üstü gerekli (bulunan: $("$PYTHON" -V))"
    echo "    sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
info "Python: $("$PYTHON" -V)"

# 2. Sanal ortam -------------------------------------------------------------
# Yalnızca .venv/bin/python'a bakmak yetmez: python3-venv kurulu değilken
# ortam yarım kalabiliyor (python var, pip yok). pip'i de sınıyoruz.
venv_ok() {
    [ -x "$VENV/bin/python" ] \
        && "$VENV/bin/python" -m pip --version >/dev/null 2>&1
}

apt_hint() {
    error "$1"
    echo "    sudo apt install python3-venv python3-pip        # Debian/Ubuntu"
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
    venv_ok || "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
    if ! venv_ok; then
        apt_hint "Sanal ortamda pip yok. Eksik paketi kurup tekrar deneyin:"
        exit 1
    fi
fi

info "pygame-ce kuruluyor"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
if ! "$VENV/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"; then
    error "pygame-ce kurulamadı. İnternet bağlantısını kontrol edin."
    echo "    Eski dağıtımlarda hazır paket bulunamayıp derleme gerekebilir:"
    echo "    sudo apt install python3-dev build-essential libsdl2-dev \\"
    echo "        libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev"
    exit 1
fi

# 3. Sesler ------------------------------------------------------------------
# Sesler depoyla birlikte geldiği için normalde üretim gerekmez.
if "$VENV/bin/python" "$INSTALL_DIR/scripts/build_audio.py" --check >/dev/null 2>&1; then
    info "Sesler hazır, yeniden üretilmiyor"
else
    warn "Ses dosyaları eksik, üretiliyor (bir kerelik, internet gerekmez)"
    if ! "$VENV/bin/python" "$INSTALL_DIR/scripts/build_audio.py"; then
        warn "Sesler üretilemedi. Oyun sessiz çalışır; eksik TTS motorunu"
        warn "kurup 'bash install.sh' ile tekrar deneyebilirsiniz."
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
    # Masaüstü klasörü dile göre değişir (Desktop / Masaüstü). xdg-user-dir
    # kurulu olsa bile boş bir yol dönebiliyor; sonucu doğrulayıp yedeklere
    # düşüyoruz.
    local candidate
    if command -v xdg-user-dir >/dev/null 2>&1; then
        candidate="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
        if [ -n "$candidate" ] && [ -d "$candidate" ] \
           && [ "$candidate" != "$HOME" ]; then
            echo "$candidate"
            return 0
        fi
    fi
    for candidate in "$HOME/Masaüstü" "$HOME/Desktop"; do
        [ -d "$candidate" ] && echo "$candidate" && return 0
    done
    return 1
}

if [ "$(uname -s)" = "Linux" ]; then
    ENTRY="$(mktemp)"
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
        "$INSTALL_DIR/bayrak-hirsizi.desktop.in" > "$ENTRY"
    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$ENTRY" && info "Kısayol dosyası doğrulandı"
    fi

    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"
    install -m 755 "$ENTRY" "$APPS_DIR/bayrak-hirsizi.desktop"
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$APPS_DIR" 2>/dev/null || true
    info "Uygulama menüsüne eklendi: 'Bayrak Hırsızı'"

    if DESK="$(desktop_dir)" && [ -n "$DESK" ] && [ -d "$DESK" ]; then
        install -m 755 "$ENTRY" "$DESK/bayrak-hirsizi.desktop"
        # Cinnamon/GNOME kısayolu "güvenilir" işaretlenmeden çalıştırmıyor
        if command -v gio >/dev/null 2>&1; then
            gio set "$DESK/bayrak-hirsizi.desktop" metadata::trusted true 2>/dev/null \
                || gio set "$DESK/bayrak-hirsizi.desktop" \
                       -t string metadata::trusted yes 2>/dev/null || true
        fi
        touch "$DESK/bayrak-hirsizi.desktop"
        info "Masaüstü ikonu kuruldu: $DESK/bayrak-hirsizi.desktop"
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
