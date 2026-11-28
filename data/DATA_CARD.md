# Data card — dữ liệu bản chạy thử dùng

## Dataset 1 · Transcript bài giảng chia đoạn có mã (`data/lesson_segments.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `get_lesson_segments` và `check_citations`; căn cứ để viết cột `expected` của bộ câu thử |
| Từ đâu | Phụ đề YouTube công khai của 2 video 3Blue1Brown "Neural networks": B1 = *But what is a neural network?* (`aircAruvnKk`, phụ đề tiếng Anh do kênh cung cấp), B2 = *Gradient descent, how neural networks learn* (`IHZwWFHWa-w`, phụ đề tiếng Việt cộng đồng) |
| Xử lý những bước gì | Lấy phụ đề bằng `youtube-transcript-api` · bỏ tạp âm `[Music]` · gộp dòng phụ đề thành đoạn ~45–75 s giữ timestamp gốc · đánh mã `B<bài>-<số đoạn>` (script: dự án `lecture-videorag`, `app/transcript.py`, xuất từ DB ngày 27/11) |
| Số dòng / số đoạn | 39 đoạn (B1: 22, B2: 17), cột: `ma_doan, bai, tieu_de_bai, youtube_id, start, end, text` |
| Phiên bản / ngày lấy | 27/11/2026 |
| Nhãn | thật (transcript công khai), không phải `synthetic` |
| Giới hạn | **Thay thế tạm cho video pre-class Day08** (data BTC chưa có trên máy chạy code) — cần thay bằng transcript Day08 để khớp lát cắt ở canvas. Phụ đề B2 là bản dịch cộng đồng, câu văn lủng củng, có chỗ dịch sai thuật ngữ. Chỉ có lời nói, chưa có chữ trên slide |

## Dataset 2 · Bộ câu thử (`eval/benchmark.csv`)

| | |
|---|---|
| Dùng để làm gì | Đo 3 metric ở `eval/metric_spec.yaml` |
| Từ đâu | 14 câu nhóm tự viết dựa trên Dataset 1 (B01–B14, CP2) + 12 câu hỏi thật của người học lấy nguyên văn từ bình luận công khai dưới 2 video bài giảng (B15–B26, CP3; chỉ bỏ lời cảm ơn đầu câu; mã bình luận đã ẩn danh; cách lấy: `evidence/count_comments.py`) |
| Xử lý những bước gì | Mỗi câu ghi `expected` + tập mã đoạn hợp lệ, đối chiếu tay với transcript |
| Số dòng / số đoạn | 26 (thuong 8 · kho 13 · tu_choi 5) |
| Phiên bản / ngày lấy | 27/11/2026 (CP2, 14 câu) · 28/11/2026 09:00 (CP3, thêm 12 câu thật) |
| Nhãn | `tu_viet` 14 · `data_that` 12 (12/26 ≥ 1/3) |
| Giới hạn | Câu thật là người tự học trên YouTube (tiếng Anh), không phải học viên L3B; nên thêm câu hỏi thật từ `chat.csv` (data BTC) / phỏng vấn khi có |

**Thay đổi 28/11 09:20 (sau lượt 1):** chữ của 17 đoạn B2 trong `data/lesson_segments.csv` đổi từ bản dịch máy tiếng Việt sang phụ đề tiếng Anh gốc (manual) của video `IHZwWFHWa-w`; mã đoạn, mốc start/end giữ nguyên nên `pass_criterion` không đổi. Lượt 1 (`run-1`) chạy trên bản cũ, lượt 2 (`run-2`) trên bản mới.
