# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): hỏi ít 58% (1,5 phiên / tháng) · hỏi vừa 33% (6,1) · hỏi nhiều 9% (16,8); 2 câu / phiên. Nguồn: chat log BTC, 144 người hỏi trợ giảng dưới video trong 05–25/11/2026 (`evidence/count_usage_btc.py`)
- **Số người dùng thật** 3 kịch bản: thấp 144 · cơ sở 361 · cao 721. Nguồn: thấp = số người đã hỏi trợ giảng (`chat.csv`); cao = số tài khoản học viên (`learners.csv`); cơ sở = 50% tài khoản *(tự ước tính)*
- **Giá** ≥2 mức model (từ `further-reading/model-prices.md` của repo đề, có link + ngày xem): gpt-4o-mini vào 0,15 / ra 0,60 USD / 1M token (https://developers.openai.com/api/docs/pricing, BTC xem 25/11/2026) · Claude Sonnet 5.5 vào 2,00 / ra 10,00 (trang giá Anthropic, BTC xem 25/11/2026)
- **Tỉ lệ đạt** dùng để tính: 18/26 (69%) — lượt `run-2@20261128-092049` (lượt 2)
- Đo token trên model openai/gpt-4o-mini (qua OpenRouter), tính giá model gpt-4o-mini và Claude Sonnet 5.5 (bộ tách token của Claude khác nên số token thật có thể lệch)

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID simulate-1@20261128-100024 · 50 phiên (0 phiên lỗi) · seed 42 · token vào ~18.400 / ra ~200 mỗi phiên (2 câu)

*(chép từ `cost/simulate-1-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| gpt-4o-mini | $0.0029 | $0.0042 | $1.82 | $4.57 | $9.14 | $0.0127 |
| Claude Sonnet 5.5 | $0.0388 | $0.0561 | $24.58 | $61.62 | $123.08 | $0.1707 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): ~50 phút học viên tự tìm lại trong video (§2: 7.300 phút / 144 người; số lần từ data BTC, số phút *tự ước tính*, chờ phỏng vấn)
- Chi phí / người / tháng (cơ sở, model gpt-4o-mini): $0.0127 (Sonnet 5.5: $0.1707)
- **Kết luận một dòng — đáng làm không:** đáng — dưới 2 cent / người / tháng để bớt ~50 phút tìm lại; nút thắt là chất lượng (69% < 80%), không phải chi phí, nên giữ gpt-4o-mini và dồn sức vào giảm từ chối nhầm.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: ~96% chi phí (gpt-4o-mini) là token vào (cả 39 đoạn transcript ~9.200 token mỗi câu). Chỉ đưa 5–8 đoạn sát nhất sẽ cắt token vào khoảng 4–5 lần *(tự ước tính theo tỉ lệ số đoạn)*; cache phần transcript cố định (giá cache gpt-4o-mini 0,075 USD / 1M theo bảng BTC) cắt khoảng một nửa giá phần đó.
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
