# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-090408 | 15/26 | 58% | 5/8 | 5/13 | 5/5 | chưa (cần ≥80%) |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

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

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: __
- Nếu có thêm 1 tuần: __
