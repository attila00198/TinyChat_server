#!/usr/bin/env bash
# install_certs_and_hook.sh
# Copies latest Certbot archive certs to /opt/tinychat/certs with correct perms,
# installs a Certbot renewal hook to re-copy & restart supervisor, and tests SSL load.

set -euo pipefail

ARCHIVE_DIR="/etc/letsencrypt/archive/krassus.ddns.net-0001"
DEST_DIR="/opt/tinychat/certs"
SERVICE_USER="tinychat"
SUPERVISOR_SERVICE="tinychat"
HOOK_PATH="/etc/letsencrypt/renewal-hooks/post/tinychat-copy.sh"

usage(){
  cat <<EOF
Usage: sudo $0 [archive_dir] [dest_dir]

Default archive dir: $ARCHIVE_DIR
Default destination dir: $DEST_DIR

This script must be run as root (it installs hook into /etc/letsencrypt).
EOF
}

if [ "${1-}" = "-h" ] || [ "${1-}" = "--help" ]; then
  usage
  exit 0
fi

if [ $# -ge 1 ] && [ -n "$1" ]; then
  ARCHIVE_DIR="$1"
fi
if [ $# -ge 2 ] && [ -n "$2" ]; then
  DEST_DIR="$2"
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Use sudo." >&2
  exit 2
fi

if [ ! -d "$ARCHIVE_DIR" ]; then
  echo "ERROR: archive directory not found: $ARCHIVE_DIR" >&2
  exit 3
fi

mkdir -p "$DEST_DIR"
chown root:root "$DEST_DIR"
chmod 755 "$DEST_DIR"

# Pick latest fullchain and privkey from archive (sorted by version)
FULL=$(ls -1 "$ARCHIVE_DIR"/fullchain*.pem 2>/dev/null | sort -V | tail -n1 || true)
KEY=$(ls -1 "$ARCHIVE_DIR"/privkey*.pem 2>/dev/null | sort -V | tail -n1 || true)

if [ -z "$FULL" ] || [ -z "$KEY" ]; then
  echo "ERROR: Could not find fullchain*.pem or privkey*.pem in $ARCHIVE_DIR" >&2
  exit 4
fi

echo "Found cert: $FULL"
echo "Found key:  $KEY"

echo "Copying latest certs to $DEST_DIR..."
cp -f "$FULL" "$DEST_DIR/fullchain.pem"
cp -f "$KEY" "$DEST_DIR/privkey.pem"

# Set ownership to service user and secure permissions
if id "$SERVICE_USER" >/dev/null 2>&1; then
  chown "$SERVICE_USER:$SERVICE_USER" "$DEST_DIR/fullchain.pem" "$DEST_DIR/privkey.pem" || true
else
  echo "Warning: user $SERVICE_USER not found; leaving ownership as root" >&2
fi

chmod 644 "$DEST_DIR/fullchain.pem"
chmod 640 "$DEST_DIR/privkey.pem"

# Install renewal hook to copy files and restart supervisor on renew
echo "Installing Certbot renewal hook at $HOOK_PATH"
mkdir -p "$(dirname "$HOOK_PATH")"
cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
set -e
ARCHIVE_DIR="/etc/letsencrypt/archive/krassus.ddns.net-0001"
DEST_DIR="/opt/tinychat/certs"
SERVICE_USER="tinychat"

FULL=$(ls -1 "$ARCHIVE_DIR"/fullchain*.pem | sort -V | tail -n1)
KEY=$(ls -1 "$ARCHIVE_DIR"/privkey*.pem | sort -V | tail -n1)

cp -f "$FULL" "$DEST_DIR/fullchain.pem"
cp -f "$KEY" "$DEST_DIR/privkey.pem"

chown "$SERVICE_USER:$SERVICE_USER" "$DEST_DIR/fullchain.pem" "$DEST_DIR/privkey.pem" || true
chmod 644 "$DEST_DIR/fullchain.pem"
chmod 640 "$DEST_DIR/privkey.pem"

# Restart the service so it picks up new certs
if command -v supervisorctl >/dev/null 2>&1; then
  supervisorctl restart tinychat || true
fi
HOOK

chmod +x "$HOOK_PATH"

# Test SSL load as the service user (attempt to load cert and key)
echo "Testing SSL load as user $SERVICE_USER..."
if id "$SERVICE_USER" >/dev/null 2>&1; then
  # Use python3 to load certs; if venv python preferred, user can run test manually
  sudo -u "$SERVICE_USER" python3 - <<'PY'
import ssl,sys
try:
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain('/opt/tinychat/certs/fullchain.pem', '/opt/tinychat/certs/privkey.pem')
    print('OK: SSL certs load for tinychat user')
except Exception as e:
    print('ERROR: SSL load failed:', e)
    sys.exit(1)
PY
else
  echo "Warning: user $SERVICE_USER not found; skipping SSL load test" >&2
fi

# Restart supervisor service to pick up changes
if command -v supervisorctl >/dev/null 2>&1; then
  echo "Restarting supervisor service $SUPERVISOR_SERVICE..."
  supervisorctl restart "$SUPERVISOR_SERVICE" || true
  supervisorctl status "$SUPERVISOR_SERVICE" || true
else
  echo "Warning: supervisorctl not found; please restart the service manually" >&2
fi

echo "Done. Certificates copied to $DEST_DIR and hook installed at $HOOK_PATH"
