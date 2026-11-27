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
| Từ đâu | Nhóm tự viết dựa trên Dataset 1 (14 câu: thuong 6 · kho 5 · tu_choi 3, gồm 2 câu tấn công) |
| Xử lý những bước gì | Mỗi câu ghi `expected` + tập mã đoạn hợp lệ, đối chiếu tay với transcript |
| Số dòng / số đoạn | 14 |
| Phiên bản / ngày lấy | 27/11/2026 (CP2) |
| Nhãn | `tu_viet` |
| Giới hạn | **Chưa đạt ≥1/3 câu từ người dùng / data thật**: cần thêm câu hỏi thật lấy từ `chat.csv` (data BTC) hoặc phỏng vấn học viên trước CP3 |
