#!/bin/sh
# RetailIQ automated backup — nightly mysqldump, compressed, uploaded off-box.
#
# Runs inside the `backup` container (alpine). Requires:
#   - BACKUP_REMOTE set in .env, e.g. s3:retailiq-backups:/prod (rclone remote)
#   - /backup/rclone.conf with the remote's credentials
#
# If BACKUP_REMOTE is empty, backups are kept locally under /backup/local.

set -e

STAMP=$(date +%Y%m%d-%H%M%S)
DUMP=/backup/local/retailiq-$STAMP.sql.gz
KEEP_LOCAL=14          # days of local copies
RCLONE=/backup/rclone.conf

mkdir -p /backup/local

echo "[backup] dumping database..."
mysqldump \
  -h db -u retailiq -p"$MYSQL_PASSWORD" retailiq \
  --single-transaction --quick --routines --triggers \
  | gzip > "$DUMP"

echo "[backup] wrote $DUMP ($(du -h "$DUMP" | cut -f1))"

if [ -n "$BACKUP_REMOTE" ] && [ -f "$RCLONE" ]; then
  echo "[backup] uploading to $BACKUP_REMOTE ..."
  if command -v rclone >/dev/null 2>&1; then
    rclone --config "$RCLONE" copy "$DUMP" "$BACKUP_REMOTE"
    echo "[backup] upload complete"
  else
    echo "[backup] WARNING: rclone not installed in this image; keeping local copy only"
  fi
fi

echo "[backup] pruning local copies older than ${KEEP_LOCAL} days"
find /backup/local -name 'retailiq-*.sql.gz' -mtime +"$KEEP_LOCAL" -delete

echo "[backup] done"
