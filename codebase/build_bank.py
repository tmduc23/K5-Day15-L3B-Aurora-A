"""Dựng ngân hàng câu hỏi ôn tập cho mỗi bài: trắc nghiệm, điền khuyết, tự luận — có đáp án, giải thích, nguồn.

Chạy:  python codebase/build_bank.py            (mọi bài, ≥40 câu / bài)
       python codebase/build_bank.py --bai B2 --min 40

Workflow cố định, đi lần lượt từng cụm 2 đoạn liền nhau để phủ đều cả bài:
    1. call_model: soạn 5 câu cho cụm (2 trắc nghiệm, 2 điền khuyết, 1 tự luận), CHỈ từ 2 đoạn đó, mỗi câu kèm
       "trich_nguyen_van" — một câu chép nguyên văn từ đoạn làm căn cứ cho đáp án.
    2. Code kiểm từng câu: đúng cấu trúc theo loại; mã đoạn có thật và thuộc cụm; câu trích nguyên văn CÓ THẬT trong
       đoạn được ghi (so khớp chữ, không phân biệt hoa thường). Không qua → bỏ. Thiếu câu → soạn lại cụm đó 1 lần.
    3. Bỏ câu trùng; gắn link đúng giây (check_citations) và tài liệu tham khảo đã kiểm (get_references).
Kết quả: data/question_bank.json + quiz/ngan-hang-<bài>.md. Mọi câu đánh dấu da_duyet = false (AI soạn, chờ người duyệt).
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
from video_source import cite, load_video  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "data", "question_bank.json")
OUT_DIR = os.path.join(ROOT, "quiz")
TYPES = {"trac_nghiem": "Trắc nghiệm", "dien_khuyet": "Điền khuyết", "tu_luan": "Tự luận"}

SYSTEM = """Bạn soạn câu hỏi ôn tập cho học viên, CHỈ dựa trên các đoạn bài giảng được cung cấp (mã dạng B1-04).
Soạn đúng 5 câu: 2 "trac_nghiem", 2 "dien_khuyet", 1 "tu_luan". Phủ các ý khác nhau của các đoạn, không lặp ý.
Luật chung:
- Câu hỏi, đáp án, giải thích bằng tiếng Việt, giữ thuật ngữ tiếng Anh khi cần. Không dùng kiến thức ngoài đoạn,
  không viết URL, link hay thời gian.
