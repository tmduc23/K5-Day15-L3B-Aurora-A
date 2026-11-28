# Lecture VideoRAG

Trợ lý học tập cho **chuỗi video bài giảng**: video LMS (tải file lên, hoặc link tải trực tiếp) và YouTube (link playlist / video). Hệ thống:

1. chuyển **giọng nói thành chữ bằng Whisper** (bài giảng LMS thường không có phụ đề; với YouTube có thể dùng phụ đề có sẵn), giữ timestamp; tải video và cắt **frame tại mỗi lần đổi slide**, cho model (mặc định GPT qua OpenAI API, có thể đổi sang Claude) đọc chữ/công thức trên slide;
2. lập chỉ mục tìm kiếm (vector + từ khoá) cho cả chuỗi;
3. viết **ghi chú kiến thức** cho từng video, mỗi ý kèm trích dẫn: link nhảy đúng giây (trình phát trong app với video LMS, YouTube với video YouTube) + ảnh slide lúc đó;
4. cho **chat hỏi đáp** trên cả chuỗi, câu trả lời trích dẫn `[Bài 2 · 12:34]`, bấm là video nhảy tới đó.

Bản "đủ dùng" của master prompt: SQLite thay PostgreSQL, worker thread thay Celery/Redis, không Docker, giao diện HTML/JS không cần build.

Nhật ký triển khai, quyết định kỹ thuật và kết quả chạy thật: [docs/NHAT_KY_TRIEN_KHAI.md](docs/NHAT_KY_TRIEN_KHAI.md).

## Chạy

Cần Python 3.10+. Không cần ffmpeg, Node hay Docker.

```bash
python -m venv --system-site-packages .venv      # hoặc venv thường
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
cp .env.example .env                              # điền OPENAI_API_KEY
.venv/Scripts/python -m app                       # http://127.0.0.1:8000
```

Không có API key: đặt `LVR_LLM_PROVIDER=fake` để chạy thử toàn bộ luồng với câu trả lời giả (phụ đề, slide, tìm kiếm vẫn thật).

Lần đầu chạy sẽ tải model embedding `intfloat/multilingual-e5-small` (~470 MB) và model Whisper `large-v3-turbo` (~1,6 GB).

Whisper chạy trên GPU nếu có (đã đo trên RTX 3050 4 GB: ~12× thời gian thực, video 19 phút xử lý trọn luồng trong ~3 phút). Máy chỉ có CPU: đặt `LVR_WHISPER_MODEL=small`.

Test (không gọi mạng, không tốn phí API):

```bash
.venv/Scripts/python -m pytest -q -p no:asyncio
```

Kiểm tra nhanh phần YouTube thật (không gọi LLM): `python scripts/smoke_youtube.py <link>`.

## Video LMS

Ở trang chủ, mục **Video bài giảng LMS**: chọn một hoặc nhiều file (`.mp4 .m4v .mov .mkv .webm .avi`, xếp theo tên file
kiểu tự nhiên: `Bai 2` trước `Bai 10`), hoặc dán link tải trực tiếp file video. Ở trang một chuỗi LMS có thể thêm video
vào chuỗi đó.

- File được lưu ở `data/videos/` và giữ lại: Whisper đọc âm thanh từ chính file, keyframe cắt từ file, và trang video
  phát file bằng trình phát HTML5 (trích dẫn trỏ tới `/media/videos/<file>#t=<giây>`, bấm là tua tới đúng chỗ).
- Video LMS luôn dùng Whisper (không có phụ đề), bất kể `LVR_TRANSCRIPT_MODE`.
- File không có tiếng, không đọc được hình hoặc sai định dạng bị từ chối với thông báo rõ.
- Link cần đăng nhập LMS sẽ trả về trang web chứ không phải video: hệ thống từ chối và báo tải file về rồi upload.
- Xoá video / chuỗi thì xoá luôn file đã lưu.

## Kiến trúc

```
app/
  youtube.py     kiểm tra URL (chỉ host YouTube), mở rộng playlist, metadata, phụ đề, tải luồng video
  localvideo.py  video LMS: kiểm tra file, lưu upload theo từng khối, tải link trực tiếp, đọc thời lượng, kiểm tra âm thanh
  transcript.py  Whisper speech-to-text (faster-whisper, model nạp 1 lần dùng cho mọi video);
                 làm sạch + chia lời nói / phụ đề thành đoạn ~45 s giữ timestamp
  frames.py      tìm keyframe: lấy mẫu 2 s/lần, mở frame mới khi hình đổi đủ nhiều và đã đứng yên, bỏ trùng bằng dHash
  pipeline.py    tạo chuỗi + job; xử lý 1 video: metadata → transcript → keyframe + model đọc slide → index → ghi chú
  worker.py      worker thread lấy job từ bảng `jobs` (SQLite); job đang chạy khi app tắt được chạy lại
  search.py      hybrid: cosine trên embedding + FTS5 BM25 (không phân biệt dấu), gộp bằng Reciprocal Rank Fusion,
                 gom kết quả gần nhau thành đoạn thời gian
  notes.py       ghi chú kiến thức từng video (structured output)
  chat.py        hỏi đáp trên cả chuỗi, lịch sử hội thoại lưu DB
  citations.py   đổi ID trích dẫn thành giây / link / frame; loại ID không hợp lệ
  llm.py         OpenAILLM (GPT, JSON schema strict), AnthropicLLM (Claude, refusal fallback), FakeLLM cho test
  embeddings.py  sentence-transformers (đa ngôn ngữ) hoặc HashEmbedder cho test
  api.py, main.py  FastAPI + phục vụ giao diện ở app/static
```

