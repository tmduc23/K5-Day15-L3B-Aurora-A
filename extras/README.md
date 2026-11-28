# extras/ — ngoài phần nộp

Thư mục này **không thuộc bản chạy thử được chấm**. Bản chạy thử của lát cắt nằm ở `codebase/` và chạy bằng `python run.py` (chỉ thư viện chuẩn).

## `lecture-videorag/` — hướng mở rộng sau hackathon

Bản đủ dùng cho phần `spec.md` §4 ghi là *không làm* trong lát cắt: xử lý **cả chuỗi video bài giảng** (video LMS tải lên hoặc YouTube), Whisper chuyển lời giảng thành chữ, cắt slide tại điểm đổi slide, ghi chú kiến thức từng video và chat hỏi đáp cả chuỗi — mọi ý đều trích mã đoạn / slide, mở đúng giây.

- Repo gốc: https://github.com/lamtt262004/lecture-videorag (bản chép ở đây là commit `f9d489f`).
- Cách chạy, kiến trúc, giới hạn: `lecture-videorag/README.md`; nhật ký triển khai: `lecture-videorag/docs/NHAT_KY_TRIEN_KHAI.md`.
- Cần cài thêm (`pip install -r extras/lecture-videorag/requirements.txt`: torch qua sentence-transformers, faster-whisper, OpenCV…) và API key riêng trong `extras/lecture-videorag/.env` — **không** ảnh hưởng `python run.py`, `eval`, `simulate` của repo này.
- Không kèm dữ liệu đã xử lý (`data/`), file video hay `.env`.
