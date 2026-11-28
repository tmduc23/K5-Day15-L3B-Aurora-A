"use strict";
// Lecture VideoRAG — single-page UI (no build step). Routes: #/  #/series/:id  #/video/:id?t=seconds

const $app = document.getElementById("app");
const STATUS_VI = {
  PENDING: "Đang chờ", FETCHING_METADATA: "Lấy thông tin", FETCHING_TRANSCRIPT: "Lấy phụ đề",
  PROCESSING_FRAMES: "Xử lý hình ảnh", INDEXING: "Lập chỉ mục", SUMMARIZING: "Viết ghi chú",
  COMPLETED: "Xong", FAILED: "Lỗi",
};
let pollTimer = null;
let player = null;          // YouTube player of the video page
let playerVideoId = null;   // our video id shown in the player

// ---------- helpers ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmt(sec) {
  sec = Math.floor(sec || 0);
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const mm = String(m).padStart(2, "0"), ss = String(s).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
async function api(path, opts = {}) {
  const res = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : res.statusText);
  return data;
}
// Multipart upload with progress (fetch has no upload progress). onProgress gets 0..1.
function upload(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api" + path);
    xhr.upload.onprogress = e => { if (e.lengthComputable) onProgress?.(e.loaded / e.total); };
    xhr.onload = () => {
      let data = {}; try { data = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(typeof data.detail === "string" ? data.detail : xhr.statusText || "Tải lên thất bại"));
    };
    xhr.onerror = () => reject(new Error("Mất kết nối khi tải lên"));
    xhr.send(formData);
  });
}
const isFile = v => v.source_type === "file";
const PLACEHOLDER_THUMB = "data:image/svg+xml," + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90"><rect width="160" height="90" fill="#e5e7eb"/><path d="M68 30l28 15-28 15z" fill="#9ca3af"/></svg>');
function thumbOf(v) {
  return v.thumbnail_url || (isFile(v) ? PLACEHOLDER_THUMB : `https://i.ytimg.com/vi/${v.youtube_id}/mqdefault.jpg`);
}
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 4000);
}
function lightbox(src) {
  const d = document.createElement("div");
  d.className = "lightbox";
  d.setAttribute("role", "dialog"); d.setAttribute("aria-label", "Xem ảnh lớn");
  d.innerHTML = `<img src="${esc(src)}" alt="">`;
  d.onclick = () => d.remove();
  document.body.appendChild(d);
}
function statusBadge(v) {
  const cls = v.status === "COMPLETED" ? "ok" : v.status === "FAILED" ? "bad" : "";
  return `<span class="badge ${cls}">${esc(STATUS_VI[v.status] || v.status)}</span>`;
}
function stopPolling() { if (pollTimer) clearInterval(pollTimer); pollTimer = null; }

