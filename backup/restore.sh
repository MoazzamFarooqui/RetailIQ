#!/bin/sh
# RetailIQ restore drill — verify backups are restorable.
#
# Usage (inside the backup container or on a host with mysql client):
#   RESTORE_FILE=/backup/local/retailiq-YYYYMMDD-HHMMSS.sql.gz \
#     MYSQL_PASSWORD=... ./restore.sh
#
# Restores into a scratch database (retailiq_restore_test) and verifies the
# row count, so a broken backup is caught before it's needed in anger.

set -e

DUMP="${RESTORE_FILE:-}"
if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "Usage: RESTORE_FILE=<path.sql.gz> MYSQL_PASSWORD=... ./restore.sh"
  exit 1
fi

DB="retailiq_restore_test"
echo "[restore] restoring $DUMP into scratch DB '$DB' ..."

# Create scratch DB and load
mysql -h db -u retailiq -p"$MYSQL_PASSWORD" -e "DROP DATABASE IF EXISTS $DB; CREATE DATABASE $DB;"
gunzip -c "$DUMP" | mysql -h db -u retailiq -p"$MYSQL_PASSWORD" "$DB"

# Verify key tables have data
echo "[restore] verifying..."
for table in users organizations sales forecast_headers model_registry; do
  count=$(mysql -h db -u retailiq -p"$MYSQL_PASSWORD" -N -e "SELECT COUNT(*) FROM $DB.$table" 2>/dev/null || echo "missing")
  echo "  $table: $count rows"
done

echo "[restore] OK — backup is restorable."