**Trích dẫn không thể bịa timestamp.** Model chỉ thấy đoạn transcript dạng `[C12] (12:30–13:15) …` và slide dạng
`[F3] (12:41) …`, và chỉ được trích ID. Code tra ID trong DB ra giây, link `?t=` và ảnh. ID không tồn tại hoặc thuộc
video ngoài phạm vi bị loại; ý ghi chú không còn trích dẫn nào bị bỏ (số ý bị bỏ được hiển thị).

## Cấu hình chính (`.env`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LVR_TRANSCRIPT_MODE` | `auto` (file `.env` mẫu đặt `whisper`) | `whisper`: luôn chuyển giọng nói thành chữ (đường LMS) · `auto`: phụ đề YouTube nếu có, không thì Whisper · `subtitles`: chỉ phụ đề |
| `LVR_WHISPER_MODEL` | `large-v3-turbo` | `small` cho máy không có GPU |
| `LVR_WHISPER_LANGUAGE` | (trống = tự nhận) | `vi` / `en` để ép ngôn ngữ |
| `LVR_LLM_PROVIDER` | `openai` | `openai`, `anthropic`, hoặc `fake` để chạy không cần key |
| `LVR_OPENAI_MODEL` | `gpt-5-mini` | model cho mọi bước (cần `OPENAI_API_KEY`); qua OpenRouter dùng id có tiền tố, vd `openai/gpt-4o-mini` |
| `LVR_OPENAI_BASE_URL` | (trống = OpenAI) | `https://openrouter.ai/api/v1` để dùng OpenRouter |
| `LVR_LLM_MODEL` | `claude-opus-5-5` | model Claude khi provider là `anthropic` |
| `LVR_EFFORT_FRAMES` / `_NOTES` / `_CHAT` | `low` / `high` / `medium` | độ sâu suy nghĩ từng bước |
| `LVR_LLM_FALLBACKS` | `true` | refusal fallback phía server của Claude (beta) |
| `LVR_OUTPUT_LANGUAGE` | `vi` | `vi`, `en` hoặc `auto` |
| `LVR_DESCRIBE_FRAMES` | `true` | tắt để không gọi model cho từng slide |
| `LVR_MAX_FRAMES_PER_VIDEO` | `60` | giới hạn slide mỗi video |
| `LVR_MAX_UPLOAD_MB` | `4096` | giới hạn mỗi file video LMS |
| `LVR_EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | đổi sang `BAAI/bge-m3` nếu cần chất lượng cao hơn |

## API

`POST /api/series` `{urls, title?}` · `POST /api/series/upload` (multipart: `files`, `title?`, `series_id?`) ·
`POST /api/series/links` `{urls, title?, series_id?}` · `GET /api/series` · `GET /api/series/{id}` · `DELETE /api/series/{id}` ·
`GET /api/videos/{id}` · `POST /api/videos/{id}/reprocess` · `DELETE /api/videos/{id}` ·
`POST /api/series/{id}/search` `{query, video_ids?, mode}` · `POST /api/series/{id}/chat/sessions` ·
`GET /api/chat/sessions/{id}` · `POST /api/chat/sessions/{id}/messages` `{question, video_ids?}` ·
`GET /api/stats` · `GET /api/health`. Tài liệu OpenAPI: `/docs`.

## Giới hạn đã biết

- Chạy cục bộ một người dùng: chưa có đăng nhập, rate limit.
- Chưa tự đăng nhập LMS để lấy video: cần tải file về rồi upload (hoặc link tải trực tiếp không cần đăng nhập).
- Whisper mới kiểm trên bài giảng tiếng Anh; chưa đo độ chính xác với bài giảng tiếng Việt.
- Tìm kiếm vector bằng numpy trên toàn bộ vector của chuỗi: đủ cho vài chục video; kho lớn hơn nên thay bằng Qdrant.
- Với YouTube, chỉ dùng nội dung công khai; không vượt qua video riêng tư, giới hạn tuổi hay DRM.
