"""Nhập transcript / phụ đề video thành các đoạn có mã cho data/lesson_segments.csv.

Dùng khi nhóm có transcript thật của video pre-class (vd Day08 "From workflows to agents", 6 video d08-r1-v01…v06)
để thay bản tạm 3Blue1Brown. Chỉ thư viện chuẩn.

    python data/import_transcript.py --bai B1 --title "Day08 v01" --link "https://preclass-online.com/...?t={t}" d08-v01.srt
    python data/import_transcript.py --bai B2 --title "Day08 v02" --link "..." d08-v02.vtt --append

Input: file .srt / .vtt (có mốc thời gian) hoặc .txt dạng "mm:ss câu chữ" mỗi dòng.
Output: ghi vào data/lesson_segments_new.csv (không đụng file đang dùng). Kiểm tay xong thì đổi tên thành
data/lesson_segments.csv. Lưu ý: đổi bài giảng thì phải viết lại expected / pass_criterion của bộ câu thử cho bài mới
và ghi vào spec.md §10 — không trộn kết quả hai bộ.

Cột `youtube_id`: nếu là mã YouTube thì link là youtu.be/<mã>?t=giây; nếu là URL có "{t}" thì code thay {t} bằng giây.
"""
import argparse
import csv
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lesson_segments_new.csv")
FIELDS = ["ma_doan", "bai", "tieu_de_bai", "youtube_id", "start", "end", "text"]
TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d+))?")


def _sec(m):
    h, mi, s = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    return h * 3600 + mi * 60 + s


def read_cues(path):
    """Trả về [(giây bắt đầu, câu chữ)]."""
    text = open(path, encoding="utf-8-sig").read()
    cues = []
    if path.lower().endswith((".srt", ".vtt")):
        for block in re.split(r"\n\s*\n", text):
            lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
            for i, l in enumerate(lines):
                if "-->" in l:
                    m = TS.search(l)
                    body = " ".join(re.sub(r"<[^>]+>", "", x) for x in lines[i + 1:])
                    if m and body:
                        cues.append((_sec(m), body))
                    break
    else:
        for l in text.splitlines():
            m = TS.match(l.strip())
            if m:
                cues.append((_sec(m), l.strip()[m.end():].strip(" -:\t")))
    return [c for c in cues if c[1]]


def group(cues, target=60):
    """Gộp câu thành đoạn ~target giây."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--bai", required=True, help="mã bài, vd B1")
    ap.add_argument("--title", required=True)
    ap.add_argument("--link", required=True, help="mã YouTube, hoặc URL có {t}")
    ap.add_argument("--seconds", type=int, default=60, help="độ dài mỗi đoạn (giây)")
    ap.add_argument("--append", action="store_true", help="thêm vào lesson_segments_new.csv thay vì ghi mới")
    a = ap.parse_args()

    rows = group(read_cues(a.file), a.seconds)
    if not rows:
        raise SystemExit("Không đọc được mốc thời gian nào trong %s" % a.file)
    mode = "a" if a.append and os.path.exists(OUT) else "w"
    with open(OUT, mode, encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if mode == "w":
            w.writeheader()
        for i, (s, e, t) in enumerate(rows, 1):
            w.writerow({"ma_doan": "%s-%02d" % (a.bai, i), "bai": a.bai, "tieu_de_bai": a.title,
                        "youtube_id": a.link, "start": s, "end": e, "text": t})
    print("Đã ghi %d đoạn %s → %s" % (len(rows), a.bai, OUT))


if __name__ == "__main__":
    main()