// ---------- inline icons (no external assets) ----------
const ICONS = {
  layers: '<path d="M12 3 3 8l9 5 9-5z"/><path d="m3 13 9 5 9-5"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert: '<path d="M12 3 2 20h20z"/><path d="M12 9v5M12 17.5v.01"/>',
  spark: '<path d="M12 3v5M5.5 5.5l3 3M3 12h5M18.5 5.5l-3 3M21 12h-5"/><path d="m9 15 1.5 3L13 15l3-1.5-3-1.5L11 9 9.5 12 6 13.5z"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2z"/><path d="M4 5v14"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  play: '<circle cx="12" cy="12" r="9"/><path d="m10 8.5 6 3.5-6 3.5z" fill="currentColor" stroke="none"/>',
  chat: '<path d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 3z"/>',
  trash: '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13h10l1-13"/>',
  back: '<path d="M11 6l-6 6 6 6M5 12h14"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.5 6"/><path d="M20 5v6h-6"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2"/>',
  inbox: '<path d="M4 13h4l1.5 3h5L16 13h4"/><path d="M5 5h14l1 8v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-5z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
};
const ic = name => `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
const emptyState = (icon, title, text = "") =>
  `<div class="empty">${ic(icon)}<strong>${esc(title)}</strong>${text ? `<span class="small">${esc(text)}</span>` : ""}</div>`;
function setBusy(btn, busy, busyText = "Đang xử lý...") {
  if (!btn) return;
  if (busy) {
    btn.dataset.label = btn.dataset.label || btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="typing"><span class="dots"><i></i><i></i><i></i></span></span> ${esc(busyText)}`;
  } else {
    if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
    btn.disabled = false;
  }
}
const HERO_ART = `<svg viewBox="0 0 340 230" aria-hidden="true">
  <defs><linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#7c3aed"/></linearGradient></defs>
  <rect x="16" y="24" width="216" height="136" rx="16" fill="url(#hg)" opacity=".12"/>
  <rect x="16" y="24" width="216" height="136" rx="16" fill="none" stroke="url(#hg)" stroke-width="2.5"/>
  <circle cx="124" cy="92" r="26" fill="url(#hg)" opacity=".9"/>
  <path d="M117 80l20 12-20 12z" fill="#fff"/>
  <rect x="180" y="128" width="146" height="92" rx="14" fill="var(--panel)" stroke="var(--line-strong)" stroke-width="2.5"/>
  <rect x="196" y="146" width="96" height="9" rx="4.5" fill="var(--line-strong)"/>
  <rect x="196" y="164" width="112" height="9" rx="4.5" fill="var(--line)"/>
  <rect x="196" y="186" width="56" height="20" rx="10" fill="var(--accent-soft)"/>
</svg>`;

// ---------- theme ----------
const THEME_KEY = "lvr-theme";
function applyTheme(t) { if (t === "light" || t === "dark") document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
const currentTheme = () => localStorage.getItem(THEME_KEY) || "auto";
const THEMES = ["auto", "light", "dark"];
const THEME_VI = { auto: "theo hệ thống", light: "sáng", dark: "tối" };
applyTheme(currentTheme());
document.getElementById("theme")?.addEventListener("click", () => {
  const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
  if (next === "auto") localStorage.removeItem(THEME_KEY); else localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
  toast(`Chế độ ${THEME_VI[next]}`);
});

// ---------- answer rendering ----------
// Minimal safe markdown: paragraphs, "- " bullets, **bold**, `code`; [C12, F3] markers -> citation chips.
function renderAnswer(text, citations) {
  const byRef = Object.fromEntries((citations || []).map(c => [c.ref, c]));
  const inline = s => esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[((?:[CF]\d+)(?:\s*,\s*[CF]\d+)*)\]/g, (m, group) => {
      const chips = group.split(/\s*,\s*/).filter(r => byRef[r]).map(r => citeChip(byRef[r], true)).join(" ");
      return chips ? `<sup>${chips}</sup>` : "";
    });
  const out = []; let list = [];
  const flush = () => { if (list.length) { out.push("<ul>" + list.map(li => `<li>${inline(li)}</li>`).join("") + "</ul>"); list = []; } };
  for (const line of String(text || "").split("\n")) {
    const b = line.match(/^\s*[-*•]\s+(.*)/);
    if (b) { list.push(b[1]); continue; }
    flush();
    if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  flush();
  return out.join("");
}
function citeChip(c, short = false) {
  const label = short ? `${c.position + 1}·${fmt(c.start)}` : `Bài ${c.position + 1} · ${c.label}`;
  return `<button class="chip" data-video="${c.video_id}" data-t="${c.start}" title="${esc(c.video_title || "")} — ${esc(c.label)}">${esc(label)}</button>`;
}
function evidenceList(citations) {
  if (!citations?.length) return "";
  return `<div class="evidence">` + citations.map(c => `
    <div class="ev">
      ${c.frame_url ? `<img src="${esc(c.frame_url)}" data-zoom="${esc(c.frame_url)}" alt="Slide ${esc(c.label)}">` : ""}
      <div class="grow">${citeChip(c)} ${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener" class="small">${isFile(c) ? "Mở video ↗" : "YouTube ↗"}</a>` : ""}
        <div class="muted small">${esc((c.quote || "").slice(0, 160))}${(c.quote || "").length > 160 ? "..." : ""}</div></div>
    </div>`).join("") + `</div>`;
}

// Clicking a citation: seek the open player if it shows that video, else open the video page at that time.
document.addEventListener("click", e => {
  const chip = e.target.closest(".chip[data-video]");
  if (chip) {
    const vid = Number(chip.dataset.video), t = Number(chip.dataset.t);
    if (player && playerVideoId === vid && player.seekTo) { player.seekTo(t, true); player.playVideo?.(); window.scrollTo({ top: 0, behavior: "smooth" }); }
    else location.hash = `#/video/${vid}?t=${Math.floor(t)}`;
    return;
  }
  const z = e.target.closest("[data-zoom]");
  if (z) lightbox(z.dataset.zoom);
});

