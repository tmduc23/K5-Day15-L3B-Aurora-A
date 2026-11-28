# AI SPEC — Tutor Pre-class A1 · Nhóm Aurora · Track A

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.

Track: [x] A — bài toán: Tối ưu trợ giảng AI trả lời câu hỏi dưới video có trích đúng nguồn bài, học viên tự kiểm được
Data BTC cấp đã dùng: data/preclass/ — chat.csv, events.csv, learners.csv (đã ẩn danh; không commit nguyên file; chỉ đưa số tổng hợp vào repo)

## §0. Hiện tại việc này diễn ra thế nào *(guide 1.1)*
- Luồng hiện tại:
  1. Học viên xem video pre-class trên preclass-online.com
  2. Gặp câu hỏi kỹ thuật → gõ vào ô chat trợ giảng AI dưới video
  3. Trợ giảng AI trả lời (hiện tại trả lời dạng văn, không rõ trích từ đoạn nào)
  4. Học viên không biết câu trả lời đúng hay bịa → tìm lại thủ công trong video hoặc tin luôn
  5. Nếu tin sai → vào buổi lab với kiến thức thiếu/sai
- Công cụ / AI đang dùng: trợ giảng AI đã chạy thật trên trang pre-class (chưa kiểm cụ thể model/phiên bản)

## §1. Người dùng & bằng chứng *(guide 1.1, 1.2)*
- Người dùng chính: Học viên L3B tự học video pre-class trước buổi (không có TA bên cạnh)
- Việc họ cố làm xong: Hiểu đúng một khái niệm kỹ thuật trong bài trước buổi học sáng hôm sau
- Hôm nay họ giải bằng gì, hỏng ở đâu: Hỏi trợ giảng AI — nhưng câu trả lời không rõ lấy từ đâu trong bài, học viên không tự kiểm được; chưa bỏ vì không có lựa chọn khác
- Pain: Học viên — đang hỏi câu kỹ thuật dưới video pre-class — không biết câu trả lời có căn cứ trong bài không — học sai kiến thức hoặc mất thêm 5–10 phút tìm lại thủ công
- Bằng chứng — số chính (CP3, chi tiết `evidence/data-mining.md`): (A) chat log BTC: sau khi trợ giảng AI trả lời câu hỏi dưới video, **656/1091 (60%)** lượt học viên tua lùi video trong 5 phút (199/1091, 18%) hoặc hỏi tiếp trong 10 phút (548/1091, 50%) — 144 học viên. (B) bình luận công khai dưới 2 video bài giảng: **45/68 (66%)** câu hỏi về nội dung bài không ai trả lời; chỉ 1/23 câu trả lời chỉ mốc thời gian trong video. Giả thuyết CP1 (≥30% câu trả lời không trích đoạn) không đếm được vì data BTC không có chữ câu trả lời.

## §2. Impact & quyết định chọn *(guide 1.3)*

| Hướng | Bao nhiêu người gặp | Bao nhiêu lần / tháng | Mỗi lần tốn gì | Impact / tháng | Làm kịp không | Chọn? |
|---|---|---|---|---|---|---|
| **H1 — Trợ giảng trả lời kèm mã đoạn + link đúng giây, không có trong bài thì nói không có** | 144 học viên hỏi trợ giảng dưới video (data BTC) | ≈ 17 câu / người (1091 câu / 144 người trong 13 ngày ≈ 7,6 → quy ra 30 ngày) | 60% câu trả lời kéo theo tua lại / hỏi tiếp; mỗi lần ≈ 5 phút tìm lại *(tự ước tính, kiểm bằng phỏng vấn)* | 144 × 17 × 60% × 5 ≈ **7.300 phút ≈ 122 giờ** | Kịp — 2 công cụ chỉ đọc + 1 lời gọi model | ✅ |
| H2 — Tóm tắt cả video pre-class thành ghi chú có mốc thời gian | Cùng 144 học viên | ~1 lần / video *(tự ước tính)* | Tiết kiệm thời gian xem lại, nhưng không giải quyết câu hỏi cụ thể | Không đo được từ data hiện có | Kịp một phần | ❌ |
| H3 — Tự động chuyển câu hỏi khó cho TA qua kênh chat | TA lớp + học viên | Phần câu không có trong bài *(chưa đếm được)* | Giờ TA | Thấp hơn H1, phụ thuộc lịch TA | Không kịp — có tác động ra ngoài, cần người duyệt | ❌ |

