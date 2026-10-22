# Quy Tắc AI Cho Dự Án antigravity-history-fixer (Workspace Rules)

Tất cả AI Agent / Assistant làm việc trong dự án này BẮT BUỘC phải đọc và tuân thủ nghiêm ngặt các quy tắc sau:

---

## 🔍 QUY TRÌNH LÀM VIỆC CẨN THẬN

Phần lớn lỗi do AI gây ra không phải vì code khó, mà vì **sửa khi chưa đọc đủ, đoán thay vì tra,
và báo xong khi chưa kiểm tra**. Các bước dưới đây để chặn đúng ba lỗi đó.

### 1. Trước khi sửa: đọc và tra, không đoán
- Đọc toàn bộ hàm/class/component sẽ sửa, cùng nơi gọi nó và nơi nó gọi tới. Không sửa chỉ dựa vào
  tên hàm, một đoạn trích, hoặc trí nhớ từ lượt trước — file có thể đã đổi.
- Không đoán tên hàm, tham số, key config, field dữ liệu, route, biến môi trường. Grep để xác nhận
  nó tồn tại và đúng chính tả. Không tìm thấy thì nói rõ là không tìm thấy, không tự bịa ra.
- Sửa hàm/module/component dùng chung: grep **tất cả** chỗ dùng và liệt kê ra trước khi sửa.
  Thay đổi phải giữ đúng hành vi cũ cho những chỗ không liên quan.
- Yêu cầu có từ hai cách hiểu trở lên mà mỗi cách cho ra code khác nhau → hỏi lại một câu ngắn,
  không tự chọn. Yêu cầu đủ rõ → làm luôn, không hỏi thừa.
- Debug: tìm nguyên nhân gốc trước khi sửa (đọc log/traceback, tái hiện, xác định dòng gây lỗi).
  Không vá triệu chứng bằng nuốt exception, thêm `if` né lỗi, hay tăng timeout cho qua.

### 2. Khi sửa: đúng phạm vi, đúng phong cách
- Chỉ sửa những gì yêu cầu cần. Thấy vấn đề khác → ghi lại để báo cuối lượt, không tự sửa,
  không tiện tay refactor, đổi tên, format lại file.
- Bám theo cách viết của code xung quanh: cách đặt tên, cách log, cách xử lý lỗi, cách đọc config.
  Có helper sẵn thì dùng lại, không viết bản thứ hai.
- Không xóa comment, log, nhánh xử lý lỗi mà mình chưa hiểu vì sao tồn tại.
- Không đổi chữ ký hàm/định dạng dữ liệu trả về nếu chưa sửa đồng thời mọi nơi gọi.

### 3. Sau khi sửa: kiểm tra thật rồi mới báo
Bắt buộc làm, theo thứ tự:
1. **Đọc lại diff của chính mình** (`git diff`), rà: import thiếu/thừa, biến chưa định nghĩa,
   null/chuỗi rỗng/list rỗng, encoding tiếng Việt, đường dẫn Windows, exception bị nuốt.
2. **Chạy kiểm tra phù hợp với phần đã sửa** (chọn đúng test liên quan, không chạy tràn lan):
   - Python: `python -X utf8 -m py_compile <file.py> ...`
   - Dự án chưa có test tự động → nói rõ phần nào chưa được chạy thử thật.
   - Không tự chạy các script vá/khôi phục lên bản cài Antigravity hoặc dữ liệu chat thật
     (`run_fix.bat`, `run_restore.bat`, `run_watch.bat`, `patch_ui.py`, `restore.py`,
     `sync_conversations.py`) khi chưa hỏi.
   - **Không** tự chạy lệnh/test gọi dịch vụ thật, tốn phí, gửi tin nhắn, hoặc ghi vào dữ liệu/cấu hình
     thật — hỏi trước.
   - Test fail: xác định đó là lỗi do mình hay lỗi có sẵn (chạy lại trên code chưa sửa nếu cần).
     Không sửa test cho xanh khi chưa hiểu vì sao nó fail.
3. **Báo cáo trung thực**, gồm:
   - Đã sửa gì (file + hàm/dòng), vì sao.
   - Đã kiểm tra gì và kết quả thật (số test qua/fail, dán lỗi nếu có).
   - **Chưa** kiểm tra được gì (ví dụ: chưa chạy thử giao diện thật, chưa test với dịch vụ thật).
   - Các vấn đề khác phát hiện được nhưng không sửa.

