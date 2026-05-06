#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-enp1s0f0np0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="${ROOT_DIR}/results/attached_state.json"

echo "[INFO] Detaching BPF filter from ${IFACE} ingress"
(tc filter del dev "${IFACE}" ingress pref 1 handle 1 bpf 2>/dev/null) || true

# keep clsact only if user wants it for other filters; default remove for clean testbed
(tc qdisc del dev "${IFACE}" clsact 2>/dev/null) || true

rm -f "${STATE_FILE}"
echo "[INFO] Detached and cleaned state"