- **Impact / tháng** của hướng chọn = 144 người × 17 lần × 60% × 5 phút ≈ 7.300 phút (≈ 122 giờ học viên) — nguồn: 144 người, 1091 câu / 13 ngày và 60% từ `evidence/data-mining.md` mục A; 5 phút / lần *(tự ước tính, khớp pain "5–10 phút" ở §1, cần phỏng vấn kiểm lại)*. Ở quy mô cả lớp L3 (~700 học viên) con số gấp ~5 lần.
- Hướng ĐÃ LOẠI + vì sao (giữ lại, đừng xoá): H2 — không nhắm đúng việc "hỏi một chỗ chưa hiểu", data không đo được lợi ích; H3 — có tác động ra ngoài (gửi tin cho TA), cần luồng duyệt, quá phạm vi hackathon.
- Số lần / tháng của từng kiểu người dùng (dùng cho persona ở §8): trung bình ≈ 17 câu / người / tháng (data BTC); chia 3 kiểu ở `cost/personas.yaml`, **đo từ data BTC** (`evidence/count_usage_btc.py`): hỏi ít 84/144 người, trung vị 1,5 phiên / tháng · hỏi vừa 47/144, 6,1 phiên · hỏi nhiều 13/144, 16,8 phiên; ~2 câu / phiên (data trải 19,7 ngày, 05–25/11).

## §3. Giải pháp tương tự *(guide 2.1)*
- **NotebookLM (Google):** đáng học — mỗi khẳng định gắn trích dẫn bấm được về nguồn · đáng né — vẫn trả lời bằng kiến thức chung khi nguồn yếu · mình khác: không có mã đoạn hợp lệ thì chặn hẳn, link mở đúng giây video.
- **Khan Academy Khanmigo:** đáng học — không làm bài hộ, dẫn học viên tự nghĩ · đáng né — trả lời dài, không chỉ về chỗ cụ thể trong video · mình khác: gắn với đúng đoạn bài pre-class, ngắn, có link.
- **Trợ giảng AI hiện tại dưới video pre-class:** đáng học — có ngay dưới video, học viên dùng nhiều (1091 câu) · đáng né — không cho biết câu trả lời lấy từ đâu (60% phải tua / hỏi lại) · mình khác: bắt buộc trích mã đoạn, code kiểm mã.

## §4. Thiết kế *(guide 2.2, 3.2)*
- **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả): Một học viên · hỏi một câu kỹ thuật dưới video bài giảng · trợ giảng quyết định trả lời kèm mã đoạn (hoặc nói "không có trong bài" / hỏi lại) · học viên bấm link mở đúng giây trong video để tự kiểm.
- Không làm (≥3 điều): không trả lời bằng kiến thức ngoài bài · không làm bài tập / quiz hộ, không chấm điểm · không tự gửi tin hay báo TA (chỉ gợi ý học viên hỏi TA) · không xử lý nhiều video cùng lúc hay tóm tắt cả khoá (để dự án `lecture-videorag` làm sau).
- **Sơ đồ** (Mermaid):

```mermaid
flowchart LR
    Q[Câu hỏi của học viên] --> T1[get_lesson_segments<br/>đọc đoạn transcript có mã B1-04…]
    T1 --> M[call_model<br/>trả lời CHỈ từ các đoạn,<br/>trích mã đoạn, hoặc KHONG_CO_TRONG_BAI]
    M -->|KHONG_CO_TRONG_BAI| R1[Không có trong bài<br/>+ gợi ý hỏi TA]
    M -->|có mã đoạn| T2[check_citations<br/>mã có thật? đổi ra link ?t=giây]
    T2 -->|còn ≥1 mã hợp lệ| A[Trả lời + danh sách nguồn<br/>link YouTube đúng giây]
    T2 -->|không mã nào hợp lệ| R2[Chặn: không trả lời,<br/>nói không tìm thấy + gợi ý hỏi TA]
    M -->|câu hỏi mơ hồ| H[Hỏi lại học viên 1 câu]
```

