# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): hỏi ít 58% (1,5 phiên / tháng) · hỏi vừa 33% (6,1) · hỏi nhiều 9% (16,8); 2 câu / phiên. Nguồn: chat log BTC, 144 người hỏi trợ giảng dưới video trong 05–25/11/2026 (`evidence/count_usage_btc.py`)
- **Số người dùng thật** 3 kịch bản: thấp 144 · cơ sở 361 · cao 721. Nguồn: thấp = số người đã hỏi trợ giảng (`chat.csv`); cao = số tài khoản học viên (`learners.csv`); cơ sở = 50% tài khoản *(tự ước tính)*
- **Giá** ≥2 mức model (từ `further-reading/model-prices.md` của repo đề, có link + ngày xem): gpt-4o-mini vào 0,15 / ra 0,60 USD / 1M token (https://developers.openai.com/api/docs/pricing, BTC xem 25/11/2026) · Claude Sonnet 5.5 vào 2,00 / ra 10,00 (trang giá Anthropic, BTC xem 25/11/2026)
- **Tỉ lệ đạt** dùng để tính: **23/26 (88%) — lượt `run-4@20261128-123056`** (lượt 4, code hiện tại). Bản trước giữ lại để so sánh: `simulate-2` (code lượt 3, 73%), `simulate-1` (code lượt 2, 69%)
- Đo token trên model openai/gpt-4o-mini (qua OpenRouter), tính giá model gpt-4o-mini và Claude Sonnet 5.5 (bộ tách token của Claude khác nên số token thật có thể lệch)

## 2. Kết quả mô phỏng

**Bản nộp — code hiện tại (lượt 4, chọn đoạn → trả lời):** `cost/simulate-3.csv` · run ID simulate-3@20261128-123404 · 50 phiên (0 phiên lỗi) · seed 42 · token vào ~25.600 / ra ~275 mỗi phiên (2 câu, ~4 lần gọi model) · tỉ lệ đạt 23/26 (88%)

*(chép từ `cost/simulate-3-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| gpt-4o-mini | $0.0040 | **$0.0045** | $2.50 | $6.27 | $12.53 | $0.0174 |
| Claude Sonnet 5.5 | $0.0538 | $0.0609 | $33.70 | $84.49 | $168.74 | $0.2340 |

So với lượt 3: chi phí / phiên −7% (bước trả lời chỉ đọc vài đoạn), tỉ lệ đạt 73% → 88% → chi phí / task thành công $0.0059 → **$0.0045** (−24%), thấp hơn cả lượt 2 ($0.0042 ở 69% nhưng chất lượng chưa đạt chuẩn).

**Bản trước — code lượt 3 (có 2 bước tự kiểm):** `cost/simulate-2.csv` · run ID simulate-2@20261128-121222 · 50 phiên (0 phiên lỗi) · seed 42 · token vào ~27.700 / ra ~265 mỗi phiên (2 câu, 3 lần gọi model) · tỉ lệ đạt 19/26 (73%)

*(chép từ `cost/simulate-2-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| gpt-4o-mini | $0.0043 | **$0.0059** | $2.74 | $6.86 | $13.70 | $0.0190 |
| Claude Sonnet 5.5 | $0.0580 | $0.0794 | $36.80 | $92.25 | $184.25 | $0.2556 |

So với bản lượt 2 dưới đây: chi phí / phiên +48% (2 bước tự kiểm gọi model thêm ~0,5 lần / câu), tỉ lệ đạt 69% → 73% → chi phí / task thành công $0.0042 → $0.0059 (+40%).

**Bản trước — code lượt 2:**

Lượt mô phỏng: `cost/simulate-1.csv` · run ID simulate-1@20261128-100024 · 50 phiên (0 phiên lỗi) · seed 42 · token vào ~18.400 / ra ~200 mỗi phiên (2 câu)

*(chép từ `cost/simulate-1-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| gpt-4o-mini | $0.0029 | $0.0042 | $1.82 | $4.57 | $9.14 | $0.0127 |
| Claude Sonnet 5.5 | $0.0388 | $0.0561 | $24.58 | $61.62 | $123.08 | $0.1707 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): **≥ 9 phút** học viên tự tua lại / hỏi lại (17 câu × 60% × 0,9 phút — mọi thừa số đo từ data BTC, cận dưới; phỏng vấn ghi 5–60 phút / lần khi tìm cả ngoài trang). Bản CP3 ghi ~50 phút do dùng 5 phút / lần tự ước tính.
- Chi phí / người / tháng (cơ sở, model gpt-4o-mini): **$0.0174** với code lượt 4 (lượt 3: $0.0190; lượt 2: $0.0127); Sonnet 5.5: $0.2340
- **Kết luận một dòng — đáng làm không:** đáng — dưới 2 cent / người / tháng để bớt ≥ 9 phút tự tìm lại (cận dưới) và để 70% câu trả lời hiện không có mốc nào đều có nguồn kiểm được; chất lượng lượt 4 đã đạt chuẩn (88% ≥ 80%), giữ gpt-4o-mini, không phải chi phí, nên giữ gpt-4o-mini và dồn sức vào giảm từ chối nhầm.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: ~96% chi phí (gpt-4o-mini) là token vào (lượt 4: bước chọn đoạn vẫn đọc cả 39 đoạn ~9.200 token mỗi câu; bước trả lời chỉ ~1.500). Chọn đoạn bằng code (không gọi model) sẽ cắt phần lớn token vào *(tự ước tính)*; cache phần transcript cố định (giá cache gpt-4o-mini 0,075 USD / 1M theo bảng BTC) cắt khoảng một nửa giá phần đó.
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
