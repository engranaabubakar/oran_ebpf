#!/usr/bin/env python3
import argparse
import ipaddress
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "results" / "attached_state.json"

STAT_KEYS = {
    0: "gtpu_packets_total",
    1: "gtpu_bytes_total",
    2: "malformed_packets_total",
    3: "non_gtpu_packets_total",
}


def run_json(cmd):
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def parse_u32_from_hex_list(hex_list):
    b = bytes(int(x, 16) for x in hex_list)
    return int.from_bytes(b, byteorder="little", signed=False)


def parse_u64_from_hex_list(hex_list):
    b = bytes(int(x, 16) for x in hex_list)
    return int.from_bytes(b, byteorder="little", signed=False)


def resolve_maps(map_ids):
    name_to_id = {}
    for mid in map_ids:
        info = run_json(["bpftool", "-j", "map", "show", "id", str(mid)])
        if not info:
            continue
        item = info[0] if isinstance(info, list) else info
        name = item.get("name")
        if name:
            name_to_id[name] = mid
    return name_to_id


def read_array_map(map_id):
    entries = run_json(["bpftool", "-j", "map", "dump", "id", str(map_id)])
    out = {}
    for e in entries:
        k = parse_u32_from_hex_list(e["key"])
        v = parse_u64_from_hex_list(e["value"])
        out[STAT_KEYS.get(k, f"stat_{k}")] = v
    return out


def read_u64_hash_map(map_id):
    entries = run_json(["bpftool", "-j", "map", "dump", "id", str(map_id)])
    out = {}
    for e in entries:
        k = parse_u32_from_hex_list(e["key"])
        v = parse_u64_from_hex_list(e["value"])
        out[str(k)] = v
    return out


def read_last_seen_map(map_id):
    entries = run_json(["bpftool", "-j", "map", "dump", "id", str(map_id)])
    out = {}
    for e in entries:
        teid = parse_u32_from_hex_list(e["key"])
        raw = bytes(int(x, 16) for x in e["value"])
        if len(raw) < 24:
            continue
        outer_src = int.from_bytes(raw[0:4], "little")
        outer_dst = int.from_bytes(raw[4:8], "little")
        udp_src = int.from_bytes(raw[8:10], "little")
        udp_dst = int.from_bytes(raw[10:12], "little")
        msg_type = raw[12]
        last_pkt_len = int.from_bytes(raw[16:20], "little")
        out[str(teid)] = {
            "outer_src": str(ipaddress.IPv4Address(outer_src)),
            "outer_dst": str(ipaddress.IPv4Address(outer_dst)),
            "udp_src": udp_src,
            "udp_dst": udp_dst,
            "gtpu_msg_type": msg_type,
            "last_packet_len": last_pkt_len,
        }
    return out


def main():
    p = argparse.ArgumentParser(description="Read TC-BPF GTP-U telemetry maps")
    p.add_argument("--json", action="store_true", help="Emit JSON only")
    args = p.parse_args()

    if not STATE_FILE.exists():
        raise SystemExit(f"state file not found: {STATE_FILE}")

    state = json.loads(STATE_FILE.read_text())
    name_to_id = resolve_maps(state.get("map_ids", []))

    required = ["global_stats", "teid_pkt_cnt", "teid_byte_cnt", "teid_last_seen"]
    missing = [m for m in required if m not in name_to_id]
    if missing:
        raise SystemExit(f"missing map ids for: {missing}")

    payload = {
        "iface": state.get("iface"),
        "prog_id": state.get("prog_id"),
        "global": read_array_map(name_to_id["global_stats"]),
        "per_teid_packets": read_u64_hash_map(name_to_id["teid_pkt_cnt"]),
        "per_teid_bytes": read_u64_hash_map(name_to_id["teid_byte_cnt"]),
        "per_teid_last_seen": read_last_seen_map(name_to_id["teid_last_seen"]),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print(f"Interface: {payload['iface']} | prog_id: {payload['prog_id']}")
    print("Global Counters:")
    for k, v in payload["global"].items():
        print(f"  - {k}: {v}")

    print("Per-TEID Counters:")
    teids = sorted(payload["per_teid_packets"].keys(), key=lambda x: int(x))
    if not teids:
        print("  (no TEIDs observed yet)")
    for t in teids:
        print(
            f"  - teid={t} packets={payload['per_teid_packets'].get(t,0)} "
            f"bytes={payload['per_teid_bytes'].get(t,0)} "
            f"meta={payload['per_teid_last_seen'].get(t,{})}"
        )


if __name__ == "__main__":
    main()
