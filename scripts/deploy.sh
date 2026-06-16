#!/usr/bin/env bash
set -e

# ==========================================
# Açar🔐 — One-Click Deploy Script
# Ubuntu 20.04/22.04/24.04, Debian 11/12
# ==========================================

echo "🚀 Açar🔐 Auto-Deploy starting..."

PROJECT_DIR="/opt/acar"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-$(openssl rand -base64 24)}"

# 1. Install Docker + Docker Compose if not present
if ! command -v docker &>/dev/null; then
    echo "📦 Installing Docker..."
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(lsb_release -is | tr '[:upper:]' '[:lower:]')/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(lsb_release -is | tr '[:upper:]' '[:lower:]') $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo "📦 Installing docker-compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Prefer 'docker compose' over 'docker-compose'
DC="docker compose"
if ! docker compose version &>/dev/null; then
    DC="docker-compose"
fi

# 2. Prepare project directory
echo "📁 Preparing $PROJECT_DIR..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# If we are running inside project folder, copy. Otherwise assume user cloned.
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml already present"
else
    echo "⚠️  Please copy all project files to $PROJECT_DIR before running this script."
    exit 1
fi

# 3. Create .env
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env with auto-generated secrets..."
    cat > .env <<EOF
DATABASE_URL=sqlite:///./data/relaxpanel.db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=$(openssl rand -hex 32)
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
FIRST_ADMIN_USERNAME=$ADMIN_USER
FIRST_ADMIN_PASSWORD=$ADMIN_PASS
HAPP_API_URL=https://happ.su/api/encrypt
EOF
    echo "✅ .env created. SAVE THIS PASSWORD:"
    echo "   Admin: $ADMIN_USER"
    echo "   Pass:  $ADMIN_PASS"
else
    echo "✅ .env already exists, keeping it."
fi

# 4. Ensure data dir exists
mkdir -p data

# 5. Pull and start
$DC pull
$DC up -d --build

echo ""
echo "========================================"
echo "  ✅ Açar🔐 deployed!"
echo "========================================"
echo ""

# 6. Wait for app to be ready
echo "⏳ Waiting for API to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 7. Check cloudflared tunnel URL
if $DC ps | grep -q cloudflared; then
    echo "☁️  Cloudflare Tunnel starting..."
    sleep 10
    TUNNEL_LOG=$($DC logs cloudflared --tail=20 2>&1)
    URL=$(echo "$TUNNEL_LOG" | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | tail -1)
    if [ -n "$URL" ]; then
        echo "🌐 Your panel URL:"
        echo "   $URL/app"
        echo "   Admin login: $ADMIN_USER / $ADMIN_PASS"
        echo "   (save this URL — it changes on restart unless you configure a named tunnel)"
    else
        echo "☁️  Cloudflared starting... Check logs: docker-compose logs -f cloudflared"
    fi
fi

echo ""
echo "📋 Useful commands:"
echo "   cd $PROJECT_DIR && $DC logs -f app     # API logs"
echo "   cd $PROJECT_DIR && $DC logs -f worker  # Worker logs"
echo "   cd $PROJECT_DIR && $DC ps              # Status"
echo "   cd $PROJECT_DIR && $DC down            # Stop everything"
echo ""

# 8. Create systemd service for auto-start
if [ ! -f /etc/systemd/system/acar.service ]; then
    echo "🛠️  Creating systemd service for auto-start..."
    cat > /etc/systemd/system/acar.service <<EOF
[Unit]
Description=Açar🔐 Panel
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$DC up -d
ExecStop=$DC down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable acar.service
    echo "✅ systemd service 'acar' created (auto-start on boot)"
fi

echo ""
echo "🎉 Done! Açar🔐 is running."
