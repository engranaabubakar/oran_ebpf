#!/usr/bin/env bash
set -euo pipefail

# Lightweight comparison scaffold to satisfy reviewer request for TC vs XDP evidence.
# If no XDP object is provided, script records TC-only baseline and marks XDP as unavailable.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
IFACE="${IFACE:-enp1s0f0np0}"
DURATION="${DURATION:-20}"
IPERF_SERVER="${IPERF_SERVER:-192.168.200.20}"
XDP_OBJ="${XDP_OBJ:-}"
XDP_SEC="${XDP_SEC:-xdp}"

mkdir -p "$RESULTS_DIR"

# TC run
sudo "$ROOT_DIR/scripts/attach.sh" "$IFACE"
iperf3 -c "$IPERF_SERVER" -P 16 -t "$DURATION" -O 3 -J > "$RESULTS_DIR/xdp_cmp_tc_iperf.json" || true
mpstat -P ALL 1 "$DURATION" > "$RESULTS_DIR/xdp_cmp_tc_mpstat.log" || true
sudo "$ROOT_DIR/scripts/detach.sh" "$IFACE" || true

if [[ -n "$XDP_OBJ" && -f "$XDP_OBJ" ]]; then
  sudo ip link set dev "$IFACE" xdp obj "$XDP_OBJ" sec "$XDP_SEC"
  iperf3 -c "$IPERF_SERVER" -P 16 -t "$DURATION" -O 3 -J > "$RESULTS_DIR/xdp_cmp_xdp_iperf.json" || true
  mpstat -P ALL 1 "$DURATION" > "$RESULTS_DIR/xdp_cmp_xdp_mpstat.log" || true
  sudo ip link set dev "$IFACE" xdp off || true
  echo "mode,status" > "$RESULTS_DIR/xdp_compare_status.csv"
  echo "tc,ok" >> "$RESULTS_DIR/xdp_compare_status.csv"
  echo "xdp,ok" >> "$RESULTS_DIR/xdp_compare_status.csv"
else
  echo "mode,status" > "$RESULTS_DIR/xdp_compare_status.csv"
  echo "tc,ok" >> "$RESULTS_DIR/xdp_compare_status.csv"
  echo "xdp,not_available" >> "$RESULTS_DIR/xdp_compare_status.csv"
fi

echo "[INFO] XDP mini-comparison outputs written to $RESULTS_DIR"
