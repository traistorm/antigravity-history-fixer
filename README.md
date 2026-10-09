# 🛠️ Antigravity History Fixer

> **Bộ công cụ vá lỗi "Tàng hình lịch sử chat", cứu hộ phiên chat bị crash và mở khóa danh sách hội thoại trong Antigravity IDE.**

---

## 🧐 Vấn Đề (Bug Của Google)

Nếu bạn dùng **Antigravity IDE** và thấy rằng:
1. Trong menu chọn hội thoại (`Ctrl + Shift + A` hoặc bấm vào tiêu đề chat), mục **Recent** chỉ hiện vài hội thoại từ cả tháng trước, còn các hội thoại gần đây cứ tắt IDE mở lại là **biến mất**.
2. Danh sách thường bị ẩn và thu gọn dưới nút **`Show more...`** rất khó chịu.
3. Khi một phiên chat đang chạy mà IDE bị **crash đột ngột hoặc tắt ngang**, phiên đó hoàn toàn biến mất khỏi danh sách vì SQLite bị kẹt file tạm `.db-wal` và các bước chưa hoàn tất bị kẹt ở trạng thái `Running (status=2)`.

### 🔍 Nguyên nhân kỹ thuật:
- **Dữ liệu thực tế KHÔNG HỀ BỊ MẤT**: Language Server của Google vẫn lưu 100% các cuộc hội thoại tại `~/.gemini/antigravity-ide/conversations/*.db` và `brain/`.
- **Nhưng giao diện Menu lại bị lỗi**:
  - Giao diện UI chỉ đọc từ IPC channel `trajectorySummaries`.
  - Process chính của Electron (`Antigravity IDE.exe`) giữ cache này trong RAM và bị nghẽn (stuck). Nếu chỉ sửa database SQLite trên đĩa thì khi IDE đang chạy, RAM của Electron không tự động nạp lại.
  - Cùng lúc đó, cờ `collapseLargeGroups: true` trong code JavaScript của IDE ép thu gọn danh sách hội thoại cũ.
  - Khi crash đột ngột, SQLite Write-Ahead Log (`.db-wal`) chưa được checkpoint vào database chính, khiến IDE coi phiên đó là chưa hoàn tất hoặc hỏng hóc và bỏ qua trong danh mục.

---

## ⚡ Giải Pháp Của Bộ Tool Này

Bộ công cụ này thực hiện 3 cơ chế tự động:

1. **`Crash Recovery` (Tự động cứu hộ phiên chat crash & kẹt WAL)**:
   - Tự động quét toàn bộ cơ sở dữ liệu SQLite trong `conversations/`.
   - Chạy `PRAGMA wal_checkpoint(TRUNCATE)` để hợp nhất dữ liệu từ `.db-wal` dở dang về database chính.
   - Phát hiện các bước thực thi bị treo ở trạng thái `Running` (`status=2`) và tự động chuyển về `Done` (`status=3`) để IDE có thể mở lại bình thường.

2. **`patch_ui.py` (Vá giao diện & Kích hoạt Auto-Sync IPC)**:
   - Tự động nhận diện đường dẫn cài đặt của Antigravity IDE.
   - Tạo bản backup an toàn `workbench.desktop.main.js.backup`.
   - Đổi cờ `collapseLargeGroups: !0` $\rightarrow$ `!1` để menu Recent **luôn bung 100%**, không bao giờ bị nút `Show more` giấu đi nữa.
   - **Tự động quét toàn bộ file hội thoại trên đĩa** và tiêm trực tiếp lệnh cập nhật qua bus IPC `pushUpdate(tph(...))` của chính Antigravity. Ngay khi giao diện tải lên, toàn bộ hội thoại cũ sẽ được đẩy trực tiếp vào bộ nhớ của IDE mà không sợ bị cache chặn.
   - Tự động kiểm tra cú pháp bằng `node --check` và cập nhật checksum trong `product.json` trước khi ghi đè để đảm bảo an toàn tuyệt đối.

3. **`sync_conversations.py` (Hồi sinh mục lục SQLite dự phòng)**:
   - Tự động backup `state.vscdb` thành `state.vscdb.antigravity_backup`.
   - Đóng gói chuẩn Protobuf nhị phân và bơm vào `state.vscdb` làm lớp bảo vệ thứ 2 khi khởi động nguội.

---

## 🚀 Cách Sử Dụng (1-Click)

### 1. Vá lỗi ngay lập tức:
Nhấp đúp chuột vào file:
```text
run_fix.bat
```
Sau khi chạy xong, mở **Antigravity IDE** lên và nhấn:
> **`Ctrl + R`** *(Reload Window)*

Bấm `Ctrl + Shift + A` hoặc click vào tiêu đề chat: **Toàn bộ các phiên chat từ trước tới nay sẽ hiện lên đầy đủ và chi tiết!**

---

### 2. Khi Antigravity IDE có bản Update mới hoặc bị Crash:
Mỗi khi Google tung bản update tự động cho Antigravity IDE, hoặc khi IDE bị crash đột ngột làm mất phiên làm việc gần nhất, bạn chỉ cần:
1. Nhấp đúp chạy lại file `run_fix.bat`.
2. Nhấn `Ctrl + R` trong IDE.  
Mọi thứ sẽ trở lại trạng thái hoàn hảo ngay lập tức.

---

### 3. Khôi phục nguyên bản gốc (Undo / Rollback):
Nếu muốn trả Antigravity IDE về trạng thái ban đầu của Google:
Nhấp đúp vào:
```text
run_restore.bat
```
*(Hoặc chạy lệnh `python restore.py`)*.

---

## 📁 Cấu Trúc Thư Mục

```text
antigravity-history-fixer/
│
├── run_fix.bat             # File thực thi 1-click (Cứu hộ Crash + Vá UI + Đồng bộ hội thoại)
├── run_restore.bat         # File khôi phục nguyên bản gốc
│
├── patch_ui.py             # Script vá file JS workbench của IDE, cứu hộ crash & kích hoạt IPC sync
├── sync_conversations.py   # Script cứu hộ WAL, quét ổ cứng và nạp hội thoại vào SQLite IDE
├── restore.py              # Script khôi phục từ các bản backup
│
└── README.md               # Hướng dẫn chi tiết này
```

---
*Phát triển bởi Traistorm & Antigravity Pair Programmer.*
