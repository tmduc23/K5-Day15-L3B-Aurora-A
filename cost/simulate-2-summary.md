# Tóm tắt mô phỏng simulate-2@20261128-121222

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| hoi_it | 24 | 2 | 27489 | 272 | 3.0 | 3.6 |
| hoi_vua | 23 | 2 | 27850 | 262 | 3.0 | 3.6 |
| hoi_nhieu | 3 | 2 | 27888 | 240 | 3.0 | 3.7 |

Tỉ lệ đạt dùng để tính: 19/26 (73%) — lượt run-3@20261128-120824

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-3.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (144 người) | Chi phí / tháng — cơ sở (361 người) | Chi phí / tháng — cao (721 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini (vào 0.15 · ra 0.6 $/1M) | $0.0043 | $0.0059 | $0.0029 | $2.74 | $6.86 | $13.70 | $0.0190 |
| Claude Sonnet 5.5 (vào 2.0 · ra 10.0 $/1M) | $0.0580 | $0.0794 | $0.0397 | $36.80 | $92.25 | $184.25 | $0.2556 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.0) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: openai/gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
