# Quy Tắc AI Cho Dự Án antigravity-history-fixer (Workspace Rules)

Tất cả AI Agent / Assistant làm việc trong dự án này BẮT BUỘC phải đọc và tuân thủ nghiêm ngặt các quy tắc sau:

---

## 📢 QUY TẮC CẬP NHẬT TIẾN ĐỘ (INTERMEDIATE LOGGING - DÀNH CHO GEMINI)

- Khi thực hiện các tác vụ phức tạp, debug, kiểm tra mã nguồn hoặc chạy nhiều bước công cụ liên tiếp (tool calls), Gemini **bắt buộc phải xuất tin nhắn ngắn tóm tắt tiến độ/phát hiện giữa các lần gọi tool** (tương tự trải nghiệm của Claude Code / Codex).
- Cụ thể: Báo ngắn gọn vừa tìm thấy gì hoặc chuẩn bị làm gì trước khi kích hoạt tool tiếp theo để người dùng luôn nắm bắt được diễn biến thực tế.
- Tuyệt đối **không im lặng gọi tool liên tục** từ đầu đến cuối mà không có thông báo trung gian cho người dùng.

---

## 🛑 XỬ LÝ TIN NHẮN CHEN NGANG (MID-TASK / QUEUED MESSAGES - DÀNH CHO GEMINI)

- Khi đang thực hiện tác vụ mà nhận được tin nhắn gửi chen ngang của người dùng (queued messages):
  1. Phải dừng lại để phân loại: Đây là câu hỏi, thắc mắc, trò chuyện hay là lệnh code mới?
  2. Nếu là câu hỏi hoặc thắc mắc: **Bắt buộc phải trả lời trực tiếp câu hỏi của người dùng trước**, tuyệt đối không được tự ý biến câu hỏi thành lệnh gọi tool lục lọi mã nguồn.
  3. Sau khi trả lời ngắn gọn, nếu task trước đó đang dở dang và người dùng không yêu cầu dừng lại, **BẮT BUỘC PHẢI TỰ ĐỘNG GỌI TOOL TIẾP TỤC TASK ĐANG LÀM NGAY LẬP TỨC**, tuyệt đối không dừng lại để hỏi "có muốn tiếp tục không".
