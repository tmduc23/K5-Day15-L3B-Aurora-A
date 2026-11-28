"""Đào chat log BTC (data/preclass) — chỉ in số tổng hợp, không chép dữ liệu ra repo.

Chạy lại:  python evidence/count_chat_btc.py <đường dẫn tới thư mục data/preclass của repo đề>

Định nghĩa (viết trước khi đếm, 28/11 09:08):
- Tập đếm (mẫu số N): dòng chat.csv có channel = video_question và agent_id = teaching_assistant
  (học viên hỏi trợ giảng AI ngay dưới video), có sự kiện agent_replied trong events.csv.
- "Tua lùi tìm lại": trong 5 phút sau lúc trợ giảng trả lời, cùng học viên có sự kiện video_seeked với to < from.
- "Hỏi tiếp": trong 10 phút sau lúc trả lời, cùng học viên hỏi trợ giảng thêm câu nữa dưới cùng video (cùng transcript).
- Không có chữ câu hỏi / câu trả lời trong data (BTC chỉ cho độ dài) → không đếm được "câu trả lời có trích đoạn không".
"""
from __future__ import annotations

import csv
import json
import sys
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main(root: Path) -> None:
    chats = [r for r in csv.DictReader(open(root / "chat.csv", encoding="utf-8-sig"))
             if r["channel"] == "video_question" and r["agent_id"] == "teaching_assistant"]
    chat_ids = {r["id"] for r in chats}
    replied: dict[str, datetime] = {}
    seeks: dict[str, list] = defaultdict(list)  # hv -> [(time, from, to)]
    for e in csv.DictReader(open(root / "events.csv", encoding="utf-8-sig")):
        if e["type"] == "agent_replied" and e["ref_id"] in chat_ids:
            replied[e["ref_id"]] = ts(e["occurred_at"])
        elif e["type"] == "video_seeked":
            try:
                d = json.loads(e["data"] or "{}")
                seeks[e["hv"]].append((ts(e["occurred_at"]), float(d.get("from", 0)), float(d.get("to", 0))))
            except (ValueError, TypeError):
                pass
    for v in seeks.values():
        v.sort()
    by_hv_video = defaultdict(list)
    for r in chats:
        by_hv_video[(r["hv"], r["transcript"])].append(ts(r["asked_at"]))
    for v in by_hv_video.values():
        v.sort()

    base = [r for r in chats if r["id"] in replied]
    n = len(base)
    back = follow = either = 0
    ex = []
    for r in base:
        t0 = replied[r["id"]]
        lst = seeks.get(r["hv"], [])
        i = bisect_right(lst, (t0, float("inf"), float("inf")))
        sb = any(t <= t0 + timedelta(minutes=5) and to < fr for t, fr, to in lst[i:i + 50])
        asks = by_hv_video[(r["hv"], r["transcript"])]
        j = bisect_right(asks, t0)
        fu = j < len(asks) and asks[j] <= t0 + timedelta(minutes=10)
        if sb and fu and len(ex) < 6:
            ex.append(f"{r['id']} · {r['transcript']} · câu hỏi {r['do_dai_cau_hoi']} ký tự, trả lời {r['do_dai_tra_loi']} ký tự")
        back += sb
        follow += fu
        either += sb or fu
    learners = len({r["hv"] for r in base})
    pct = lambda a: f"{a}/{n} ({100 * a / n:.0f}%)"  # noqa: E731
    print(f"Câu hỏi trợ giảng dưới video có trả lời: N = {n} (từ {learners} học viên)")
    print("Tua lùi video trong 5 phút sau khi nhận trả lời:", pct(back))
    print("Hỏi tiếp trợ giảng (cùng video) trong 10 phút:", pct(follow))
    print("Có ít nhất một trong hai:", pct(either))
    print("Ví dụ (tua lùi VÀ hỏi tiếp):")
    for x in ex:
        print("  ", x)
    d08 = [r for r in base if r["transcript"].startswith("Day08/")]
    print("Riêng Day08: N =", len(d08))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
