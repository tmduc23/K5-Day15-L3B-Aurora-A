# Tóm tắt mô phỏng simulate-1@20261128-100024

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| hoi_it | 24 | 2 | 18429 | 202 | 2.0 | 3.2 |
| hoi_vua | 23 | 2 | 18428 | 195 | 2.0 | 3.2 |
| hoi_nhieu | 3 | 2 | 18430 | 201 | 2.0 | 3.3 |

Tỉ lệ đạt dùng để tính: 18/26 (69%) — lượt run-2@20261128-092049

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (144 người) | Chi phí / tháng — cơ sở (361 người) | Chi phí / tháng — cao (721 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini (vào 0.15 · ra 0.6 $/1M) | $0.0029 | $0.0042 | $0.0021 | $1.82 | $4.57 | $9.14 | $0.0127 |
| Claude Sonnet 5.5 (vào 2.0 · ra 10.0 $/1M) | $0.0388 | $0.0561 | $0.0281 | $24.58 | $61.62 | $123.08 | $0.1707 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.0) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: openai/gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