// ---------- loading / error ----------
function skeletonPage() {
  return `<div class="stats">${Array.from({ length: 4 }, () => `<div class="card stat"><div class="skel" style="width:40px;height:40px;border-radius:11px"></div><div class="grow"><div class="skel h" style="width:50%"></div><div class="skel t" style="width:70%;margin-top:8px"></div></div></div>`).join("")}</div>
    <div class="grid cols-2"><div class="card"><div class="skel h" style="width:40%"></div><div class="skel box" style="margin-top:14px"></div><div class="skel box" style="margin-top:10px"></div></div>
    <div class="card"><div class="skel h" style="width:55%"></div><div class="skel box" style="margin-top:14px"></div></div></div>`;
}
const errorCard = msg => `<div class="card" style="border-color:var(--bad)"><div class="row top"><span class="ico" style="background:var(--bad-soft);color:var(--bad)">${ic("alert")}</span><div class="grow"><strong>Không tải được trang</strong><div class="muted small">${esc(msg)}</div><a class="small" href="#/">← Về trang chủ</a></div></div></div>`;

// ---------- pages ----------
async function pageHome() {
  const [stats, series] = await Promise.all([api("/stats"), api("/series")]);
  const s = stats.videos_by_status || {};
  const processing = stats.videos - (s.COMPLETED || 0) - (s.FAILED || 0);
  const cards = [
    ["layers", "Chuỗi bài giảng", stats.series], ["film", "Video", stats.videos],
    ["check", "Đã xử lý", s.COMPLETED || 0], ["clock", "Đang xử lý", processing],
    ["alert", "Lỗi", s.FAILED || 0], ["spark", "Slide đã cắt", stats.frames],
    ["book", "Đoạn transcript", stats.transcript_chunks],
  ];
  $app.innerHTML = `
    <section class="hero">
      <div class="hero-copy">
        <span class="eyebrow">Trợ lý học tập</span>
        <h1>Hỏi đáp và ghi chú từ chuỗi video bài giảng</h1>
        <p>Tải video LMS lên hoặc dán link YouTube. Hệ thống chuyển lời giảng thành văn bản, cắt slide và trả lời kèm trích dẫn nhảy đúng giây trong video.</p>
        <div class="row hero-actions">
          <button class="primary" id="jump-new" type="button">${ic("plus")} Thêm chuỗi bài giảng</button>
          <span class="muted small">Hoặc mở một chuỗi có sẵn ở bên dưới.</span>
        </div>
      </div>
      <div class="hero-art">${HERO_ART}</div>
    </section>
    <div class="stats">
      ${cards.map(([name, label, v]) => `<div class="card stat"><span class="ico">${ic(name)}</span><div><div class="num">${v}</div><div class="lbl">${label}</div></div></div>`).join("")}
    </div>
    <div class="grid cols-2">
      <section class="card">
        <div class="section-head"><h2>Chuỗi bài giảng</h2><div class="spacer"></div>${series.length ? `<span class="badge plain">${series.length}</span>` : ""}</div>
        <div class="list">${series.length ? series.map(x => `
          <a class="item" href="#/series/${x.id}">
            <span class="ico">${ic("layers")}</span>
            <div class="grow"><div class="title truncate">${esc(x.title)}</div>
            <div class="muted small">${x.completed}/${x.video_count} video xong${x.failed ? ` · <span class="err">${x.failed} lỗi</span>` : ""}</div></div>
            <span class="chip" aria-hidden="true">Mở</span>
          </a>`).join("") : emptyState("inbox", "Chưa có chuỗi nào", "Thêm playlist YouTube hoặc video bài giảng LMS ở khung bên cạnh.")}</div>
      </section>
      <section class="card" id="new">
        <div class="section-head"><h2>Thêm chuỗi bài giảng</h2></div>
        <div class="seg" id="src-seg" role="tablist" aria-label="Nguồn video">
          <button type="button" class="active" data-pane="yt" role="tab" aria-selected="true">YouTube</button>
          <button type="button" data-pane="lms" role="tab" aria-selected="false">Video LMS</button>
        </div>
        <form id="add" class="pane" data-pane="yt">
          <label for="yt-urls">Link playlist YouTube, hoặc nhiều link video (mỗi dòng một link)</label>
          <textarea id="yt-urls" name="urls" required placeholder="https://www.youtube.com/playlist?list=..."></textarea>
          <label for="yt-title">Tên chuỗi (không bắt buộc)</label>
          <input type="text" id="yt-title" name="title" placeholder="Lấy theo tên playlist nếu để trống">
          <div class="row" style="margin-top:14px"><button class="primary" type="submit">${ic("plus")} Bắt đầu xử lý</button>
          <span class="muted small" id="addmsg" role="status" aria-live="polite"></span></div>
        </form>
        <form id="addlms" class="pane" data-pane="lms" hidden>
          <label for="lms-files">File video tải từ LMS (chọn nhiều file; xếp thứ tự theo tên file)</label>
          <input type="file" id="lms-files" name="files" multiple accept="video/*,.mp4,.m4v,.mov,.mkv,.webm,.avi">
          <div class="field-note">Lời giảng được chuyển thành chữ bằng Whisper (bài giảng LMS thường không có phụ đề).</div>
          <label for="lms-links">...hoặc link tải trực tiếp file video (mỗi dòng một link)</label>
          <textarea id="lms-links" name="links" placeholder="https://.../bai-01.mp4"></textarea>
          <div class="field-note">Link cần đăng nhập LMS sẽ không tải được — hãy tải file về rồi chọn ở trên.</div>
          <label for="lms-title">Tên chuỗi (không bắt buộc)</label>
          <input type="text" id="lms-title" name="title" placeholder="Ví dụ: Học máy — Học kỳ 1">
          <div class="row" style="margin-top:14px"><button class="primary" type="submit">${ic("upload")} Tải lên và xử lý</button>
          <span class="muted small" id="lmsmsg" role="status" aria-live="polite"></span></div>
        </form>
      </section>
    </div>`;
  document.getElementById("jump-new").onclick = () => document.getElementById("new")?.scrollIntoView({ behavior: "smooth", block: "start" });
  document.getElementById("src-seg").addEventListener("click", e => {
    const b = e.target.closest("[data-pane]"); if (!b) return;
    e.currentTarget.querySelectorAll("[data-pane]").forEach(x => { const on = x === b; x.classList.toggle("active", on); x.setAttribute("aria-selected", on ? "true" : "false"); });
    document.querySelectorAll(".pane").forEach(p => (p.hidden = p.dataset.pane !== b.dataset.pane));
  });
  document.getElementById("addlms").onsubmit = e => { e.preventDefault(); submitLms(e.target, null, "lmsmsg"); };
  document.getElementById("add").onsubmit = async e => {
    e.preventDefault();
    const f = e.target, btn = f.querySelector("button");
    const urls = f.urls.value.split(/\s+/).map(u => u.trim()).filter(Boolean);
    setBusy(btn, true, "Đang đọc danh sách..."); document.getElementById("addmsg").textContent = "";
    try {
      const s = await api("/series", { method: "POST", body: { urls, title: f.title.value.trim() || null } });
      location.hash = `#/series/${s.id}`;
    } catch (err) { toast(err.message); setBusy(btn, false); }
  };
}

