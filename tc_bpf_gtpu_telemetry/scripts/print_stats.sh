#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo python3 "${ROOT_DIR}/tools/read_stats.py" "$@"
fi
exec python3 "${ROOT_DIR}/tools/read_stats.py" "$@"
