#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
})


def read_single(path: Path):
    if not path.exists():
        return {}
    with path.open() as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def throughput_plot(results_dir: Path, out_dir: Path):
    b = read_single(results_dir / "baseline_iperf_metrics.csv")
    t = read_single(results_dir / "tcbpf_iperf_metrics.csv")
    vals = [float(b.get("throughput_gbps", 0) or 0), float(t.get("throughput_gbps", 0) or 0)]
    labels = ["Baseline", "TC-BPF"]
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    ax.bar(labels, vals, color=["#4C78A8", "#F58518"])
    ax.set_ylabel("Throughput (Gb/s)")
    ax.set_title("Throughput Comparison")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "throughput_comparison.pdf")
    fig.savefig(out_dir / "throughput_comparison.png")
    plt.close(fig)


def cpu_plot(results_dir: Path, out_dir: Path):
    b = read_single(results_dir / "baseline_cpu_metrics.csv")
    t = read_single(results_dir / "tcbpf_cpu_metrics.csv")
    vals = [float(b.get("cpu_avg_percent", 0) or 0), float(t.get("cpu_avg_percent", 0) or 0)]
    labels = ["Baseline", "TC-BPF"]
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    ax.bar(labels, vals, color=["#54A24B", "#E45756"])
    ax.set_ylabel("CPU Avg (%)")
    ax.set_title("CPU Overhead Comparison")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "cpu_overhead_comparison.pdf")
    fig.savefig(out_dir / "cpu_overhead_comparison.png")
    plt.close(fig)


def latency_cdf_plot(results_dir: Path, out_dir: Path):
    def extract_samples(log_path: Path):
        samples = []
        if not log_path.exists():
            return samples
        for line in log_path.read_text(errors="ignore").splitlines():
            if "time=" in line and " ms" in line:
                try:
                    v = float(line.split("time=")[1].split(" ms")[0])
                    samples.append(v)
                except Exception:
                    pass
        return sorted(samples)

    base = extract_samples(results_dir / "latency_baseline_ping.log")
    tcbpf = extract_samples(results_dir / "latency_tcbpf_ping.log")

    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    for samples, label, color in [(base, "Baseline", "#4C78A8"), (tcbpf, "TC-BPF", "#F58518")]:
        if not samples:
            continue
        y = [(i + 1) / len(samples) for i in range(len(samples))]
        ax.plot(samples, y, label=label, color=color, linewidth=1.4)
    ax.set_xlabel("RTT (ms)")
    ax.set_ylabel("CDF")
    ax.set_title("Latency CDF")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "latency_cdf.pdf")
    fig.savefig(out_dir / "latency_cdf.png")
    plt.close(fig)


def teid_plot(results_dir: Path, out_dir: Path):
    snap = results_dir / "tcbpf_stats_snapshot.json"
    if not snap.exists():
        return
    data = json.loads(snap.read_text())
    teid_packets = data.get("teid_packets", {})
    teid_bytes = data.get("teid_bytes", {})
    if not teid_packets:
        return

    teids = sorted(teid_packets.keys(), key=lambda x: int(x))
    packets = [float(teid_packets[t]) for t in teids]
    bytes_ = [float(teid_bytes.get(t, 0)) for t in teids]

    fig, ax1 = plt.subplots(figsize=(5.0, 3.2))
    x = range(len(teids))
    ax1.bar([i - 0.2 for i in x], packets, width=0.4, label="Packets", color="#4C78A8")
    ax1.set_ylabel("Packets")
    ax2 = ax1.twinx()
    ax2.bar([i + 0.2 for i in x], bytes_, width=0.4, label="Bytes", color="#F58518")
    ax2.set_ylabel("Bytes")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(teids, rotation=30, ha="right")
    ax1.set_title("Per-TEID Counters")
    ax1.set_xlabel("TEID")
    ax1.grid(axis="y", alpha=0.3)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "per_teid_counters.pdf")
    fig.savefig(out_dir / "per_teid_counters.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--out-dir", default="figures")
    args = ap.parse_args()

    rdir = Path(args.results_dir)
    odir = Path(args.out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    throughput_plot(rdir, odir)
    cpu_plot(rdir, odir)
    latency_cdf_plot(rdir, odir)
    teid_plot(rdir, odir)


if __name__ == "__main__":
    main()
