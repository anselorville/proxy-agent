#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

echo "=== Backup China Stock Proxy ==="

echo "Creating backup: $TIMESTAMP"

docker-compose exec -T postgres pg_dump -U stock_user stock_data | gzip > "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql.gz"

if [ $? -eq 0 ]; then
    echo "Database backup successful: $BACKUP_DIR/postgres_backup_$TIMESTAMP.sql.gz"
else
    echo "Database backup failed"
    exit 1
fi

if [ -d "data/redis" ]; then
    cp -r data/redis "$BACKUP_DIR/redis_backup_$TIMESTAMP"
    echo "Redis backup successful: $BACKUP_DIR/redis_backup_$TIMESTAMP"
fi

echo "Configuration backup..."
cp .env "$BACKUP_DIR/env_backup_$TIMESTAMP"
cp docker-compose.yml "$BACKUP_DIR/docker-compose_backup_$TIMESTAMP"

echo "Backup completed: $TIMESTAMP"
echo "Backup location: $BACKUP_DIR"
echo ""
echo "To restore from backup:"
echo "  gunzip < backups/postgres_backup_$TIMESTAMP.sql.gz | docker-compose exec -T postgres psql -U stock_user stock_data"
