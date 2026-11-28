"""Công cụ của bài toán — trợ giảng trả lời câu hỏi dưới video, có trích mã đoạn.

Mỗi công cụ là một hàm Python có @tool. Docstring ghi: tên · input · output · có tác động ra ngoài không.
Dữ liệu: data/lesson_segments.csv (transcript bài giảng đã chia đoạn, mỗi đoạn một mã như "B1-04").
"""
import csv
import os

from tracing import tool, TOOLS  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGMENTS_CSV = os.path.join(ROOT, "data", "lesson_segments.csv")
_cache = {}


def _load():
    if "rows" not in _cache:
        with open(SEGMENTS_CSV, encoding="utf-8") as f:
            _cache["rows"] = [dict(r, start=int(r["start"]), end=int(r["end"])) for r in csv.DictReader(f)]
    return _cache["rows"]


def fmt_time(sec):
    sec = int(sec)
    return "%02d:%02d" % (sec // 60, sec % 60) if sec < 3600 else "%d:%02d:%02d" % (sec // 3600, sec % 3600 // 60, sec % 60)


@tool
def get_lesson_segments(bai: str = "") -> list:
    """get_lesson_segments — lấy các đoạn transcript của bài giảng.
    Input: mã bài ("B1", "B2"; rỗng = mọi bài). Output: danh sách {ma_doan, bai, start, end, text}.
    Không tác động ra ngoài (chỉ đọc data/lesson_segments.csv)."""
    rows = _load()
    return [r for r in rows if not bai or r["bai"] == bai]


@tool
def check_citations(codes: list) -> dict:
    """check_citations — kiểm mã đoạn model trích có thật trong dữ liệu không, và đổi ra link YouTube đúng giây.
    Input: danh sách mã đoạn (vd ["B1-04", "B9-99"]). Output: {"valid": [{ma_doan, link, khoang}], "invalid": [mã]}.
    Không tác động ra ngoài."""
    by_code = {r["ma_doan"]: r for r in _load()}
    valid, invalid = [], []
    for c in codes:
        r = by_code.get(c)
        if r is None:
            invalid.append(c)
            continue
        valid.append({
            "ma_doan": c,
            # youtube_id là mã YouTube, hoặc URL trang pre-class có "{t}" (data/import_transcript.py)
            "link": (r["youtube_id"].replace("{t}", str(r["start"])) if "{t}" in r["youtube_id"]
                     else "https://youtu.be/%s?t=%d" % (r["youtube_id"], r["start"])),
            "khoang": "%s–%s" % (fmt_time(r["start"]), fmt_time(r["end"])),
        })
    return {"valid": valid, "invalid": invalid}


REFERENCES_CSV = os.path.join(ROOT, "data", "references.csv")


@tool
def get_references(text: str, bai: str = "", limit: int = 2, min_hits: int = 1) -> list:
    """get_references — tìm tài liệu tham khảo trên internet cho một nội dung, từ danh sách link đã kiểm tay
    (data/references.csv: mỗi link có nguồn và ngày kiểm). Model KHÔNG tự viết URL; code chọn link theo từ khoá.
    Input: đoạn chữ cần tìm tài liệu (câu hỏi + đoạn bài được trích), mã bài, số link tối đa.
    Output: [{id, tieu_de, url, nguon}] xếp theo số từ khoá khớp. Không tác động ra ngoài (chỉ đọc file)."""
    if "refs" not in _cache:
        with open(REFERENCES_CSV, encoding="utf-8") as f:
            _cache["refs"] = list(csv.DictReader(f))
    low = text.lower()
    scored = []
    for r in _cache["refs"]:
        if bai and r["bai"] not in (bai, "all"):
            continue
        hits = sum(1 for k in r["tu_khoa"].split("|") if k and k.lower() in low)
        if hits >= max(1, min_hits):
            scored.append((hits, r))
    scored.sort(key=lambda x: -x[0])
    return [{k: r[k] for k in ("id", "tieu_de", "url", "nguon")} for _, r in scored[:limit]]
