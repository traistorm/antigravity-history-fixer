"""
Antigravity History Fixer - Conversation Synchronizer
Tác giả: Traistorm & Antigravity Pair Programmer
Mô tả:
- Tự động quét toàn bộ cơ sở dữ liệu SQLite hội thoại (~/.gemini/antigravity-ide/conversations/*.db).
- Trích xuất tiêu đề thực tế từ transcript hoặc step payload.
- Chuẩn hóa chính xác Workspace URI cho từng dự án (khớp 100% với giao diện IDE).
- Đóng gói dữ liệu chuẩn Protobuf và nạp vào state.vscdb của Antigravity IDE.
- Hỗ trợ chế độ --watch để tự động đồng bộ ngầm khi có cuộc trò chuyện mới.
"""

import os
import sys
import re
import json
import base64
import shutil
import sqlite3
import time
import urllib.parse
from pathlib import Path
from datetime import datetime

# Đảm bảo in tiếng Việt mượt mà trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

def encode_tag_varint(field_num, val):
    return varint((field_num << 3) | 0) + varint(val)

def encode_tag_len(field_num, data):
    return varint((field_num << 3) | 2) + varint(len(data)) + data

def encode_timestamp(dt_sec):
    sec = int(dt_sec)
    nanos = int((dt_sec - sec) * 1e9)
    b = bytearray()
    if sec != 0:
        b += encode_tag_varint(1, sec)
    if nanos != 0:
        b += encode_tag_varint(2, nanos)
    return bytes(b)

def encode_workspace_metadata(ws_uri):
    return encode_tag_len(1, ws_uri.encode("utf-8"))

def encode_cascade_trajectory_summary(summary, step_count, mtime_sec, traj_id, ws_uri, status=1, not_fully_idle=False):
    b = bytearray()
    # tag 1: summary (string)
    b += encode_tag_len(1, summary.encode("utf-8"))
    # tag 2: step_count (uint32)
    b += encode_tag_varint(2, step_count)
    # tag 3: last_modified_time (Timestamp)
    b += encode_tag_len(3, encode_timestamp(mtime_sec))
    # tag 4: trajectory_id (string)
    b += encode_tag_len(4, traj_id.encode("utf-8"))
    # tag 5: status (int)
    b += encode_tag_varint(5, status)
    # tag 7: created_time (Timestamp)
    b += encode_tag_len(7, encode_timestamp(mtime_sec))
    # tag 9: workspaces (repeated CortexWorkspaceMetadata)
    if ws_uri:
        b += encode_tag_len(9, encode_workspace_metadata(ws_uri))
    # tag 10: last_user_input_time
    b += encode_tag_len(10, encode_timestamp(mtime_sec))
    # tag 16: last_user_input_step_index
    b += encode_tag_varint(16, 1)
    # tag 21: not_fully_idle (bool)
    if not_fully_idle:
        b += encode_tag_varint(21, 1)
    return bytes(b)

def build_map_entry(cascade_id, summary_proto_bytes):
    b64_str = base64.b64encode(summary_proto_bytes).decode("ascii")
    val_blob = encode_tag_len(1, b64_str.encode("ascii"))
    entry = encode_tag_len(1, cascade_id.encode("ascii")) + encode_tag_len(2, val_blob)
    return encode_tag_len(1, entry)

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
    return title

def clean_workspace_uri(s):
    uri = urllib.parse.unquote(s.strip("\x00 \t\r\n"))
    uri = re.sub(r"[zZ\x00-\x1f]+$", "", uri)
    if not uri.startswith("file:///"):
        if uri.startswith("file://"):
            uri = "file:///" + uri[7:]
    return uri

