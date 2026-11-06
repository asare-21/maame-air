#!/bin/bash
# Install the MAVLink2 signing key the Maame companion signs with. Run on the Pi with sudo.
#   sudo ./install-signing-key.sh --generate   new random key; prints it once for ArduDeck
#   sudo ./install-signing-key.sh < key.hex    use an existing 64-hex-char key from stdin
# The FC and ArduDeck must hold the same key: paste the hex into ArduDeck
# (Settings > Signing, key field accepts raw hex), then "Send to FC" and enable signing.
set -euo pipefail
KEY_FILE=/etc/maame/mavlink-signing.key

if [ "${1:-}" = "--generate" ]; then
    key="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
else
    read -r key
fi
key="$(printf '%s' "$key" | tr -d '[:space:]' | tr 'A-F' 'a-f')"
if ! [[ "$key" =~ ^[0-9a-f]{64}$ ]]; then
    echo "key must be 64 hex characters" >&2
    exit 1
fi

install -d -m 700 /etc/maame
umask 077
printf '%s\n' "$key" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
echo "installed $KEY_FILE (root, 600); restart maame-startup to use it"
[ "${1:-}" = "--generate" ] && echo "key for ArduDeck: $key"
exit 0
