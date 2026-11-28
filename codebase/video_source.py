"""Nạp nội dung một video bất kỳ để ôn tập: link YouTube, hoặc file phụ đề .srt / .vtt / .txt (vd tải từ nút CC trang pre-class).

    segs = load_video("https://www.youtube.com/watch?v=aircAruvnKk")          # tự lấy phụ đề bằng yt-dlp
    segs = load_video("d08-v01.vtt", link="https://preclass-online.com/...?t={t}", title="Day08 v01")

Kết quả: danh sách đoạn {ma_doan, bai, tieu_de_bai, youtube_id, start, end, text} — cùng dạng data/lesson_segments.csv —
và bản lưu data/videos/<mã video>.csv. KHÔNG ghi vào data/lesson_segments.csv (bài của trợ giảng và bộ câu thử giữ nguyên).
Lấy phụ đề YouTube cần yt-dlp (có trong .venv của repo, hoặc trên PATH); không có thì dùng file phụ đề.
Tác động ra ngoài: chỉ tải phụ đề công khai (đọc), không đăng gì.
"""
import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(ROOT, "data", "videos")
FIELDS = ["ma_doan", "bai", "tieu_de_bai", "youtube_id", "start", "end", "text"]
YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/))([A-Za-z0-9_-]{11})")
TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d+))?")


def _sec(m):
    return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def read_cues(path):
    """[(giây bắt đầu, câu chữ)] từ .srt / .vtt / .txt ("mm:ss câu chữ"). Bỏ thẻ và dòng lặp của phụ đề tự sinh."""
    text = open(path, encoding="utf-8-sig", errors="replace").read()
    cues, last = [], ""
    if path.lower().endswith((".srt", ".vtt")):
        for block in re.split(r"\n\s*\n", text):
            lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
            for i, l in enumerate(lines):
                if "-->" in l:
                    m = TS.search(l)
                    for body in (re.sub(r"<[^>]+>", "", x).strip() for x in lines[i + 1:]):
                        if m and body and body != last:  # phụ đề tự sinh lặp lại dòng trước
                            cues.append((_sec(m), body))
                            last = body
                    break
    else:
        for l in text.splitlines():
            m = TS.match(l.strip())
            if m:
                cues.append((_sec(m), l.strip()[m.end():].strip(" -:\t")))
    return [c for c in cues if c[1]]


def _group(cues, target=60):
    segs, cur = [], []
    for start, body in cues:
        if cur and start - cur[0][0] >= target:
            segs.append(cur)
            cur = []
        cur.append((start, body))
    if cur:
        segs.append(cur)
    out = []
    for i, s in enumerate(segs):
        end = segs[i + 1][0][0] if i + 1 < len(segs) else s[-1][0] + 10
        out.append((s[0][0], end, " ".join(b for _, b in s)))
    return out


def _ytdlp():
    for p in (shutil.which("yt-dlp"),
              os.path.join(ROOT, ".venv", "Scripts", "yt-dlp.exe"),
              os.path.join(ROOT, ".venv", "bin", "yt-dlp")):
        if p and os.path.exists(p):
            return p
    return None


def _youtube_subs(video_id, langs):
    """Tải phụ đề bằng yt-dlp vào thư mục tạm; thử phụ đề do người làm trước, rồi phụ đề tự sinh; từng ngôn ngữ."""
    exe = _ytdlp()
    if not exe:
        raise RuntimeError("Không thấy yt-dlp. Dùng file phụ đề .srt / .vtt thay cho link YouTube.")
    tmp = tempfile.mkdtemp(prefix="subs-")
    url = "https://www.youtube.com/watch?v=" + video_id
    errors = []
    for auto in (False, True):
        for lang in langs:
            args = [exe, "--skip-download", "--sub-format", "vtt", "--sub-langs", lang, "--no-warnings",
                    "--write-auto-subs" if auto else "--write-subs", "-o", os.path.join(tmp, "%(id)s.%(ext)s"), url]
            r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            files = glob.glob(os.path.join(tmp, "*.vtt"))
            if files:
                return files[0], lang, auto
            errors.append((lang, "tự sinh" if auto else "gốc", (r.stderr or "").strip().splitlines()[-1:]))
    raise RuntimeError("Không lấy được phụ đề YouTube (%s). Thử lại sau, hoặc tải file phụ đề rồi dùng đường dẫn file."
                       % "; ".join("%s/%s: %s" % (l, k, " ".join(e)) for l, k, e in errors))


def load_video(source, code="V1", title="", link="", langs=("vi", "en"), seconds=60):
    """Nạp video → các đoạn có mã <code>-01, <code>-02… Trả (segments, mô tả nguồn)."""
    m = YT_RE.search(source) or (re.fullmatch(r"[A-Za-z0-9_-]{11}", source) and re.match(r"(.*)", source))
    if os.path.exists(source):
        path, key, desc = source, re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.splitext(os.path.basename(source))[0]), "file " + source
        link = link or key
    elif m:
        vid = m.group(1)
        path, lang, auto = _youtube_subs(vid, list(langs))
        key, link = vid, link or vid
        desc = "YouTube %s, phụ đề %s%s" % (vid, lang, " (tự sinh)" if auto else "")
    else:
        raise ValueError("Nguồn không phải link YouTube hay file có thật: %s" % source)
    rows = _group(read_cues(path), seconds)
    if not rows:
        raise RuntimeError("Phụ đề không có mốc thời gian nào đọc được.")
    segs = [{"ma_doan": "%s-%02d" % (code, i), "bai": code, "tieu_de_bai": title or key, "youtube_id": link,
             "start": s, "end": e, "text": t} for i, (s, e, t) in enumerate(rows, 1)]
    os.makedirs(VIDEO_DIR, exist_ok=True)
    with open(os.path.join(VIDEO_DIR, key + ".csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(segs)
    return segs, desc


def cite(codes, segments):
    """Như tools.check_citations nhưng trên các đoạn của video vừa nạp."""
    from tools import fmt_time
    by = {s["ma_doan"]: s for s in segments}
    valid, invalid = [], []
    for c in codes:
        s = by.get(c)
        if not s:
            invalid.append(c)
            continue
        y = s["youtube_id"]
        valid.append({"ma_doan": c, "khoang": "%s–%s" % (fmt_time(s["start"]), fmt_time(s["end"])),
                      "link": y.replace("{t}", str(s["start"])) if "{t}" in y
                      else ("https://youtu.be/%s?t=%d" % (y, s["start"]) if re.fullmatch(r"[A-Za-z0-9_-]{11}", y) else y)})
    return {"valid": valid, "invalid": invalid}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    segs, desc = load_video(sys.argv[1], *(sys.argv[2:3] or []))
    print("Đã nạp %d đoạn từ %s → data/videos/" % (len(segs), desc))
