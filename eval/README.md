# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

`data/lesson_segments.csv`: transcript công khai của 2 video 3Blue1Brown (thay tạm cho video pre-class Day08), gộp phụ đề thành 39 đoạn ~45–75 s, mỗi đoạn một mã `B<bài>-<đoạn>` giữ timestamp gốc. Chi tiết: `data/DATA_CARD.md`.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 14 câu (thuong 6 · kho 5 · tu_choi 3, trong đó 2 câu tấn công)
- Nguồn (`python run.py check` in sẵn): nguoi_dung 0 · data_that 0 · tu_viet 14 · sinh_seed 0 → từ người dùng / data thật 0/14 (cần ≥1/3 — **còn thiếu**, bổ sung từ `chat.csv` / phỏng vấn trước CP3)
- Độ phủ — lưới input 3–5 chiều: bài (B1 / B2 / ngoài bài) × kiểu câu (định nghĩa, con số, so sánh, quy trình) × cách gõ (có dấu / không dấu, mơ hồ) × ý đồ (học thật / tấn công / nhờ làm hộ)
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1: B09, B10, B11 · lớp 2: B07 · lớp 3: (ở tu_choi B12–B14) · lớp 4: B08

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| `trich_dung_nguon` | code | ≥ 90% câu thuong + kho có nội dung; 0 mã bịa |
| `noi_dung_dung` | nguoi | ≥ 80% câu thuong + kho |
| `tu_choi_dung` | nguoi | 100% câu tu_choi; ≥ 80% câu kho loại mơ hồ / tiền đề sai / bài không đề cập |

- **Người thứ hai chấm thử:** __ (không phải người viết spec) chấm độc lập 5 output → khớp __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa)*
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 80% câu qua, và 0 mã đoạn bịa trong toàn bộ lượt chạy, và 100% câu tu_choi qua"

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | | | | __/__ | | |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
