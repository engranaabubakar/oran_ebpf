#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
IFACE="${IFACE:-enp1s0f0np0}"
IPERF_SERVER="${IPERF_SERVER:-192.168.200.20}"
IPERF_PORT="${IPERF_PORT:-5201}"
IPERF_PAR="${IPERF_PAR:-32}"
IPERF_TIME="${IPERF_TIME:-30}"
IPERF_OMIT="${IPERF_OMIT:-5}"

mkdir -p "${RESULTS_DIR}"

echo "[INFO] Attaching TC-BPF telemetry"
sudo "${ROOT_DIR}/scripts/attach_tc_bpf.sh" "${IFACE}" "src/gtpu_tc_bpf.o"

echo "[INFO] Running iperf3 with TC-BPF enabled"
iperf3 -c "${IPERF_SERVER}" -p "${IPERF_PORT}" -P "${IPERF_PAR}" -t "${IPERF_TIME}" -O "${IPERF_OMIT}" \
  | tee "${RESULTS_DIR}/tcbpf_iperf.log"
iperf3 -c "${IPERF_SERVER}" -p "${IPERF_PORT}" -P "${IPERF_PAR}" -t "${IPERF_TIME}" -O "${IPERF_OMIT}" -J \
  > "${RESULTS_DIR}/tcbpf_iperf.json"

echo "[INFO] Collecting CPU and link stats"
mpstat -P ALL 1 "${IPERF_TIME}" | tee "${RESULTS_DIR}/tcbpf_cpu.log"
ip -s link show "${IFACE}" | tee "${RESULTS_DIR}/tcbpf_link_stats.log"

"${ROOT_DIR}/scripts/show_gtpu_stats.sh" | tee "${RESULTS_DIR}/tcbpf_gtpu_stats.log"

if command -v curl >/dev/null 2>&1; then
  curl -sS http://127.0.0.1:18110/stats > "${RESULTS_DIR}/tcbpf_stats_snapshot.json" || true
fi

echo "[INFO] TC-BPF run complete"
