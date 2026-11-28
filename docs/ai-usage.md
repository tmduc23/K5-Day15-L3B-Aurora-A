# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Claude Code | Viết `codebase/agent.py`, `tools.py`, `ai.py` (workflow, kiểm mã đoạn, nối OpenRouter) | __ đọc lại, chạy `python run.py`, giải thích được từng bước | Ngô Ngọc Hải |
| Prompt / thiết kế lời gọi mô hình | Claude Code | Viết SYSTEM prompt (chỉ trích mã, nói không có trong bài, hỏi lại khi mơ hồ) | __ | Ngô Ngọc Hải |
| Đào data (viết script đếm, gợi ý nhãn) | Claude Code | Viết `evidence/count_chat_btc.py` (chat log BTC) và `evidence/count_comments.py` (bình luận YouTube), điền `evidence/data-mining.md` mục A, B | Chạy lại script ra cùng số; kiểm tay __/68 dòng bình luận, khớp __ | Trần Minh Đức |
| Rà câu hỏi phỏng vấn / khảo sát | | Chỉ rà câu dẫn dắt | | |
| Viết câu thử (benchmark) | Claude Code | B01–B14: AI viết (`tu_viet`); B15–B26: AI chọn câu hỏi thật từ bình luận và viết `expected` / `pass_criterion` từ transcript | Mỗi câu thử có `source`; __ đối chiếu `expected` với transcript | Trần Thị Nhài |
| Sinh data `synthetic` (nếu có) | | | Seed __ · kiểm tay __ dòng | |
| Chấm cột `pass` bằng LLM (nếu có) | Claude Code | Chấm cột `pass` + `ghi_chu` của `eval/run-1.csv` (26 câu) theo `pass_criterion`, theo yêu cầu của nhóm; lý do từng câu ghi ở `ghi_chu` | Kiểm tra thủ công __/26 câu, khớp __/__ | Trần Thị Nhài |
| Slide, văn bản | | | | |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
