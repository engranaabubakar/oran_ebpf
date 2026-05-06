#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
PING_TARGET="${PING_TARGET:-12.1.1.1}"
PING_IFACE="${PING_IFACE:-oaitun_ue1}"
PING_COUNT="${PING_COUNT:-300}"

mkdir -p "${RESULTS_DIR}"

echo "[INFO] Baseline latency test (TC-BPF detached)"
sudo "${ROOT_DIR}/scripts/detach_tc_bpf.sh" "${IFACE:-enp1s0f0np0}" || true
ping -I "${PING_IFACE}" -c "${PING_COUNT}" "${PING_TARGET}" | tee "${RESULTS_DIR}/latency_baseline_ping.log"

echo "[INFO] TC-BPF latency test (TC-BPF attached)"
sudo "${ROOT_DIR}/scripts/attach_tc_bpf.sh" "${IFACE:-enp1s0f0np0}" "src/gtpu_tc_bpf.o"
ping -I "${PING_IFACE}" -c "${PING_COUNT}" "${PING_TARGET}" | tee "${RESULTS_DIR}/latency_tcbpf_ping.log"

echo "[INFO] Latency test complete"
