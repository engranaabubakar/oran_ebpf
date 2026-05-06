# Lightweight TC-BPF GTP-U Telemetry for Containerized O-RAN xHaul Monitoring

## Overview
This repository provides a pass-only TC-BPF telemetry module to monitor 5G user-plane GTP-U traffic (UDP/2152) on O-RAN-aligned xHaul links. It enables global and per-TEID observability without modifying packet forwarding behavior.

## Testbed
- Access-side DGX (`spark-925b`)
  - xHaul interface: `enp1s0f0np0`
  - xHaul IP: `192.168.200.21`
  - OAI gNB + OAI NR-UE
  - UE tunnel: `oaitun_ue1`, UE IP `12.1.1.66`
- Core-side DGX (`spark-6e5e`)
  - xHaul IP: `192.168.200.20`
  - OAI 5GC: AMF, SMF, UPF, NRF, UDM, UDR, AUSF
  - UPF internal network IP often seen as `192.168.150.8`
- DNN: `oai.ipv4`
- Slice: `SST 1`, `SD 000001`

## Repository Layout
```text
tc_bpf_gtpu_telemetry/
├── include/
│   └── gtpu.h
├── src/
│   ├── tc_gtpu_telemetry.c
│   ├── gtpu_tc_bpf.c
│   └── telemetry_exporter.py
├── exporter/
│   └── server.py
├── scripts/
│   ├── attach.sh
│   ├── detach.sh
│   ├── print_stats.sh
│   ├── run_exporter.sh
│   ├── attach_tc_bpf.sh
│   ├── detach_tc_bpf.sh
│   ├── show_gtpu_stats.sh
│   ├── run_baseline.sh
│   ├── run_tcbpf.sh
│   ├── run_latency_test.sh
│   └── run_cpu_overhead_test.sh
├── tools/
│   ├── read_stats.py
│   ├── parse_ping.py
│   ├── parse_iperf.py
│   ├── parse_mpstat.py
│   ├── make_tables.py
│   └── make_plots.py
├── results/
├── figures/
├── Makefile
└── README.md
```

## Requirements
Install on access-side host:
```bash
sudo apt-get update
sudo apt-get install -y clang llvm bpftool iproute2 jq make python3 python3-pip sysstat iperf3
python3 -m pip install --user matplotlib
```

## Build
For ARM64 (DGX Spark):
```bash
cd /home/rana/Desktop/mcp-qos-server/smo_rapp/tc_bpf_gtpu_telemetry
make clean
make BPF_CLANG=clang BPF_CFLAGS="-O2 -g -Wall -Werror -target bpf -D__TARGET_ARCH_arm64 -Iinclude -I/usr/include/aarch64-linux-gnu" all
```

## Attach / Detach
Attach:
```bash
sudo ./scripts/attach_tc_bpf.sh enp1s0f0np0 src/gtpu_tc_bpf.o
```
Detach:
```bash
sudo ./scripts/detach_tc_bpf.sh enp1s0f0np0
```

## Validate GTP-U Telemetry
1. Confirm user-plane GTP-U packets:
```bash
sudo tcpdump -ni enp1s0f0np0 udp port 2152 -c 20
```
2. Print counters:
```bash
./scripts/show_gtpu_stats.sh
```
3. Start exporter:
```bash
./scripts/run_exporter.sh
```
4. Query endpoints:
```bash
curl -sS http://127.0.0.1:18110/health | jq .
curl -sS http://127.0.0.1:18110/stats | jq .
curl -sS http://127.0.0.1:18110/stats/teid | jq .
```

## Run Experiments
### Baseline (No TC-BPF)
```bash
./scripts/run_baseline.sh
```

### TC-BPF Enabled
```bash
./scripts/run_tcbpf.sh
```

### Latency Impact
```bash
PING_IFACE=oaitun_ue1 PING_TARGET=12.1.1.1 ./scripts/run_latency_test.sh
```

### CPU Overhead
```bash
DURATION=60 ./scripts/run_cpu_overhead_test.sh
```

## Parse Results and Generate Tables/Figures
### Parse iperf and CPU logs
```bash
python3 tools/parse_iperf.py --input results/baseline_iperf.json --mode baseline --output results/baseline_iperf_metrics.csv
python3 tools/parse_iperf.py --input results/tcbpf_iperf.json --mode tc_bpf --output results/tcbpf_iperf_metrics.csv
python3 tools/parse_mpstat.py --input results/baseline_cpu.log --mode baseline --output results/baseline_cpu_metrics.csv
python3 tools/parse_mpstat.py --input results/tcbpf_cpu.log --mode tc_bpf --output results/tcbpf_cpu_metrics.csv
```

### Parse ping latency logs
```bash
python3 tools/parse_ping.py --input results/latency_baseline_ping.log --mode baseline --output results/latency_baseline_metrics.csv
python3 tools/parse_ping.py --input results/latency_tcbpf_ping.log --mode tc_bpf --output results/latency_tcbpf_metrics.csv
```

### Build summary tables
```bash
python3 tools/make_tables.py --results-dir results
```

### Build publication-ready plots
```bash
python3 tools/make_plots.py --results-dir results --out-dir figures
```

## Table Templates
### Table 1: Functional validation
| Interface | Hook | Protocol | GTP-U packets | GTP-U bytes | active TEIDs | malformed packets |
|---|---|---|---:|---:|---:|---:|

### Table 2: Baseline vs TC-BPF overhead
| Mode | Throughput Gb/s | CPU avg % | softirq avg % | packet drops | retransmissions |
|---|---:|---:|---:|---:|---:|

### Table 3: Latency impact
| Mode | avg RTT | P50 | P95 | P99 | P99.9 | max | packet loss |
|---|---:|---:|---:|---:|---:|---:|---:|

### Table 4: Per-TEID telemetry
| TEID | packets | bytes | average packet size | direction |
|---:|---:|---:|---:|---|

### Table 5: tcpdump vs TC-BPF comparison
| Method | always-on suitability | per-TEID support | CPU overhead | packet processing path | limitations |
|---|---|---|---|---|---|

## Troubleshooting
- `gtpu_packets_total=0` with high traffic:
  - verify traffic is truly UE user-plane (`udp/2152`) not only host `iperf3`.
- exporter `/stats` empty reply:
  - restart exporter after updates, ensure running with root privileges.
- build fails with `asm/types.h` missing:
  - include ARM64 include path in `BPF_CFLAGS` as shown above.

## Safety Notes
- Current eBPF action is telemetry-only pass mode (`TC_ACT_OK`).
- No drop or packet rewrite logic is enabled.
- Keep this mode for production-safety during measurement campaigns.

## Citation
```text
@article{tbd_tc_bpf_gtpu_oran,
  title={Lightweight TC-BPF GTP-U Telemetry for Containerized O-RAN xHaul Monitoring},
  author={TBD},
  journal={TBD},
  year={TBD}
}
```
