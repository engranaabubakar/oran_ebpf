#!/usr/bin/env bash
set -euo pipefail
IFACE="${1:-enp1s0f0np0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[INFO] Detaching ingress/egress bpf filters on ${IFACE}"
(tc filter del dev "$IFACE" ingress pref 1 handle 1 bpf 2>/dev/null) || true
(tc filter del dev "$IFACE" egress  pref 1 handle 1 bpf 2>/dev/null) || true
(tc qdisc del dev "$IFACE" clsact 2>/dev/null) || true
rm -f "$ROOT_DIR/results/attached_state_bidir.json"
echo "[INFO] Detached bidirectional hooks"
