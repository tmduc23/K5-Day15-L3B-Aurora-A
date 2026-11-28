# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — không chép lại nguyên file data.

Hai nguồn: **(A) chat log BTC** `data/preclass/chat.csv` + `events.csv` (nguồn chính đã khai ở CP1)
và **(B) bình luận công khai dưới 2 video bài giảng** đang dùng làm dữ liệu bài `data/lesson_segments.csv` (đã đào, chạy lại được).

## A. Chat log BTC (`data/preclass` của repo đề — không commit nguyên file)

### 1. Cách đếm — viết trước khi chạy (28/11 09:08, định nghĩa nằm ở đầu script)

- Data dùng: `chat.csv` (1,260 lượt) nối với `events.csv` (`agent_replied`, `video_seeked`) qua mã lượt chat.
- **Mẫu số N:** câu học viên hỏi **trợ giảng AI ngay dưới video** (`channel = video_question`, `agent_id = teaching_assistant`) có sự kiện trả lời.
- Đếm: *tua lùi tìm lại* = trong 5 phút sau khi nhận trả lời, cùng học viên tua video lùi (`to < from`); *hỏi tiếp* = trong 10 phút, hỏi trợ giảng thêm câu nữa dưới cùng video.
- Script: `python evidence/count_chat_btc.py <thư mục data/preclass>` (thư viện chuẩn).
- Giả thuyết CP1 ("≥30% câu trả lời không trích mã đoạn") **không đếm được**: BTC chỉ cho độ dài câu hỏi / câu trả lời, không có chữ.

### 2. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Câu hỏi trợ giảng dưới video có trả lời | N = 1091 | — | từ 144 học viên; Day08: 86 câu |
| Tua lùi video trong 5 phút sau khi nhận trả lời | 199 / 1091 | 18% | học viên tự đi tìm lại đoạn trong video |
| Hỏi tiếp trợ giảng (cùng video) trong 10 phút | 548 / 1091 | 50% | |
| Có ít nhất một trong hai | 656 / 1091 | 60% | |

### 3. Ví dụ (mã lượt chat của BTC, đã ẩn danh sẵn) — vừa tua lùi vừa hỏi tiếp

1. `C01122` · Day01/d01-r1-v02 · hỏi 42 ký tự, trả lời 366 ký tự
2. `C00470` · Day01/d01-r1-v02 · hỏi 45 ký tự, trả lời 293 ký tự
3. `C00070` · Day01/d01-r1-v02 · hỏi 42 ký tự, trả lời 257 ký tự
4. `C01046` · Day01/d01-r1-v01 · hỏi 41 ký tự, trả lời 380 ký tự
5. `C00913` · Day02/d02-r2-v03 · hỏi 46 ký tự, trả lời 398 ký tự

### 4. Giới hạn

"Hỏi tiếp" có thể là học viên tò mò hỏi thêm chứ không phải câu trả lời chưa đủ; "tua lùi" có thể vì lý do khác câu trả lời. Data cho biết **họ làm gì sau khi nhận trả lời**, không cho biết **vì sao** → kiểm lại bằng phỏng vấn (hỏi: lần gần nhất nhận trả lời của trợ giảng, bạn làm gì tiếp, có tua lại video không, vì sao).

## B. Bình luận YouTube dưới 2 video bài giảng

### 1. Cách đếm — viết TRƯỚC khi chạy (giả thuyết ở `evidence/hypothesis.md`, 08:57 28/11)

- Data dùng: bình luận công khai dưới `aircAruvnKk` (B1, *But what is a neural network?*) và `IHZwWFHWa-w` (B2, *Gradient descent*), lấy lúc 09:00 28/11/2026: 500 bình luận gốc xếp theo "Top" mỗi video + tối đa 5 trả lời mỗi bình luận.
- Đếm gì: câu hỏi về nội dung bài, câu nào không có trả lời, câu trả lời có chỉ mốc thời gian trong video không.
- Định nghĩa (cố định trong script): *câu hỏi* = bình luận gốc có "?" và ≥4 từ · *về nội dung bài* = có ≥1 từ khoá kỹ thuật trong danh sách `KEYWORDS` · *không ai trả lời* = không có trả lời nào trong dữ liệu lấy về · *trả lời chỉ đoạn trong video* = trả lời chứa mốc `m:ss`.
- **Mẫu số:** tỉ lệ "không ai trả lời" tính trên số *câu hỏi về nội dung bài* (không phải trên tổng bình luận).
- Script: `evidence/count_comments.py` — `python evidence/count_comments.py fetch` rồi `python evidence/count_comments.py count` (cần `pip install yt-dlp`). File raw có tên tài khoản lưu ở `evidence/youtube/raw-*.json`, đã gitignore, không commit.