// Shared by the home page (new series) and the series page (append to seriesId).
async function submitLms(form, seriesId, msgId) {
  const btn = form.querySelector("button[type=submit]"), msg = document.getElementById(msgId);
  const files = [...(form.elements.files?.files || [])];
  const links = (form.elements.links?.value || "").split(/\s+/).map(u => u.trim()).filter(Boolean);
  const title = form.elements.title?.value.trim() || "";
  if (!files.length && !links.length) { toast("Chọn file video hoặc dán link"); return; }
  setBusy(btn, true);
  try {
    let sid = seriesId;
    if (files.length) {
      const fd = new FormData();
      files.forEach(f => fd.append("files", f));
      if (title) fd.append("title", title);
      if (sid) fd.append("series_id", sid);
      const mb = files.reduce((a, f) => a + f.size, 0) / 1048576;
      const s = await upload("/series/upload", fd, p => {
        msg.textContent = p < 1 ? `Đang tải lên ${Math.round(p * 100)}% (${mb.toFixed(0)} MB)...` : "Đang kiểm tra file...";
      });
      sid = s.id;
    }
    if (links.length) {
      msg.textContent = "Đang thêm link...";
      const s = await api("/series/links", { method: "POST", body: { urls: links, title: title || null, series_id: sid } });
      sid = s.id;
    }
    if (seriesId) { toast("Đã thêm video, đang xử lý"); route(); }
    else location.hash = `#/series/${sid}`;
  } catch (err) { toast(err.message); msg.textContent = ""; setBusy(btn, false); }
}

