# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-090408 | 15/26 | 58% | 5/8 | 5/13 | 5/5 | chưa (cần ≥80%) |
| 2 | run-2@20261128-092049 | 18/26 | 69% | 4/8 | 9/13 | 5/5 | chưa (cần ≥80%) |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Từ chối nhầm: bài có nội dung nhưng trả "không có trong bài" | 7 | B15, B18, B19, B20, B21, B22, B10 |
| Trả lời thiếu / sai ý chính dù trích đúng mã | 2 | B06, B16 |
| Không hỏi lại câu mơ hồ, hoặc hỏi lại khi nên nói "bài không đề cập" | 2 | B07, B11 |
| Bịa mã đoạn | 0 | — |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B21 | "…why you added the negative gradient vector to the weight vector?" (câu hỏi thật) | "Không có trong bài: , bài không đề cập đến lý do về việc thêm vector gradient âm…" | Bài giải thích rõ ở B2-07/B2-08 (gradient âm = hướng giảm chi phí nhanh nhất); transcript bài 2 là bản dịch máy nên model không khớp được câu tiếng Anh |
| B10 | "Vì sao mạng trong bài dùng 3 lớp ẩn?" | "Không có trong bài: , bài không đề cập cụ thể lý do vì sao mạng sử dụng 3 lớp ẩn." | Không sửa tiền đề sai: bài dùng 2 lớp ẩn 16 nơ-ron (B1-05) |
| B07 | "cái hàm đó là gì vậy?" | "Không có trong bài: , bài giảng không đề cập rõ về khái niệm \"cái hàm\"…" | Câu mơ hồ phải hỏi lại học viên muốn hỏi hàm nào, không phải từ chối |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: **từ chối nhầm / xử lý sai câu khó** (lượt 1: 9/11 câu trượt — B07, B10, B11, B15, B18–B22) — vì sao là nhóm **đau nhất với người dùng**: học viên hỏi đúng chỗ có trong bài mà bị bảo "không có trong bài" thì lại phải tự tua tìm — đúng cái pain 60% (tua lùi / hỏi tiếp) mà sản phẩm muốn bớt; phần lớn là câu hỏi thật của người học.
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): (1) `data/lesson_segments.csv`: chữ 17 đoạn B2 đổi từ bản dịch máy sang phụ đề tiếng Anh gốc, giữ nguyên mã đoạn và mốc thời gian; (2) prompt `codebase/agent.py`: đối chiếu theo nghĩa khi câu hỏi và transcript khác ngôn ngữ, đọc đoạn quanh mốc thời gian trong câu hỏi, trả lời phần có trong bài, sửa tiền đề sai, chỉ hỏi lại khi câu trỏ tới thứ không xác định. Không đổi bộ câu thử, cách chấm, chuẩn "đạt".
- Kết quả: nhóm lỗi đó 0/9 → 3/9 qua (B07, B10, B11) · tổng 58% → 69% (15/26 → 18/26); ngoài nhóm này, B06 và B16 (thiếu ý ở lượt 1) cũng qua nhờ luật giữ đúng ý chính và đọc đoạn quanh mốc thời gian.
- Câu nào **tệ đi** sau khi sửa: **B03** (bias — lượt 1 đúng, lượt 2 bị chặn bằng câu trả lời an toàn) và **B05** (hàm chi phí — lượt 2 thêm khẳng định sai "đo trên ảnh chưa thấy"). Luật "trả lời phần có trong bài" làm model thêm câu thừa kiểu "Phần còn lại bài không đề cập…" ở B01, B02, B04 (không sai nhưng dài).

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: vẫn từ chối nhầm 6/26 câu có nội dung trong bài (B03, B15, B19–B22) — không làm học viên học sai nhưng bắt họ tự tìm lại, đúng pain cần giải; 2 câu trả lời sai ý dù trích đúng mã (B05, B18) — **nguy hiểm hơn**, vì có mã đoạn nên học viên dễ tin; code hiện chỉ kiểm mã có tồn tại, không kiểm nội dung có khớp đoạn.
- Nếu có thêm 1 tuần: thêm bước tìm đoạn liên quan trước khi gọi model (đưa 5–8 đoạn sát nhất thay vì cả 39 đoạn) để bớt từ chối nhầm; thêm bước kiểm mỗi câu khẳng định có nằm trong đoạn được trích không (giảm B05, B18); thay dữ liệu bài bằng transcript Day08 thật khi có; phỏng vấn ≥3 học viên để đo đúng số phút mất mỗi lần.
