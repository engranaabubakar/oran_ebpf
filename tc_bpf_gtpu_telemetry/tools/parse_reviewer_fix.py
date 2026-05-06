#!/usr/bin/env python3
import csv
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    r = root / "results"

    out = r / "reviewer_fix_summary.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["concern", "status", "evidence_file"])

        teid_csv = r / "teid_cycle_observations.csv"
        if teid_csv.exists():
            w.writerow(["single_teid", "addressed", teid_csv.name])
        else:
            w.writerow(["single_teid", "pending", teid_csv.name])

        bidir_state = r / "attached_state_bidir.json"
        if bidir_state.exists():
            w.writerow(["ingress_only", "addressed", bidir_state.name])
        else:
            w.writerow(["ingress_only", "pending", bidir_state.name])

        path_sep = r / "path_separation_summary.csv"
        if path_sep.exists():
            w.writerow(["host_bypass_gtpu", "addressed", path_sep.name])
        else:
            w.writerow(["host_bypass_gtpu", "pending", path_sep.name])

        xdp_cmp = r / "xdp_compare_status.csv"
        if xdp_cmp.exists():
            status = "addressed"
            try:
                rows = list(csv.DictReader(xdp_cmp.open()))
                for row in rows:
                    if row.get("mode") == "xdp" and row.get("status") == "not_available":
                        status = "partial"
            except Exception:
                pass
            w.writerow(["no_xdp_comparison", status, xdp_cmp.name])
        else:
            w.writerow(["no_xdp_comparison", "pending", xdp_cmp.name])

    print(f"wrote {out}")


if __name__ == "__main__":
    main()
