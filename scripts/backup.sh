#!/usr/bin/env bash
set -e

BACKUP_DIR="/root/backups"
PROJECT_DIR="/root/acar-panel-v2"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR"

# Backup SQLite database
docker exec acar_api tar czf - /app/data > "$BACKUP_DIR/acar_$DATE.tar.gz"

# Keep last 14 backups
ls -t "$BACKUP_DIR"/acar_*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "$(date) Backup: $BACKUP_DIR/acar_$DATE.tar.gz" >> "$BACKUP_DIR/backup.log"