Không được nói "đã xong", "đã fix", "chạy ổn" nếu chưa làm bước 1–2. Nếu không chạy được
kiểm tra (thiếu môi trường, cần dịch vụ thật), nói rõ như vậy thay vì bỏ qua im lặng.

---

## 📢 QUY TẮC CẬP NHẬT TIẾN ĐỘ (INTERMEDIATE LOGGING)

- Trước khi bắt đầu tác vụ phức tạp, debug hoặc chuỗi thao tác công cụ, **báo ngắn gọn việc sắp làm** để người dùng biết yêu cầu đã được tiếp nhận.
- Trong quá trình làm, cập nhật khi có phát hiện quan trọng, hoàn thành một chặng, thay đổi hướng xử lý hoặc gặp trở ngại. Mỗi cập nhật nên có 1–3 câu, nói rõ vừa xác minh được gì và bước tiếp theo; không cần báo trước mọi tool call.
- **Không im lặng gọi tool liên tục từ đầu đến cuối.** Với tác vụ kéo dài, cố gắng không để quá khoảng 60 giây thiếu cập nhật khi môi trường cho phép. Nếu một tool chạy lâu, cập nhật trước khi chờ và sau khi có kết quả; không bịa tiến độ trong lúc chưa nhận được kết quả.
- Chỉ báo hành động và phát hiện thực tế. Phân biệt rõ đang điều tra, đã sửa file, đã kiểm tra và đã commit/push; không nói “đã xong” hoặc “đã fix triệt để” khi chưa có bằng chứng tương ứng. Nêu phần chưa kiểm tra hoặc đang bị chặn.
- Nội dung cập nhật phải hữu ích, không lặp tin chờ, không liệt kê mọi thao tác vụn vặt và không tiết lộ suy luận nội bộ, token, cookie hoặc thông tin bí mật.
- Khi kết thúc, tóm tắt kết quả, cách đã kiểm tra và giới hạn còn lại để người dùng không phải tìm lại các tin tiến độ.

---

## 🛑 XỬ LÝ TIN NHẮN CHEN NGANG (MID-TASK / QUEUED MESSAGES)

- Khi nhận được tin chen ngang, **đọc và phân loại ở điểm chuyển bước an toàn gần nhất**: câu hỏi/trò chuyện, thông tin bổ sung/chỉnh hướng, yêu cầu mới hay yêu cầu dừng. Không tự hủy process, transaction hoặc thao tác đang chạy chỉ để trả lời một câu hỏi.
- Nếu là câu hỏi hoặc thắc mắc, **trả lời trực tiếp và ngắn gọn trước khi tiếp tục các bước không liên quan**. Dùng thông tin đã xác minh; nếu chưa đủ căn cứ thì nói rõ và chỉ đọc/kiểm tra phần cần thiết để trả lời chính xác. Không tự sửa code, cấu hình, dữ liệu hoặc triển khai một tính năng chỉ vì người dùng hỏi về nó.
- Nếu là thông tin bổ sung hoặc chỉnh hướng, kết hợp vào task đang làm và giữ các mục tiêu/ràng buộc trước đó còn hiệu lực. Không tự coi tin mới là thay thế toàn bộ task cũ. Chỉ dừng hoặc chuyển hẳn mục tiêu khi người dùng yêu cầu rõ, hoặc yêu cầu mới thực sự mâu thuẫn với việc đang làm; nếu không rõ, hỏi ngắn gọn về điểm mâu thuẫn.
- **Sau khi trả lời, tự tiếp tục công việc đã được giao nếu còn bước hợp lệ để làm.** Không hỏi lại “có muốn tiếp tục không” và không kết thúc lượt chỉ vì vừa trả lời tin chen ngang trong khi task vẫn còn việc có thể thực hiện.
- Giữ nguyên các điểm chờ bắt buộc: thiếu thông tin thiết yếu, chờ duyệt prompt/TOML, thiếu quyền hoặc trở ngại kỹ thuật. Nêu cụ thể đang chờ gì và vì sao; tiếp tục những phần độc lập có thể làm, không tự coi im lặng hay thời gian trôi qua là đồng ý.
- Nếu người dùng yêu cầu dừng/hủy, không bắt đầu bước mới; xử lý thao tác đang chạy theo cơ chế dừng an toàn hiện có và báo lại trạng thái thực tế.
