"""
Antigravity History Fixer - UI Patcher
Vá workbench.desktop.main.js của Antigravity IDE:
 1. Chống crash khi gõ tìm kiếm (K2u/z2u/Hmt/W2u/S3u/b3u/y3u + decodeURIComponent an toàn).
 2. Bộ lọc workspace chuẩn hóa URI (B5u); hội thoại không có workspace hiện ở mọi dự án.
 3. Mở khóa đồng bộ liên dự án (sAh).
 4. Nạp hội thoại còn thiếu: đọc agy_convos.json lúc chạy (poll 20s) -> hội thoại mới tự hiện,
    không cần vá lại / Ctrl+R. Snapshot nhúng sẵn chỉ là dự phòng.
 5. Bỏ giới hạn collapseLargeGroups.
 6. Cập nhật checksum product.json.
Mọi bản vá bắt buộc không khớp => báo lỗi rõ ràng và KHÔNG ghi gì (không im lặng bỏ qua).
Luôn vá từ bản backup gốc; nếu IDE được cập nhật (commit đổi) thì backup được làm mới.
"""

import sys
import json
import base64
import hashlib
import shutil
import subprocess

import common
from common import app_dir

MARKER = "/*AGY_CONVO_SYNC*/"


def find_workbench_js():
    return app_dir() / "out" / "vs" / "workbench" / "workbench.desktop.main.js"


