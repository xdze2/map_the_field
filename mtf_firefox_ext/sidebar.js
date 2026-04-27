const FLASK = "http://localhost:5001";

const RANK_LABELS = {
  1: "Hell no",
  2: "Not interested",
  3: "What?",
  4: "Boring",
  5: "Interested",
  6: "Excited",
};

// In the extension, icons are local files; in the web UI they're served from Flask
const _isExtension = typeof browser !== "undefined" && browser.runtime && browser.runtime.getURL;
function _iconUrl(filename) {
  return _isExtension ? filename : `/assets/${filename}`;
}
const RANK_ICONS = {
  1: _iconUrl("1_nope.png"),
  2: _iconUrl("2_skip_it.png"),
  3: _iconUrl("3_what.png"),
  4: _iconUrl("4_keep_it.png"),
  5: _iconUrl("5_interested.png"),
  6: _iconUrl("6_excited.png"),
};

let currentNodeId = null;
let currentTab = null;
let easyMDE = null;   // EasyMDE instance, lives for the duration of a node view
let nodeList = [];
let currentIndex = -1;

// ── Tab tracking ──────────────────────────────────────────────────────────────
// Only available inside the Firefox extension context

function updateCurrentTab() {
  if (typeof browser === "undefined") return;
  browser.tabs.query({ active: true }).then(tabs => {
    const tab = tabs.find(t => t.url && !t.url.startsWith("about:") && !t.url.startsWith("moz-extension:"));
    if (tab) currentTab = tab;
  });
}

if (typeof browser !== "undefined") {
  updateCurrentTab();
  browser.tabs.onActivated.addListener(updateCurrentTab);
  browser.tabs.onUpdated.addListener((_id, change) => { if (change.url) updateCurrentTab(); });
}

// ── Flask health ──────────────────────────────────────────────────────────────

function setFlaskStatus(ok) {
  const el = document.getElementById("flask-status");
  el.textContent = "●";
  el.className = ok ? "" : "err";
}

async function checkFlask() {
  try {
    const r = await fetch(`${FLASK}/nodes?sort=unranked`);
    setFlaskStatus(r.ok);
    return r.ok;
  } catch {
    setFlaskStatus(false);
    return false;
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.background = isError ? "#3a1a1a" : "#1a3a2a";
  t.style.borderColor = isError ? "#6a2a2a" : "#2a6a3a";
  t.style.color = isError ? "#cc8888" : "#88cc88";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2000);
}

// ── View switching ────────────────────────────────────────────────────────────

function destroyEditor() {
  if (easyMDE) {
    easyMDE.toTextArea();
    easyMDE = null;
  }
}

function showListView() {
  destroyEditor();
  document.getElementById("list-view").style.display = "block";
  document.getElementById("node-view").style.display = "none";
  document.getElementById("node-bottom").style.display = "none";
  document.getElementById("list-toolbar").style.display = "flex";
  document.getElementById("back-btn").style.display = "none";
  document.getElementById("capture-btn").style.display = "none";
  const title = document.getElementById("topbar-title");
  title.textContent = "Map the Field";
  title.className = "list-title";
  currentNodeId = null;
}

function showNodeView(nodeId) {
  document.getElementById("list-view").style.display = "none";
  document.getElementById("node-view").style.display = "block";
  document.getElementById("node-bottom").style.display = "flex";
  document.getElementById("list-toolbar").style.display = "none";
  document.getElementById("back-btn").style.display = "block";
  document.getElementById("capture-btn").style.display = "block";
  const title = document.getElementById("topbar-title");
  title.textContent = nodeId;
  title.className = "";
  updateNavButtons();
}

function updateNavButtons() {
  const prev = document.getElementById("prev-btn");
  const next = document.getElementById("next-btn");
  const counter = document.getElementById("nav-counter");
  if (!prev || !next) return;
  prev.disabled = currentIndex <= 0;
  next.disabled = currentIndex < 0 || currentIndex >= nodeList.length - 1;
  counter.textContent = nodeList.length > 0 ? `${currentIndex + 1}/${nodeList.length}` : "";
}

// ── List view ─────────────────────────────────────────────────────────────────

