import hashlib
import base64
import os
import sys
import glob
import json
import sqlite3
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def clean_title(raw_text):
    if not raw_text:
        return None
    text = re.sub(r"<USER_REQUEST>", "", raw_text, flags=re.I)
    text = re.sub(r"</USER_REQUEST>", "", text, flags=re.I)
    lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith("<")]
    if not lines:
        return None
    title = lines[0]
    title = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", title)
    title = re.sub(r"https?://\S+", "", title).strip()
    if len(title) > 65:
        title = title[:62] + "..."
    return title

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

def scan_all_conversations():
    user_home = Path(os.path.expanduser("~"))
    convos_dir = user_home / ".gemini" / "antigravity-ide" / "conversations"
    brain_dir = user_home / ".gemini" / "antigravity-ide" / "brain"

    items = []
    if not convos_dir.exists():
        return items

    # Cuu ho cac phien bi crash truoc khi scan
    recover_crashed_conversations(convos_dir)

    db_files = sorted(convos_dir.glob("*.db"), key=os.path.getmtime, reverse=True)
    for db_path in db_files:
        cid = db_path.stem
        mtime = os.path.getmtime(db_path)
        mtime_ms = int(mtime * 1000)
        title = None
        workspace_uri = "file:///d:/projects/hopeless-netizens/RedditVideoMakerBot"

        # Transcript
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
                        except: pass
            except: pass

        # SQLite
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1")
            blob = cur.fetchone()
            if blob and blob[0]:
                uris = re.findall(rb"file:///[a-zA-Z0-9_/%:.-]+", blob[0])
                if uris:
                    try:
                        workspace_uri = uris[0].decode("latin1", errors="ignore").rstrip("\x00")
                    except: pass

            if not title:
                cur.execute("SELECT step_payload FROM steps WHERE step_type=1 LIMIT 1")
                sp = cur.fetchone()
                if sp and sp[0]:
                    matches = re.findall(rb"[\x20-\x7E\xC2-\xF4][\x20-\x7E\x80-\xBF]{4,}", sp[0])
                    for m in matches:
                        try:
                            s = m.decode("utf-8")
                            t = clean_title(s)
                            if t and len(t) > 5:
                                title = t
                                break
                        except: pass
            conn.close()
        except: pass

        if not title:
            dt_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            title = f"Hội thoại ngày {dt_str}"

        items.append([cid, [workspace_uri], mtime_ms, title])
    return items

def find_workbench_js():
    local_app_data = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Traistorm\AppData\Local"))
    candidates = [
        local_app_data / "Programs" / "Antigravity IDE" / "resources" / "app" / "out" / "vs" / "workbench" / "workbench.desktop.main.js",
        local_app_data / "Programs" / "antigravity" / "resources" / "app" / "out" / "vs" / "workbench" / "workbench.desktop.main.js",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

def apply_test_patch():
    wb_path = find_workbench_js()
    if not wb_path.exists():
        print(f"[-] Khong tim thay file workbench JS tai: {wb_path}")
        return False

    backup_path = wb_path.with_name(wb_path.name + ".backup")

    if not backup_path.exists():
        print(f"[*] Dang tao ban backup: {backup_path.name}...")
        shutil.copyfile(wb_path, backup_path)
    
    # Read clean base from backup
    with open(backup_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 1. Uncollapse groups
    content = content.replace("collapseLargeGroups:!0", "collapseLargeGroups:!1")

    # 2. Extract convos
    items = scan_all_conversations()
    print(f"[i] Tim thay {len(items)} hoi thoai tren o cung.")
    json_str = json.dumps(items, ensure_ascii=False)

    target_init = 'async _initializeTrajectorySummariesProvider(){const e=await this._unifiedStateSyncService.subscribe("trajectorySummaries"),'
    if target_init not in content:
        print("[-] Khong tim thay target_init trong base JS!")
        return False

    replacement_init = (
        'async _initializeTrajectorySummariesProvider(){'
        'const e=await this._unifiedStateSyncService.subscribe("trajectorySummaries");'
        '/*AGY_CONVO_SYNC*/try{'
        'const _kd=e.get()?.data||{},_al=' + json_str + ';'
        'for(const[c,w,t,s]of _al){'
        'if(!_kd[c]){'
        'this._unifiedStateSyncService.pushUpdate(tph(c,w,new Date(t),s))'
        '}'
        '}'
        '}catch(_e){};const '
    )

    patched_content = content.replace(target_init, replacement_init, 1)

    # Validate syntax with node --check
    scratch_js = wb_path.with_name("test_workbench_syntax.js")
    with open(scratch_js, "w", encoding="utf-8") as f:
        f.write(patched_content)

    print("[*] Dang kiem tra cu phap JavaScript bang node --check...")
    res = subprocess.run(["node", "--check", str(scratch_js)], capture_output=True, text=True)
    if scratch_js.exists():
        try: scratch_js.unlink()
        except: pass
    if res.returncode != 0:
        print("[-] Cu phap JS khong hop le:")
        print(res.stderr)
        return False

    print("[+] Cu phap JS hop le 100%!")
    # Write to target
    with open(wb_path, "w", encoding="utf-8") as f:
        f.write(patched_content)
    print(f"[+] Da cap nhat {wb_path.name} thanh cong!")

    # Cap nhat ma checksum trong product.json de chan thong bao 'corrupt installation'
    try:
        app_dir = wb_path.parents[3] # resources/app
        prod_path = app_dir / "product.json"
        if prod_path.exists():
            prod_backup = prod_path.with_name("product.json.backup")
            if not prod_backup.exists():
                shutil.copyfile(prod_path, prod_backup)
            with open(wb_path, "rb") as f:
                new_hash = base64.b64encode(hashlib.sha256(f.read()).digest()).decode("utf-8").rstrip("=")
            with open(prod_path, "r", encoding="utf-8") as f:
                prod_data = json.load(f)
            if "checksums" in prod_data:
                prod_data["checksums"]["vs/workbench/workbench.desktop.main.js"] = new_hash
                with open(prod_path, "w", encoding="utf-8") as f:
                    json.dump(prod_data, f, indent=2)
                print("[+] Da cap nhat ma checksum trong product.json (triet tieu thong bao 'corrupt installation')!")
    except Exception as e:
        print(f"[!] Khong the cap nhat product.json: {e}")

    return True

if __name__ == "__main__":
    apply_test_patch()