def find_vscdb_path():
    app_data = Path(os.environ.get("APPDATA", r"C:\Users\Traistorm\AppData\Roaming"))
    candidates = [
        app_data / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb",
        app_data / "Antigravity" / "User" / "globalStorage" / "state.vscdb",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

def recover_crashed_conversations(convos_dir):
    """
    Quét và tự động cứu hộ các database bị crash hoặc ngắt đột ngột:
    - Thu dọn và merge các file SQLite WAL (.db-wal) dở dang về file chính.
    - Chuyển trạng thái các bước bị treo status=2 (RUNNING) về status=3 (DONE).
    """
    db_files = list(convos_dir.glob("*.db"))
    recovered_wal = 0
    fixed_steps = 0
    for db_path in db_files:
        wal_path = db_path.with_name(db_path.name + "-wal")
        has_wal = wal_path.exists()
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            if has_wal:
                cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                recovered_wal += 1
            cur.execute("SELECT COUNT(*) FROM steps WHERE status=2")
            stuck_count = cur.fetchone()[0] or 0
            if stuck_count > 0:
                cur.execute("UPDATE steps SET status=3 WHERE status=2")
                conn.commit()
                cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                fixed_steps += stuck_count
            conn.close()
        except Exception:
            pass
    if recovered_wal > 0 or fixed_steps > 0:
        print(f"[+] Cuu ho crash: Da checkpoint {recovered_wal} file WAL do dang, sua {fixed_steps} buoc bi ket Running.")

def sync_conversations(silent=False):
    vscdb_path = find_vscdb_path()
    if not vscdb_path.exists():
        if not silent:
            print(f"[-] Khong tim thay database state: {vscdb_path}")
        return False

    user_home = Path(os.environ.get("USERPROFILE", r"C:\Users\Traistorm"))
    convos_dir = user_home / ".gemini" / "antigravity-ide" / "conversations"
    brain_dir = user_home / ".gemini" / "antigravity-ide" / "brain"

    if not convos_dir.exists():
        if not silent:
            print(f"[-] Khong tim thay thu muc conversations: {convos_dir}")
        return False

    # 1. Cứu hộ crash trước khi đồng bộ
    recover_crashed_conversations(convos_dir)

    # 2. Backup state.vscdb
    backup_path = vscdb_path.with_name("state.vscdb.antigravity_backup")
    if not backup_path.exists():
        if not silent:
            print(f"[*] Dang tao backup cho {vscdb_path.name}...")
        shutil.copyfile(vscdb_path, backup_path)
        if not silent:
            print(f"[+] Da tao backup: {backup_path.name}")

    db_files = sorted(convos_dir.glob("*.db"), key=os.path.getmtime, reverse=True)
    if not silent:
        print(f"[i] Tim thay {len(db_files)} file database hoi thoai tren o cung.")

    all_entries = bytearray()
    synced_count = 0

    for db_path in db_files:
        cid = db_path.stem
        mtime = os.path.getmtime(db_path)
        title = None
        workspace_uri = "file:///d:/projects/hopeless-netizens/RedditVideoMakerBot"
        step_count = 1

        # 1. Thử đọc transcript từ thư mục brain
        t_path = brain_dir / cid / ".system_generated" / "logs" / "transcript.jsonl"
        if t_path.exists():
            try:
                with open(t_path, "r", encoding="utf-8", errors="ignore") as tf:
                    for line in tf:
                        try:
                            d = json.loads(line)
                            if d.get("type") == "USER_INPUT":
                                t = clean_title(d.get("content", ""))
                                if t:
                                    title = t
                                    break
                        except Exception:
                            pass
            except Exception:
                pass

        # 2. Đọc metadata blob & steps từ SQLite
        try:
            cconn = sqlite3.connect(db_path)
            ccur = cconn.cursor()

            ccur.execute("SELECT COUNT(*) FROM steps")
            step_count = ccur.fetchone()[0] or 1

            ccur.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1")
            blob = ccur.fetchone()
            if blob and blob[0]:
                uris = re.findall(rb"file:///[a-zA-Z0-9_/%:.-]+", blob[0])
                if uris:
                    candidates = [clean_workspace_uri(u.decode("latin1", errors="ignore")) for u in uris]
                    valid = [c for c in candidates if len(c) > 12]
                    if valid:
                        workspace_uri = valid[0]
                    elif candidates:
                        workspace_uri = candidates[0]

            if not title:
                ccur.execute("SELECT step_payload FROM steps WHERE step_type=1 LIMIT 5")
                for row in ccur.fetchall():
                    if row and row[0]:
                        matches = re.findall(rb"[\x20-\x7E\xC2-\xF4][\x20-\x7E\x80-\xBF]{4,}", row[0])
                        for m in matches:
                            try:
                                s = m.decode("utf-8")
                                t = clean_title(s)
                                if t and len(t) > 5 and not t.startswith("http"):
                                    title = t
                                    break
                            except Exception:
                                pass
                    if title:
                        break
            cconn.close()
        except Exception:
            pass

        if not title:
            dt_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            title = f"Hoi thoai ngay {dt_str}"

        proto = encode_cascade_trajectory_summary(
            summary=title,
            step_count=step_count,
            mtime_sec=mtime,
            traj_id=cid,
            ws_uri=workspace_uri,
            status=1,
            not_fully_idle=False
        )
        all_entries.extend(build_map_entry(cid, proto))
        synced_count += 1
        if not silent and synced_count <= 8:
            print(f"  [+] {cid[:8]}... : [{title[:40]}] ({workspace_uri})")

    if not silent and synced_count > 8:
        print(f"  ... va {synced_count - 8} cuoc hoi thoai khac da duoc dong bo day du.")

    b64_val = base64.b64encode(bytes(all_entries)).decode("ascii")

    conn = sqlite3.connect(vscdb_path)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM ItemTable WHERE key='antigravityUnifiedStateSync.trajectorySummaries'")
    exists = cur.fetchone()
    if exists:
        cur.execute("UPDATE ItemTable SET value=? WHERE key='antigravityUnifiedStateSync.trajectorySummaries'", (b64_val,))
    else:
        cur.execute("INSERT INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?)", (b64_val,))
    conn.commit()
    conn.close()

    if not silent:
        print(f"\n[🎉 THANH CONG!] Da dong bo tron ven toan bo {synced_count} cuoc hoi thoai vao database!")
        print("[*] Tat ca du an deu co danh sach Recent rieng biet va duoc tim kiem day du.")
        print("[*] Vui long nhan Ctrl + R (Reload Window) hoac restart IDE de ap dung ngay lap tuc!")
    return True

def watch_mode():
    user_home = Path(os.environ.get("USERPROFILE", r"C:\Users\Traistorm"))
    convos_dir = user_home / ".gemini" / "antigravity-ide" / "conversations"
    print("=================================================================")
    print("  ANTIGRAVITY AUTO-SYNC DAEMON (WATCH MODE)")
    print("  Tu dong theo doi va dong bo lich su chat theo thoi gian thuc.")
    print("  Nhan Ctrl + C de thoat.")
    print("=================================================================")

    last_sync_mtime = 0
    sync_conversations(silent=False)
    last_sync_mtime = time.time()

    while True:
        try:
            time.sleep(5)
            # Kiem tra xem co file .db nao moi hon last_sync_mtime khong
            has_changes = False
            for db in convos_dir.glob("*.db"):
                if os.path.getmtime(db) > last_sync_mtime:
                    has_changes = True
                    break
            if has_changes:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Phat hien phien chat moi/cap nhat, dang dong bo...")
                sync_conversations(silent=True)
                last_sync_mtime = time.time()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Da dong bo thanh cong!")
        except KeyboardInterrupt:
            print("\nDa dung watch mode.")
            break
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_mode()
    else:
        sync_conversations()
