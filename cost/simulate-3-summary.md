# Tóm tắt mô phỏng simulate-3@20261128-123404

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| hoi_it | 24 | 2 | 25992 | 281 | 4.2 | 3.8 |
| hoi_vua | 23 | 2 | 25133 | 272 | 4.1 | 3.8 |
| hoi_nhieu | 3 | 2 | 25217 | 228 | 4.0 | 3.7 |

Tỉ lệ đạt dùng để tính: 23/26 (88%) — lượt run-4@20261128-123056

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-4.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (144 người) | Chi phí / tháng — cơ sở (361 người) | Chi phí / tháng — cao (721 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini (vào 0.15 · ra 0.6 $/1M) | $0.0040 | $0.0045 | $0.0023 | $2.50 | $6.27 | $12.53 | $0.0174 |
| Claude Sonnet 5.5 (vào 2.0 · ra 10.0 $/1M) | $0.0538 | $0.0609 | $0.0304 | $33.70 | $84.49 | $168.74 | $0.2340 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.0) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: openai/gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
