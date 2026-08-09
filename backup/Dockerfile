# Backup container: MySQL client + rclone for off-box storage.
FROM alpine:3.19

RUN apk add --no-cache mysql-client rclone bash

COPY backup.sh /backup/backup.sh
RUN chmod +x /backup/backup.sh

ENTRYPOINT ["/bin/sh", "/backup/backup.sh"]
