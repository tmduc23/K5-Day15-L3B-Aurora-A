# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Claude Code | Viết `codebase/agent.py`, `tools.py`, `ai.py` (workflow, kiểm mã đoạn, nối OpenRouter); lượt 3–4: bước sửa trích dẫn, bước chọn đoạn → trả lời; `data/import_transcript.py`; tính năng đề ôn tập `codebase/quiz.py` (danh sách link tham khảo `data/references.csv` do Claude Code chọn, đã kiểm mở được bằng curl 28/11); script đo `evidence/count_time_btc.py` | __ đọc lại, chạy `python run.py`, giải thích được từng bước | Ngô Ngọc Hải |
| Prompt / thiết kế lời gọi mô hình | Claude Code | Viết SYSTEM prompt (chỉ trích mã, nói không có trong bài, hỏi lại khi mơ hồ) | __ | Ngô Ngọc Hải |
| Đào data (viết script đếm, gợi ý nhãn) | Claude Code | Viết `evidence/count_chat_btc.py` (chat log BTC) và `evidence/count_comments.py` (bình luận YouTube), điền `evidence/data-mining.md` mục A, B | Chạy lại script ra cùng số; kiểm tay __/68 dòng bình luận, khớp __ | Trần Minh Đức |
| Rà câu hỏi phỏng vấn / khảo sát | Claude Code | Soạn câu hỏi theo kiểu hỏi chuyện đã xảy ra (không dẫn dắt), làm phiếu docx + script Google Form; chép 4 câu trả lời phỏng vấn (ghi qua form) sang `evidence/interviews/ghi-chep-form.csv`, dựng `P1.md`–`P4.md` theo mẫu và tổng hợp x/4 vào `evidence/summary.md` — không thêm, không sửa câu trả lời; kết luận 1 dòng mỗi file viết từ chính câu trả lời | __ đối chiếu `ghi-chep-form.csv` với Sheet câu trả lời, điền người hỏi / ghi | Trần Tùng Lâm |
| Viết câu thử (benchmark) | Claude Code | B01–B14: AI viết (`tu_viet`); B15–B26: AI chọn câu hỏi thật từ bình luận và viết `expected` / `pass_criterion` từ transcript | Mỗi câu thử có `source`; __ đối chiếu `expected` với transcript | Trần Thị Nhài |
| Sinh data `synthetic` (nếu có) | | | Seed __ · kiểm tay __ dòng | |
| Chấm cột `pass` bằng LLM (nếu có) | Claude Code | Chấm cột `pass` + `ghi_chu` của `eval/run-1.csv` … `eval/run-4.csv` (26 câu mỗi lượt) theo `pass_criterion`, theo yêu cầu của nhóm; lý do từng câu ghi ở `ghi_chu` | Trần Thị Nhài kiểm tay lượt 2 và lượt 4: 26/26 câu mỗi lượt, khớp 26/26 (không đổi điểm; 3 câu có khẳng định mâu thuẫn đoạn trích ghi ở `eval/report.md` §4) · Ngô Ngọc Hải chấm chéo độc lập 5 output, khớp 5/5 | Trần Thị Nhài |
| Slide, văn bản | Claude Code | Soạn nháp `spec.md` §2, §3, §5, §6, §8, §9, `eval/report.md`, `cost/cost-estimate.md`, `evidence/summary.md` từ số liệu đã chạy; viết script đếm tần suất dùng (`evidence/count_usage_btc.py`) cho `cost/personas.yaml`; soạn phiếu khảo sát (docx + Google Form) | __ đọc lại, đối chiếu từng con số với file nguồn | Trần Minh Đức, Trần Tùng Lâm |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
