# 🛠️ Antigravity History Fixer

> **Bộ công cụ vá lỗi "Tàng hình lịch sử chat", cứu hộ phiên chat bị crash, sửa lỗi văng ứng dụng khi tìm kiếm và đồng bộ đa dự án trong Antigravity IDE.**

---

## 🚨 Các Vấn Đề Được Giải Quyết Triệt Để

1. **Lỗi Crash Antigravity khi gõ tìm kiếm (`Search all convos...`)**:
   - Khi gõ từ khóa vào ô tìm kiếm hội thoại, nếu một cuộc trò chuyện có tiêu đề rỗng hoặc thuộc tính không xác định, bộ chấm điểm tìm kiếm `Hmt` (`K2u` / `z2u`) trong Antigravity ném ngoại lệ `TypeError: Cannot read properties of undefined` và làm sập (crash) toàn bộ tiến trình renderer của IDE.
   - **Giải pháp**: Patch bảo vệ an toàn 100% cho `K2u`, `z2u`, `y3u` và `Hmt`. Tự động tìm kiếm đồng thời cả **Tiêu đề** lẫn **Thư mục / Workspace** mà không bao giờ bị crash.

2. **Lỗi không hiện lịch sử khi chat với nhiều dự án (Workspace URI mismatch)**:
   - Khi bạn mở dự án khác (như `traistorm-ide`, `new-web`, `tts-server`...), Antigravity chỉ hiển thị các phiên chat khớp chính xác tuyệt đối từng ký tự URI. Nếu có sự sai lệch giữa `d:` và `D:`, hoặc dấu mã hóa `%3A` so với `:`, Antigravity sẽ ẩn toàn bộ lịch sử chat của dự án đó.
   - **Giải pháp**: Patch hàm lọc `B5u` với bộ chuẩn hóa URI (`decodeURIComponent`, lowercase, trim trailing slash) và trích xuất đúng Workspace URI cho từng cơ sở dữ liệu hội thoại. Giờ đây mỗi dự án đều hiện đúng các phiên chat của chính nó!

3. **Lỗi mất phiên chat gần nhất khi Antigravity bị Crash hoặc ngắt đột ngột**:
   - SQLite Write-Ahead Log (`.db-wal`) chưa kịp ghi về file `.db` chính và các bước chat bị treo ở `status=2 (RUNNING)`.
   - **Giải pháp**: Tự động chạy `wal_checkpoint(TRUNCATE)` và chuyển toàn bộ bước treo về `status=3 (DONE)`, khôi phục nguyên vẹn 100% nội dung trò chuyện.

4. **Lỗi danh sách bị thu gọn (Capped Recent List)**:
   - Antigravity mặc định bật `collapseLargeGroups: true`, chỉ cho hiển thị tối đa 4 mục rồi ẩn dưới nút `Show more...`.
   - **Giải pháp**: Tự động chuyển `collapseLargeGroups: !1`, giúp toàn bộ danh sách luôn bung mở đầy đủ.

---

## 🚀 Cách Sử Dụng (1-Click)

### Cách 1: Vá lỗi và đồng bộ ngay lập tức (Khuyên dùng)
Nhấp đúp chuột vào file:
```text
run_fix.bat
```
Sau đó vào **Antigravity IDE** và nhấn:
> **`Ctrl + R`** *(Reload Window)*

👉 Bấm `Ctrl + Shift + A` hoặc bấm vào tiêu đề chat: **Tất cả các phiên chat từ trước tới nay của mọi dự án sẽ hiện lên đầy đủ và tìm kiếm mượt mà không bao giờ crash!**

---

### Cách 2: Tự động đồng bộ ngầm khi chat liên tục (Watch Mode)
Nếu bạn thường xuyên chat tạo phiên mới và muốn lịch sử luôn tự động cập nhật ngầm:
Nhấp đúp chuột vào file:
```text
run_watch.bat
```
Script sẽ chạy nền, tự động theo dõi thư mục `conversations/` và đồng bộ ngay khi có tin nhắn hoặc phiên chat mới.

---

### Cách 3: Khôi phục nguyên bản gốc (Undo / Rollback)
Nếu bạn muốn trả Antigravity IDE về trạng thái ban đầu của Google:
Nhấp đúp vào:
```text
run_restore.bat
```

---

## 📁 Cấu Trúc Thư Mục

```text
antigravity-history-fixer/
│
├── run_fix.bat             # Thực thi 1-click (Cứu hộ Crash + Vá UI + Chống Crash Search + Đồng bộ)
├── run_watch.bat           # Chế độ chạy ngầm tự động đồng bộ theo thời gian thực
├── run_restore.bat         # Khôi phục nguyên bản gốc từ bản sao lưu
│
├── patch_ui.py             # Vá lỗi JS workbench, chống crash tìm kiếm, chuẩn hóa URI workspace
├── sync_conversations.py   # Cứu hộ WAL, trích xuất chính xác workspace & nạp danh mục vào SQLite IDE
├── restore.py              # Script khôi phục an toàn
│
└── README.md               # Tài liệu chi tiết
```

---
*Phát triển bởi Traistorm & Antigravity Pair Programmer.*
