#!/usr/bin/env python3
import argparse
import csv
import math
import re
from pathlib import Path

RTT_RE = re.compile(r"time=([0-9]*\.?[0-9]+)\s*ms")
TXRX_RE = re.compile(r"(\d+) packets transmitted, (\d+) received")


def percentile(vals, p):
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def parse_ping(path: Path):
    rtts = []
    tx = rx = None
    for line in path.read_text(errors="ignore").splitlines():
        m = RTT_RE.search(line)
        if m:
            rtts.append(float(m.group(1)))
        m2 = TXRX_RE.search(line)
        if m2:
            tx = int(m2.group(1))
            rx = int(m2.group(2))

    rtts.sort()
    loss = None
    if tx and tx > 0 and rx is not None:
        loss = (tx - rx) * 100.0 / tx

    return {
        "samples": len(rtts),
        "avg_ms": sum(rtts) / len(rtts) if rtts else float("nan"),
        "min_ms": min(rtts) if rtts else float("nan"),
        "max_ms": max(rtts) if rtts else float("nan"),
        "p50_ms": percentile(rtts, 0.50),
        "p95_ms": percentile(rtts, 0.95),
        "p99_ms": percentile(rtts, 0.99),
        "p999_ms": percentile(rtts, 0.999),
        "loss_percent": loss if loss is not None else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--mode", default="unknown")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    stats = parse_ping(Path(args.input))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", *stats.keys()])
        w.writeheader()
        w.writerow({"mode": args.mode, **stats})


if __name__ == "__main__":
    main()