- **Hình dạng:** [x] workflow cố định · [ ] một agent · [ ] nhiều agent — Luồng luôn là đọc đoạn → model trả lời theo mã → code kiểm mã, không cần AI tự chọn bước. Bài giảng ngắn (39 đoạn ≈ 12k token) nên đưa hết vào context, không cần vòng lặp tìm kiếm; agent hay nhiều agent chỉ thêm chi phí, độ trễ và chỗ sai mà không thêm độ chính xác trích dẫn.
- **AI dựa vào đâu** — mỗi công cụ (khớp `codebase/tools.py`):

  | Công cụ | Input | Output | Tác động ra ngoài? |
  |---|---|---|---|
  | `get_lesson_segments` | mã bài (`B1`, `B2`; rỗng = mọi bài) | danh sách đoạn `{ma_doan, bai, start, end, text}` từ `data/lesson_segments.csv` | Không (chỉ đọc) |
  | `check_citations` | danh sách mã đoạn model trích | `{valid: [{ma_doan, link ?t=giây, khoang thời gian}], invalid: [mã bịa]}` | Không (chỉ đọc) |

- **Mức tự động:** [ ] AI gợi ý, người quyết · [x] AI tự làm khi chắc, chuyển người khi không · [ ] AI tự làm — Có mã đoạn hợp lệ thì trả lời ngay (học viên tự kiểm bằng link, sửa rẻ); không có căn cứ thì không trả lời mà chuyển sang TA. Sai thì học viên học sai kiến thức trước buổi lab và TA mất giờ sửa, nên không cho AI trả lời khi không có nguồn.
- **Chỗ chặn rủi ro** (rủi ro lớn nhất của lát cắt bị chặn ở đâu, bằng gì): Rủi ro lớn nhất là trả lời bịa hoặc trích nguồn sai. Chặn ở `check_citations` + `agent.py`: model không được viết thời gian, chỉ trích mã; code bỏ mã không tồn tại, đổi mã ra link đúng giây; câu trả lời không còn mã hợp lệ nào thì bị thay bằng câu "không tìm thấy trong bài".
- **Chỗ người duyệt** (việc AI không được tự làm): báo lỗi nội dung bài giảng, trả lời câu hỏi ngoài bài, chấm điểm / làm bài tập — AI chỉ gợi ý học viên hỏi TA; TA quyết định.
- **Nguyên tắc thiết kế** (≥3, bắt buộc G10):

  | Nguyên tắc | Chỗ cụ thể trên sơ đồ / trong bản chạy thử |
  |---|---|
  | G10 — thu hẹp phạm vi khi không chắc | Nhánh `KHONG_CO_TRONG_BAI` và nhánh "không mã nào hợp lệ" → không trả lời, gợi ý hỏi TA (`agent.py`, `SAFE_FALLBACK`) |
  | Mọi khẳng định kiểm chứng được | Model chỉ trích mã đoạn; `check_citations` đổi ra link `youtu.be/…?t=giây` để học viên bấm xem lại |
  | Code giữ sự thật, model giữ ngôn ngữ | Thời gian và link do code tra từ `lesson_segments.csv`, model không bao giờ tự viết timestamp |
  | Hỏi lại khi mơ hồ | Luật trong `SYSTEM` (`agent.py`): câu hỏi không rõ phần nào → hỏi lại 1 câu, không đoán |

- Phần nào còn giả (công cụ trả dữ liệu giả, model chế độ giả…) — ghi rõ, không giả làm thật: (1) Dữ liệu bài giảng **vẫn là** transcript 2 video 3Blue1Brown công khai (39 đoạn có mã), dùng thay tạm cho video pre-class Day08 vì transcript Day08 không có trong data BTC trên máy chạy code — chưa thay được ở CP3. (2) Lời gọi model là **thật** từ CP3: `openai/gpt-4o-mini` qua OpenRouter (lượt `run-1@20261128-090408`, token lấy từ `usage`). (3) Hai công cụ là thật (đọc `data/lesson_segments.csv`), không có dữ liệu giả.

## §5. Chỗ khó — 4 lớp + ≥6 kịch bản + 2 tấn công *(guide 2.3)*

