#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
IFACE="${IFACE:-enp1s0f0np0}"
IPERF_SERVER="${IPERF_SERVER:-192.168.200.20}"
DURATION="${DURATION:-20}"
UE_PING_TARGET="${UE_PING_TARGET:-12.1.1.1}"
UE_PING_IFACE="${UE_PING_IFACE:-oaitun_ue1}"

mkdir -p "$RESULTS_DIR"

sudo "$ROOT_DIR/scripts/attach.sh" "$IFACE"

# host-only load
sudo timeout "$DURATION" tcpdump -ni "$IFACE" udp port 2152 > "$RESULTS_DIR/pathsep_host_tcpdump.log" 2>/dev/null &
TPID=$!
iperf3 -c "$IPERF_SERVER" -P 16 -t "$DURATION" -O 3 > "$RESULTS_DIR/pathsep_host_iperf.log" || true
wait "$TPID" || true
sudo python3 "$ROOT_DIR/tools/read_stats.py" --json > "$RESULTS_DIR/pathsep_host_stats.json"

# ue-tunnel load
sudo timeout "$DURATION" tcpdump -ni "$IFACE" udp port 2152 > "$RESULTS_DIR/pathsep_ue_tcpdump.log" 2>/dev/null &
TPID=$!
docker exec oai-nr-ue ping -I "$UE_PING_IFACE" "$UE_PING_TARGET" -c "$DURATION" > "$RESULTS_DIR/pathsep_ue_ping.log" || true
wait "$TPID" || true
sudo python3 "$ROOT_DIR/tools/read_stats.py" --json > "$RESULTS_DIR/pathsep_ue_stats.json"

printf "mode,udp2152_packets\n" > "$RESULTS_DIR/path_separation_summary.csv"
printf "host,%s\n" "$(grep -c '2152' "$RESULTS_DIR/pathsep_host_tcpdump.log" || true)" >> "$RESULTS_DIR/path_separation_summary.csv"
printf "ue_tunnel,%s\n" "$(grep -c '2152' "$RESULTS_DIR/pathsep_ue_tcpdump.log" || true)" >> "$RESULTS_DIR/path_separation_summary.csv"

echo "[INFO] Wrote path separation outputs in $RESULTS_DIR"