def _commit_of(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("commit")
    except Exception:
        return None


def prepare_backups(wb_path):
    """Dam bao backup khop voi ban IDE hien tai. Tra ve duong dan backup JS."""
    backup = wb_path.with_name(wb_path.name + ".backup")
    prod = app_dir() / "product.json"
    prod_bk = prod.with_name("product.json.backup")
    cur_js = wb_path.read_bytes()
    already_patched = MARKER.encode() in cur_js

    stale = False
    if backup.exists() and prod_bk.exists():
        c_old, c_now = _commit_of(prod_bk), _commit_of(prod)
        if c_old and c_now and c_old != c_now and not already_patched:
            stale = True
            print(f"[!] IDE da cap nhat ({c_old[:8]} -> {c_now[:8]}): lam moi backup tu ban hien tai.")
    if not backup.exists() or stale:
        if already_patched:
            raise SystemExit("[-] File workbench da duoc va nhung khong co backup goc - khong the tiep tuc an toan.")
        shutil.copyfile(wb_path, backup)
        if prod.exists():
            shutil.copyfile(prod, prod_bk)
        print(f"[+] Da tao backup: {backup.name}")
    else:
        print(f"[i] Dung ban base goc: {backup.name}")
    return backup


# (ten, target, replacement, bat_buoc)
def build_patches(snapshot_json):
    P = []

    P.append(("K2u/z2u/Hmt (crash khi search)",
        r'''function K2u(t,e){if(t.length===0)return!0;if(e.length===0)return!1;let i=0,n=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()&&i++,n++;return i===t.length}function z2u(t,e){if(t.length===0)return 1e3;if(e.length===0)return 0;let i=0,n=0,r=!1,s=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()?(r?s+=2:s+=1,r=!0,i++):r=!1,n++;return s+=Math.max(0,1-e.length/100),s}var Hmt={score:(t,e)=>({score:z2u(t,e.label)}),filter:(t,e)=>K2u(t,e.label)}''',
        r'''function K2u(t,e){if(!t||t.length===0)return!0;if(!e||typeof e!=="string"||e.length===0)return!1;let i=0,n=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()&&i++,n++;return i===t.length}function z2u(t,e){if(!t||t.length===0)return 1e3;if(!e||typeof e!=="string"||e.length===0)return 0;let i=0,n=0,r=!1,s=0;for(;n<e.length&&i<t.length;)t[i].toLowerCase()===e[n].toLowerCase()?(r?s+=2:s+=1,r=!0,i++):r=!1,n++;return s+=Math.max(0,1-e.length/100),s}var Hmt={score:(t,e)=>{try{const s=((e&&e.label)?String(e.label):"")+" "+((e&&e.description)?String(e.description):"");return{score:z2u(t||"",s)}}catch(_){return{score:0}}},filter:(t,e)=>{try{const s=((e&&e.label)?String(e.label):"")+" "+((e&&e.description)?String(e.description):"");return K2u(t||"",s)}catch(_){return!1}}}''',
        True))

    P.append(("W2u (loc/sap xep ket qua search)",
        r'''function W2u(t,e,i){return t.filter(n=>e.filter(i,n)).sort((n,r)=>e.score(i,r).score-e.score(i,n).score).map(n=>({...n,...e.score(i,n)}))}''',
        r'''function W2u(t,e,i){try{return t.filter(n=>e.filter(i,n)).map(n=>({...n,...e.score(i,n)})).sort((n,r)=>(r.score||0)-(n.score||0))}catch(_){return[]}}''',
        True))

    P.append(("B5u (loc workspace Recent)",
        r'''function B5u(t,e,i){return Object.entries(t.summaries).sort((n,r)=>Number((r[1].lastUserInputTime&&kb(r[1].lastUserInputTime))?.getTime()??0)-Number((n[1].lastUserInputTime&&kb(n[1].lastUserInputTime))?.getTime()??0)).filter(([,n])=>i&&n.trajectoryMetadata?.parentConversationId?!1:n.workspaces.map(r=>r.workspaceFolderAbsoluteUri).some(r=>e.includes(r))).map(([n])=>n)}''',
        r'''function B5u(t,e,i){let _nm=u=>{let s=String(u||"");try{s=decodeURIComponent(s)}catch(_){}return s.toLowerCase().replace(/\/+$/,"")};let _ew=(e||[]).map(_nm);return Object.entries(t.summaries).sort((n,r)=>Number((r[1].lastUserInputTime&&kb(r[1].lastUserInputTime))?.getTime()??0)-Number((n[1].lastUserInputTime&&kb(n[1].lastUserInputTime))?.getTime()??0)).filter(([,n])=>i&&n.trajectoryMetadata?.parentConversationId?!1:((n.workspaces||[]).length===0||(n.workspaces||[]).map(r=>_nm(r.workspaceFolderAbsoluteUri)).some(r=>_ew.includes(r)))).map(([n])=>n)}''',
        True))

    P.append(("y3u (label/description an toan)",
        r'''function y3u(t,e,i,n,r,s,o){let a=i.lastModifiedTime&&kb(i.lastModifiedTime);return{type:"basic",item:{id:t,label:i.summary,description:s?void 0:b3u(i.workspaces[0]?.workspaceFolderAbsoluteUri,r),descriptionOrientation:"horizontal",detail:a?Vna(a,!0):"",iconButtons:[{component:l=>E($e,{name:"delete",...l}),showOnlyOnHover:!0,onClick:()=>{o(t)}}],iconRight:n?E($e,{name:"circle",size:8,className:"fill-current"}):void 0,group:e}}}''',
        r'''function y3u(t,e,i,n,r,s,o){let a=i.lastModifiedTime&&kb(i.lastModifiedTime);let l=i.summary||("Conversation "+t.slice(0,8));let d=s?void 0:(b3u(i.workspaces?.[0]?.workspaceFolderAbsoluteUri,r)||"");return{type:"basic",item:{id:t,label:l,description:d,descriptionOrientation:"horizontal",detail:a?Vna(a,!0):"",iconButtons:[{component:c=>E($e,{name:"delete",...c}),showOnlyOnHover:!0,onClick:()=>{o(t)}}],iconRight:n?E($e,{name:"circle",size:8,className:"fill-current"}):void 0,group:e}}}''',
        True))

    P.append(("b3u (URI.parse khong the nem loi)",
        r'''function b3u(t,e){let i=t?od.parse(t):void 0''',
        r'''function b3u(t,e){try{return _agyB3u(t,e)}catch(_){return""}}function _agyB3u(t,e){let i=t?od.parse(t):void 0''',
        True))

    P.append(("S3u (waitingSteps co the undefined)",
        r'''u&&(d===i?r.push(d):u.waitingSteps.length>0?s.push(d)''',
        r'''u&&(d===i?r.push(d):(u.waitingSteps||[]).length>0?s.push(d)''',
        True))

    P.append(("sAh (dong bo lien du an)",
        r'''if(n&&a.some(l=>l.workspaceFolderAbsoluteUri===n.toString()))return s.appliedUpdate.newRow.value=LR(rpe,_r(rpe,{...o,workspaces:a})),s''',
        r'''return s.appliedUpdate.newRow.value=LR(rpe,_r(rpe,{...o,workspaces:a})),s''',
        False))

    init_target = r'''async _initializeTrajectorySummariesProvider(){const e=await this._unifiedStateSyncService.subscribe("trajectorySummaries"),'''
    init_repl = (
        r'''async _initializeTrajectorySummariesProvider(){const e=await this._unifiedStateSyncService.subscribe("trajectorySummaries");''' + MARKER +
        r'''try{const _sv=this._unifiedStateSyncService,_pd=new Set(),_q=[];let _run=!1;'''
        r'''const _drain=()=>{if(_run)return;_run=!0;const _tm=setInterval(()=>{if(_q.length===0){clearInterval(_tm);_run=!1;return}const[c,w,t,s]=_q.shift();try{_sv.pushUpdate(tph(c,w,new Date(t),s))}catch(_){}},15)};'''
        r'''const _add=al=>{try{const kd=e.get()?.data||{};for(const it of al){if(!Array.isArray(it)||!it[0]||kd[it[0]]||_pd.has(it[0]))continue;_pd.add(it[0]);_q.push(it)}if(_q.length)_drain()}catch(_){}};'''
        r'''_add(''' + snapshot_json + r''');'''
        r'''const _poll=async()=>{try{const r=await fetch(new URL("../../../../agy_convos.json",location.href).href+"?t="+Date.now(),{cache:"no-store"});if(r.ok)_add(await r.json())}catch(_){}};'''
        r'''_poll();setInterval(_poll,2e4)}catch(_){};const '''
    )
    P.append(("Nap hoi thoai thieu (manifest + poll)", init_target, init_repl, True))
    return P


def node_check(content, wb_path):
    scratch = wb_path.with_name("test_workbench_syntax.js")
    scratch.write_text(content, encoding="utf-8")
    try:
        res = subprocess.run(["node", "--check", str(scratch)], capture_output=True, text=True)
    except FileNotFoundError:
        print("[-] Khong tim thay 'node' de kiem tra cu phap - dung lai de an toan.")
        return False
    finally:
        try:
            scratch.unlink()
        except Exception:
            pass
    if res.returncode != 0:
        print("[-] Cu phap JS khong hop le:\n" + res.stderr)
        return False
    return True


def apply_ui_patches():
    wb_path = find_workbench_js()
    if not wb_path.exists():
        print(f"[-] Khong tim thay workbench JS: {wb_path}")
        return False

    backup = prepare_backups(wb_path)
    content = backup.read_text(encoding="utf-8", errors="ignore")

    convos = common.scan_conversations()
    items, mpath = common.write_manifest(convos)
    print(f"[i] Tim thay {len(items)} hoi thoai; manifest: {mpath}")

    n_collapse = content.count("collapseLargeGroups:!0")
    content = content.replace("collapseLargeGroups:!0", "collapseLargeGroups:!1")
    print(f"[+] collapseLargeGroups: bung {n_collapse} vi tri")

    failed = []
    for name, target, repl, required in build_patches(json.dumps(items, ensure_ascii=False)):
        if content.count(target) == 1:
            content = content.replace(target, repl, 1)
            print(f"[+] OK   {name}")
        else:
            tag = "THIEU" if required else "bo qua"
            print(f"[{'-' if required else '!'}] {tag} {name} (khop {content.count(target)} cho, can dung 1)")
            if required:
                failed.append(name)
    if failed:
        print("\n[-] Ban IDE nay khac ban da phan tich, KHONG ghi gi ca. Can cap nhat patch cho:")
        for n in failed:
            print("    -", n)
        return False

    if not node_check(content, wb_path):
        return False
    print("[+] Cu phap JS hop le")

    wb_path.write_text(content, encoding="utf-8")
    print(f"[+] Da cap nhat {wb_path.name}")

    try:
        prod = app_dir() / "product.json"
        if prod.exists():
            new_hash = base64.b64encode(hashlib.sha256(wb_path.read_bytes()).digest()).decode().rstrip("=")
            data = json.loads(prod.read_text(encoding="utf-8"))
            if "checksums" in data:
                data["checksums"]["vs/workbench/workbench.desktop.main.js"] = new_hash
                prod.write_text(json.dumps(data, indent=2), encoding="utf-8")
                print("[+] Da cap nhat checksum product.json")
    except Exception as e:
        print(f"[!] Khong cap nhat duoc product.json: {e}")
    return True


if __name__ == "__main__":
    common.recover_crashed_conversations()
    sys.exit(0 if apply_ui_patches() else 1)
