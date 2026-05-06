#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-enp1s0f0np0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBJ="${ROOT_DIR}/build/tc_gtpu_telemetry.o"
STATE_FILE="${ROOT_DIR}/results/attached_state.json"

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing command: $1" >&2; exit 1; }
}

require clang
require tc
require jq
require bpftool

mkdir -p "${ROOT_DIR}/results"

if [[ ! -f "${OBJ}" ]]; then
  echo "[INFO] Building BPF object..."
  make -C "${ROOT_DIR}" all
fi

echo "[INFO] Attaching clsact on ${IFACE}"
tc qdisc replace dev "${IFACE}" clsact

# Clean prior filter handle if present
(tc filter del dev "${IFACE}" ingress pref 1 handle 1 bpf 2>/dev/null) || true

echo "[INFO] Attaching BPF program on ingress"
tc filter add dev "${IFACE}" ingress pref 1 handle 1 bpf da obj "${OBJ}" sec classifier

FILTER_JSON="$(tc -j filter show dev "${IFACE}" ingress | jq 'map(select(.kind=="bpf" and .pref==1 and (.options.prog.id? != null))) | .[0]')"
if [[ "${FILTER_JSON}" == "null" || -z "${FILTER_JSON}" ]]; then
  echo "[ERROR] Unable to locate attached BPF filter" >&2
  exit 1
fi

PROG_ID="$(jq -r '.options.prog.id // empty' <<<"${FILTER_JSON}")"
if [[ -z "${PROG_ID}" ]]; then
  echo "[ERROR] Unable to extract attached BPF prog id" >&2
  exit 1
fi
MAP_IDS="$(bpftool -j prog show id "${PROG_ID}" | jq 'if type=="array" then .[0].map_ids else .map_ids end')"

jq -n \
  --arg iface "${IFACE}" \
  --arg obj "${OBJ}" \
  --arg prog_id "${PROG_ID}" \
  --argjson map_ids "${MAP_IDS}" \
  '{iface:$iface,obj:$obj,prog_id:($prog_id|tonumber),map_ids:$map_ids,attached_at:(now|todate)}' \
  > "${STATE_FILE}"

echo "[INFO] Attached successfully"
echo "[INFO] State file: ${STATE_FILE}"
cat "${STATE_FILE}"
