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
  d.innerHTML = `<img src="${esc(src)}" alt="">`;
  d.onclick = () => d.remove();
  document.body.appendChild(d);
}
function statusBadge(v) {
  const cls = v.status === "COMPLETED" ? "ok" : v.status === "FAILED" ? "bad" : "";
  return `<span class="badge ${cls}">${esc(STATUS_VI[v.status] || v.status)}</span>`;
}
function stopPolling() { if (pollTimer) clearInterval(pollTimer); pollTimer = null; }

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
      ${c.frame_url ? `<img src="${esc(c.frame_url)}" data-zoom="${esc(c.frame_url)}" alt="">` : ""}
      <div>${citeChip(c)} ${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener" class="small">${isFile(c) ? "Mở video ↗" : "YouTube ↗"}</a>` : ""}
        <div class="muted">${esc((c.quote || "").slice(0, 160))}${(c.quote || "").length > 160 ? "…" : ""}</div></div>
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

// ---------- pages ----------
async function pageHome() {
  const [stats, series] = await Promise.all([api("/stats"), api("/series")]);
  const s = stats.videos_by_status || {};
  const processing = stats.videos - (s.COMPLETED || 0) - (s.FAILED || 0);
  $app.innerHTML = `
    <div class="stats">
      ${[["Chuỗi bài giảng", stats.series], ["Video", stats.videos], ["Đã xử lý", s.COMPLETED || 0],
         ["Đang xử lý", processing], ["Lỗi", s.FAILED || 0], ["Slide đã cắt", stats.frames],
         ["Đoạn transcript", stats.transcript_chunks]]
        .map(([k, v]) => `<div class="card stat"><div class="muted small">${k}</div><div class="num">${v}</div></div>`).join("")}
    </div>
    <div class="grid cols-2">
      <section class="card">
        <h2>Chuỗi bài giảng</h2>
        <div class="list">${series.length ? series.map(x => `
          <a class="item" href="#/series/${x.id}" style="text-decoration:none;color:inherit">
            <div class="grow"><div class="title">${esc(x.title)}</div>
            <div class="muted small">${x.completed}/${x.video_count} video xong${x.failed ? ` · <span class="err">${x.failed} lỗi</span>` : ""}</div></div>
          </a>`).join("") : `<div class="empty">Chưa có chuỗi nào. Thêm playlist ở bên phải.</div>`}</div>
      </section>
      <section class="card">
        <h2>Thêm chuỗi bài giảng</h2>
        <form id="add">
          <label class="small muted">Link playlist YouTube, hoặc nhiều link video (mỗi dòng một link)</label>
          <textarea name="urls" required placeholder="https://www.youtube.com/playlist?list=..."></textarea>
          <label class="small muted">Tên chuỗi (không bắt buộc)</label>
          <input type="text" name="title" placeholder="Lấy theo tên playlist nếu để trống">
          <div class="row" style="margin-top:10px"><button class="primary" type="submit">Bắt đầu xử lý</button>
          <span class="muted small" id="addmsg"></span></div>
        </form>
        <h2 style="margin-top:22px">Video bài giảng LMS</h2>
        <form id="addlms">
          <label class="small muted">File video tải từ LMS (chọn nhiều file; xếp thứ tự theo tên file). Lời giảng được chuyển thành chữ bằng Whisper.</label>
          <input type="file" name="files" multiple accept="video/*,.mp4,.m4v,.mov,.mkv,.webm,.avi">
          <label class="small muted">…hoặc link tải trực tiếp file video (mỗi dòng một link; link cần đăng nhập LMS sẽ không tải được)</label>
          <textarea name="links" placeholder="https://.../bai-01.mp4"></textarea>
          <label class="small muted">Tên chuỗi (không bắt buộc)</label>
          <input type="text" name="title" placeholder="Ví dụ: Học máy — Học kỳ 1">
          <div class="row" style="margin-top:10px"><button class="primary" type="submit">Tải lên và xử lý</button>
          <span class="muted small" id="lmsmsg"></span></div>
        </form>
      </section>
    </div>`;
  document.getElementById("addlms").onsubmit = e => { e.preventDefault(); submitLms(e.target, null, "lmsmsg"); };
  document.getElementById("add").onsubmit = async e => {
    e.preventDefault();
    const f = e.target, btn = f.querySelector("button");
    const urls = f.urls.value.split(/\s+/).map(u => u.trim()).filter(Boolean);
    btn.disabled = true; document.getElementById("addmsg").textContent = "Đang đọc danh sách video…";
    try {
      const s = await api("/series", { method: "POST", body: { urls, title: f.title.value.trim() || null } });
      location.hash = `#/series/${s.id}`;
    } catch (err) { toast(err.message); btn.disabled = false; document.getElementById("addmsg").textContent = ""; }
  };
}

// Shared by the home page (new series) and the series page (append to seriesId).
async function submitLms(form, seriesId, msgId) {
  const btn = form.querySelector("button[type=submit]"), msg = document.getElementById(msgId);
  const files = [...(form.elements.files?.files || [])];
  const links = (form.elements.links?.value || "").split(/\s+/).map(u => u.trim()).filter(Boolean);
  const title = form.elements.title?.value.trim() || "";
  if (!files.length && !links.length) { toast("Chọn file video hoặc dán link"); return; }
  btn.disabled = true;
  try {
    let sid = seriesId;
    if (files.length) {
      const fd = new FormData();
      files.forEach(f => fd.append("files", f));
      if (title) fd.append("title", title);
      if (sid) fd.append("series_id", sid);
      const mb = files.reduce((a, f) => a + f.size, 0) / 1048576;
      const s = await upload("/series/upload", fd, p => {
        msg.textContent = p < 1 ? `Đang tải lên ${Math.round(p * 100)}% (${mb.toFixed(0)} MB)…` : "Đang kiểm tra file…";
      });
      sid = s.id;
    }
    if (links.length) {
      msg.textContent = "Đang thêm link…";
      const s = await api("/series/links", { method: "POST", body: { urls: links, title: title || null, series_id: sid } });
      sid = s.id;
    }
    if (seriesId) { toast("Đã thêm video, đang xử lý"); route(); }
    else location.hash = `#/series/${sid}`;
  } catch (err) { toast(err.message); msg.textContent = ""; btn.disabled = false; }
}

async function pageSeries(id) {
  const s = await api(`/series/${id}`);
  $app.innerHTML = `
    <div class="row"><a href="#/">← Tất cả</a></div>
    <div class="row" style="margin:8px 0 16px"><div><h1>${esc(s.title)}</h1>
      <div class="muted small">${s.video_count} video</div></div><div class="spacer"></div>
      <button id="del">Xoá chuỗi</button></div>
    <div class="grid cols-2">
      <section>
        <div class="card" style="margin-bottom:16px">
          <form id="search" class="row"><input type="text" name="q" placeholder="Tìm trong cả chuỗi bài giảng (transcript + chữ trên slide)" style="flex:1">
          <button>Tìm</button></form>
          <div id="results"></div>
        </div>
        <div class="list" id="videos"></div>
      </section>
      <section class="card">${chatShell()}</section>
    </div>
    ${s.videos.some(isFile) ? `<section class="card" style="margin-top:16px"><h2>Thêm video LMS vào chuỗi</h2>
      <form id="addlms" class="row"><input type="file" name="files" multiple accept="video/*,.mp4,.m4v,.mov,.mkv,.webm,.avi" style="flex:1">
      <button class="primary" type="submit">Tải lên</button><span class="muted small" id="lmsmsg"></span></form></section>` : ""}`;
  document.getElementById("addlms")?.addEventListener("submit", e => { e.preventDefault(); submitLms(e.target, id, "lmsmsg"); });
  document.getElementById("del").onclick = async () => {
    if (!confirm("Xoá chuỗi này cùng toàn bộ ghi chú, slide và lịch sử chat?")) return;
    await api(`/series/${id}`, { method: "DELETE" }); location.hash = "#/";
  };
  document.getElementById("search").onsubmit = async e => {
    e.preventDefault();
    const q = e.target.q.value.trim(); if (!q) return;
    const r = await api(`/series/${id}/search`, { method: "POST", body: { query: q, top_k: 10 } });
    document.getElementById("results").innerHTML = r.results.length
      ? `<div style="margin-top:10px">${evidenceList(r.results)}</div>` : `<div class="empty">Không thấy kết quả.</div>`;
  };
  const renderVideos = vids => {
    document.getElementById("videos").innerHTML = vids.map(v => `
      <div class="item">
        <img class="thumb" src="${esc(thumbOf(v))}" alt="">
        <div class="grow">
          <div class="row"><span class="muted small">Bài ${v.position + 1}</span>${statusBadge(v)}</div>
          <div class="title">${v.status === "COMPLETED" ? `<a href="#/video/${v.id}">${esc(v.title || v.youtube_id)}</a>` : esc(v.title || v.youtube_id)}</div>
          <div class="muted small">${esc([v.channel, v.duration && fmt(v.duration), isFile(v) && "video LMS",
            v.transcript_source && "transcript: " + v.transcript_source].filter(Boolean).join(" · "))}</div>
          ${v.status !== "COMPLETED" && v.status !== "FAILED" ? `<div class="progress"><div style="width:${v.progress}%"></div></div>` : ""}
          ${v.error_message ? `<div class="err small">${esc(v.error_message)}</div>` : ""}
          ${v.warning ? `<div class="warn small">${esc(v.warning)}</div>` : ""}
        </div>
        ${v.status === "FAILED" || v.status === "COMPLETED" ? `<button data-reprocess="${v.id}" title="Xử lý lại">↻</button>`
          : v.status === "PENDING" ? `<button data-reprocess="${v.id}" title="Bắt đầu xử lý video này">▶ Xử lý</button>` : ""}
      </div>`).join("");
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
    <div class="row"><a href="#/series/${v.series_id}">← Về chuỗi bài giảng</a></div>
    <div class="grid cols-2" style="margin-top:12px">
      <section>
        <div class="player">${isFile(v) ? `<video id="lv" controls preload="metadata" src="${esc(v.media_url || "")}"></video>` : `<div id="yt"></div>`}</div>
        <h1 style="margin-top:12px">Bài ${v.position + 1}: ${esc(v.title || v.youtube_id)}</h1>
        <div class="muted small">${esc(v.channel || (isFile(v) ? "Video LMS" : ""))}${v.duration ? " · " + fmt(v.duration) : ""}
          ${v.url ? ` · <a href="${esc(v.url)}" target="_blank" rel="noopener">${isFile(v) ? "Mở file video ↗" : "Mở trên YouTube ↗"}</a>` : ""}</div>
        ${v.warning ? `<div class="warn small">${esc(v.warning)}</div>` : ""}
        <div class="tabs"><button data-tab="notes" class="active">Ghi chú kiến thức</button>
          <button data-tab="frames">Slide (${v.frames.length})</button><button data-tab="transcript">Transcript</button></div>
        <div id="tab"></div>
      </section>
      <section class="card">${chatShell()}</section>
    </div>`;
  const tabs = {
    notes: () => {
      const n = v.notes;
      if (!n) return `<div class="empty">Chưa có ghi chú.</div>`;
      return `<div class="card"><p>${esc(n.summary)}</p></div>` + n.topics.map(t => `
        <h3>${esc(t.title)}</h3>
        <div class="card">${t.points.map(p => {
          const f = p.citations.find(c => c.frame_url);
          return `<div class="point"><div class="row" style="align-items:flex-start;flex-wrap:nowrap">
            <div class="grow"><div>${esc(p.text)}</div><div class="cites">${p.citations.map(c => citeChip(c)).join("")}</div></div>
            ${f ? `<img class="frame-thumb" src="${esc(f.frame_url)}" data-zoom="${esc(f.frame_url)}" alt="">` : ""}
          </div></div>`;
        }).join("")}</div>`).join("")
        + (n.dropped_uncited_points ? `<p class="muted small">Đã bỏ ${n.dropped_uncited_points} ý không có trích dẫn hợp lệ.</p>` : "");
    },
    frames: () => v.frames.length ? `<div class="frames">${v.frames.map(f => `
        <figure><img src="${esc(f.url)}" data-zoom="${esc(f.url)}" alt="">
        <figcaption><button class="chip" data-video="${v.id}" data-t="${f.timestamp}">${f.label}</button>
          ${f.has_content === false ? `<span class="badge" title="Model đánh giá khung hình này không chứa kiến thức của bài (nhân vật minh hoạ, màn chuyển, quảng cáo…), nên không dùng làm ảnh trích dẫn">ngoài nội dung bài</span>` : ""}
          ${esc(f.summary || "")}</figcaption></figure>`).join("")}</div>`
      : `<div class="empty">Không có slide (phần hình ảnh bị bỏ qua hoặc video không có slide).</div>`,
    transcript: () => `<div class="card transcript">${v.transcript.map(c => `
        <p><button class="chip" data-video="${v.id}" data-t="${c.start}">${c.label}</button> ${esc(c.text)}</p>`).join("")}</div>`,
  };
  const show = name => {
    document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
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
  return `<div class="chat"><div class="row"><h2 style="margin:0">Hỏi đáp</h2><div class="spacer"></div>
    <label class="small muted" id="scopewrap" hidden><input type="checkbox" id="scope"> chỉ bài này</label>
    <button id="newchat" class="small">Mới</button></div>
    <div class="msgs" id="msgs"></div>
    <form id="ask"><input type="text" name="q" placeholder="Hỏi về nội dung bài giảng…" autocomplete="off" style="flex:1">
    <button class="primary">Gửi</button></form></div>`;
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
      : `<div class="empty">Hỏi bất cứ điều gì về chuỗi bài giảng. Mỗi câu trả lời kèm trích dẫn tới đúng giây trong video.</div>`;
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
    const btn = e.target.querySelector("button"); btn.disabled = true; input.value = "";
    history.push({ role: "user", content: q });
    render(history);
    msgs.insertAdjacentHTML("beforeend", `<div class="msg assistant muted" id="thinking">Đang tìm trong bài giảng…</div>`);
    msgs.scrollTop = msgs.scrollHeight;
    try {
      const sid = await ensureSession();
      const only = videoId && document.getElementById("scope").checked ? [videoId] : null;
      const answer = await api(`/chat/sessions/${sid}/messages`, { method: "POST", body: { question: q, video_ids: only } });
      history.push(answer);
    } catch (err) { history.push({ role: "assistant", content: "Lỗi: " + err.message, citations: [] }); }
    btn.disabled = false; render(history); input.focus();
  };
}

// ---------- router ----------
async function route() {
  stopPolling();
  const [path, query] = location.hash.slice(1).split("?");
  const params = new URLSearchParams(query || "");
  const parts = (path || "/").split("/").filter(Boolean);
  try {
    if (parts[0] === "series" && parts[1]) await pageSeries(Number(parts[1]));
    else if (parts[0] === "video" && parts[1]) await pageVideo(Number(parts[1]), Number(params.get("t")) || 0);
    else await pageHome();
  } catch (err) { $app.innerHTML = `<div class="card err">${esc(err.message)}</div>`; }
}
window.addEventListener("hashchange", route);
api("/health").then(h => {
  document.getElementById("health").textContent =
    `${h.llm_provider === "fake" ? "Chế độ giả (không gọi model)" : h.llm_model}${!h.api_key_configured ? ` · thiếu API key (${h.llm_provider})` : ""}`;
}).catch(() => {});
route();