async function pageSeries(id) {
  const s = await api(`/series/${id}`);
  $app.innerHTML = `
    <div class="breadcrumb"><a href="#/">${ic("back")} Tất cả bài giảng</a></div>
    <header class="page-head">
      <div class="page-title"><h1>${esc(s.title)}</h1>
        <div class="row">
          <span class="badge plain">${s.video_count} video</span>
          ${s.completed ? `<span class="badge ok">${s.completed} xong</span>` : ""}
          ${s.failed ? `<span class="badge bad">${s.failed} lỗi</span>` : ""}
        </div></div>
      <div class="spacer"></div>
      <button id="del" class="btn danger" type="button">${ic("trash")} Xoá chuỗi</button>
    </header>
    <div class="grid cols-2">
      <section>
        <div class="card search-card" style="margin-bottom:16px">
          <form id="search" class="search-box" role="search">
            <div class="search-field">${ic("search")}<input type="search" name="q" placeholder="Tìm trong cả chuỗi (transcript + chữ trên slide)" aria-label="Tìm trong chuỗi bài giảng"></div>
            <button type="submit">Tìm</button>
          </form>
          <div id="results" aria-live="polite"></div>
        </div>
        <div class="list" id="videos"></div>
      </section>
      <section class="card">${chatShell()}</section>
    </div>
    ${s.videos.some(isFile) ? `<section class="card" style="margin-top:18px"><div class="section-head"><span class="ico sm">${ic("upload")}</span><h2>Thêm video LMS vào chuỗi</h2></div>
      <form id="addlms" class="row nowrap"><input type="file" name="files" multiple accept="video/*,.mp4,.m4v,.mov,.mkv,.webm,.avi" style="flex:1" aria-label="Chọn file video">
      <button class="primary" type="submit">Tải lên</button><span class="muted small" id="lmsmsg" role="status" aria-live="polite"></span></form></section>` : ""}`;
  document.getElementById("addlms")?.addEventListener("submit", e => { e.preventDefault(); submitLms(e.target, id, "lmsmsg"); });
  document.getElementById("del").onclick = async () => {
    if (!confirm("Xoá chuỗi này cùng toàn bộ ghi chú, slide và lịch sử chat?")) return;
    await api(`/series/${id}`, { method: "DELETE" }); location.hash = "#/";
  };
  document.getElementById("search").onsubmit = async e => {
    e.preventDefault();
    const q = e.target.q.value.trim(); if (!q) return;
    const box = document.getElementById("results");
    box.innerHTML = `<div class="skel box" style="margin-top:12px"></div>`;
    try {
      const r = await api(`/series/${id}/search`, { method: "POST", body: { query: q, top_k: 10 } });
      box.innerHTML = r.results.length
        ? `<div style="margin-top:12px">${evidenceList(r.results)}</div>`
        : emptyState("search", "Không tìm thấy kết quả", "Thử từ khoá khác, hoặc kiểm tra video đã xử lý xong.");
    } catch (err) { box.innerHTML = `<div class="err small" style="margin-top:12px">${esc(err.message)}</div>`; }
  };
  const renderVideos = vids => {
    document.getElementById("videos").innerHTML = vids.length ? vids.map(v => `
      <div class="item">
        <div class="thumb-wrap">
          <img class="thumb" src="${esc(thumbOf(v))}" alt="" loading="lazy">
          <span class="pos-badge">Bài ${v.position + 1}</span>
          ${v.status === "COMPLETED" ? `<span class="play">${ic("play")}</span>` : ""}
        </div>
        <div class="grow">
          <div class="row"><span class="muted small">Bài ${v.position + 1}</span>${statusBadge(v)}</div>
          <div class="title">${v.status === "COMPLETED" ? `<a href="#/video/${v.id}">${esc(v.title || v.youtube_id)}</a>` : esc(v.title || v.youtube_id)}</div>
          <div class="muted small">${esc([v.channel, v.duration && fmt(v.duration), isFile(v) && "video LMS",
            v.transcript_source && "transcript: " + v.transcript_source].filter(Boolean).join(" · "))}</div>
          ${v.status !== "COMPLETED" && v.status !== "FAILED" ? `<div class="progress"><div style="width:${v.progress}%"></div></div>` : ""}
          ${v.error_message ? `<div class="err small">${esc(v.error_message)}</div>` : ""}
          ${v.warning ? `<div class="warn small">${esc(v.warning)}</div>` : ""}
        </div>
        ${v.status === "FAILED" || v.status === "COMPLETED" ? `<button class="icon-btn" data-reprocess="${v.id}" title="Xử lý lại" aria-label="Xử lý lại video">${ic("refresh")}</button>`
          : v.status === "PENDING" ? `<button class="btn" data-reprocess="${v.id}" title="Bắt đầu xử lý video này">${ic("play")} Xử lý</button>` : ""}
      </div>`).join("") : emptyState("inbox", "Chưa có video", "Video sẽ xuất hiện ở đây sau khi bạn thêm chuỗi.");
  };
  renderVideos(s.videos);
  document.getElementById("videos").onclick = async e => {
    const b = e.target.closest("[data-reprocess]"); if (!b) return;
    await api(`/videos/${b.dataset.reprocess}/reprocess`, { method: "POST" }); toast("Đã xếp hàng xử lý");
    await refresh();
    if (!pollTimer) pollTimer = setInterval(refresh, 3000);
  };
  const refresh = async () => {
    const cur = await api(`/series/${id}`);
    renderVideos(cur.videos);
    if (cur.videos.every(v => ["COMPLETED", "FAILED"].includes(v.status))) stopPolling();
  };
  if (s.videos.some(v => !["COMPLETED", "FAILED"].includes(v.status))) pollTimer = setInterval(refresh, 3000);
  await initChat(id, null);
}