async function loadNodes(sort = "unranked") {
  const container = document.getElementById("list-view");
  try {
    const r = await fetch(`${FLASK}/nodes?sort=${sort}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const nodes = await r.json();
    renderList(nodes);
  } catch (err) {
    container.innerHTML = `<div class="empty-msg">Error: ${err.message}</div>`;
  }
}

function renderList(nodes) {
  nodeList = nodes;
  const container = document.getElementById("list-view");
  container.innerHTML = "";

  document.getElementById("count").textContent =
    `${nodes.length} · ${nodes.filter(n => n.current_rank).length} ranked`;

  if (nodes.length === 0) {
    container.innerHTML = `<div class="empty-msg">No nodes found.</div>`;
    return;
  }

  const frag = document.createDocumentFragment();
  for (const node of nodes) frag.appendChild(makeRow(node));
  container.appendChild(frag);
}

function makeRow(node) {
  const row = document.createElement("div");
  row.className = "node-row";

  const rank = node.current_rank;
  const badge = document.createElement("div");
  badge.className = `rank-badge ${rank ? "rank-" + rank : "rank-none"}`;
  badge.textContent = rank || "·";
  badge.title = rank ? RANK_LABELS[rank] : "Unranked";

  const name = document.createElement("div");
  name.className = "node-name";
  name.textContent = node.name;
  name.title = node.name;

  const meta = document.createElement("div");
  meta.className = "node-meta-col";
  meta.textContent = node.updated_at ? node.updated_at.slice(0, 8) : "";

  row.appendChild(badge);
  row.appendChild(name);
  row.appendChild(meta);

  const idx = nodeList.indexOf(node);
  row.addEventListener("click", () => openNode(node.node_id, idx));
  return row;
}

// ── Node view ─────────────────────────────────────────────────────────────────

async function openNode(nodeId, idx) {
  destroyEditor();
  currentNodeId = nodeId;
  currentIndex = idx !== undefined ? idx : nodeList.findIndex(n => n.node_id === nodeId);
  showNodeView(nodeId);
  document.getElementById("node-view").innerHTML = `<div class="empty-msg">Loading…</div>`;

  try {
    const r = await fetch(`${FLASK}/nodes/${nodeId}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderNode(data);
  } catch (err) {
    document.getElementById("node-view").innerHTML =
      `<div class="empty-msg">Error: ${err.message}</div>`;
  }
}

function renderNode(data) {
  const { node_id, meta, summary_md, current_rank, triage, sources } = data;
  const container = document.getElementById("node-view");
  container.innerHTML = "";

  // ── Rank buttons (bottom bar) ──
  const rankBar = document.getElementById("rank-bar");
  rankBar.innerHTML = "";
  for (let i = 1; i <= 6; i++) {
    const btn = document.createElement("button");
    btn.className = "rank-btn" + (current_rank === i ? " active" : "");
    btn.dataset.rank = i;
    btn.title = `${i} — ${RANK_LABELS[i]}`;
    const img = document.createElement("img");
    img.src = RANK_ICONS[i];
    img.alt = RANK_LABELS[i];
    img.className = "rank-icon";
    btn.appendChild(img);
    btn.addEventListener("click", () => postRank(i, btn, rankBar));
    rankBar.appendChild(btn);
  }

  // ── Summary (EasyMDE) ──
  container.appendChild(el("div", "section-label", "Summary"));

  const textarea = document.createElement("textarea");
  textarea.id = "summary-textarea";
  textarea.value = summary_md || "";
  container.appendChild(textarea);

  const saveRow = el("div", "summary-save-row");
  const saveBtn = el("button", "summary-btn primary", "Save");
  saveRow.appendChild(saveBtn);
  container.appendChild(saveRow);

  easyMDE = new EasyMDE({
    element: textarea,
    spellChecker: false,
    autofocus: false,
    status: false,
    toolbar: ["bold", "italic", "heading", "|", "unordered-list", "ordered-list", "|", "link", "|", "preview", "side-by-side"],
    minHeight: "180px",
    initialValue: summary_md || "",
  });

  saveBtn.addEventListener("click", () => postSummary(easyMDE.value(), saveBtn));

  // ── Sources ──
  if (sources && sources.length > 0) {
    container.appendChild(el("div", "section-label", "Sources"));
    renderSources(sources, container);
  }

  // ── History ──
  renderHistorySection(triage, container);
}

function renderSources(sources, container) {
  const sourcesList = el("div", "sources-list");
  for (const s of sources) {
    const item = el("div", "source-item");
    const link = el("a", "source-url", s.url || s._file);
    if (s.url) { link.href = s.url; link.target = "_blank"; }
    item.appendChild(link);
    if (s.captured_at) item.appendChild(el("div", "", s.captured_at.slice(0, 10)));
    sourcesList.appendChild(item);
  }
  container.appendChild(sourcesList);
}

function renderHistorySection(triage, container) {
  const labelRow = el("div", "section-label-row");
  labelRow.appendChild(el("div", "section-label", "History"));
  const refreshBtn = el("button", "refresh-btn", "↻");
  refreshBtn.title = "Refresh history";
  refreshBtn.addEventListener("click", () => refreshHistory(container));
  labelRow.appendChild(refreshBtn);
  container.appendChild(labelRow);

  const histContainer = el("div", "history-container");
  container.appendChild(histContainer);
  renderHistoryEntries(triage || [], histContainer);
}

function renderHistoryEntries(triage, container) {
  container.innerHTML = "";
  if (!triage || triage.length === 0) {
    container.appendChild(el("div", "empty-msg", "No history yet."));
    return;
  }
  const hist = el("div", "history-list");
  for (const entry of [...triage].reverse()) {
    const item = el("div", "history-item");
    const top = el("div", "");
    if (entry.rank) {
      top.appendChild(el("span", "history-rank", `${entry.rank} — ${RANK_LABELS[entry.rank]}`));
      top.appendChild(document.createTextNode("  "));
    }
    top.appendChild(el("span", "history-ts", entry.timestamp || entry.ts || ""));
    item.appendChild(top);
    if (entry.note) item.appendChild(el("div", "history-note", entry.note));
    hist.appendChild(item);
  }
  container.appendChild(hist);
}

async function refreshHistory(nodeViewContainer) {
  if (!currentNodeId) return;
  const histContainer = nodeViewContainer.querySelector(".history-container");
  if (!histContainer) return;
  histContainer.innerHTML = `<div class="empty-msg" style="padding:8px">Loading…</div>`;
  try {
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/history`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderHistoryEntries(data.triage, histContainer);

    // also refresh sources section
    if (data.sources) {
      const existing = nodeViewContainer.querySelector(".sources-list");
      if (existing) {
        existing.innerHTML = "";
        renderSources(data.sources, existing.parentNode);
        existing.remove();
      }
    }

    // sync rank buttons with updated current_rank
    if (data.current_rank !== undefined) {
      const rankBar = document.getElementById("rank-bar");
      rankBar.querySelectorAll(".rank-btn").forEach(b => {
        b.classList.toggle("active", parseInt(b.dataset.rank) === data.current_rank);
      });
    }
  } catch (err) {
    histContainer.innerHTML = `<div class="empty-msg">Error: ${err.message}</div>`;
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function postRank(rank, clickedBtn, rankRow) {
  if (!currentNodeId) return;
  try {
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/rank`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rank }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    rankRow.querySelectorAll(".rank-btn").forEach(b => b.classList.remove("active"));
    clickedBtn.classList.add("active");
    toast(`Ranked: ${rank} — ${RANK_LABELS[rank]}`);
  } catch (err) {
    toast(`Rank error: ${err.message}`, true);
  }
}

