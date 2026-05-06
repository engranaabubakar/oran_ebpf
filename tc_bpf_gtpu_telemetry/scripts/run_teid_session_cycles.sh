#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
CYCLES="${CYCLES:-10}"
IFACE="${IFACE:-enp1s0f0np0}"
PING_TARGET="${PING_TARGET:-12.1.1.1}"
PING_IFACE="${PING_IFACE:-oaitun_ue1}"
PING_COUNT="${PING_COUNT:-8}"
SESSION_RESTART_CMD="${SESSION_RESTART_CMD:-}"

mkdir -p "$RESULTS_DIR"
OUT_CSV="$RESULTS_DIR/teid_cycle_observations.csv"

echo "cycle,gtpu_packets_total,gtpu_bytes_total,active_teids,teid_list" > "$OUT_CSV"

sudo "$ROOT_DIR/scripts/attach.sh" "$IFACE"

for i in $(seq 1 "$CYCLES"); do
  echo "[INFO] Cycle $i/$CYCLES"
  if [[ -n "$SESSION_RESTART_CMD" ]]; then
    echo "[INFO] Running session restart command"
    bash -lc "$SESSION_RESTART_CMD"
    sleep 2
  fi

  docker exec oai-nr-ue ping -I "$PING_IFACE" "$PING_TARGET" -c "$PING_COUNT" >/dev/null 2>&1 || true

  JSON=$(sudo python3 "$ROOT_DIR/tools/read_stats.py" --json)
  pkts=$(echo "$JSON" | jq -r '.global.gtpu_packets_total // 0')
  bytes=$(echo "$JSON" | jq -r '.global.gtpu_bytes_total // 0')
  teids=$(echo "$JSON" | jq -r '.per_teid_packets | keys')
  teid_count=$(echo "$JSON" | jq -r '.per_teid_packets | keys | length')
  teid_compact=$(echo "$JSON" | jq -c '.per_teid_packets | keys')

  echo "$i,$pkts,$bytes,$teid_count,\"$teid_compact\"" >> "$OUT_CSV"
done

echo "[INFO] Wrote $OUT_CSV"
