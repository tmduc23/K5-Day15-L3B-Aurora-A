# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ — 2 bộ: chat log BTC (N = 1091) + bình luận dưới video bài giảng (N = 68) | `evidence/data-mining.md`, script `evidence/count_chat_btc.py`, `evidence/count_comments.py` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☑ — **4 học viên L3B ngoài nhóm** (28/11), hỏi theo bộ câu cố định, ghi vào form trong lúc hỏi | `evidence/interviews/P1.md`–`P4.md`, `questions.md`, `ghi-chep-form.csv` |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ — không làm (Google Form chỉ dùng để ghi phỏng vấn) | — |

Giả thuyết viết trước khi đào: `evidence/hypothesis.md` (CP1 17:00 27/11 cho chat log; 08:57 28/11 cho bình luận).

## 2. Số chính

- **Đào data — chat log BTC:** sau khi trợ giảng AI trả lời câu hỏi dưới video, **656/1091 (60%)** lượt học viên tua lùi video trong 5 phút (**199/1091, 18%**) hoặc hỏi tiếp trợ giảng trong 10 phút (**548/1091, 50%**) — 144 học viên, Day01–Day13.
- **Đào data — bình luận dưới 2 video bài giảng:** **45/68 (66%)** câu hỏi về nội dung bài không ai trả lời; trong 23 câu có trả lời, chỉ **1/23 (4%)** câu trả lời chỉ ra mốc thời gian trong video; tác giả video trả lời 2/68 (3%).
- **Phỏng vấn (4 học viên L3B ngoài nhóm, 28/11)** — n nhỏ nên ghi x/4, không ghi %:
  - **3/4** người gặp chỗ vướng: phải tự đối chiếu câu trả lời với bài — tua lại video để xác nhận (P1, P3) hoặc tìm YouTube / bài báo vì không biết câu trả lời có khớp định nghĩa trong bài không (P4); **1/4** dùng luôn câu trả lời (P2).
  - Lần gần nhất có tua lại video: 3/4 (P1, P2, P3).
  - Từng tin một câu trả lời rồi thấy sai / không khớp bài: **1/4** (P3: làm sai lab), Không 1/4, Không nhớ 2/4.
  - Sẵn lòng dùng thử demo: **3/4**.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | Học viên L3B (sinh viên) | Có | 3 | 5 phút | hỏi trợ giảng AI, tua lại video, hỏi bạn, Google / ChatGPT |
| P2 | Học viên L3B (sinh viên) | Không | 10 | 30–60 phút | hỏi trợ giảng AI, tua lại video, Google / ChatGPT, bỏ qua |
| P3 | Học viên L3B (sinh viên) | Có | 3 | không ghi | tua lại video, hỏi bạn, Google / ChatGPT, hỏi TA |
| P4 | Học viên L3B (sinh viên) | Có | 2 | 30 phút | hỏi bạn, Google / ChatGPT, YouTube / bài báo |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

1. "At 10:05 you say that adding the negative weights around to detect edges will increase the weighted sum, but surely as the activation value is between 0 and 1, it will decrease the weighted sum…?" — bình luận `B1/c7cdac06f`, không ai trả lời
2. "Question re 15:00: should the bias vector go from b_0->b_k instead of b_n?" — bình luận `B1/c36f2aa24`, không ai trả lời
3. "…there's one point that I didn't understand, why does the gradient descent algorithm struggle to find local minimas with swapped labels? If anyone could answer my question I'd be very grateful." — bình luận `B2/cda307a78`, không ai trả lời
4. "I'm not sure I understand the last section regarding training a neural network using mislabeled images. … why would the accuracy of the models be any different?" — bình luận `B2/c1d397872`, không ai trả lời
5. "16:50 what if we give every layer a cost to force them to think by breaking it into edges and loop?" — bình luận `B2/c2cfb5324`, không ai trả lời
6. "Tôi mở ChatGPT hỏi về 4 mức hệ thống AI, đọc giải thích nhưng không biết có khớp với định nghĩa trong bài hay không. Phải mất thêm thời gian đối chiếu lại." — phỏng vấn `P4`, câu B2
7. "phải mất thêm thời gian hỏi, tua lại và xác nhận" — phỏng vấn `P1`, câu C3 (điều khó chịu nhất)
8. "để chắc chắn AI trả lời đúng" — phỏng vấn `P3`, câu B3 (vì sao tua lại video sau khi đọc câu trả lời); lần tin sai: "Sai lab không đúng yêu cầu"
9. "Mất nhiều thời gian tìm hiểu mà không chắc đúng và không biết cách nào tốt hơn" — phỏng vấn `P4`, câu C3
10. Lượt chat `C01122` (Day01/d01-r1-v02, data BTC): học viên hỏi trợ giảng dưới video, nhận trả lời 366 ký tự, rồi trong vài phút vừa tua lùi video vừa hỏi tiếp dưới cùng video (thêm 4 lượt cùng kiểu ở `data-mining.md` mục A).

## 4. Các nguồn có khớp nhau không

Chat log BTC nói: với trợ giảng AI đang chạy, **60%** lần nhận trả lời xong học viên vẫn phải tua lại video hoặc hỏi tiếp — câu trả lời không giúp họ tự kiểm ngay trong bài. Bình luận công khai nói: khi **không** có trợ giảng, **66%** câu hỏi về nội dung bài không ai trả lời, và câu trả lời (nếu có) gần như không bao giờ chỉ về đoạn nào trong video (1/23).

Khớp ở chỗ: người học cần câu trả lời **gắn với đúng đoạn trong video** để tự kiểm, và hiện cả hai bối cảnh đều không có. Lệch ở chỗ: bình luận YouTube là người tự học công khai, không phải học viên L3B; chat log cho biết hành vi chứ không cho biết vì sao (hỏi tiếp có thể vì tò mò). Giả thuyết CP1 (≥30% câu trả lời không trích đoạn) chưa kiểm trực tiếp được vì data BTC không có chữ câu trả lời.

**Phỏng vấn (4 người) trả lời phần "vì sao" mà data không có:** người tua lại video sau khi đọc câu trả lời làm vậy **để xác nhận câu trả lời có đúng với bài** (P1, P3), không phải vì tò mò; P4 hỏi ChatGPT nhưng "không biết có khớp với định nghĩa trong bài hay không". Khớp với cách đọc số 60% ở data. **Điều ngược:** P2 hỏi AI rồi dùng luôn câu trả lời, không kiểm lại, và không thấy khó chịu gì — không phải ai cũng cần tự kiểm. Thời gian mỗi lần (5–60 phút, P1/P2/P4) dài hơn mức 5–10 phút nhóm tự ước tính, nhưng câu B5 đo cả thời gian hiểu bài, không chỉ thời gian tìm lại, nên chưa thay số ở `spec.md` §2.

## 5. Kết luận

Pain có thật và lặp lại thường xuyên: phần lớn câu hỏi dưới video bài giảng hoặc không được trả lời (66%), hoặc được trả lời mà học viên vẫn phải tự tua lại / hỏi tiếp (60%). Lát cắt "trả lời kèm mã đoạn + link mở đúng giây, không có trong bài thì nói không có" nhắm đúng chỗ này: học viên bấm link là tự kiểm được, không phải tua tìm. Phỏng vấn 4 học viên L3B ngoài nhóm xác nhận lý do: 3/4 người phải tự đối chiếu câu trả lời với bài, 1/4 từng tin sai đến mức làm sai lab, 3/4 sẵn lòng dùng thử. Giả thuyết **đúng**, với một ngoại lệ (P2 không cần tự kiểm).