async function postSummary(content, saveBtn) {
  if (!currentNodeId) return;
  const orig = saveBtn.textContent;
  saveBtn.textContent = "Saving…";
  try {
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, author: "user" }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    toast("Summary saved");
  } catch (err) {
    toast(`Save error: ${err.message}`, true);
  } finally {
    saveBtn.textContent = orig;
  }
}

async function captureCurrentTab() {
  if (!currentNodeId) return;

  // In a regular browser tab (not extension), we can't use browser.tabs API
  if (typeof browser === "undefined") {
    toast("Capture only works in the Firefox extension", true);
    return;
  }

  if (!currentTab) { toast("No active tab found", true); return; }

  const btn = document.getElementById("capture-btn");
  btn.textContent = "Capturing…";
  btn.classList.add("capturing");

  try {
    const [html] = await browser.tabs.executeScript(currentTab.id, {
      code: "document.documentElement.outerHTML"
    });
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/capture`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: currentTab.url, html }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    toast("Page captured");
  } catch (err) {
    toast(`Capture error: ${err.message}`, true);
  } finally {
    btn.textContent = "⬇ Capture";
    btn.classList.remove("capturing");
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

// ── Controls ──────────────────────────────────────────────────────────────────

document.getElementById("back-btn").addEventListener("click", () => {
  showListView();
  loadNodes(document.getElementById("sort-select").value);
});

document.getElementById("prev-btn").addEventListener("click", () => {
  if (currentIndex > 0) openNode(nodeList[currentIndex - 1].node_id, currentIndex - 1);
});

document.getElementById("next-btn").addEventListener("click", () => {
  if (currentIndex >= 0 && currentIndex < nodeList.length - 1)
    openNode(nodeList[currentIndex + 1].node_id, currentIndex + 1);
});

document.getElementById("sort-select").addEventListener("change", e => {
  loadNodes(e.target.value);
});

document.getElementById("capture-btn").addEventListener("click", captureCurrentTab);

// ── Init ──────────────────────────────────────────────────────────────────────

const titleEl = document.getElementById("topbar-title");
titleEl.className = "list-title";

checkFlask().then(ok => {
  if (ok) loadNodes("unranked");
  else {
    document.getElementById("list-view").innerHTML =
      `<div class="empty-msg">Flask not running.<br>Start: python tools/screening_app.py</div>`;
  }
});
