#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
DURATION="${DURATION:-60}"
IFACE="${IFACE:-enp1s0f0np0}"

mkdir -p "${RESULTS_DIR}"

echo "[INFO] CPU overhead baseline (no TC-BPF)"
sudo "${ROOT_DIR}/scripts/detach_tc_bpf.sh" "${IFACE}" || true
mpstat -P ALL 1 "${DURATION}" | tee "${RESULTS_DIR}/cpu_overhead_baseline_mpstat.log"

if command -v pidstat >/dev/null 2>&1; then
  pidstat -wru 1 "${DURATION}" | tee "${RESULTS_DIR}/cpu_overhead_baseline_pidstat.log"
fi

echo "[INFO] CPU overhead with TC-BPF"
sudo "${ROOT_DIR}/scripts/attach_tc_bpf.sh" "${IFACE}" "src/gtpu_tc_bpf.o"
mpstat -P ALL 1 "${DURATION}" | tee "${RESULTS_DIR}/cpu_overhead_tcbpf_mpstat.log"

if command -v pidstat >/dev/null 2>&1; then
  pidstat -wru 1 "${DURATION}" | tee "${RESULTS_DIR}/cpu_overhead_tcbpf_pidstat.log"
fi

echo "[INFO] CPU overhead test complete"
