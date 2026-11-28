# Data card — dữ liệu bản chạy thử dùng

## Dataset 1 · Transcript bài giảng chia đoạn có mã (`data/lesson_segments.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `get_lesson_segments` và `check_citations`; căn cứ để viết cột `expected` của bộ câu thử |
| Từ đâu | Phụ đề YouTube công khai của 2 video 3Blue1Brown "Neural networks": B1 = *But what is a neural network?* (`aircAruvnKk`, phụ đề tiếng Anh do kênh cung cấp), B2 = *Gradient descent, how neural networks learn* (`IHZwWFHWa-w`; đến lượt 1 là phụ đề tiếng Việt cộng đồng, từ lượt 2 là phụ đề tiếng Anh do kênh cung cấp — xem ghi chú thay đổi cuối file) |
| Xử lý những bước gì | Lấy phụ đề bằng `youtube-transcript-api` · bỏ tạp âm `[Music]` · gộp dòng phụ đề thành đoạn ~45–75 s giữ timestamp gốc · đánh mã `B<bài>-<số đoạn>` (script: dự án `lecture-videorag`, `app/transcript.py`, xuất từ DB ngày 27/11) |
| Số dòng / số đoạn | 39 đoạn (B1: 22, B2: 17), cột: `ma_doan, bai, tieu_de_bai, youtube_id, start, end, text` |
| Phiên bản / ngày lấy | 27/11/2026 |
| Nhãn | thật (transcript công khai), không phải `synthetic` |
| Giới hạn | **Thay thế tạm cho video pre-class Day08**: data BTC (`data/preclass/`) không có transcript bài giảng — cần thay bằng transcript Day08 khi có để khớp lát cắt ở canvas. Bài giảng tiếng Anh, học viên hỏi tiếng Việt. Chỉ có lời nói, chưa có chữ trên slide |

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

## Dataset 3 · Danh sách link tham khảo (`data/references.csv`)

*Thêm 28/11 14:33 cùng tính năng đề ôn tập (commit `db96658`). Không dùng cho bộ câu thử hay các lượt `run-1`…`run-4`.*

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `get_references` (`codebase/tools.py`): gợi ý tài liệu đọc thêm trong đề ôn tập. Model không tự viết URL; code chọn link theo từ khoá |
| Từ đâu | Nhóm tự soạn danh sách link công khai: Wikipedia 9 · 3Blue1Brown 2 · Michael Nielsen, *Neural Networks and Deep Learning* (sách mở) 2 · Google for Developers (ML Crash Course) 2 · 1 dòng lỗi (R13, xem Giới hạn) |
| Xử lý những bước gì | Mỗi link gắn bài (`B1` 6 · `B2` 8 · `all` 2), danh sách từ khoá ngăn bằng `\|`, ngày kiểm |
| Số dòng / số đoạn | 16 link, cột: `id, bai, tieu_de, url, nguon, tu_khoa, ngay_kiem` |
| Phiên bản / ngày lấy | Kiểm link 28/11/2026 |
| Nhãn | thật (link công khai), nhóm tự chọn |
| Giới hạn | **R13 hỏng định dạng**: URL `…/wiki/Training,_validation,_and_test_data_sets` có dấu phẩy nhưng không đặt trong ngoặc kép → khi đọc CSV, `url` bị cắt còn `…/wiki/Training`, cột `tu_khoa` thành `_and_test_data_sets` nên R13 không bao giờ được chọn — cần bọc URL trong ngoặc kép. Chọn link bằng khớp từ khoá, không theo nghĩa. Phần lớn nguồn tiếng Anh |

## Dataset 4 · Phụ đề video nạp cho tính năng ôn tập (`data/videos/`)

*Thêm 28/11 14:33 (commit `db96658`). Không ghi vào `data/lesson_segments.csv`, không dùng cho bộ câu thử hay các lượt `run-1`…`run-4`.*

| | |
|---|---|
| Dùng để làm gì | Nguồn cho trang web học + đề ôn tập (`codebase/web.py`, `quiz.py`, `build_bank.py`): sinh câu hỏi và đáp án có mã đoạn, tua đúng giây |
| Từ đâu | `codebase/video_source.py`: link YouTube → phụ đề công khai lấy bằng yt-dlp; hoặc file phụ đề `.srt` / `.vtt` / `.txt` người dùng tải lên. Hai file mẫu trong repo: `aircAruvnKk.csv` (phụ đề YouTube của video B1) và `bai-hoc.csv` (cùng nội dung, nạp thử bằng file tải lên, không có mã YouTube) |
| Xử lý những bước gì | Gộp dòng phụ đề thành đoạn ~60 s giữ timestamp gốc, đánh mã `V<số>-<đoạn>`, cùng cột với `lesson_segments.csv` |
| Số dòng / số đoạn | Mỗi file 18 đoạn, 4 → 1115 s (cùng video B1 nhưng chia khác `lesson_segments.csv`: 18 đoạn thay vì 22, mã `V1-…` thay vì `B1-…`) |
| Phiên bản / ngày lấy | 28/11/2026 |
| Nhãn | thật (phụ đề công khai) |
| Giới hạn | Phụ đề học viên tải lên lưu ở `data/videos/uploads/`, đã thêm vào `.gitignore`, không commit (có thể là nội dung riêng của khoá). Mã `V1-…` không trùng hệ mã `B1-…` của trợ giảng nên không so được với `expected` của bộ câu thử. Chỉ có lời nói, không có chữ trên slide |

**Đề ôn tập đã sinh (`quiz/de-on-tap-*.md`, 3 file):** do model sinh từ Dataset 4 → là output, không phải dữ liệu nguồn hay bằng chứng; chưa có bộ câu thử / metric đo chất lượng đề (xem `eval/README.md` mục 2, "Phạm vi").
