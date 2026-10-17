"""
Antigravity History Fixer - phan dung chung (scan hoi thoai, manifest, duong dan).

Moi thao tac voi database hoi thoai o day deu CHI DOC (mode=ro),
tru recover_crashed_conversations() chi dung cho hoi thoai da im lang > 10 phut.
"""

import os
import re
import sys
import json
import time
import sqlite3
import urllib.parse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MANIFEST_NAME = "agy_convos.json"   # nam o resources/app/out/ de renderer fetch duoc
IDLE_SECONDS = 600                  # chi cuu ho hoi thoai da im lang >= 10 phut


def user_home():
    return Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))


def convos_dir():
    return user_home() / ".gemini" / "antigravity-ide" / "conversations"


def brain_dir():
    return user_home() / ".gemini" / "antigravity-ide" / "brain"


def app_dir():
    base = Path(os.environ.get("LOCALAPPDATA", user_home() / "AppData" / "Local"))
    for name in ("Antigravity IDE", "antigravity"):
        p = base / "Programs" / name / "resources" / "app"
        if p.exists():
            return p
    return base / "Programs" / "Antigravity IDE" / "resources" / "app"


def manifest_path():
    return app_dir() / "out" / MANIFEST_NAME


def find_vscdb_path():
    app_data = Path(os.environ.get("APPDATA", user_home() / "AppData" / "Roaming"))
    candidates = [
        app_data / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb",
        app_data / "Antigravity" / "User" / "globalStorage" / "state.vscdb",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def open_ro(path):
    uri = "file:" + urllib.parse.quote(str(path).replace("\\", "/"), safe="/:") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5)


def last_activity(db_path):
    """mtime moi nhat cua .db / .db-wal (hoi thoai dang chay chi ghi vao WAL)."""
    t = os.path.getmtime(db_path)
    wal = db_path.with_name(db_path.name + "-wal")
    if wal.exists():
        t = max(t, os.path.getmtime(wal))
    return t


def clean_title(raw):
    if not raw:
        return None
    raw = re.sub(r"</?USER_REQUEST>", "", raw)
    raw = re.sub(r"```[\s\S]*?```", "", raw)
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    if not lines:
        return None
    title = lines[0]
    title = re.sub(r"^#+\s*", "", title)
    title = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", title)
    title = re.sub(r"https?://\S+", "", title).strip()
    if len(title) > 65:
        title = title[:62] + "..."
    return title or None


# URI dau tien trong blob luon sach (sau byte do dai, truoc byte dieu khien).
# Cac ban sao phia sau co the dinh byte tag protobuf ('z') o duoi nen khong dung.
_URI_RE = re.compile(rb"file:///[\x21-\x7e]+?(?=[\x00-\x1f\x7f-\xff]|$)")


def extract_workspace_uri(blob):
    if not blob:
        return None
    m = _URI_RE.search(blob)
    if not m:
        return None
    uri = m.group(0).decode("ascii", errors="ignore")
    return uri if len(uri) > len("file:///x") else None


def _title_from_transcript(cid):
    t_path = brain_dir() / cid / ".system_generated" / "logs" / "transcript.jsonl"
    if not t_path.exists():
        return None
    try:
        with open(t_path, "r", encoding="utf-8", errors="ignore") as tf:
            for line in tf:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") == "USER_INPUT":
                    t = clean_title(d.get("content", ""))
                    if t:
                        return t
    except Exception:
        pass
    return None


def _title_from_steps(cur):
    try:
        rows = cur.execute("SELECT step_payload FROM steps WHERE step_type=1 LIMIT 5").fetchall()
    except Exception:
        return None
    for row in rows:
        if not (row and row[0]):
            continue
        for m in re.findall(rb"[\x20-\x7E\xC2-\xF4][\x20-\x7E\x80-\xBF]{4,}", row[0]):
            try:
                t = clean_title(m.decode("utf-8"))
            except Exception:
                continue
            if t and len(t) > 5 and not t.startswith("http"):
                return t
    return None


def scan_conversations():
    """Tra ve list dict {id, workspace, mtime, steps, title} (chi doc)."""
    cdir = convos_dir()
    out = []
    if not cdir.exists():
        return out
    # Dung mtime cua .db (mtime cua -wal bi IDE cham dong loat khi khoi dong nen khong phan biet duoc)
    for db_path in sorted(cdir.glob("*.db"), key=os.path.getmtime, reverse=True):
        cid = db_path.stem
        mtime = os.path.getmtime(db_path)
        ws, steps, title = None, 1, _title_from_transcript(cid)
        try:
            conn = open_ro(db_path)
            cur = conn.cursor()
            try:
                steps = cur.execute("SELECT COUNT(*) FROM steps").fetchone()[0] or 1
            except Exception:
                pass
            try:
                row = cur.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1").fetchone()
                ws = extract_workspace_uri(row[0] if row else None)
            except Exception:
                pass
            if not title:
                title = _title_from_steps(cur)
            conn.close()
        except Exception as e:
            print(f"[!] Khong doc duoc {db_path.name}: {e}")
        if not title:
            title = "Hoi thoai ngay " + datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
        out.append({"id": cid, "workspace": ws, "mtime": mtime, "steps": steps, "title": title})
    return out


def to_items(convos):
    return [[c["id"], [c["workspace"]] if c["workspace"] else [], int(c["mtime"] * 1000), c["title"]]
            for c in convos]


def write_manifest(convos=None):
    """Ghi resources/app/out/agy_convos.json de IDE tu nap hoi thoai moi (khong can va lai)."""
    convos = scan_conversations() if convos is None else convos
    items = to_items(convos)
    p = manifest_path()
    if not p.parent.exists():
        return items, None
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    return items, p


def recover_crashed_conversations():
    """
    Cuu ho hoi thoai bi ngat dot ngot: checkpoint WAL va chuyen buoc ket status=2 -> 3.
    AN TOAN: bo qua hoi thoai dang hoat dong (db/wal thay doi trong IDLE_SECONDS gan day).
    """
    now = time.time()
    wal_n = fixed = skipped = 0
    for db_path in convos_dir().glob("*.db"):
        if now - last_activity(db_path) < IDLE_SECONDS:
            skipped += 1
            continue
        try:
            conn = sqlite3.connect(db_path, timeout=3)
            cur = conn.cursor()
            if db_path.with_name(db_path.name + "-wal").exists():
                cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                wal_n += 1
            stuck = cur.execute("SELECT COUNT(*) FROM steps WHERE status=2").fetchone()[0] or 0
            if stuck:
                cur.execute("UPDATE steps SET status=3 WHERE status=2")
                conn.commit()
                fixed += stuck
            conn.close()
        except Exception:
            pass
    print(f"[+] Cuu ho crash: checkpoint {wal_n} WAL, sua {fixed} buoc ket Running, bo qua {skipped} phien dang hoat dong.")
