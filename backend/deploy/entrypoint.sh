#!/bin/sh
set -eu

artifact_dir="${ITSPEAK_ARTIFACT_DIR:-/data/itspeak-sessions}"
matplotlib_dir="${MPLCONFIGDIR:-/tmp/itspeak-matplotlib}"
numba_cache_dir="${NUMBA_CACHE_DIR:-$artifact_dir/.numba-cache}"

mkdir -p "$artifact_dir" "$matplotlib_dir" "$numba_cache_dir"
chown -R itspeak:itspeak "$artifact_dir" "$matplotlib_dir" "$numba_cache_dir"

# Librosa uses Numba-compiled audio kernels. Keep their cache on the persistent
# artifact volume so deployments can reuse warmed analysis code.
export NUMBA_CACHE_DIR="$numba_cache_dir"

python -m itspeak.preflight

exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