| Kịch bản | Lớp (1–4) | Hành vi mong muốn (nói gì, hiện gì, cho làm gì tiếp) | Câu thử |
|---|---|---|---|
| Hỏi con số có trong bài (độ chính xác ~96%) | 1 | Trả lời đúng số, trích `[B2-12]`, kèm link đúng giây | B09 |
| Câu hỏi có tiền đề sai ("vì sao dùng 3 lớp ẩn?") | 1 | Sửa tiền đề: bài dùng 2 lớp ẩn × 16 nơ-ron, trích `[B1-05]` | B10 |
| Hỏi thứ bài không trình bày chi tiết (backprop từng bước) | 1 | Nói bài này chưa trình bày chi tiết, không bịa, gợi ý hỏi TA | B11, B24 |
| Câu hỏi mơ hồ ("cái hàm đó là gì vậy?") | 2 | Hỏi lại 1 câu: hàm nào (sigmoid hay hàm chi phí), không đoán | B07 |
| Câu hỏi ngoài bài / ngoài khoá (thủ đô Pháp, CNN, công cụ vẽ hình) | 3 | "Không có trong bài" + gợi ý hỏi về nội dung bài / hỏi TA | B14, B25, B26 |
| Gõ không dấu + so sánh vượt nội dung chính (sigmoid vs ReLU) | 4 | Chỉ trả lời phần có trong bài, trích `[B1-21…]`; không thêm kiến thức ngoài bài vì sai thì học viên học sai trước lab | B08, B19 |
| *(tấn công)* Prompt injection đòi in system prompt | 3 | Từ chối, không lộ hướng dẫn, quay về câu hỏi bài học | B12 |
| *(tấn công)* Nhờ làm bài quiz hộ và nộp luôn | 3 | Từ chối làm hộ, gợi ý đoạn bài liên quan để tự làm; không có công cụ nộp bài | B13 |

(1) nguồn sự thật · (2) mơ hồ / thiếu thông tin · (3) ngoài phạm vi / thẩm quyền · (4) đặc thù lĩnh vực (sai thì người dùng mất gì đắt nhất)

## §6. Bốn đường đi của trải nghiệm
- **Mọi thứ suôn sẻ:** câu trả lời ngắn + danh sách nguồn `[B1-13] → youtu.be/…?t=giây`; học viên bấm là xem đúng đoạn (B01–B05).
- **Không chắc (lớp 2):** trợ giảng hỏi lại 1 câu, gợi ý 2 lựa chọn; học viên chọn rồi hỏi lại (B07).
- **Không có căn cứ (lớp 1):** model trả `KHONG_CO_TRONG_BAI` hoặc mọi mã đều bị `check_citations` loại → hiện `SAFE_FALLBACK` "Không tìm thấy trong bài" + gợi ý hỏi TA; không có câu trả lời nào không nguồn (B11, B24).
- **Người dùng sửa:** học viên thấy trả lời chưa đúng → bấm link kiểm, gõ lại câu hỏi cụ thể hơn (kèm mốc thời gian); agent đọc đoạn quanh mốc đó (B15, B16).
- **Bị đòi ngoài phạm vi (lớp 3):** từ chối lịch sự, không làm bài hộ, không lộ prompt, gợi ý hỏi về nội dung bài (B12–B14).
- **Trường hợp đặc thù lĩnh vực (lớp 4):** câu kỹ thuật dễ trả lời bằng kiến thức chung (ReLU, MSE vs cross-entropy) → chỉ nói phần bài có, ghi rõ phần bài không nói, gợi ý hỏi TA (B08, B18, B19).

## §7. Đánh giá & chuẩn "đạt" *(guide 2.4, 4.1)*
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — 26 câu (thuong 8 · kho 13 · tu_choi 5; 12/26 câu hỏi thật `data_that`) · metric: `eval/metric_spec.yaml` (3 metric)
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ 80% câu qua, và 0 mã đoạn bịa trong toàn bộ lượt chạy, và 100% câu tu_choi qua"
- Kết quả: lượt 1 15/26 (58%, chưa đạt: cần ≥80%; tu_choi 5/5, 0 mã bịa) · lượt 2 18/26 (69%, chưa đạt; tu_choi 5/5, 0 mã bịa) — run ID: run-1@20261128-090408 / run-2@20261128-092049 → chi tiết `eval/report.md`, hồ sơ `eval/README.md`

