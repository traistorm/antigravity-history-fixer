import os
import shutil
from pathlib import Path

def restore():
    print("[*] Bat dau khoi phuc Antigravity IDE ve trang thai goc...")

    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\Traistorm\AppData\Local")
    app_dir = Path(local_app_data) / "Programs" / "Antigravity IDE" / "resources" / "app"

    # 1. Restore workbench.desktop.main.js
    wb_path = app_dir / "out" / "vs" / "workbench" / "workbench.desktop.main.js"
    wb_backup = wb_path.with_name(wb_path.name + ".backup")
    if wb_backup.exists():
        shutil.copyfile(wb_backup, wb_path)
        print(f"[+] Da khoi phuc thanh cong: {wb_path.name}")
    else:
        print(f"[-] Khong tim thay ban backup: {wb_backup}")

    # 2. Restore product.json
    prod_path = app_dir / "product.json"
    prod_backup = prod_path.with_name("product.json.backup")
    if prod_backup.exists():
        shutil.copyfile(prod_backup, prod_path)
        print(f"[+] Da khoi phuc thanh cong: {prod_path.name}")
    else:
        print(f"[-] Khong tim thay ban backup: {prod_backup}")

    # 3. Restore state.vscdb
    app_data = Path(os.environ.get("APPDATA", r"C:\Users\Traistorm\AppData\Roaming"))
    vscdb_path = app_data / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb"
    vscdb_backup = vscdb_path.with_name("state.vscdb.antigravity_backup")
    if vscdb_backup.exists():
        shutil.copyfile(vscdb_backup, vscdb_path)
        print(f"[+] Da khoi phuc thanh cong: {vscdb_path.name}")
    else:
        print(f"[-] Khong tim thay ban backup: {vscdb_backup}")

    print("\n[+] Hoan tat khoi phuc. Vui long Reload Window (Ctrl + R) hoac restart IDE.")

if __name__ == "__main__":
    restore()