- "ma_doan": các mã đoạn làm căn cứ (chỉ mã có trong danh sách).
- "trich_nguyen_van": CHÉP Y NGUYÊN 8–25 từ tiếng Anh liên tiếp từ đoạn làm căn cứ, không sửa chữ nào.
- "giai_thich": ≤ 45 từ, vì sao đáp án đúng (và vì sao lựa chọn sai là sai, với trắc nghiệm).
- "muc_do": "de" (nhớ lại), "vua" (hiểu ý), hoặc "kho" (nối ý / bẫy hiểu lầm).
Theo loại:
- trac_nghiem: "lua_chon" {"A","B","C","D"}, đúng MỘT đáp án; "dap_an" là chữ cái. Lựa chọn sai phải hợp lý.
- dien_khuyet: "cau_hoi" là một câu có đúng một chỗ trống viết "____"; "dap_an" là từ / cụm ≤ 5 từ điền vào.
- tu_luan: "dap_an" là đáp án mẫu 2–4 câu; "y_chinh" là 2–4 ý bắt buộc phải có để tự chấm.
Trả về DUY NHẤT một mảng JSON, mỗi phần tử có: loai, muc_do, cau_hoi, (lua_chon), dap_an, (y_chinh), giai_thich,
ma_doan, trich_nguyen_van."""


def _norm(s):
    s = str(s).lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9' ]+", " ", s).split()


def _contains(text, quote):
    t, q = " ".join(_norm(text)), " ".join(_norm(quote))
    return len(q.split()) >= 6 and q in t


def _parse(text):
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def check(q, window):
    """Kiểm một câu theo cụm đoạn. Trả lý do bị loại, hoặc "" nếu đạt."""
    codes = {s["ma_doan"]: s for s in window}
    loai = q.get("loai")
    if loai not in TYPES:
        return "loại không hợp lệ"
    if not str(q.get("cau_hoi", "")).strip() or not str(q.get("dap_an", "")).strip():
        return "thiếu câu hỏi / đáp án"
    if loai == "trac_nghiem":
        o = q.get("lua_chon")
        if not (isinstance(o, dict) and sorted(o) == ["A", "B", "C", "D"] and all(str(v).strip() for v in o.values())):
            return "không đủ 4 lựa chọn"
        if str(q["dap_an"]).strip().upper() not in o:
            return "đáp án ngoài lựa chọn"
    if loai == "dien_khuyet":
        if str(q["cau_hoi"]).count("____") != 1 or len(str(q["dap_an"]).split()) > 5:
            return "điền khuyết sai dạng"
    if loai == "tu_luan" and not (isinstance(q.get("y_chinh"), list) and 2 <= len(q["y_chinh"]) <= 4):
        return "tự luận thiếu ý chính"
    mas = [str(c) for c in (q.get("ma_doan") or [])]
    if not mas or any(c not in codes for c in mas):
        return "mã đoạn không có / ngoài cụm"
    if not any(_contains(codes[c]["text"], q.get("trich_nguyen_van", "")) for c in mas):
        return "câu trích nguyên văn không có trong đoạn"
    return ""


def _ask(window, note=""):
    ctx = "\n".join("[%s] (%s–%s) %s" % (s["ma_doan"], fmt_time(s["start"]), fmt_time(s["end"]), s["text"])
                    for s in window)
    return _parse(call_model(SYSTEM, "Các đoạn bài giảng:\n%s\n%s" % (ctx, note))["text"])


def build_lesson(bai, need, log, segs=None):
    from_video = segs is not None
    segs = segs if from_video else get_lesson_segments(bai)
    windows = [segs[i:i + 2] for i in range(0, len(segs), 2)]
    kept, seen, dropped = [], set(), 0
    for w in windows:
        got = []
        for attempt in range(2):  # soạn lại cụm 1 lần nếu chưa đủ 5 câu hợp lệ
            for q in _ask(w, "" if attempt == 0 else "Lần trước có câu không đạt: nhớ chép trich_nguyen_van Y NGUYÊN."):
                why = check(q, w)
                key = " ".join(_norm(q.get("cau_hoi", "")))
                if why or key in seen:
                    dropped += 1
                    continue
                seen.add(key)
                got.append(q)
            if len(got) >= 4:
                break
        kept += got
        log("  %s: cụm %s → %d câu" % (bai, "+".join(s["ma_doan"] for s in w), len(got)))
    if len(kept) < need:
        log("  %s: mới %d < %d câu — soạn thêm vòng 2 trên các cụm" % (bai, len(kept), need))
        for w in windows:
            if len(kept) >= need:
                break
            for q in _ask(w, "Soạn câu MỚI, khác các câu thường gặp nhất về đoạn này."):
                key = " ".join(_norm(q.get("cau_hoi", "")))
                if not check(q, w) and key not in seen:
                    seen.add(key)
                    kept.append(q)
    out = []
    by_code = {s["ma_doan"]: s for s in segs}
    for i, q in enumerate(kept, 1):
        links = cite([str(c) for c in q["ma_doan"]], segs)["valid"]
        text = q["cau_hoi"] + " " + " ".join(by_code[c]["text"] for c in q["ma_doan"])
        refs = get_references(text, bai="" if from_video else bai, min_hits=2 if from_video else 1)
        item = {
            "id": "%s-Q%03d" % (bai, i), "bai": bai, "loai": q["loai"], "muc_do": q.get("muc_do", "vua"),
            "cau_hoi": q["cau_hoi"].strip(), "dap_an": str(q["dap_an"]).strip(),
            "giai_thich": str(q.get("giai_thich", "")).strip(), "ma_doan": q["ma_doan"],
            "trich_nguyen_van": q["trich_nguyen_van"].strip(),
            "nguon_bai": links, "tham_khao": refs, "tieu_de_bai": segs[0]["tieu_de_bai"],
            "nguon_soan": "AI soạn (openai/gpt-4o-mini), code kiểm căn cứ", "da_duyet": False,
        }
        if q["loai"] == "trac_nghiem":
            item["lua_chon"] = q["lua_chon"]
            item["dap_an"] = item["dap_an"].upper()
        if q["loai"] == "tu_luan":
            item["y_chinh"] = q["y_chinh"]
        out.append(item)
    return out, dropped


def to_markdown(bai, items):
    count = {t: sum(1 for q in items if q["loai"] == t) for t in TYPES}
    L = ["# Ngân hàng câu hỏi ôn tập — bài %s" % bai, "",
         "%d câu: %s. Mỗi đáp án có mã đoạn, link mở đúng giây, câu trích nguyên văn từ bài và tài liệu tham khảo. "
         "*AI soạn, code kiểm căn cứ; chưa qua người duyệt.*" % (len(items), " · ".join("%s %d" % (TYPES[t], n) for t, n in count.items())),
         ""]
    for t in TYPES:
        qs = [q for q in items if q["loai"] == t]
        if not qs:
            continue
        L += ["## %s (%d câu)" % (TYPES[t], len(qs)), ""]
        for q in qs:
            L.append("**%s** · mức %s — %s" % (q["id"], q["muc_do"], q["cau_hoi"]))
            if t == "trac_nghiem":
                L += ["- %s. %s" % (k, q["lua_chon"][k]) for k in "ABCD"]
            L.append("")
    L += ["---", "", "## Đáp án và giải thích", ""]
    for q in items:
        L.append("**%s — %s:** %s" % (q["id"], TYPES[q["loai"]], q["dap_an"]))
        if q.get("y_chinh"):
            L.append("- Ý chính cần có: " + " · ".join(q["y_chinh"]))
        L.append("- Giải thích: " + q["giai_thich"])
        L.append("- Bài nói: “%s”" % q["trich_nguyen_van"])
        L += ["- Trong bài: [%s] %s → %s" % (c["ma_doan"], c["khoang"], c["link"]) for c in q["nguon_bai"]]
        L += ["- Tham khảo: %s (%s) — %s" % (r["tieu_de"], r["nguon"], r["url"]) for r in q["tham_khao"]]
        L.append("")
    return "\n".join(L)


def main():
    for s in (sys.stdout,):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--bai", default="")
    ap.add_argument("--min", type=int, default=40)
    ap.add_argument("--video", default="", help="link YouTube hoặc file phụ đề .srt / .vtt / .txt")
    ap.add_argument("--code", default="V1", help="mã cho video, các đoạn thành V1-01, V1-02…")
    ap.add_argument("--title", default="")
    ap.add_argument("--link", default="", help="với file phụ đề: URL trang video có {t}")
    a = ap.parse_args()
    video = None
    if a.video:
        video, desc = load_video(a.video, code=a.code, title=a.title, link=a.link)
        print("Đã nạp %d đoạn (%s)." % (len(video), desc))
        bais = [a.code]
    else:
        bais = [a.bai] if a.bai else sorted({s["bai"] for s in get_lesson_segments()})
    bank = json.load(open(BANK, encoding="utf-8")) if os.path.exists(BANK) else {"items": []}
    bank["items"] = [q for q in bank["items"] if q["bai"] not in bais]
    os.makedirs(OUT_DIR, exist_ok=True)
    for b in bais:
        items, dropped = build_lesson(b, a.min, print, segs=video)
        bank["items"] += items
        with open(os.path.join(OUT_DIR, "ngan-hang-%s.md" % b), "w", encoding="utf-8") as f:
            f.write(to_markdown(b, items) + "\n")
        print("%s: %d câu (bỏ %d câu không qua kiểm)" % (b, len(items), dropped))
    bank["cap_nhat"] = datetime.now().isoformat(timespec="seconds")
    with open(BANK, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=1)
    print("Đã ghi data/question_bank.json (%d câu) và quiz/ngan-hang-*.md" % len(bank["items"]))


if __name__ == "__main__":
    main()
