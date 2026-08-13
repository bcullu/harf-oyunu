#!/usr/bin/env bash
# Oyunu boşta çalıştırıp ortalama CPU kullanımını ölçer.
# Kullanım: bash scripts/measure_cpu.sh [saniye]   (varsayılan 30)
#
# Bir pencere açılır; ÖLÇÜM BİTENE KADAR DOKUNMAYIN, sonunda kendisi kapanır.

set -euo pipefail

DURATION="${1:-30}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$DIR/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

cpu_seconds() {  # ps TIME alanını (mm:ss veya hh:mm:ss) saniyeye çevirir
    ps -o time= -p "$1" 2>/dev/null | tr -d ' ' | awk -F: '
        NF==2 {print $1*60 + $2}
        NF==3 {print $1*3600 + $2*60 + $3}
        NF==0 {print ""}'
}

echo "Oyun açılıyor (pencere modunda). Lütfen ${DURATION} saniye dokunmayın..."
"$PYTHON" "$DIR/main.py" --windowed >/tmp/harf_oyunu_cpu.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT

sleep 5  # açılış ve ses yüklemesi ölçüme karışmasın
T0="$(cpu_seconds "$PID")"
if [ -z "$T0" ]; then
    echo "HATA: oyun başlamadı. Günlük: /tmp/harf_oyunu_cpu.log" >&2
    exit 1
fi

sleep "$DURATION"
T1="$(cpu_seconds "$PID")"
if [ -z "$T1" ]; then
    echo "HATA: pencere ölçüm sırasında kapandı, tekrar deneyin." >&2
    exit 1
fi

kill $PID 2>/dev/null || true

awk -v t0="$T0" -v t1="$T1" -v d="$DURATION" 'BEGIN {
    used = t1 - t0
    printf "\nBoşta %d saniyede kullanılan CPU: %.2f sn\n", d, used
    printf "Ortalama CPU kullanımı: %%%.2f\n", used / d * 100
    if (used / d * 100 < 1.0) print "Sonuç: hedefin (%1) altında. ✓"
    else print "Sonuç: hedefin üstünde. Bu çıktıyı paylaşın."
}'
