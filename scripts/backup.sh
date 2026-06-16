#!/usr/bin/env bash
set -e

BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
PROJECT_DIR="/opt/relaxpanel"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "🗄️  Backing up Açar🔐..."

cd "$PROJECT_DIR"

# Backup SQLite database
docker-compose exec -T app tar czf - /app/data > "$BACKUP_DIR/acar_backup_$DATE.tar.gz"

# Keep last 7 backups
ls -t "$BACKUP_DIR"/acar_backup_*.tar.gz | tail -n +8 | xargs -r rm -f

echo "✅ Backup saved: $BACKUP_DIR/acar_backup_$DATE.tar.gz"
