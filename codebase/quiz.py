"""Tính năng "Đề ôn tập" — học viên chọn bài, số câu, mức độ, chủ đề → đề trắc nghiệm bám nội dung bài.

Chạy:
    python run.py            rồi gõ  /on-tap          (hỏi từng lựa chọn)
    python codebase/quiz.py --bai B1 --so-cau 5 --muc-do vua --chu-de "sigmoid"

Workflow cố định (giống trợ giảng, spec.md §4):
    1. get_lesson_segments(bai)   — lấy đoạn bài có mã.
    2. call_model                 — sinh câu hỏi JSON CHỈ từ các đoạn; mỗi câu ghi mã đoạn làm căn cứ.
    3. Code kiểm từng câu         — đủ 4 lựa chọn, đáp án nằm trong lựa chọn, mã đoạn có thật (check_citations).
                                    Câu không qua kiểm thì BỎ, không sửa hộ.
    4. get_references             — tài liệu internet lấy từ data/references.csv (link đã kiểm tay, có ngày kiểm);
                                    model KHÔNG tự viết URL.
Kết quả: in ra màn hình + lưu quiz/de-on-tap-<thời gian>.md (đề trước, đáp án + giải thích + nguồn ở cuối).
Không tác động ra ngoài: không nộp bài, không chấm điểm học viên.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai import call_model  # noqa: E402
from tools import fmt_time, get_lesson_segments, get_references  # noqa: E402
from tracing import note  # noqa: E402
from video_source import cite, load_video  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "quiz")
LEVELS = {
    "de": "DỄ — nhớ lại định nghĩa, con số, tên gọi nêu thẳng trong đoạn",
    "vua": "VỪA — hiểu ý: vì sao, so sánh, điều gì xảy ra nếu…, vẫn trả lời được chỉ từ đoạn",
    "kho": "KHÓ — nối 2 đoạn trở lên, hoặc bẫy hiểu lầm thường gặp mà đoạn đã giải thích",
}

SYSTEM = """Bạn soạn đề ôn tập trắc nghiệm cho học viên, CHỈ dựa trên các đoạn bài giảng được cung cấp (mã dạng B1-04).
Luật:
- Mỗi câu: 4 lựa chọn A–D, đúng MỘT đáp án; đáp án và giải thích phải nằm trong đoạn được ghi ở "ma_doan".
- Không hỏi điều đoạn không nói; không dùng kiến thức ngoài; không viết URL, link hay thời gian.
- Lựa chọn sai phải hợp lý (hiểu lầm có thể gặp), không vô lý.
- Câu hỏi, lựa chọn, giải thích bằng tiếng Việt, giữ thuật ngữ tiếng Anh khi cần. Giải thích ≤ 40 từ.
- Trả về DUY NHẤT một mảng JSON, không chữ nào khác:
[{"cau_hoi": "...", "lua_chon": {"A": "...", "B": "...", "C": "...", "D": "..."}, "dap_an": "B",
  "giai_thich": "...", "ma_doan": ["B1-04"]}]"""


def _context(segments):
    return "\n".join("[%s] (%s–%s) %s" % (s["ma_doan"], fmt_time(s["start"]), fmt_time(s["end"]), s["text"])
                     for s in segments)


def _parse(text):
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _valid(q, segments):
    """Code kiểm một câu: đủ trường, 4 lựa chọn, đáp án thuộc lựa chọn, mã đoạn có thật. Trả (ok, lý do, link)."""
    try:
        opts = q["lua_chon"]
        if not (isinstance(opts, dict) and sorted(opts) == ["A", "B", "C", "D"] and all(str(v).strip() for v in opts.values())):
            return False, "không đủ 4 lựa chọn A–D", []
        if str(q["dap_an"]).strip().upper() not in opts:
            return False, "đáp án không nằm trong lựa chọn", []
        if not str(q["cau_hoi"]).strip() or not q.get("ma_doan"):
            return False, "thiếu câu hỏi hoặc mã đoạn", []
    except (KeyError, TypeError, AttributeError):
        return False, "sai cấu trúc", []
    checked = cite([str(c) for c in q["ma_doan"]], segments)
    if checked["invalid"] or not checked["valid"]:
        return False, "mã đoạn không tồn tại: %s" % ", ".join(checked["invalid"]), []
    return True, "", checked["valid"]


def make_quiz(bai="", so_cau=5, muc_do="vua", chu_de="", segments=None, nguon=""):
    """Sinh đề từ bài có sẵn (bai) hoặc từ các đoạn của một video vừa nạp (segments, xem video_source.load_video).
    Trả {"questions": [...], "dropped": [(câu, lý do)], "bai", "muc_do", "chu_de"}."""
    so_cau = max(1, min(int(so_cau), 10))
    muc_do = muc_do if muc_do in LEVELS else "vua"
    from_video = segments is not None
    segments = segments if from_video else get_lesson_segments(bai)
    if not segments:
        raise ValueError("Không có bài %r trong data/lesson_segments.csv" % bai)
    focus = ("Tập trung vào chủ đề: %s (nếu bài không có chủ đề này thì soạn từ phần gần nhất trong bài).\n" % chu_de
             if chu_de else "")
    user = ("Các đoạn bài giảng:\n%s\n\nSoạn %d câu, mức độ %s.\n%sPhủ nhiều đoạn khác nhau, không lặp ý."
            % (_context(segments), so_cau, LEVELS[muc_do], focus))
    raw = _parse(call_model(SYSTEM, user)["text"])
    by_code = {s["ma_doan"]: s for s in segments}
    questions, dropped = [], []
    for q in raw[:so_cau]:
        ok, why, links = _valid(q, segments)
        if not ok:
            dropped.append((str(q.get("cau_hoi", ""))[:80] if isinstance(q, dict) else "", why))
            continue
        cited_text = " ".join(by_code[c["ma_doan"]]["text"] for c in links if c["ma_doan"] in by_code)
        q["dap_an"] = str(q["dap_an"]).strip().upper()
        q["nguon_bai"] = links
        # video ngoài: chỉ gợi ý link khi khớp ≥2 từ khoá, tránh gắn tài liệu lạc đề
        q["tham_khao"] = get_references(q["cau_hoi"] + " " + cited_text, bai="" if from_video else bai,
                                        min_hits=2 if from_video else 1)
        questions.append(q)
    if dropped:
        note("bỏ %d câu không qua kiểm: %s" % (len(dropped), "; ".join(w for _, w in dropped)))
    label = nguon or (segments[0]["tieu_de_bai"] if from_video else (bai or "B1 + B2"))
    return {"questions": questions, "dropped": dropped, "bai": label, "muc_do": muc_do, "chu_de": chu_de}


def to_markdown(quiz):
    qs = quiz["questions"]
    out = ["# Đề ôn tập — bài %s · mức %s%s" % (quiz["bai"], quiz["muc_do"],
                                                 " · chủ đề: %s" % quiz["chu_de"] if quiz["chu_de"] else ""),
           "", "*Câu hỏi soạn từ nội dung bài giảng; mỗi đáp án có mã đoạn và link mở đúng giây để tự kiểm.*", ""]
    for i, q in enumerate(qs, 1):
        out.append("**Câu %d.** %s" % (i, q["cau_hoi"]))
        out += ["- %s. %s" % (k, q["lua_chon"][k]) for k in "ABCD"]
        out.append("")
    out += ["---", "", "## Đáp án, giải thích và nguồn", ""]
    refs_all = {}
    for i, q in enumerate(qs, 1):
        out.append("**Câu %d: %s.** %s" % (i, q["dap_an"], q.get("giai_thich", "")))
        for c in q["nguon_bai"]:
            out.append("- Trong bài: [%s] %s → %s" % (c["ma_doan"], c["khoang"], c["link"]))
        for r in q["tham_khao"]:
            out.append("- Tham khảo thêm: %s (%s) — %s" % (r["tieu_de"], r["nguon"], r["url"]))
            refs_all[r["id"]] = r
        out.append("")
    if refs_all:
        out += ["## Tài liệu tham khảo trên internet", ""]
        out += ["- %s — %s · %s" % (r["tieu_de"], r["nguon"], r["url"]) for r in refs_all.values()]
        out += ["", "*Link lấy từ danh sách đã kiểm (`data/references.csv`), không do AI tự viết.*", ""]
    if quiz["dropped"]:
        out.append("*Đã bỏ %d câu không qua kiểm (sai cấu trúc hoặc mã đoạn không tồn tại).*" % len(quiz["dropped"]))
    return "\n".join(out)


def save(md):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "de-on-tap-%s.md" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    return path


def _ask(prompt, choices, default):
    raw = input("%s [%s] (Enter = %s): " % (prompt, "/".join(choices), default)).strip()
    return raw if raw in choices else default


def interactive():
    """Hỏi từng lựa chọn rồi sinh đề — dùng trong python run.py (lệnh /on-tap)."""
    bais = sorted({s["bai"] for s in get_lesson_segments()})
    src = input("Nguồn: Enter = bài có sẵn (%s) · hoặc dán link YouTube / đường dẫn file phụ đề .srt .vtt: "
                % ", ".join(bais)).strip()
    segs, nguon, bai = None, "", ""
    if src:
        print("Đang lấy nội dung video…")
        segs, nguon = load_video(src)
        print("Đã nạp %d đoạn (%s)." % (len(segs), nguon))
    else:
        bai = _ask("Chọn bài", bais + ["all"], "all")
        bai = "" if bai == "all" else bai
    so = _ask("Số câu", [str(n) for n in range(3, 11)], "5")
    muc = _ask("Mức độ (de = dễ, vua = vừa, kho = khó)", list(LEVELS), "vua")
    chu_de = input("Chủ đề muốn ôn (bỏ trống = cả bài): ").strip()
    quiz = make_quiz(bai, int(so), muc, chu_de, segments=segs, nguon=nguon)
    md = to_markdown(quiz)
    print("\n" + md)
    print("\n(Đã lưu: %s)" % os.path.relpath(save(md), ROOT))


def main():
    for s in (sys.stdout, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Sinh đề ôn tập bám nội dung bài giảng")
    ap.add_argument("--bai", default=None, help="B1, B2 hoặc all")
    ap.add_argument("--so-cau", type=int, default=5)
    ap.add_argument("--muc-do", default="vua", choices=list(LEVELS))
    ap.add_argument("--chu-de", default="")
    ap.add_argument("--video", default="", help="link YouTube hoặc file phụ đề .srt / .vtt / .txt")
    ap.add_argument("--title", default="")
    ap.add_argument("--link", default="", help="với file phụ đề: URL trang video có {t} để mở đúng giây")
    a = ap.parse_args()
    if a.video:
        segs, nguon = load_video(a.video, title=a.title, link=a.link)
        print("Đã nạp %d đoạn (%s)." % (len(segs), nguon))
        md = to_markdown(make_quiz("", a.so_cau, a.muc_do, a.chu_de, segments=segs, nguon=a.title or nguon))
        print(md)
        print("\n(Đã lưu: %s)" % os.path.relpath(save(md), ROOT))
        return
    if a.bai is None:
        return interactive()
    md = to_markdown(make_quiz("" if a.bai == "all" else a.bai, a.so_cau, a.muc_do, a.chu_de))
    print(md)
    print("\n(Đã lưu: %s)" % os.path.relpath(save(md), ROOT))


if __name__ == "__main__":
    main()
