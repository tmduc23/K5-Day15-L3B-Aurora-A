"""Đào bình luận công khai dưới 2 video bài giảng đang dùng làm dữ liệu bài (data/lesson_segments.csv).

Chạy lại:  python evidence/count_comments.py fetch   (cần: pip install yt-dlp; ~3–5 phút)
           python evidence/count_comments.py count   (chỉ đọc file raw, in số + ví dụ đã ẩn danh)

- Lấy 500 bình luận gốc xếp theo "Top" mỗi video + tối đa 5 trả lời mỗi bình luận.
  "Top" thiên về bình luận được chú ý (nhiều trả lời hơn) → tỉ lệ "không ai trả lời" đo được là cận dưới.
- File raw (có tên tài khoản) lưu ở evidence/youtube/raw-*.json — đã gitignore (evidence/**/raw-*), KHÔNG commit.
- Định nghĩa (viết trước khi đếm):
  * câu hỏi = bình luận gốc có dấu "?" và ≥ 4 từ;
  * câu hỏi về nội dung bài = câu hỏi có ít nhất một từ khoá kỹ thuật trong KEYWORDS (danh sách cố định bên dưới);
  * "không ai trả lời" = không có trả lời nào trong dữ liệu lấy về;
  * "trả lời chỉ về đoạn trong video" = có trả lời chứa mốc thời gian dạng m:ss.
  Mẫu số của mọi tỉ lệ ghi rõ khi in.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

VIDEOS = {"B1": "aircAruvnKk", "B2": "IHZwWFHWa-w"}
OUT = Path(__file__).resolve().parent / "youtube"
KEYWORDS = [
    "neuron", "weight", "bias", "sigmoid", "relu", "activation", "layer", "hidden", "gradient", "cost",
    "loss", "descent", "backprop", "matrix", "pixel", "network", "train", "learn", "function", "input",
    "output", "derivative", "minimum", "minima", "step", "dataset", "mnist", "accuracy", "edge", "pattern",
]
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")


def fetch() -> None:
    import yt_dlp

    OUT.mkdir(parents=True, exist_ok=True)
    for bai, vid in VIDEOS.items():
        opts = {
            "skip_download": True, "getcomments": True, "quiet": True, "no_warnings": True,
            "extractor_args": {"youtube": {"comment_sort": ["top"], "max_comments": ["all", "500", "all", "5"]}},
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        comments = [{k: c.get(k) for k in ("id", "parent", "text", "like_count", "author_is_uploader", "timestamp")}
                    for c in info.get("comments") or []]
        (OUT / f"raw-{bai}.json").write_text(json.dumps(comments, ensure_ascii=False), encoding="utf-8")
        print(bai, vid, len(comments), "bình luận (gốc + trả lời)")


def anon(cid: str) -> str:
    return "c" + hashlib.sha1(cid.encode()).hexdigest()[:8]


def is_question(t: str) -> bool:
    return "?" in t and len(t.split()) >= 4


def is_lesson_question(t: str) -> bool:
    low = t.lower()
    return is_question(t) and any(k in low for k in KEYWORDS)


def count() -> None:
    total = {"roots": 0, "q": 0, "lq": 0, "lq_noreply": 0, "lq_reply": 0, "lq_reply_time": 0, "lq_uploader": 0}
    examples = []
    for bai in VIDEOS:
        rows = json.loads((OUT / f"raw-{bai}.json").read_text(encoding="utf-8"))
        roots = [r for r in rows if r["parent"] == "root"]
        replies: dict[str, list] = {}
        for r in rows:
            if r["parent"] != "root":
                replies.setdefault(r["parent"], []).append(r)
        qs = [r for r in roots if is_question(r["text"] or "")]
        lqs = [r for r in qs if is_lesson_question(r["text"])]
        no = [r for r in lqs if not replies.get(r["id"])]
        yes = [r for r in lqs if replies.get(r["id"])]
        with_time = [r for r in yes if any(TIME_RE.search(x["text"] or "") for x in replies[r["id"]])]
        upl = [r for r in yes if any(x.get("author_is_uploader") for x in replies[r["id"]])]
        print(f"{bai}: {len(roots)} bình luận gốc · {len(qs)} câu hỏi · {len(lqs)} câu hỏi về nội dung bài · "
              f"{len(no)} không ai trả lời · {len(with_time)}/{len(yes)} câu có trả lời chỉ mốc thời gian · "
              f"{len(upl)} được tác giả video trả lời")
        for k, v in (("roots", roots), ("q", qs), ("lq", lqs), ("lq_noreply", no), ("lq_reply", yes),
                     ("lq_reply_time", with_time), ("lq_uploader", upl)):
            total[k] += len(v)
        examples += [(bai, r) for r in sorted(no, key=lambda r: -(r["like_count"] or 0))[:6]]

    t = total
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"  # noqa: E731
    print("\nTỔNG (2 video):")
    print("  Câu hỏi về nội dung bài / bình luận gốc:", pct(t["lq"], t["roots"]))
    print("  Câu hỏi về nội dung bài KHÔNG ai trả lời:", pct(t["lq_noreply"], t["lq"]))
    print("  Trong câu có trả lời, trả lời chỉ mốc thời gian m:ss:", pct(t["lq_reply_time"], t["lq_reply"]))
    print("  Câu hỏi về nội dung bài được tác giả video trả lời:", pct(t["lq_uploader"], t["lq"]))
    print("\nVí dụ câu hỏi không ai trả lời (mã ẩn danh, nhiều like nhất trước):")
    for bai, r in examples:
        print(f"  [{bai} · {anon(r['id'])} · {r['like_count'] or 0} like] {(r['text'] or '').strip()[:300]}")


if __name__ == "__main__":
    {"fetch": fetch, "count": count}[sys.argv[1] if len(sys.argv) > 1 else "count"]()
