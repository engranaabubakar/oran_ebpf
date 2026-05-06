#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-enp1s0f0np0}"
OBJ="${2:-src/gtpu_tc_bpf.o}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Build expected object if missing or if alias path requested
if [[ "${OBJ}" == "src/gtpu_tc_bpf.o" ]]; then
  make -C "${ROOT_DIR}" all
fi

exec "${ROOT_DIR}/scripts/attach.sh" "${IFACE}"
