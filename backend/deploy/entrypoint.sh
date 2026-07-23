#!/bin/sh
set -eu

artifact_dir="${ITSPEAK_ARTIFACT_DIR:-/data/itspeak-sessions}"
matplotlib_dir="${MPLCONFIGDIR:-/tmp/itspeak-matplotlib}"
numba_cache_dir="${NUMBA_CACHE_DIR:-$artifact_dir/.numba-cache}"

mkdir -p "$artifact_dir" "$matplotlib_dir" "$numba_cache_dir"
chown -R itspeak:itspeak "$artifact_dir" "$matplotlib_dir" "$numba_cache_dir"

# Librosa uses Numba-compiled kernels for pitch tracking. Keeping their cache
# on the persistent artifact volume avoids recompiling them after deployments
# without changing the pitch algorithm or any calibrated scoring inputs.
export NUMBA_CACHE_DIR="$numba_cache_dir"

python -m itspeak.preflight

exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
