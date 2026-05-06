#!/usr/bin/env bash
set -euo pipefail
IFACE="${1:-enp1s0f0np0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${ROOT_DIR}/scripts/detach.sh" "${IFACE}"