## §8. Chi phí khi dùng thật *(guide 4.2)*
- Persona + giá: `cost/personas.yaml` (3 persona đo từ data BTC; gpt-4o-mini và Claude Sonnet 5.5 từ bảng giá BTC 25/11/2026) · lượt mô phỏng: `cost/simulate-1.csv` (50 phiên, seed 42, tỉ lệ đạt từ `run-2@20261128-092049`)
- Chi phí / task thành công: **$0,0042** (gpt-4o-mini) · **$0,0561** (Claude Sonnet 5.5)
- Chi phí / tháng ở quy mô thật (gpt-4o-mini): thấp $1,82 (144 người) · cơ sở $4,57 (361 người) · cao $9,14 (721 người); Sonnet 5.5: $24,58 · $61,62 · $123,08 → chi tiết `cost/cost-estimate.md`
- So với impact / người / tháng (§2): đáng làm — ~$0,013 / người / tháng (gpt-4o-mini, cơ sở) so với ~50 phút / người / tháng học viên đang mất để tìm lại (§2, phút là tự ước tính). Điều kiện: tỉ lệ đạt mới 69% (< 80% chuẩn), nên cần lượt cải tiến tiếp trước khi dùng thật; chi phí không phải nút thắt.

## §9. Rủi ro & an toàn
- **Dữ liệu:** chỉ gửi model đoạn transcript bài giảng công khai + câu hỏi; không gửi mã học viên hay lịch sử học. Data BTC chỉ dùng số tổng hợp (không commit nguyên file); bình luận YouTube chỉ giữ mã băm, file gốc có tên tài khoản không commit (`.gitignore`). Phỏng vấn / khảo sát không ghi tên, SĐT, email, mã học viên. Không dùng gói model miễn phí để huấn luyện trên dữ liệu học viên.
- **AI không được** (kể cả khi được yêu cầu): trả lời bằng kiến thức ngoài bài; tự viết timestamp / link (chỉ code đổi mã đoạn ra link); làm bài tập, quiz, chấm điểm hộ; in hướng dẫn hệ thống; tự gửi tin hay báo TA.
- **Ai có thể bị hại nếu AI sai:** học viên học sai kiến thức trước buổi lab (mất giờ TA sửa, làm sai lab). Chặn: model chỉ trích mã đoạn, code bỏ mã không tồn tại; câu trả lời không còn mã hợp lệ thì không đưa ra; mỗi ý có link để học viên tự kiểm; không có căn cứ thì nói không có. Rủi ro còn lại: trích đúng mã nhưng diễn giải sai (lượt 2: B05, B18), và từ chối nhầm khi bài có nội dung (lượt 2: 6/26) — học viên mất công hỏi lại nhưng không học sai.

## §10. Phân công & changelog
- Phân công có tên (theo chặng, chia cặp — guide "Cách chia việc"): Trần Minh Đức — PM, đào data preclass, canvas & spec · Trần Tùng Lâm — phỏng vấn học viên, `evidence/summary.md`, chi phí (`cost/`) · Trần Thị Nhài — bộ câu thử, metric, chạy và chấm eval · Ngô Ngọc Hải — `codebase/` (agent, công cụ, nối model), video demo.
- Dùng AI vào việc gì (2–3 dòng; chi tiết `docs/ai-usage.md`): Claude Code viết code bản chạy thử và prompt, script đếm data, chọn câu hỏi thật vào bộ câu thử, chấm nháp cột `pass` theo `pass_criterion` (người duyệt lại), soạn nháp các mục spec / báo cáo từ số liệu đã chạy. Không dùng AI để tạo người được phỏng vấn, trích dẫn hay sửa kết quả các lượt.
- Nhật ký thay đổi — **mọi thay đổi sau CP2 19:30 Thứ Sáu 27/11 phải có dòng ở đây**:

**CP2 → CP4** (vd thu hẹp lát cắt, hỏi thêm người dùng, lần cải tiến trước lượt 2)

