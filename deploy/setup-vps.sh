#!/usr/bin/env bash
# RetailIQ production VPS bootstrap — run this ONCE as root on a fresh server.
#
# What it does:
#   1. Installs Docker + Compose plugin
#   2. Installs Caddy as an automatic-HTTPS reverse proxy
#   3. Sets up the deploy directory and a systemd unit for the app
#   4. Creates a dedicated deploy user and prints instructions
#
# Usage:  bash setup-vps.sh yourdomain.com  (as root on the VPS)
#
# NOTE: this script is a template — the Caddy site address is set from $1.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "Usage: bash setup-vps.sh yourdomain.com"
  exit 1
fi

APP_DIR="/opt/retailiq"

echo "==> Setting up RetailIQ production on $DOMAIN"

# ---- 1. Docker + compose plugin ----
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing docker compose plugin..."
  apt-get update && apt-get install -y docker-compose-plugin
fi

# ---- 2. Caddy reverse proxy (automatic HTTPS) -----------------------------------
if ! command -v caddy >/dev/null 2>&1; then
  echo "==> Installing Caddy..."
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https ca-certificates curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  apt-get update && apt-get install -y caddy
fi

cat > /etc/caddy/Caddyfile.retailiq <<EOF
$DOMAIN {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /docs localhost:8000
    reverse_proxy /health localhost:8000
    reverse_proxy /metrics localhost:8000
    reverse_proxy / client:80
    encode gzip zstd

    # Optional: basic monitoring path for UptimeRobot-like pings
    respond /ping 200
}
EOF

# Merge the site into the main Caddyfile (append if not present)
if ! grep -q "$DOMAIN" /etc/caddy/Caddyfile 2>/dev/null; then
  cat /etc/caddy/Caddyfile.retailiq >> /etc/caddy/Caddyfile
fi
systemctl enable --now caddy

# ---- 3. App directory + deploy user -----------------------------------------------
mkdir -p "$APP_DIR"
useradd -r -s /bin/bash -d "$APP_DIR" retailiq 2>/dev/null || true
chown -R retailiq:retailiq "$APP_DIR"

echo ""
echo "RetailIQ server provisioned for $DOMAIN."
echo ""
echo "Next steps:"
echo "  1. Clone/release the app into $APP_DIR (via CI on push to main)."
echo "  2. Create $APP_DIR/.env from .env.example and set a strong SECRET_KEY."
echo "  3. Copy a backup rclone config to $APP_DIR/backup/rclone.conf if using off-box backups."
echo "  4. docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "CI/CD deploy: add these secrets to the repo:"
echo "  VPS_HOST        = your VPS IP"
echo "  VPS_USER        = a user with sudo/ssh access"
echo "  VPS_SSH_KEY     = private key for that user"
echo "  VPS_PORT        = 22 (or custom)"
echo "  VPS_DIR         = $APP_DIR"
