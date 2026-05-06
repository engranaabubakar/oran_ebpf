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

echo "[INFO] Baseline mode: detaching TC-BPF"
sudo "${ROOT_DIR}/scripts/detach_tc_bpf.sh" "${IFACE}" || true

echo "[INFO] Running iperf3 baseline"
iperf3 -c "${IPERF_SERVER}" -p "${IPERF_PORT}" -P "${IPERF_PAR}" -t "${IPERF_TIME}" -O "${IPERF_OMIT}" \
  | tee "${RESULTS_DIR}/baseline_iperf.log"
iperf3 -c "${IPERF_SERVER}" -p "${IPERF_PORT}" -P "${IPERF_PAR}" -t "${IPERF_TIME}" -O "${IPERF_OMIT}" -J \
  > "${RESULTS_DIR}/baseline_iperf.json"

echo "[INFO] Collecting CPU and link stats"
mpstat -P ALL 1 "${IPERF_TIME}" | tee "${RESULTS_DIR}/baseline_cpu.log"
ip -s link show "${IFACE}" | tee "${RESULTS_DIR}/baseline_link_stats.log"

echo "[INFO] Baseline run complete"