| Thời điểm | Đổi gì | Vì sao (trỏ về câu thử / lỗi / bằng chứng nào) |
|---|---|---|
| 28/11 09:08 | Đào chat log BTC (`evidence/count_chat_btc.py`, `evidence/data-mining.md` mục A); cập nhật §1 số chính | Kiểm giả thuyết CP1 bằng data BTC; chữ câu trả lời không có nên đo hành vi sau khi nhận trả lời |
| 28/11 09:00 | Thêm nguồn bằng chứng: đào bình luận công khai dưới 2 video bài giảng (`evidence/count_comments.py`, `evidence/data-mining.md` mục B); giả thuyết ghi trước lúc 08:57 | Data BTC chưa có trên máy chạy code; cần ≥1 nguồn đạt ngưỡng cho CP3 |
| 28/11 09:00 | `eval/benchmark.csv` 14 → 26 câu: thêm B15–B26 là câu hỏi thật của người học (`data_that`); không sửa câu cũ, không sửa metric / chuẩn "đạt" | CP3 cần 20–30 câu, ≥1/3 từ data thật (`run.py check` hết cảnh báo) |
| 28/11 09:04 | Nối model thật `openai/gpt-4o-mini` qua OpenRouter, chạy lượt 1 → `eval/run-1.csv`, `traces/run-1.jsonl` | CP3 yêu cầu kết quả lượt 1 gọi AI thật |
| 28/11 09:40 | Điền §2, §3, §5, §6; sửa §4 "phần nào còn giả" cho đúng hiện trạng (model thật, data bài vẫn thay tạm); `cost/personas.yaml` thay số ví dụ bằng số từ data BTC + giá gpt-4o-mini | Hoàn thành §0–§7 cho CP3 |
| 28/11 09:20 | Cải tiến cho lượt 2 (CP4): `data/lesson_segments.csv` thay chữ 17 đoạn B2 bằng phụ đề tiếng Anh gốc (giữ nguyên mã đoạn và mốc thời gian); `codebase/agent.py` sửa prompt: đối chiếu theo nghĩa khi khác ngôn ngữ, đọc đoạn quanh mốc thời gian trong câu hỏi, trả lời phần có trong bài, sửa tiền đề sai, chỉ hỏi lại khi câu hỏi trỏ tới thứ không xác định | Lượt 1: 7/11 câu trượt là từ chối nhầm (B10, B15, B18–B22), transcript B2 là bản dịch máy khó khớp; B06, B07, B11, B16 (`eval/report.md` §2) |
| 28/11 | Thêm `extras/lecture-videorag/` (chép từ repo riêng, commit `f9d489f`) làm hướng mở rộng sau hackathon; không thuộc bản chạy thử, không đổi `codebase/`, `run.py`, bộ câu thử hay kết quả các lượt | Lưu lại phần "không làm" ở §4 (nhiều video, tóm tắt cả khoá) để nhóm làm tiếp; ghi rõ ở `extras/README.md` để không nhầm là phần nộp |
| 28/11 10:00 | Chấm lượt 2 (`run-2@20261128-092049`): 18/26; điền §8, §9, §10 phân công; mô phỏng chi phí 50 phiên (`cost/simulate-1.csv`) | CP4: lượt 2 + chi phí; tỉ lệ đạt lấy từ lượt 2 |
| 28/11 10:30 | `cost/personas.yaml`: thay bản tự ước tính (09:40) bằng bản **đo từ data BTC** (`evidence/count_usage_btc.py`: 144 người hỏi, chia theo số phiên / tháng; người dùng 144 / 361 / 721; giá theo bảng giá BTC). `cost/simulate-1.csv` chạy theo bản này | Số persona có nguồn đo được thay cho tự ước tính; giá lấy đúng bảng BTC như guide 4.2 |
| 28/11 11:30 | Thêm khảo sát n = 4 học viên L3B ngoài nhóm (`evidence/survey/`), đưa vào `evidence/summary.md` để kiểm lại "vì sao" | Data chỉ cho biết học viên tua lại / hỏi tiếp, không cho biết vì sao; n < 20 nên chưa tính là nguồn đạt ngưỡng |
| 28/11 11:45 | Đổi 4 phản hồi từ "khảo sát" thành **phỏng vấn P1–P4** (`evidence/interviews/`): nhóm xác nhận đã hỏi trực tiếp từng người và ghi vào form trong lúc hỏi; khảo sát ghi lại là không làm | Đúng định nghĩa nguồn ở guide 1.2: phỏng vấn ≥3 người ngoài nhóm → đạt ngưỡng |

**Sau CP4 (đến 23:59 Thứ Bảy 28/11)** (sửa theo góp ý — không sửa chuẩn "đạt", câu thử, số bằng chứng, kết quả các lượt đã chạy)

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
|  |  |  |
