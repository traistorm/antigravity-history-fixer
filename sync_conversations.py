import os
import sys
import glob
import json
import sqlite3
import base64
import shutil
import re
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def encode_varint(v):
    res = bytearray()
    while v > 0x7F:
        res.append((v & 0x7F) | 0x80)
        v >>= 7
    res.append(v & 0x7F)
    return bytes(res)

def encode_tag_len(tag, data_bytes):
    header = encode_varint((tag << 3) | 2)
    length = encode_varint(len(data_bytes))
    return header + length + data_bytes

def encode_tag_varint(tag, val):
    header = encode_varint((tag << 3) | 0)
    return header + encode_varint(val)

def encode_timestamp(seconds, nanos=0):
    b = encode_tag_varint(1, int(seconds))
    if nanos:
        b += encode_tag_varint(2, int(nanos))
    return b

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
    # UnifiedStateValue: tag 1 is string value
    val_blob = encode_tag_len(1, b64_str.encode("ascii"))
    # Map entry: tag 1 is key (cascade_id), tag 2 is UnifiedStateValue
    entry = encode_tag_len(1, cascade_id.encode("ascii")) + encode_tag_len(2, val_blob)
    # Map entry wrapped with tag 1
    return encode_tag_len(1, entry)

def clean_title(raw_text):
    if not raw_text:
        return None
    # Strip <USER_REQUEST> tags if present
    text = re.sub(r"<USER_REQUEST>", "", raw_text, flags=re.I)
    text = re.sub(r"</USER_REQUEST>", "", text, flags=re.I)
    lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith("<")]
    if not lines:
        return None
    title = lines[0]
    # Remove markdown links [text](url) -> text
    title = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", title)
    title = re.sub(r"https?://\S+", "", title).strip()
    if len(title) > 65:
        title = title[:62] + "..."
    return title

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
    - Phát hiện và chuyển trạng thái các bước bị treo status=2 (RUNNING) về status=3 (DONE).
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
            # Check for stuck steps
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

def sync_conversations():
    vscdb_path = find_vscdb_path()
    if not vscdb_path.exists():
        print(f"[-] Khong tim thay database state: {vscdb_path}")
        return False

    user_home = Path(os.environ.get("USERPROFILE", r"C:\Users\Traistorm"))
    convos_dir = user_home / ".gemini" / "antigravity-ide" / "conversations"
    brain_dir = user_home / ".gemini" / "antigravity-ide" / "brain"

    if not convos_dir.exists():
        print(f"[-] Khong tim thay thu muc conversations: {convos_dir}")
        return False

    # 0. Cuu ho cac database bi crash / stuck WAL truoc khi sync
    recover_crashed_conversations(convos_dir)

    # Backup state.vscdb
    backup_path = vscdb_path.with_name("state.vscdb.antigravity_backup")
    if not backup_path.exists():
        print(f"[*] Dang tao backup cho {vscdb_path.name}...")
        shutil.copyfile(vscdb_path, backup_path)
        print(f"[+] Da tao backup: {backup_path.name}")
    else:
        print(f"[i] Ban backup {backup_path.name} da ton tai.")

    conn = sqlite3.connect(vscdb_path)
    cur = conn.cursor()
    cur.execute("SELECT value FROM ItemTable WHERE key='antigravityUnifiedStateSync.trajectorySummaries'")
    row = cur.fetchone()
    if not row or not row[0]:
        print("[-] Khong tim thay key trajectorySummaries trong database.")
        conn.close()
        return False

    existing_val = row[0]
    existing_raw = base64.b64decode(existing_val)

    # Parse existing cascade IDs from decoded raw
    existing_cids = set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", existing_raw.decode("latin1", errors="ignore")))
    print(f"[i] Hien tai co {len(existing_cids)} hoi thoai trong cache menu Recent cua IDE.")

    db_files = list(convos_dir.glob("*.db"))
    print(f"[i] Tim thay tong cong {len(db_files)} file database hoi thoai tren o cung.")

    new_entries_bytes = bytearray()
    added_count = 0

    for db_path in sorted(db_files, key=os.path.getmtime, reverse=True):
        cid = db_path.stem
        if cid in existing_cids:
            continue

        mtime = os.path.getmtime(db_path)
        title = None
        workspace_uri = "file:///d:/projects/hopeless-netizens/RedditVideoMakerBot"
        step_count = 1

        # 1. Try reading transcript from brain
        transcript_path = brain_dir / cid / ".system_generated" / "logs" / "transcript.jsonl"
        if transcript_path.exists():
            try:
                with open(transcript_path, "r", encoding="utf-8", errors="ignore") as tf:
                    for line in tf:
                        try:
                            d = json.loads(line)
                            if d.get("type") == "USER_INPUT":
                                title = clean_title(d.get("content", ""))
                                if title:
                                    break
                        except Exception:
                            pass
            except Exception:
                pass

        # 2. Query sqlite for workspace & steps count
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
                    try:
                        workspace_uri = uris[0].decode("latin1", errors="ignore").rstrip("\x00")
                    except Exception:
                        pass

            if not title:
                ccur.execute("SELECT step_payload FROM steps WHERE step_type=1 LIMIT 1")
                sp = ccur.fetchone()
                if sp and sp[0]:
                    matches = re.findall(rb"[\x20-\x7E\xC2-\xF4][\x20-\x7E\x80-\xBF]{4,}", sp[0])
                    for m in matches:
                        try:
                            s = m.decode("utf-8")
                            t = clean_title(s)
                            if t and len(t) > 5:
                                title = t
                                break
                        except Exception:
                            pass
            cconn.close()
        except Exception:
            pass

        if not title:
            dt_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            title = f"Hoi thoai ngay {dt_str}"

        # Build proto summary
        summary_proto = encode_cascade_trajectory_summary(
            summary=title,
            step_count=step_count,
            mtime_sec=mtime,
            traj_id=cid,
            ws_uri=workspace_uri,
            status=1,
            not_fully_idle=False
        )

        entry_bytes = build_map_entry(cid, summary_proto)
        new_entries_bytes.extend(entry_bytes)
        added_count += 1
        existing_cids.add(cid)
        print(f"  [+] Da phuc hoi: [{title}] ({cid[:8]}...) - {workspace_uri}")

    if added_count == 0:
        print("[+] Tat ca hoi thoai da duoc dong bo day du, khong can bo sung.")
        conn.close()
        return True

    # Combine existing_raw + new_entries_bytes
    combined_raw = bytes(existing_raw) + bytes(new_entries_bytes)
    combined_val = base64.b64encode(combined_raw).decode("ascii")

    cur.execute("UPDATE ItemTable SET value=? WHERE key='antigravityUnifiedStateSync.trajectorySummaries'", (combined_val,))
    conn.commit()
    conn.close()

    print(f"\n[🎉 THANH CONG!] Da phuc hoi thanh cong {added_count} hoi thoai bi an vao danh sach!")
    print("[*] Gio day menu Recent se hien thi day du toan bo cac hoi thoai tu truoc den nay.")
    print("[*] Vui long nhan Ctrl + R (Reload Window) hoac restart IDE de Antigravity ap dung ngay lap tuc!")
    return True

if __name__ == "__main__":
    sync_conversations()
