"""Trang web học + ôn tập: tải video lên (kèm phụ đề) hoặc dán link YouTube → xem video → nút "Tạo tài liệu ôn tập".

Chạy:  python codebase/web.py        rồi mở http://localhost:8000
Chỉ thư viện chuẩn. Video tải lên chỉ phát trong trình duyệt (không gửi lên server); server chỉ nhận chữ phụ đề.

API (JSON):
  POST /api/load   {"youtube": "<link>"}  hoặc  {"subtitle": "<nội dung .srt/.vtt>", "filename": "...", "title": "..."}
                   → {"id", "title", "segments": [...]}   (video_source.load_video)
  POST /api/review {"id", "kieu": "nhanh"|"day_du", "so_cau", "muc_do"}
                   → {"items": [...]}   nhanh = quiz.make_quiz · day_du = build_bank.build_lesson (trắc nghiệm,
                     điền khuyết, tự luận; code kiểm câu trích nguyên văn có thật trong phụ đề)
"""
import json
import os
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tracing  # noqa: E402
from build_bank import build_lesson  # noqa: E402
from quiz import make_quiz  # noqa: E402
from video_source import VIDEO_DIR, load_video  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "web_index.html")
UPLOADS = os.path.join(VIDEO_DIR, "uploads")
_videos = {}  # id -> {"title", "segments"}
_lock = threading.Lock()


def _load(body):
    if body.get("youtube"):
        segs, desc = load_video(body["youtube"].strip(), code="V1", title=body.get("title", ""))
    else:
        name = re.sub(r"[^A-Za-z0-9_.-]+", "-", body.get("filename") or "phude.vtt")[-80:]
        if not name.lower().endswith((".srt", ".vtt", ".txt")):
            name += ".vtt"
        os.makedirs(UPLOADS, exist_ok=True)
        path = os.path.join(UPLOADS, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body.get("subtitle") or "")
        # video tải lên phát ngay trong trình duyệt: link nguồn là "#t=<giây>" để trang tự tua
        segs, desc = load_video(path, code="V1", title=body.get("title") or name, link="#t={t}")
    vid = "%s-%d" % (re.sub(r"[^A-Za-z0-9]+", "", segs[0]["tieu_de_bai"])[:20] or "video", len(_videos) + 1)
    _videos[vid] = {"title": segs[0]["tieu_de_bai"], "segments": segs, "desc": desc}
    return {"id": vid, "title": segs[0]["tieu_de_bai"], "desc": desc, "segments": segs}


def _review(body):
    v = _videos.get(body.get("id"))
    if not v:
        raise ValueError("Chưa nạp video này — tải lại video / phụ đề.")
    segs = v["segments"]
    tracing.begin("web")
    try:
        if body.get("kieu") == "day_du":
            need = max(5, min(int(body.get("so_cau") or 40), 5 * ((len(segs) + 1) // 2)))
            items, dropped = build_lesson("V1", need, lambda *_: None, segs=segs)
            out = {"kieu": "day_du", "items": items, "dropped": dropped}
        else:
            q = make_quiz("", int(body.get("so_cau") or 5), body.get("muc_do") or "vua", body.get("chu_de") or "",
                          segments=segs, nguon=v["title"])
            items = [{"id": "Q%d" % i, "loai": "trac_nghiem", "muc_do": q["muc_do"], "cau_hoi": x["cau_hoi"],
                      "lua_chon": x["lua_chon"], "dap_an": x["dap_an"], "giai_thich": x.get("giai_thich", ""),
                      "nguon_bai": x["nguon_bai"], "tham_khao": x["tham_khao"]} for i, x in enumerate(q["questions"], 1)]
            out = {"kieu": "nhanh", "items": items, "dropped": len(q["dropped"])}
    finally:
        s, _ = tracing.end()
    out["chi_phi"] = {"goi_model": s["model_calls"], "token_vao": s["tokens_in"], "token_ra": s["tokens_out"]}
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data, ctype="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
        self._send(404, {"error": "không có"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 5_000_000:
                return self._send(413, {"error": "Phụ đề quá lớn (> 5 MB)."})
            body = json.loads(self.rfile.read(n) or b"{}")
            with _lock:  # một việc gọi model một lúc
                if self.path == "/api/load":
                    return self._send(200, _load(body))
                if self.path == "/api/review":
                    return self._send(200, _review(body))
            self._send(404, {"error": "không có"})
        except Exception as e:
            self._send(400, {"error": "%s: %s" % (type(e).__name__, e)})

    def log_message(self, *a):
        pass


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    port = int(os.environ.get("PORT", "8000"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://localhost:%d" % port
    print("Trang học + ôn tập: %s   (Ctrl+C để tắt)" % url)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
