# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-090408 | 15/26 | 58% | 5/8 | 5/13 | 5/5 | chưa (cần ≥80%) |
| 2 | run-2@20261128-092049 | 18/26 | 69% | 4/8 | 9/13 | 5/5 | chưa (cần ≥80%) |
| 3 | run-3@20261128-120824 | 19/26 | 73% | 5/8 | 9/13 | 5/5 | chưa (cần ≥80%) |
| 4 | run-4@20261128-123056 | **23/26** | **88%** | 8/8 | 10/13 | 5/5 | **đạt** (≥80%, tu_choi 5/5, 0 mã bịa) |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`, `eval/run-3.csv`, `eval/run-4.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`, `traces/run-3.jsonl`, `traces/run-4.jsonl`.

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

## 3b. Cải tiến thêm — lượt 3

- Nhắm vào: 6 câu lượt 2 vẫn từ chối nhầm. Đọc trace `traces/run-2.jsonl` thấy **2 nguyên nhân khác nhau**: (1) model trả lời đúng nhưng **quên ghi mã đoạn** hoặc ghi mã không tồn tại → code chặn cả câu (B03, B22: không mã; B19: `B2-21`); (2) model **kết luận "không có trong bài" quá vội** (B15, B20, B21).
- Đã sửa gì (`codebase/agent.py`, vẫn workflow cố định, mỗi bước tối đa 1 lần gọi thêm): (a) **rà lại trước khi từ chối** — model báo `KHONG_CO_TRONG_BAI` thì gọi lại 1 lần với yêu cầu rà từng đoạn, trả lời phần có trong bài; (b) **sửa trích dẫn** — câu trả lời không còn mã hợp lệ thì gọi lại 1 lần, đưa danh sách mã hợp lệ, yêu cầu ghi lại; vẫn không có mã hợp lệ thì chặn như cũ. Không đổi bộ câu thử, cách chấm, chuẩn "đạt".
- Kết quả: 18/26 → **19/26 (73%)**. Nguyên nhân (1): sửa được B03, B22; B19 vẫn bị chặn (model lặp lại mã không tồn tại — chặn đúng, 0 mã bịa lọt ra). Nguyên nhân (2): bước rà lại **không cứu được** B15, B20, B21 — model giữ nguyên kết luận khi rà lại trên cùng 39 đoạn; nhưng câu ngoài bài thật (B12–B14, B23–B26) vẫn từ chối đúng 9/9.
- Tệ đi: **B06** (lượt 2 qua, lượt 3 lại thiếu ý "nhanh nhất" — câu này dao động giữa các lượt, không do bước mới). **Chi phí:** 1,6 lần gọi model / câu (lượt 2: 1,0); token vào 9,2k → 15k / câu; chi phí cả bộ 26 câu $0,037 → $0,061 (+63%, giá gpt-4o-mini) — chi phí / câu đạt $0,0021 → $0,0032.
- Mô phỏng chi phí 50 phiên trên code lượt 3: `cost/simulate-2.csv` — $0,0059 / task thành công (lượt 2: $0,0042).
- Bài học: lỗi "từ chối nhầm" còn lại không sửa được bằng cách hỏi lại cùng model trên cùng ngữ cảnh → cần bước **tìm đoạn liên quan bằng code** (đưa 5–8 đoạn sát nhất) thay vì đưa cả 39 đoạn.

## 3c. Cải tiến lượt 4 — tách "chọn đoạn" và "trả lời"

- Nhắm vào: 7 câu trượt lượt 3. Bài học lượt 3: hỏi lại cùng model trên cùng 39 đoạn không đổi được kết luận → đổi **ngữ cảnh** chứ không hỏi lại.
- Đã sửa gì (`codebase/agent.py`): (a) **chọn đoạn** — model #1 đọc cả bài, chỉ trả về ≤6 mã đoạn liên quan (kể cả liên quan một phần / tiền đề sai / khái niệm gần nhất); code thêm đoạn chứa mốc thời gian học viên nhắc trong câu hỏi và đoạn kề ±1; (b) **trả lời** — model #2 chỉ thấy các đoạn đã chọn; thêm 2 luật chung: nêu đủ ý then chốt theo cách bài nói, không thêm nhận xét / kiến thức ngoài các đoạn; (c) giữ bước sửa trích dẫn, bỏ bước rà lại. Không có luật nào nhắm riêng một câu thử; không đổi bộ câu thử, cách chấm, chuẩn "đạt".
- Kết quả: 19/26 → **23/26 (88%) — đạt chuẩn "đạt"** lần đầu. Sửa được **B05** (đủ ý lấy trung bình), **B06** (đủ ý "nhanh nhất"), **B18** (không còn kiến thức ngoài), **B21** (không còn từ chối nhầm). Không câu nào tệ đi so với lượt 3. 0 mã bịa; bước sửa trích dẫn chỉ cần ở 1 câu (B10).
- Chi phí: 2,0 lần gọi model / câu nhưng bước trả lời chỉ đọc vài đoạn → token vào 15k → 13,7k / câu; cả bộ $0,061 → **$0,055** (rẻ hơn lượt 3).
- Còn trượt: **B15** (trích đúng B1-17 nhưng không nêu ý số phần tử vector bias), **B19** (đúng ý ReLU nhưng trích nhầm B2-09 thay vì B1-22), **B20** (vẫn nói bài không có dữ liệu huấn luyện / ảnh mới). Lưu ý: kết quả dao động giữa các lượt (B06 lượt 2 qua, lượt 3 trượt) — 88% là **một** lượt, chưa chạy lặp để đo độ dao động.

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào (sau lượt 4): còn 3/26 câu trượt — B20 từ chối nhầm; B15, B19 có mã nhưng thiếu ý / trích nhầm đoạn, nguy hiểm hơn vì học viên dễ tin. (Sau lượt 3: vẫn từ chối nhầm 4/26 câu có nội dung trong bài (B15, B19, B20, B21) — không làm học viên học sai nhưng bắt họ tự tìm lại, đúng pain cần giải; 3 câu trả lời thiếu / sai ý dù trích đúng mã (B05, B06, B18) — cả 3 đã sửa ở lượt 4) — **nguy hiểm hơn**, vì có mã đoạn nên học viên dễ tin; code hiện chỉ kiểm mã có tồn tại, không kiểm nội dung có khớp đoạn.
- Lỗi lọt qua cách chấm (phát hiện khi kiểm tay cột `pass`, không đổi điểm): một số câu đạt `pass_criterion` (có ý chính + mã hợp lệ) nhưng vẫn có khẳng định mâu thuẫn với bài — **B16 lượt 2** ("không phải là việc tổng trọng số sẽ giảm", trái B1-12: tổng lớn nhất khi pixel xung quanh tối) · **B21 lượt 4** ("bài không đề cập cụ thể / không nói rõ" vì sao cộng gradient âm, trong khi B2-07, B2-08 giải thích đúng điều này) · **B16 lượt 4** (bác lại thắc mắc đúng của học viên: "không có nghĩa là… sẽ giảm, mà ngược lại", mức nhẹ hơn lượt 2). Nguy hiểm vì câu trả lời có mã đoạn nên học viên dễ tin, và câu "bài không nói" đẩy học viên đi tìm chỗ khác — đúng pain cần giải. `pass_criterion` (chốt CP2) chỉ kiểm có ý chính và mã hợp lệ, chưa bắt được lỗi này; metric `noi_dung_dung` ("không có khẳng định mâu thuẫn với đoạn được trích") cần người chấm đọc cả câu trả lời, không chỉ tìm ý chính.
- Nếu có thêm 1 tuần: chạy lặp mỗi cấu hình ≥3 lần để đo độ dao động (88% mới là 1 lượt); kiểm mã trích có khớp nội dung câu (B19 trích nhầm đoạn); thêm bước kiểm mỗi câu khẳng định có nằm trong đoạn được trích không (giảm B05, B18); thay dữ liệu bài bằng transcript Day08 thật khi có; phỏng vấn ≥3 học viên để đo đúng số phút mất mỗi lần.
