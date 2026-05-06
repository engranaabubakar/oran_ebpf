#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


def parse_iperf(path: Path):
    data = json.loads(path.read_text())
    end = data.get("end", {})
    sent = end.get("sum_sent", {})
    recv = end.get("sum_received", {})
    bps = recv.get("bits_per_second", sent.get("bits_per_second", 0.0))
    throughput_gbps = float(bps) / 1e9
    retrans = sent.get("retransmits", 0)
    return {
        "throughput_gbps": throughput_gbps,
        "retransmissions": retrans,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--mode", default="unknown")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    stats = parse_iperf(Path(args.input))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", *stats.keys()])
        w.writeheader()
        w.writerow({"mode": args.mode, **stats})


if __name__ == "__main__":
    main()
