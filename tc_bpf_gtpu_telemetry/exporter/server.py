#!/usr/bin/env python3
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

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


def parse_u32(hex_list):
    return int.from_bytes(bytes(int(x, 16) for x in hex_list), "little")


def parse_u64(hex_list):
    return int.from_bytes(bytes(int(x, 16) for x in hex_list), "little")


def resolve_maps():
    state = json.loads(STATE_FILE.read_text())
    name_to_id = {}
    for mid in state.get("map_ids", []):
        info = run_json(["bpftool", "-j", "map", "show", "id", str(mid)])
        if not info:
            continue
        item = info[0] if isinstance(info, list) else info
        if item.get("name"):
            name_to_id[item["name"]] = mid
    return state, name_to_id


def dump_map(map_id):
    return run_json(["bpftool", "-j", "map", "dump", "id", str(map_id)])


def read_stats_payload():
    if not STATE_FILE.exists():
        return {"error": "not_attached", "detail": str(STATE_FILE)}

    state, name_to_id = resolve_maps()
    required = ["global_stats", "teid_pkt_cnt", "teid_byte_cnt"]
    for key in required:
        if key not in name_to_id:
            return {"error": "missing_map", "map": key, "available": list(name_to_id.keys())}

    global_stats = {}
    for e in dump_map(name_to_id["global_stats"]):
        k = parse_u32(e["key"])
        global_stats[STAT_KEYS.get(k, f"stat_{k}")] = parse_u64(e["value"])

    teid_packets = {}
    for e in dump_map(name_to_id["teid_pkt_cnt"]):
        teid_packets[str(parse_u32(e["key"]))] = parse_u64(e["value"])

    teid_bytes = {}
    for e in dump_map(name_to_id["teid_byte_cnt"]):
        teid_bytes[str(parse_u32(e["key"]))] = parse_u64(e["value"])

    return {
        "iface": state.get("iface"),
        "prog_id": state.get("prog_id"),
        "global": global_stats,
        "teid_packets": teid_packets,
        "teid_bytes": teid_bytes,
    }


def reset_maps():
    if not STATE_FILE.exists():
        return {"ok": False, "error": "not_attached"}

    _, name_to_id = resolve_maps()
    for idx in range(4):
        subprocess.check_call([
            "bpftool", "map", "update", "id", str(name_to_id["global_stats"]),
            "key", "hex", f"{idx:02x}", "00", "00", "00",
            "value", "hex", "00", "00", "00", "00", "00", "00", "00", "00",
            "any",
        ])

    for map_name in ["teid_pkt_cnt", "teid_byte_cnt", "teid_last_seen"]:
        if map_name not in name_to_id:
            continue
        map_id = name_to_id[map_name]
        entries = dump_map(map_id)
        for e in entries:
            key = e["key"]
            subprocess.check_call(["bpftool", "map", "delete", "id", str(map_id), "key", "hex", *key])

    return {"ok": True}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {"status": "ok", "service": "tc-bpf-gtpu-exporter"})
            return
        if path == "/stats":
            payload = read_stats_payload()
            code = 200 if "error" not in payload else 503
            self._send(code, payload)
            return
        if path == "/stats/teid":
            payload = read_stats_payload()
            if "error" in payload:
                self._send(503, payload)
            else:
                self._send(200, {"teid_packets": payload["teid_packets"], "teid_bytes": payload["teid_bytes"]})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/reset":
            try:
                payload = reset_maps()
                self._send(200 if payload.get("ok") else 503, payload)
            except Exception as exc:
                self._send(500, {"ok": False, "error": str(exc)})
            return
        self._send(404, {"error": "not_found"})


def main():
    host = "0.0.0.0"
    port = 18110
    server = HTTPServer((host, port), Handler)
    print(f"tc-bpf-gtpu-exporter listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
