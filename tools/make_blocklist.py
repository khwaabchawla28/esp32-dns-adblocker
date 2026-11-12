"""Regenerate adblocker/data/blocklist.bin from the StevenBlack/hosts list.

Every domain is hashed with FNV-1a 32-bit (must match the sketch), the hashes
are sorted and packed little-endian, 4 bytes each. The sketch binary-searches
this file directly from LittleFS flash.

Usage:  python tools/make_blocklist.py
"""
import struct
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
SKIP = {"localhost", "localhost.localdomain", "local", "broadcasthost",
        "ip6-localhost", "ip6-loopback", "0.0.0.0"}

OUT = Path(__file__).resolve().parent.parent / "adblocker" / "data" / "blocklist.bin"


def fnv(s):                      # FNV-1a, 32-bit (must match the ESP32 code)
    h = 2166136261
    for b in s.encode():
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


domains = set()
for line in urllib.request.urlopen(URL).read().decode().splitlines():
    parts = line.split("#")[0].split()
    if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1") and parts[1] not in SKIP:
        domains.add(parts[1].lower())

hashes = sorted({fnv(d) for d in domains})
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "wb") as f:
    f.write(b"".join(struct.pack("<I", h) for h in hashes))
print(len(hashes), "domains ->", len(hashes) * 4 // 1024, "KB ->", OUT)
