"""Luyện tập tương tác từ ngân hàng câu hỏi (data/question_bank.json) — không gọi model, không tốn token.

Chạy:  python run.py  rồi gõ  /luyen
       python codebase/practice.py --bai B1 --loai trac_nghiem --so-cau 5

Máy hỏi từng câu → học viên trả lời → chấm ngay (trắc nghiệm, điền khuyết) hoặc hiện ý chính để tự chấm (tự luận)
→ hiện giải thích, câu trích nguyên văn từ bài, link mở đúng giây, tài liệu tham khảo. Cuối buổi: điểm và câu cần xem lại.
Không lưu điểm, không gửi đi đâu.
"""
import argparse
import json
import os
import random
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "data", "question_bank.json")
TYPES = {"trac_nghiem": "Trắc nghiệm", "dien_khuyet": "Điền khuyết", "tu_luan": "Tự luận"}


def _plain(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def load(bai="", loai="", muc_do=""):
    if not os.path.exists(BANK):
        raise RuntimeError("Chưa có ngân hàng câu hỏi. Chạy: python codebase/build_bank.py")
    items = json.load(open(BANK, encoding="utf-8"))["items"]
    return [q for q in items if (not bai or q["bai"] == bai) and (not loai or q["loai"] == loai)
            and (not muc_do or q["muc_do"] == muc_do)]


def _show_answer(q):
    print("   Đáp án: %s" % q["dap_an"])
    if q.get("y_chinh"):
        print("   Ý chính cần có: " + " · ".join(q["y_chinh"]))
    print("   Giải thích: " + q["giai_thich"])
    print("   Bài nói: “%s”" % q["trich_nguyen_van"])
    for c in q["nguon_bai"]:
        print("   Xem lại: [%s] %s → %s" % (c["ma_doan"], c["khoang"], c["link"]))
    for r in q.get("tham_khao", []):
        print("   Tham khảo: %s — %s" % (r["tieu_de"], r["url"]))


def run(items, so_cau=5, seed=None):
    rnd = random.Random(seed)
    picked = rnd.sample(items, min(so_cau, len(items)))
    score, review = 0, []
    for i, q in enumerate(picked, 1):
        print("\nCâu %d/%d · %s · mức %s · %s" % (i, len(picked), TYPES[q["loai"]], q["muc_do"], q["id"]))
        print(q["cau_hoi"])
        if q["loai"] == "trac_nghiem":
            for k in "ABCD":
                print("   %s. %s" % (k, q["lua_chon"][k]))
        ans = input("Trả lời: ").strip()
        if q["loai"] == "trac_nghiem":
            ok = ans.upper()[:1] == q["dap_an"]
        elif q["loai"] == "dien_khuyet":
            ok = bool(ans) and _plain(ans) == _plain(q["dap_an"])
        else:
            _show_answer(q)
            ok = input("Tự chấm — bài của bạn có đủ các ý chính? (c/k): ").strip().lower().startswith("c")
        if q["loai"] != "tu_luan":
            print("→ %s" % ("ĐÚNG" if ok else "CHƯA ĐÚNG"))
            _show_answer(q)
        score += ok
        if not ok:
            review.append(q)
    print("\nKết quả: %d/%d câu đạt." % (score, len(picked)))
    if review:
        print("Nên xem lại:")
        for q in review:
            c = q["nguon_bai"][0]
            print("   %s → [%s] %s" % (q["id"], c["ma_doan"], c["link"]))
    return score, len(picked)


def interactive():
    items = load()
    bais = sorted({q["bai"] for q in items})
    raw = input("Bài [%s] (Enter = tất cả): " % "/".join(bais)).strip()
    bai = raw if raw in bais else ""
    raw = input("Loại câu [trac_nghiem/dien_khuyet/tu_luan] (Enter = trộn): ").strip()
    loai = raw if raw in TYPES else ""
    raw = input("Số câu (Enter = 5): ").strip()
    pool = load(bai, loai)
    if not pool:
        print("Không có câu nào khớp lựa chọn.")
        return
    run(pool, int(raw) if raw.isdigit() else 5)


def main():
    for s in (sys.stdout, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--bai", default=None)
    ap.add_argument("--loai", default="", choices=["", *TYPES])
    ap.add_argument("--muc-do", default="")
    ap.add_argument("--so-cau", type=int, default=5)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    if a.bai is None and not a.loai:
        return interactive()
    run(load(a.bai or "", a.loai, a.muc_do), a.so_cau, a.seed)


if __name__ == "__main__":
    main()