### 2. Đọc trước, đếm sau

Đã đọc 33 câu ngắn (dưới 260 ký tự) và 12 câu nhiều like nhất trong 68 câu được lọc. Các kiểu thấy được:
- Hỏi lại một chỗ cụ thể trong video, có ghi mốc thời gian (vd "At 10:05…", "at 14:59…") — người học tự chỉ đoạn, nhưng câu trả lời (nếu có) thì không chỉ lại đoạn nào.
- Hỏi mở rộng ra ngoài bài (CNN, cross-entropy, đạo hàm bậc hai) — trợ giảng cần biết nói "không có trong bài".
- Có lẫn câu đùa / không phải hỏi bài nhưng lọt bộ lọc từ khoá (vd `c3ec4e7cc` "Hey, I love Machine Learning?!") → số "câu hỏi về nội dung bài" bị thổi lên một ít; xem mục 5.

### 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Câu hỏi về nội dung bài / bình luận gốc | 68 / 1000 | 7% | B1: 18/500 · B2: 50/500 |
| Câu hỏi về nội dung bài **không ai trả lời** | 45 / 68 | 66% | B1: 8/18 · B2: 37/50. Lấy theo "Top" nên đây là cận dưới |
| Câu có trả lời, trả lời **chỉ mốc thời gian** trong video | 1 / 23 | 4% | Người học không được chỉ lại đoạn để tự kiểm |
| Câu hỏi về nội dung bài được tác giả video trả lời | 2 / 68 | 3% | |

So với giả thuyết (≥30% không ai trả lời; <10% trả lời chỉ mốc thời gian): **đúng cả hai**.

### 4. ≥5 ví dụ cụ thể (nguyên văn, mã đã ẩn danh)

1. `B1 · c7cdac06f` (không ai trả lời): "At 10:05 you say that adding the negative weights around to detect edges will increase the weighted sum, but surely as the activation value is between 0 and 1, it will decrease the weighted sum…?"
2. `B1 · c36f2aa24` (không ai trả lời): "Question re 15:00: should the bias vector go from b_0->b_k instead of b_n?"
3. `B2 · cda307a78` (không ai trả lời): "However there's one point that I didn't understand, why does the gradient descent algorithm struggle to find local minimas with swapped labels? If anyone could answer my question I'd be very grateful."
4. `B2 · c1d397872` (không ai trả lời): "I'm not sure I understand the last section regarding training a neural network using mislabeled images. … why would the accuracy of the models be any different?"
5. `B2 · c2cfb5324` (không ai trả lời): "16:50 what if we give every layer a cost to force them to think by breaking it into edges and loop?"
6. `B2 · c66561f19`: "…regarding the cost function part, it seems that you used the MSE for a classification task, normally, you should use Binary cross entropy?"

12 câu hỏi thật trong số này được đưa vào `eval/benchmark.csv` (B15–B26, `source = data_that`).

### 5. Giới hạn của data

- **Không đúng hẳn người dùng của lát cắt:** người bình luận YouTube là người tự học công khai, không phải học viên L3B trên trang pre-class; cùng *việc* (hỏi một chỗ chưa hiểu khi xem video bài giảng) nhưng khác bối cảnh (không có trợ giảng AI). Data cho biết họ **hỏi gì và có ai trả lời không**, không cho biết **vì sao** hay họ mất bao lâu.
- **Bộ lọc từ khoá có nhiễu** (câu đùa lọt vào) và có thể bỏ sót câu hỏi không chứa từ khoá; *chưa kiểm tay từng dòng* — cần kiểm tay 68 dòng và ghi tỉ lệ khớp.
- Lấy theo "Top" → thiên về bình luận được chú ý; tỉ lệ "không ai trả lời" thật còn cao hơn.
→ Kiểm lại bằng: chat log BTC (mục A) và phỏng vấn học viên L3B (`evidence/interviews/`).
