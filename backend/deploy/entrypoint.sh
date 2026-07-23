#!/bin/sh
set -eu

artifact_dir="${ITSPEAK_ARTIFACT_DIR:-/data/itspeak-sessions}"
matplotlib_dir="${MPLCONFIGDIR:-/tmp/itspeak-matplotlib}"

mkdir -p "$artifact_dir" "$matplotlib_dir"
chown -R itspeak:itspeak "$artifact_dir" "$matplotlib_dir"

python -m itspeak.preflight

exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
