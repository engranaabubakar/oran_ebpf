#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path

LINE_RE = re.compile(r"^\s*\d{2}:\d{2}:\d{2}\s+(AM|PM)\s+all\s+(.*)$")


def parse_mpstat(path: Path):
    cpu_vals = []
    softirq_vals = []

    for raw in path.read_text(errors="ignore").splitlines():
        m = LINE_RE.match(raw)
        if not m:
            continue
        fields = m.group(2).split()
        if len(fields) < 10:
            continue
        try:
            # common order: %usr %nice %sys %iowait %irq %soft %steal %guest %gnice %idle
            soft = float(fields[5])
            idle = float(fields[-1])
            cpu = 100.0 - idle
            cpu_vals.append(cpu)
            softirq_vals.append(soft)
        except Exception:
            continue

    avg_cpu = sum(cpu_vals) / len(cpu_vals) if cpu_vals else float("nan")
    avg_soft = sum(softirq_vals) / len(softirq_vals) if softirq_vals else float("nan")
    return {
        "cpu_avg_percent": avg_cpu,
        "softirq_avg_percent": avg_soft,
        "samples": len(cpu_vals),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--mode", default="unknown")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    stats = parse_mpstat(Path(args.input))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", *stats.keys()])
        w.writeheader()
        w.writerow({"mode": args.mode, **stats})


if __name__ == "__main__":
    main()
