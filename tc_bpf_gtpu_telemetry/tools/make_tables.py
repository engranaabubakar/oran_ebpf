#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def load_single_row_csv(path: Path):
    if not path.exists():
        return {}
    with path.open() as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()

    rdir = Path(args.results_dir)

    baseline_iperf = load_single_row_csv(rdir / "baseline_iperf_metrics.csv")
    tcbpf_iperf = load_single_row_csv(rdir / "tcbpf_iperf_metrics.csv")
    baseline_cpu = load_single_row_csv(rdir / "baseline_cpu_metrics.csv")
    tcbpf_cpu = load_single_row_csv(rdir / "tcbpf_cpu_metrics.csv")
    base_ping = load_single_row_csv(rdir / "latency_baseline_metrics.csv")
    tcbpf_ping = load_single_row_csv(rdir / "latency_tcbpf_metrics.csv")

    table2_rows = [
        {
            "Mode": "baseline",
            "Throughput Gb/s": baseline_iperf.get("throughput_gbps", ""),
            "CPU avg %": baseline_cpu.get("cpu_avg_percent", ""),
            "softirq avg %": baseline_cpu.get("softirq_avg_percent", ""),
            "packet drops": "",
            "retransmissions": baseline_iperf.get("retransmissions", ""),
        },
        {
            "Mode": "tc_bpf",
            "Throughput Gb/s": tcbpf_iperf.get("throughput_gbps", ""),
            "CPU avg %": tcbpf_cpu.get("cpu_avg_percent", ""),
            "softirq avg %": tcbpf_cpu.get("softirq_avg_percent", ""),
            "packet drops": "",
            "retransmissions": tcbpf_iperf.get("retransmissions", ""),
        },
    ]
    write_csv(
        rdir / "table2_baseline_vs_tcbpf.csv",
        ["Mode", "Throughput Gb/s", "CPU avg %", "softirq avg %", "packet drops", "retransmissions"],
        table2_rows,
    )

    table3_rows = [
        {
            "Mode": "baseline",
            "avg RTT": base_ping.get("avg_ms", ""),
            "P50": base_ping.get("p50_ms", ""),
            "P95": base_ping.get("p95_ms", ""),
            "P99": base_ping.get("p99_ms", ""),
            "P99.9": base_ping.get("p999_ms", ""),
            "max": base_ping.get("max_ms", ""),
            "packet loss": base_ping.get("loss_percent", ""),
        },
        {
            "Mode": "tc_bpf",
            "avg RTT": tcbpf_ping.get("avg_ms", ""),
            "P50": tcbpf_ping.get("p50_ms", ""),
            "P95": tcbpf_ping.get("p95_ms", ""),
            "P99": tcbpf_ping.get("p99_ms", ""),
            "P99.9": tcbpf_ping.get("p999_ms", ""),
            "max": tcbpf_ping.get("max_ms", ""),
            "packet loss": tcbpf_ping.get("loss_percent", ""),
        },
    ]
    write_csv(
        rdir / "table3_latency_impact.csv",
        ["Mode", "avg RTT", "P50", "P95", "P99", "P99.9", "max", "packet loss"],
        table3_rows,
    )


if __name__ == "__main__":
    main()
