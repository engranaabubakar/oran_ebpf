#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-enp1s0f0np0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBJ="${ROOT_DIR}/build/tc_gtpu_telemetry.o"
STATE_FILE="${ROOT_DIR}/results/attached_state_bidir.json"

require() { command -v "$1" >/dev/null 2>&1 || { echo "missing command: $1" >&2; exit 1; }; }
require tc
require bpftool
require jq

[[ -f "$OBJ" ]] || make -C "$ROOT_DIR" all

mkdir -p "${ROOT_DIR}/results"

echo "[INFO] Installing clsact on ${IFACE}"
tc qdisc replace dev "$IFACE" clsact

(tc filter del dev "$IFACE" ingress pref 1 handle 1 bpf 2>/dev/null) || true
(tc filter del dev "$IFACE" egress  pref 1 handle 1 bpf 2>/dev/null) || true

echo "[INFO] Attaching ingress"
tc filter add dev "$IFACE" ingress pref 1 handle 1 bpf da obj "$OBJ" sec classifier
echo "[INFO] Attaching egress"
tc filter add dev "$IFACE" egress  pref 1 handle 1 bpf da obj "$OBJ" sec classifier

ING_JSON="$(tc -j filter show dev "$IFACE" ingress | jq 'map(select(.kind=="bpf" and .pref==1 and (.options.prog.id? != null))) | .[0]')"
EGR_JSON="$(tc -j filter show dev "$IFACE" egress  | jq 'map(select(.kind=="bpf" and .pref==1 and (.options.prog.id? != null))) | .[0]')"

ING_PROG_ID="$(jq -r '.options.prog.id // empty' <<<"$ING_JSON")"
EGR_PROG_ID="$(jq -r '.options.prog.id // empty' <<<"$EGR_JSON")"

if [[ -z "$ING_PROG_ID" || -z "$EGR_PROG_ID" ]]; then
  echo "[ERROR] Unable to determine ingress/egress prog ids" >&2
  exit 1
fi

ING_MAP_IDS="$(bpftool -j prog show id "$ING_PROG_ID" | jq 'if type=="array" then .[0].map_ids else .map_ids end')"
EGR_MAP_IDS="$(bpftool -j prog show id "$EGR_PROG_ID" | jq 'if type=="array" then .[0].map_ids else .map_ids end')"

jq -n \
  --arg iface "$IFACE" \
  --arg obj "$OBJ" \
  --arg ing_prog_id "$ING_PROG_ID" \
  --arg egr_prog_id "$EGR_PROG_ID" \
  --argjson ing_map_ids "$ING_MAP_IDS" \
  --argjson egr_map_ids "$EGR_MAP_IDS" \
  '{iface:$iface,obj:$obj,ingress_prog_id:($ing_prog_id|tonumber),egress_prog_id:($egr_prog_id|tonumber),ingress_map_ids:$ing_map_ids,egress_map_ids:$egr_map_ids,attached_at:(now|todate)}' \
  > "$STATE_FILE"

echo "[INFO] Bidirectional attach complete"
cat "$STATE_FILE"
