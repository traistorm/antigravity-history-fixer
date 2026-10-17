"""
Antigravity History Fixer - Conversation Synchronizer
- Quet cac DB hoi thoai (chi doc) va ghi manifest agy_convos.json; IDE da va se tu nap (poll 20s).
- Che do --watch: cap nhat manifest khi co hoi thoai moi / thay doi (theo ca file -wal).
- --write-state: (tuy chon, khong khuyen dung) ghi them vao state.vscdb. Mac dinh TAT vi
  no ghi de toan bo trajectorySummaries that cua IDE bang du lieu tong hop.
"""

import os
import sys
import base64
import shutil
import sqlite3
import time
from datetime import datetime

import common
from common import find_vscdb_path


def varint(n):
    buf = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break
    return bytes(buf)


def tag_varint(f, v):
    return varint((f << 3) | 0) + varint(v)


def tag_len(f, data):
    return varint((f << 3) | 2) + varint(len(data)) + data


def ts(sec):
    s = int(sec)
    n = int((sec - s) * 1e9)
    return (tag_varint(1, s) if s else b"") + (tag_varint(2, n) if n else b"")


def summary_proto(c):
    b = bytearray()
    b += tag_len(1, c["title"].encode("utf-8"))
    b += tag_varint(2, c["steps"])
    b += tag_len(3, ts(c["mtime"]))
    b += tag_len(4, c["id"].encode("utf-8"))
    b += tag_varint(5, 1)
    b += tag_len(7, ts(c["mtime"]))
    if c["workspace"]:
        b += tag_len(9, tag_len(1, c["workspace"].encode("utf-8")))
    b += tag_len(10, ts(c["mtime"]))
    b += tag_varint(16, 1)
    return bytes(b)


def map_entry(c):
    b64 = base64.b64encode(summary_proto(c)).decode("ascii")
    entry = tag_len(1, c["id"].encode("ascii")) + tag_len(2, tag_len(1, b64.encode("ascii")))
    return tag_len(1, entry)


def write_state(convos):
    vscdb = find_vscdb_path()
    if not vscdb.exists():
        print(f"[-] Khong thay state.vscdb: {vscdb}")
        return
    bk = vscdb.with_name("state.vscdb.antigravity_backup")
    if not bk.exists():
        shutil.copyfile(vscdb, bk)
    val = base64.b64encode(b"".join(map_entry(c) for c in convos)).decode("ascii")
    conn = sqlite3.connect(vscdb, timeout=10)
    conn.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES "
                 "('antigravityUnifiedStateSync.trajectorySummaries', ?)", (val,))
    conn.commit()
    conn.close()
    print("[+] Da ghi state.vscdb (--write-state).")


def sync_conversations(silent=False, with_state=False):
    if not common.convos_dir().exists():
        print(f"[-] Khong thay thu muc hoi thoai: {common.convos_dir()}")
        return False
    convos = common.scan_conversations()
    items, path = common.write_manifest(convos)
    if path is None:
        print(f"[-] Khong thay thu muc IDE de ghi manifest: {common.manifest_path()}")
        return False
    if with_state:
        write_state(convos)
    if not silent:
        print(f"[+] Da ghi {len(items)} hoi thoai vao {path}")
        for c in convos[:8]:
            print(f"  {c['id'][:8]}  [{c['title'][:40]}]  {c['workspace']}")
        print("[*] IDE tu nap hoi thoai moi trong ~20 giay; neu moi vá file JS thi nhan Ctrl + R mot lan.")
    return True


def signature():
    d = common.convos_dir()
    return {p.name: (p.stat().st_mtime, p.stat().st_size) for p in d.glob("*.db*")}


def watch_mode(with_state=False):
    print("ANTIGRAVITY AUTO-SYNC (WATCH) - Ctrl + C de thoat.")
    sync_conversations(silent=False, with_state=with_state)
    last = signature()
    while True:
        try:
            time.sleep(5)
            cur = signature()
            if cur != last:
                sync_conversations(silent=True, with_state=with_state)
                last = cur
                print(f"[{datetime.now():%H:%M:%S}] Da dong bo manifest.")
        except KeyboardInterrupt:
            print("\nDa dung watch mode.")
            break
        except Exception as e:
            print(f"[!] {e}")
            time.sleep(5)


if __name__ == "__main__":
    ws = "--write-state" in sys.argv
    if "--watch" in sys.argv:
        watch_mode(ws)
    else:
        sys.exit(0 if sync_conversations(with_state=ws) else 1)
