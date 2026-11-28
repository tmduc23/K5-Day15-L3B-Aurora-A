"""Đo thời gian học viên mất sau khi nhận trả lời của trợ giảng AI dưới video, và tỉ lệ câu trả lời có trích mốc bài.

Chạy: python evidence/count_time_btc.py <thư mục data/preclass của bộ đề>

Cách đếm (viết trước khi chạy, 28/11 12:40):
- Tập đếm (mẫu số): giống count_chat_btc.py — dòng chat.csv có channel = video_question và
  agent_id = teaching_assistant, có sự kiện agent_replied trong events.csv.
- (1) Có trích mốc bài: khoá `moc_trich_dan` trong data của agent_replied không rỗng.
- (2) Tua lùi xem lại: lần tua lùi đầu tiên (to < from) của cùng học viên trong 5 phút sau khi nhận trả lời.
      "Thời gian tua lùi" = from − to (giây video học viên quay lại xem); "thời gian tới lúc tua" = từ lúc nhận trả lời
      tới lúc tua.
- (3) Hỏi tiếp: câu hỏi kế tiếp của cùng học viên dưới cùng video trong 10 phút; "thời gian tới câu hỏi tiếp" = từ lúc
      nhận trả lời tới lúc gửi câu kế.
- "Phút mất mỗi lần phải tìm lại" (dùng cho spec.md §2) = trung vị của: thời gian tới câu hỏi tiếp (nếu hỏi tiếp),
  hoặc thời gian tới lúc tua + độ dài đoạn tua lùi (nếu chỉ tua lùi). Đây là cận dưới: không tính thời gian đọc
  câu trả lời, không tính lần tìm lại ngoài trang (Google, hỏi bạn).
- So sánh: tỉ lệ tua lùi / hỏi tiếp giữa câu trả lời CÓ và KHÔNG có trích mốc bài.
- (4) Với câu trả lời CÓ trích mốc mà học viên vẫn tua lùi: lần tua tới gần một mốc được trích (±15 giây; mốc dạng
      "...@giây") = dùng trích dẫn để tự kiểm; tới chỗ khác = vẫn phải tự tìm.
(Bổ sung 12:55 sau khi thấy kết quả (1)–(3): mục (4) viết sau, không phải giả thuyết đặt trước.)
"""
import csv
import json
import statistics
import sys
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def ts(s):
    return datetime.fromisoformat(s)


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def main(root: Path) -> None:
    chats = [r for r in csv.DictReader(open(root / "chat.csv", encoding="utf-8-sig"))
             if r["channel"] == "video_question" and r["agent_id"] == "teaching_assistant"]
    chat_ids = {r["id"] for r in chats}
    replied, cites = {}, {}
    seeks = defaultdict(list)
    for e in csv.DictReader(open(root / "events.csv", encoding="utf-8-sig")):
        if e["type"] == "agent_replied" and e["ref_id"] in chat_ids:
            replied[e["ref_id"]] = ts(e["occurred_at"])
            try:
                moc = json.loads(e["data"] or "{}").get("moc_trich_dan") or []
            except ValueError:
                moc = []
            cites[e["ref_id"]] = [float(m.split("@")[-1]) for m in moc if isinstance(m, str) and "@" in m]
        elif e["type"] == "video_seeked":
            try:
                d = json.loads(e["data"] or "{}")
                seeks[e["hv"]].append((ts(e["occurred_at"]), float(d.get("from", 0)), float(d.get("to", 0))))
            except (ValueError, TypeError):
                pass
    for v in seeks.values():
        v.sort()
    asks = defaultdict(list)
    for r in chats:
        asks[(r["hv"], r["transcript"])].append(ts(r["asked_at"]))
    for v in asks.values():
        v.sort()

    base = [r for r in chats if r["id"] in replied]
    n = len(base)
    to_follow, to_seek, rewind, lost = [], [], [], []
    grp = {True: [0, 0], False: [0, 0]}  # có trích mốc? -> [số câu, số câu phải tìm lại]
    near = far = near_link = 0
    for r in base:
        t0 = replied[r["id"]]
        lst = seeks.get(r["hv"], [])
        i = bisect_right(lst, (t0, float("inf"), float("inf")))
        sb = next(((t, fr, to) for t, fr, to in lst[i:i + 50] if t <= t0 + timedelta(minutes=5) and to < fr), None)
        a = asks[(r["hv"], r["transcript"])]
        j = bisect_right(a, t0)
        fu = a[j] if j < len(a) and a[j] <= t0 + timedelta(minutes=10) else None
        g = grp[bool(cites[r["id"]])]
        if sb and cites[r["id"]]:
            if min(abs(sb[2] - m) for m in cites[r["id"]]) <= 15:
                near += 1
            else:
                far += 1
        g[0] += 1
        g[1] += bool(sb or fu)
        if fu:
            to_follow.append((fu - t0).total_seconds() / 60)
        if sb:
            to_seek.append((sb[0] - t0).total_seconds() / 60)
            rewind.append((sb[1] - sb[2]) / 60)
        if fu:
            lost.append((fu - t0).total_seconds() / 60)
        elif sb:
            lost.append((sb[0] - t0).total_seconds() / 60 + (sb[1] - sb[2]) / 60)

    def show(name, xs):
        print(f"{name}: n = {len(xs)} · trung vị {statistics.median(xs):.1f} phút · "
              f"Q1 {q(xs, .25):.1f} · Q3 {q(xs, .75):.1f}")

    n_cite = grp[True][0]
    print(f"Câu hỏi trợ giảng dưới video có trả lời: N = {n}")
    print(f"(1) Câu trả lời KHÔNG trích mốc bài nào: {n - n_cite}/{n} ({100 * (n - n_cite) / n:.0f}%)")
    show("(2) Từ lúc nhận trả lời tới lúc tua lùi", to_seek)
    show("    Độ dài đoạn tua lùi (phút video xem lại)", rewind)
    show("(3) Từ lúc nhận trả lời tới câu hỏi tiếp", to_follow)
    show("=> Phút mất mỗi lần phải tìm lại (cận dưới)", lost)
    for k, label in ((True, "CÓ trích mốc"), (False, "KHÔNG trích mốc")):
        c, s = grp[k]
        if c:
            print(f"Trả lời {label}: {s}/{c} ({100 * s / c:.0f}%) phải tua lùi hoặc hỏi tiếp")
    print(f"(4) Trả lời có trích mốc rồi vẫn tua lùi: tới gần mốc được trích {near}/{near + far} "
          f"({100 * near / (near + far):.0f}%) · tới chỗ khác {far}/{near + far} ({100 * far / (near + far):.0f}%)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
