# 🛠️ Antigravity History Fixer

> **Bộ công cụ vá lỗi "Tàng hình lịch sử chat" và mở khóa danh sách hội thoại trong Antigravity IDE.**

---

## 🧐 Vấn Đề (Bug Của Google)

Nếu bạn dùng **Antigravity IDE** và thấy rằng:
1. Trong menu chọn hội thoại (`Ctrl + Shift + A` hoặc bấm vào tiêu đề chat), mục **Recent** chỉ hiện vài hội thoại từ cả tháng trước, còn các hội thoại gần đây (tháng 9/2026) cứ tắt IDE mở lại là **biến mất**.
2. Danh sách thường bị ẩn và thu gọn dưới nút **`Show 8 more...`** rất khó chịu.

### 🔍 Nguyên nhân kỹ thuật:
- **Dữ liệu thực tế KHÔNG HỀ BỊ MẤT**: Language Server của Google vẫn lưu 100% các cuộc hội thoại tại `~/.gemini/antigravity-ide/conversations/*.db` và `brain/`.
- **Nhưng giao diện Menu lại bị lỗi**:
  - Giao diện UI chỉ đọc từ IPC channel `trajectorySummaries`.
  - Process chính của Electron (`Antigravity IDE.exe`) giữ cache này trong RAM và bị nghẽn (stuck) từ đầu tháng 09/2026. Nếu chỉ sửa database SQLite trên đĩa thì khi IDE đang chạy, RAM của Electron không tự động nạp lại.
  - Cùng lúc đó, cờ `collapseLargeGroups: true` trong code JavaScript của IDE ép thu gọn danh sách hội thoại cũ.

---

## ⚡ Giải Pháp Của Bộ Tool Này

Bộ công cụ này thực hiện 2 cơ chế tự động:

1. **`patch_ui.py` (Vá giao diện & Kích hoạt Auto-Sync IPC)**:
   - Tự động tìm file `workbench.desktop.main.js` của Antigravity IDE.
   - Tạo bản backup an toàn `workbench.desktop.main.js.backup`.
   - Đổi cờ `collapseLargeGroups: !0` $\rightarrow$ `!1` để menu Recent **luôn bung 100%**, không bao giờ bị nút `Show more` giấu đi nữa.
   - **Tự động quét toàn bộ 55+ file hội thoại trên đĩa** và tiêm trực tiếp lệnh cập nhật qua bus IPC `pushUpdate(tph(...))` của chính Antigravity. Ngay khi giao diện tải lên, toàn bộ hội thoại cũ sẽ được đẩy trực tiếp vào bộ nhớ của IDE mà không sợ bị cache chặn.
   - Tự động kiểm tra cú pháp bằng `node --check` trước khi ghi đè để đảm bảo an toàn tuyệt đối.

2. **`sync_conversations.py` (Hồi sinh mục lục SQLite dự phòng)**:
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

### 2. Khi Antigravity IDE có bản Update mới:
Mỗi khi Google tung bản update tự động cho Antigravity IDE, file code giao diện có thể bị Google ghi đè lại. Bạn chỉ cần:
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
├── run_fix.bat             # File thực thi 1-click (Vá UI + Đồng bộ hội thoại)
├── run_restore.bat         # File khôi phục nguyên bản gốc
│
├── patch_ui.py             # Script vá file JS workbench của IDE & kích hoạt đồng bộ IPC
├── sync_conversations.py   # Script quét ổ cứng và nạp hội thoại vào SQLite IDE
├── restore.py              # Script khôi phục từ các bản backup
│
└── README.md               # Hướng dẫn chi tiết này
```

---
*Phát triển bởi Traistorm & Antigravity Pair Programmer.*
