"""Tần suất dùng trợ giảng dưới video, từ chat log BTC — số cho cost/personas.yaml.

Chạy lại: python evidence/count_usage_btc.py <thư mục data/preclass của repo đề>
- "Phiên" = các câu một học viên hỏi trợ giảng dưới CÙNG một video (cùng transcript) trong cùng một ngày.
- Số phiên / người / tháng = số phiên của người đó ÷ số ngày quan sát × 30 (số ngày = từ câu hỏi đầu tiên tới cuối cùng trong data).
- Chia người đã hỏi thành 3 nhóm theo số phiên / tháng: ít (< 4), vừa (4–11), nhiều (≥ 12).
"""
import csv
import statistics as stx
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

root = Path(sys.argv[1])
rows = [r for r in csv.DictReader(open(root / "chat.csv", encoding="utf-8-sig"))
        if r["channel"] == "video_question" and r["agent_id"] == "teaching_assistant"]
learners = sum(1 for _ in csv.DictReader(open(root / "learners.csv", encoding="utf-8-sig")))
ts = [datetime.fromisoformat(r["asked_at"]) for r in rows]
days = max((max(ts) - min(ts)).total_seconds() / 86400, 1)
sessions = defaultdict(lambda: defaultdict(int))  # hv -> (video, date) -> số câu
for r, t in zip(rows, ts):
    sessions[r["hv"]][(r["transcript"], t.date())] += 1
print(f"Tài khoản học viên (learners.csv): {learners}")
print(f"Người đã hỏi trợ giảng dưới video: {len(sessions)} ({100 * len(sessions) / learners:.0f}%)")
print(f"Khoảng quan sát: {min(ts).date()} → {max(ts).date()} = {days:.1f} ngày · {len(rows)} câu")
tiers = {"it": [], "vua": [], "nhieu": []}
for hv, ss in sessions.items():
    per_month = len(ss) / days * 30
    key = "it" if per_month < 4 else "vua" if per_month < 12 else "nhieu"
    tiers[key].append((per_month, list(ss.values())))
for k, v in tiers.items():
    pm = [x for x, _ in v]; turns = [t for _, ts_ in v for t in ts_]
    print(f"{k:6s}: {len(v):3d} người ({100 * len(v) / len(sessions):.0f}% người hỏi) · "
          f"phiên/tháng trung vị {stx.median(pm):.1f} · câu/phiên trung bình {stx.mean(turns):.2f}")
