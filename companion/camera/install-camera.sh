#!/bin/bash
# Install the MaameDrone camera stream on the Pi. Run from this folder with sudo:
#   sudo ./install-camera.sh            # MediaMTX v1.21.3
#   sudo ./install-camera.sh v1.22.0    # another release
# Needs: Raspberry Pi OS Bookworm/Trixie, a Pi camera on the CSI port, internet on the Pi.
# Then in ArduDeck: Camera panel > "Maame Pi camera (Wi-Fi)".
set -euo pipefail
VERSION="${1:-v1.21.3}"
HERE="$(cd "$(dirname "$0")" && pwd)"

case "$(uname -m)" in
    armv6l) ARCH=armv6 ;;
    armv7l) ARCH=armv7 ;;
    aarch64) ARCH=arm64 ;;
    *) echo "unsupported CPU $(uname -m)" >&2; exit 1 ;;
esac
FILE="mediamtx_${VERSION}_linux_${ARCH}.tar.gz"
URL="https://github.com/bluenviron/mediamtx/releases/download/${VERSION}"

if ! rpicam-hello --list-cameras 2>/dev/null | grep -q '^0 :'; then
    echo "warning: no camera detected (rpicam-hello --list-cameras); installing anyway" >&2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -o "$TMP/$FILE" "$URL/$FILE"
curl -fsSL -o "$TMP/checksums.sha256" "$URL/checksums.sha256"
# refuse a corrupted or tampered download (lines read "<sha256> *<file>")
(cd "$TMP" && grep -E " \*?${FILE}\$" checksums.sha256 | sha256sum -c -)
tar -xzf "$TMP/$FILE" -C "$TMP" mediamtx

install -m 755 "$TMP/mediamtx" /usr/local/bin/mediamtx
install -d -m 755 /etc/maame-camera
install -m 644 "$HERE/mediamtx.yml" /etc/maame-camera/mediamtx.yml
install -m 644 "$HERE/maame-camera.service" /etc/systemd/system/maame-camera.service
systemctl daemon-reload
systemctl enable --now maame-camera.service
sleep 3
systemctl --no-pager --lines=5 status maame-camera.service || true
echo "stream: rtsp://$(hostname).local:8554/cam"
