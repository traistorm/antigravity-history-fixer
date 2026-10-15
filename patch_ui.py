"""
Antigravity History Fixer - UI Patcher & Crash Recovery
Tác giả: Traistorm & Antigravity Pair Programmer
Mô tả:
1. Cứu hộ tự động các phiên chat bị crash / kẹt WAL dở dang.
2. Vá lỗi crash khi gõ tìm kiếm trong ô 'Search all convos...' (guard undefined label / search scoring).
3. Vá thuật toán lọc workspace trong menu Recent (chuẩn hóa URI so sánh, khớp cả d: lẫn D:, unescape %3A).
4. Mở rộng toàn bộ danh sách hội thoại Recent (bỏ giới hạn collapseLargeGroups).
5. Tự động cập nhật mã checksum trong product.json để loại bỏ thông báo 'corrupt installation'.
"""

import os
import sys
import shutil
import hashlib
import json
import base64
import sqlite3
import subprocess
from pathlib import Path

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

def apply_ui_patches():
    wb_path = find_workbench_js()
    if not wb_path.exists():
        print(f"[-] Khong tim thay file workbench JS tai: {wb_path}")
        return False

    user_home = Path(os.path.expanduser("~"))
    convos_dir = user_home / ".gemini" / "antigravity-ide" / "conversations"
    if convos_dir.exists():
        recover_crashed_conversations(convos_dir)

    backup_path = wb_path.with_name(wb_path.name + ".backup")
    if not backup_path.exists():
        print(f"[*] Dang tao ban backup nguyen ban: {backup_path.name}...")
        shutil.copyfile(wb_path, backup_path)
        print(f"[+] Da tao backup: {backup_path.name}")
    else:
        print(f"[i] Su dung ban base goc tu: {backup_path.name}")

    # Luon doc tu ban base goc de patch luon nhat quan va co the chay lai bat ky luc nao
    with open(backup_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 1. Mo rong nhom (Uncollapse Large Groups)
    content = content.replace("collapseLargeGroups:!0", "collapseLargeGroups:!1")

    # 2. Va loi crash khi tim kiem (Search Scorer & Filter TypeError guard)
    target_k2u_hmt = (
        'function K2u(t,e){if(t.length===0)return!0;if(e.length===0)return!1;'
        'let i=0,n=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()&&i++,n++;'
        'return i===t.length}function z2u(t,e){if(t.length===0)return 1e3;if(e.length===0)return 0;'
        'let i=0,n=0,r=!1,s=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()?'
        '(r?s+=2:s+=1,r=!0,i++):r=!1,n++;return s+=Math.max(0,1-e.length/100),s}'
        'var Hmt={score:(t,e)=>({score:z2u(t,e.label)}),filter:(t,e)=>K2u(t,e.label)}'
    )
    replacement_k2u_hmt = (
        'function K2u(t,e){if(!t||t.length===0)return!0;if(!e||typeof e!=="string"||e.length===0)return!1;'
        'let i=0,n=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()&&i++,n++;'
        'return i===t.length}function z2u(t,e){if(!t||t.length===0)return 1e3;if(!e||typeof e!=="string"||e.length===0)return 0;'
        'let i=0,n=0,r=!1,s=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()?'
        '(r?s+=2:s+=1,r=!0,i++):r=!1,n++;return s+=Math.max(0,1-e.length/100),s}'
        'var Hmt={score:(t,e)=>{try{const s=((e&&e.label)?String(e.label):"")+" "+((e&&e.description)?String(e.description):"");'
        'return{score:z2u(t||"",s)}}catch(_){return{score:0}}},filter:(t,e)=>{try{const s=((e&&e.label)?String(e.label):"")+" "+'
        '((e&&e.description)?String(e.description):"");return K2u(t||"",s)}catch(_){return!1}}}'
    )
    if target_k2u_hmt in content:
        content = content.replace(target_k2u_hmt, replacement_k2u_hmt, 1)
        print("[+] Da va loi Crash khi tim kiem (K2u, z2u, Hmt Scorer Safe Guard)!")
    else:
        print("[!] Chu y: target_k2u_hmt khong tim thay trong base, co the da duoc cap nhat.")

    # 3. Va bo loc workspace trong Recent list (B5u URI normalizer)
    target_b5u = (
        'function B5u(t,e,i){return Object.entries(t.summaries).sort((n,r)=>Number((r[1].lastUserInputTime&&kb(r[1].lastUserInputTime))?.getTime()??0)'
        '-Number((n[1].lastUserInputTime&&kb(n[1].lastUserInputTime))?.getTime()??0)).filter(([,n])=>i&&n.trajectoryMetadata?.parentConversationId?!1:'
        'n.workspaces.map(r=>r.workspaceFolderAbsoluteUri).some(r=>e.includes(r))).map(([n])=>n)}'
    )
    replacement_b5u = (
        'function B5u(t,e,i){let _nm=u=>decodeURIComponent(String(u||"")).toLowerCase().replace(/\\/+$/,"");'
        'let _ew=(e||[]).map(_nm);return Object.entries(t.summaries).sort((n,r)=>Number((r[1].lastUserInputTime&&kb(r[1].lastUserInputTime))?.getTime()??0)'
        '-Number((n[1].lastUserInputTime&&kb(n[1].lastUserInputTime))?.getTime()??0)).filter(([,n])=>i&&n.trajectoryMetadata?.parentConversationId?!1:'
        '(n.workspaces||[]).map(r=>_nm(r.workspaceFolderAbsoluteUri)).some(r=>_ew.includes(r))).map(([n])=>n)}'
    )
    if target_b5u in content:
        content = content.replace(target_b5u, replacement_b5u, 1)
        print("[+] Da va bo loc Workspace cho menu Recent (B5u URI Normalizer)!")
    else:
        print("[!] Chu y: target_b5u khong tim thay trong base.")

    # 4. Va ham y3u de luon dam bao label va description ton tai (khong bao gio undefined)
    target_y3u = (
        'function y3u(t,e,i,n,r,s,o){let a=i.lastModifiedTime&&kb(i.lastModifiedTime);'
        'return{type:"basic",item:{id:t,label:i.summary,description:s?void 0:b3u(i.workspaces[0]?.workspaceFolderAbsoluteUri,r),'
        'descriptionOrientation:"horizontal",detail:a?Vna(a,!0):"",'
        'iconButtons:[{component:l=>E($e,{name:"delete",...l}),showOnlyOnHover:!0,onClick:()=>{o(t)}}],'
        'iconRight:n?E($e,{name:"circle",size:8,className:"fill-current"}):void 0,group:e}}}'
    )
    replacement_y3u = (
        'function y3u(t,e,i,n,r,s,o){let a=i.lastModifiedTime&&kb(i.lastModifiedTime);'
        'let l=i.summary||("Conversation "+t.slice(0,8));let d=s?void 0:(b3u(i.workspaces?.[0]?.workspaceFolderAbsoluteUri,r)||"");'
        'return{type:"basic",item:{id:t,label:l,description:d,descriptionOrientation:"horizontal",detail:a?Vna(a,!0):"",'
        'iconButtons:[{component:c=>E($e,{name:"delete",...c}),showOnlyOnHover:!0,onClick:()=>{o(t)}}],'
        'iconRight:n?E($e,{name:"circle",size:8,className:"fill-current"}):void 0,group:e}}}'
    )
    if target_y3u in content:
        content = content.replace(target_y3u, replacement_y3u, 1)
        print("[+] Da bao ve an toan thuoc tinh Label & Description trong y3u!")
    else:
        print("[!] Chu y: target_y3u khong tim thay trong base.")

    # Kiem tra cu phap voi node --check truoc khi ghi
    scratch_js = wb_path.with_name("test_workbench_syntax.js")
    with open(scratch_js, "w", encoding="utf-8") as f:
        f.write(content)

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

    # Ghi de vao file chinh
    with open(wb_path, "w", encoding="utf-8") as f:
        f.write(content)
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
    apply_ui_patches()