async function pageVideo(id, startAt) {
  const v = await api(`/videos/${id}`);
  $app.innerHTML = `
    <div class="breadcrumb"><a href="#/series/${v.series_id}">${ic("back")} Về chuỗi bài giảng</a></div>
    <div class="grid cols-2" style="margin-top:4px">
      <section>
        <div class="player">${isFile(v) ? `<video id="lv" controls preload="metadata" src="${esc(v.media_url || "")}"></video>` : `<div id="yt"></div>`}</div>
        <div class="video-head">
          <h1>Bài ${v.position + 1}: ${esc(v.title || v.youtube_id)}</h1>
          <div class="meta">${esc(v.channel || (isFile(v) ? "Video LMS" : ""))}${v.duration ? " · " + fmt(v.duration) : ""}
            ${v.url ? ` · <a href="${esc(v.url)}" target="_blank" rel="noopener">${isFile(v) ? "Mở file video ↗" : "Mở trên YouTube ↗"}</a>` : ""}</div>
          ${v.warning ? `<div class="warn small">${esc(v.warning)}</div>` : ""}
        </div>
        <div class="tabs" role="tablist">
          <button type="button" data-tab="notes" class="active" role="tab" aria-selected="true">Ghi chú kiến thức</button>
          <button type="button" data-tab="frames" role="tab" aria-selected="false">Slide (${v.frames.length})</button>
          <button type="button" data-tab="transcript" role="tab" aria-selected="false">Transcript</button>
        </div>
        <div id="tab"></div>
      </section>
      <section class="card">${chatShell()}</section>
    </div>`;
  const tabs = {
    notes: () => {
      const n = v.notes;
      if (!n) return emptyState("book", "Chưa có ghi chú", "Video này chưa được viết ghi chú kiến thức.");
      return `<div class="card" style="margin-bottom:14px"><p class="text-soft" style="margin:0">${esc(n.summary)}</p></div>` + n.topics.map(t => `
        <h3>${esc(t.title)}</h3>
        <div class="card">${t.points.map((p, i) => {
          const f = p.citations.find(c => c.frame_url);
          return `<div class="point"><div class="row top nowrap" style="gap:12px">
            <span class="idx">${i + 1}</span>
            <div class="grow"><div>${esc(p.text)}</div><div class="cites">${p.citations.map(c => citeChip(c)).join("")}</div></div>
            ${f ? `<img class="frame-thumb" src="${esc(f.frame_url)}" data-zoom="${esc(f.frame_url)}" alt="Slide tại ${esc(f.label || "")}">` : ""}
          </div></div>`;
        }).join("")}</div>`).join("")
        + (n.dropped_uncited_points ? `<p class="muted small">Đã bỏ ${n.dropped_uncited_points} ý không có trích dẫn hợp lệ.</p>` : "");
    },
    frames: () => v.frames.length ? `<div class="frames">${v.frames.map(f => `
        <figure><img src="${esc(f.url)}" data-zoom="${esc(f.url)}" alt="Slide ${esc(f.label)}" loading="lazy">
        <figcaption><button class="chip" data-video="${v.id}" data-t="${f.timestamp}">${f.label}</button>
          ${f.has_content === false ? `<span class="badge" title="Model đánh giá khung hình này không chứa kiến thức của bài (nhân vật minh hoạ, màn chuyển, quảng cáo...), nên không dùng làm ảnh trích dẫn">ngoài nội dung bài</span>` : ""}
          <span class="muted">${esc(f.summary || "")}</span></figcaption></figure>`).join("")}</div>`
      : emptyState("film", "Không có slide", "Phần hình ảnh bị bỏ qua hoặc video không có slide."),
    transcript: () => v.transcript.length ? `<div class="card transcript">${v.transcript.map(c => `
        <p><button class="chip" data-video="${v.id}" data-t="${c.start}">${c.label}</button> <span class="grow">${esc(c.text)}</span></p>`).join("")}</div>`
      : emptyState("book", "Chưa có transcript", "Video này chưa được chuyển thành văn bản."),
  };
  const show = name => {
    document.querySelectorAll(".tabs button").forEach(b => {
      const on = b.dataset.tab === name;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.getElementById("tab").innerHTML = tabs[name]();
  };
  document.querySelector(".tabs").onclick = e => { const b = e.target.closest("[data-tab]"); if (b) show(b.dataset.tab); };
  show("notes");
  mountPlayer(v, startAt);
  await initChat(v.series_id, v.id);
}

function mountPlayer(v, startAt) {
  playerVideoId = v.id; player = null;
  if (isFile(v)) {  // HTML5 player over the stored file; same seekTo/playVideo shape as the YouTube player
    const el = document.getElementById("lv");
    player = { seekTo: t => { el.currentTime = t; }, playVideo: () => el.play().catch(() => {}) };
    if (startAt) el.addEventListener("loadedmetadata", () => { el.currentTime = startAt; }, { once: true });
    return;
  }
  const make = () => {
    player = new YT.Player("yt", { videoId: v.youtube_id, playerVars: { start: Math.floor(startAt || 0), rel: 0 },
      events: { onReady: () => { if (startAt) player.seekTo(startAt, true); } } });
  };
  if (window.YT && YT.Player) make();
  else window.onYouTubeIframeAPIReady = make;
}

// ---------- chat ----------
function chatShell() {
  return `<div class="chat">
    <div class="chat-head"><span class="ico sm">${ic("chat")}</span><h2>Hỏi đáp</h2>
      <div class="spacer"></div>
      <label class="small muted row" id="scopewrap" hidden style="margin:0;gap:6px"><input type="checkbox" id="scope"> chỉ bài này</label>
      <button id="newchat" class="btn ghost" type="button">Mới</button></div>
    <div class="msgs" id="msgs"></div>
    <form id="ask" autocomplete="off">
      <div class="search-field"><input type="text" name="q" placeholder="Hỏi về nội dung bài giảng..." autocomplete="off" aria-label="Câu hỏi"></div>
      <button class="primary" type="submit">${ic("chat")} Gửi</button></form></div>`;
}

async function initChat(seriesId, videoId) {
  const key = `chat-session-${seriesId}`;
  let sessionId = Number(localStorage.getItem(key)) || null;
  const msgs = document.getElementById("msgs");
  if (videoId) document.getElementById("scopewrap").hidden = false;
  const render = list => {
    msgs.innerHTML = list.length ? list.map(m => m.role === "user"
      ? `<div class="msg user">${esc(m.content)}</div>`
      : `<div class="msg assistant">${renderAnswer(m.content, m.citations)}${evidenceList(m.citations)}</div>`).join("")
      : emptyState("chat", "Hỏi bất cứ điều gì về chuỗi bài giảng", "Mỗi câu trả lời kèm trích dẫn tới đúng giây trong video.");
    msgs.scrollTop = msgs.scrollHeight;
  };
  let history = [];
  if (sessionId) {
    try { history = (await api(`/chat/sessions/${sessionId}`)).messages; } catch { sessionId = null; }
  }
  render(history);
  const ensureSession = async () => {
    if (!sessionId) { sessionId = (await api(`/series/${seriesId}/chat/sessions`, { method: "POST" })).id; localStorage.setItem(key, sessionId); }
    return sessionId;
  };
  document.getElementById("newchat").onclick = () => { localStorage.removeItem(key); sessionId = null; history = []; render(history); };
  document.getElementById("ask").onsubmit = async e => {
    e.preventDefault();
    const input = e.target.q, q = input.value.trim(); if (!q) return;
    const btn = e.target.querySelector("button"); setBusy(btn, true, "Đang gửi...");
    input.value = "";
    history.push({ role: "user", content: q });
    render(history);
    msgs.insertAdjacentHTML("beforeend", `<div class="msg assistant" id="thinking"><span class="typing"><span class="dots"><i></i><i></i><i></i></span> Đang tìm trong bài giảng...</span></div>`);
    msgs.scrollTop = msgs.scrollHeight;
    try {
      const sid = await ensureSession();
      const only = videoId && document.getElementById("scope").checked ? [videoId] : null;
      const answer = await api(`/chat/sessions/${sid}/messages`, { method: "POST", body: { question: q, video_ids: only } });
      history.push(answer);
    } catch (err) { history.push({ role: "assistant", content: "Lỗi: " + err.message, citations: [] }); }
    setBusy(btn, false); render(history); input.focus();
  };
}

// ---------- router ----------
async function route() {
  stopPolling();
  const [path, query] = location.hash.slice(1).split("?");
  const params = new URLSearchParams(query || "");
  const parts = (path || "/").split("/").filter(Boolean);
  $app.innerHTML = skeletonPage();
  try {
    if (parts[0] === "series" && parts[1]) await pageSeries(Number(parts[1]));
    else if (parts[0] === "video" && parts[1]) await pageVideo(Number(parts[1]), Number(params.get("t")) || 0);
    else await pageHome();
  } catch (err) { $app.innerHTML = errorCard(err.message); }
}
window.addEventListener("hashchange", route);
api("/health").then(h => {
  document.getElementById("health").textContent =
    `${h.llm_provider === "fake" ? "Chế độ giả (không gọi model)" : h.llm_model}${!h.api_key_configured ? ` · thiếu API key (${h.llm_provider})` : ""}`;
}).catch(() => {
  const el = document.getElementById("health");
  if (el) { el.textContent = "Không kết nối được máy chủ"; el.classList.add("offline"); }
});
route();
