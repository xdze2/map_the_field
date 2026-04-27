const FLASK = "http://localhost:5001";

const RANK_LABELS = {
  1: "Hell no",
  2: "Not interested",
  3: "What?",
  4: "Boring",
  5: "Interested",
  6: "Excited",
};

let currentNodeId = null;
let currentTab = null;
let summaryEditMode = false;

// ── Tab tracking ─────────────────────────────────────────────────────────────

function updateCurrentTab() {
  browser.tabs.query({ active: true }).then(tabs => {
    const tab = tabs.find(t => t.url && !t.url.startsWith("about:") && !t.url.startsWith("moz-extension:"));
    if (tab) currentTab = tab;
  });
}

updateCurrentTab();
browser.tabs.onActivated.addListener(updateCurrentTab);
browser.tabs.onUpdated.addListener((_id, change) => { if (change.url) updateCurrentTab(); });

// ── Flask health ─────────────────────────────────────────────────────────────

function setFlaskStatus(ok) {
  const el = document.getElementById("flask-status");
  el.textContent = "●";
  el.className = ok ? "ok" : "err";
  el.title = ok ? "Flask reachable" : "Flask not reachable";
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

// ── View switching ───────────────────────────────────────────────────────────

function showListView() {
  document.getElementById("list-view").style.display = "block";
  document.getElementById("node-view").style.display = "none";
  document.getElementById("list-toolbar").style.display = "flex";
  document.getElementById("back-btn").style.display = "none";
  document.getElementById("capture-btn").style.display = "none";
  document.getElementById("topbar-title").textContent = "Map the Field";
  currentNodeId = null;
}

function showNodeView() {
  document.getElementById("list-view").style.display = "none";
  document.getElementById("node-view").style.display = "block";
  document.getElementById("list-toolbar").style.display = "none";
  document.getElementById("back-btn").style.display = "block";
  document.getElementById("capture-btn").style.display = "block";
}

// ── List view ────────────────────────────────────────────────────────────────

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

  row.addEventListener("click", () => openNode(node.node_id, node.name));
  return row;
}

// ── Node view ────────────────────────────────────────────────────────────────

async function openNode(nodeId, nodeName) {
  showNodeView();
  currentNodeId = nodeId;
  summaryEditMode = false;
  document.getElementById("topbar-title").textContent = nodeName || nodeId;
  document.getElementById("node-view").innerHTML = `<div class="empty-msg">Loading…</div>`;

  try {
    const r = await fetch(`${FLASK}/nodes/${nodeId}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    try {
      renderNode(data);
    } catch (renderErr) {
      document.getElementById("node-view").innerHTML =
        `<div class="empty-msg">Render error: ${renderErr.message}<br><pre style="font-size:10px;color:#888">${renderErr.stack}</pre></div>`;
    }
  } catch (err) {
    document.getElementById("node-view").innerHTML =
      `<div class="empty-msg">Fetch error: ${err.message}</div>`;
  }
}

function renderNode(data) {
  const { meta, summary_md, current_rank, triage, sources } = data;
  const container = document.getElementById("node-view");
  container.innerHTML = "";

  // ── Header ──
  const header = el("div", "node-header");
  header.appendChild(el("div", "node-title", meta.name));
  const submeta = [];
  if (meta.city) submeta.push(meta.city);
  if (meta.naf_label) submeta.push(meta.naf_label);
  if (meta.headcount_range) submeta.push(meta.headcount_range + " salariés");
  if (meta.identifiers?.siren) submeta.push("SIREN " + meta.identifiers.siren);
  header.appendChild(el("div", "node-submeta", submeta.join(" · ")));
  container.appendChild(header);

  // ── Rank buttons ──
  container.appendChild(el("div", "section-label", "Rank"));
  const rankRow = el("div", "rank-buttons");
  for (let i = 1; i <= 6; i++) {
    const btn = el("button", "rank-btn" + (current_rank === i ? " active" : ""), `${i}\n${RANK_LABELS[i]}`);
    btn.dataset.rank = i;
    btn.style.whiteSpace = "pre-line";
    btn.addEventListener("click", () => postRank(i, btn, rankRow));
    rankRow.appendChild(btn);
  }
  container.appendChild(rankRow);

  // ── Summary ──
  container.appendChild(el("div", "section-label", "Summary"));

  const summaryToolbar = el("div", "summary-toolbar");
  const editBtn = el("button", "summary-btn", "Edit");
  const saveBtn = el("button", "summary-btn primary", "Save");
  saveBtn.style.display = "none";
  summaryToolbar.appendChild(editBtn);
  summaryToolbar.appendChild(saveBtn);
  container.appendChild(summaryToolbar);

  const summaryBox = el("div", "summary-box");
  const rendered = el("div", "summary-rendered");
  rendered.innerHTML = renderMarkdown(summary_md);
  summaryBox.appendChild(rendered);

  const textarea = document.createElement("textarea");
  textarea.id = "summary-textarea";
  textarea.value = summary_md || "";
  textarea.style.display = "none";
  summaryBox.appendChild(textarea);
  container.appendChild(summaryBox);

  editBtn.addEventListener("click", () => {
    summaryEditMode = !summaryEditMode;
    if (summaryEditMode) {
      rendered.style.display = "none";
      textarea.style.display = "block";
      textarea.focus();
      editBtn.textContent = "Cancel";
      saveBtn.style.display = "block";
    } else {
      rendered.style.display = "block";
      textarea.style.display = "none";
      editBtn.textContent = "Edit";
      saveBtn.style.display = "none";
      // restore textarea to current rendered content on cancel
      textarea.value = summary_md || "";
    }
  });

  saveBtn.addEventListener("click", () => postSummary(textarea.value, rendered, editBtn, saveBtn));

  // ── Sources ──
  if (sources && sources.length > 0) {
    container.appendChild(el("div", "section-label", "Sources"));
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

  // ── History ──
  if (triage && triage.length > 0) {
    container.appendChild(el("div", "section-label", "History"));
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
}

// ── Actions ──────────────────────────────────────────────────────────────────

async function postRank(rank, clickedBtn, rankRow) {
  if (!currentNodeId) return;
  try {
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/rank`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rank }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    // update active state
    rankRow.querySelectorAll(".rank-btn").forEach(b => b.classList.remove("active"));
    clickedBtn.classList.add("active");
    toast(`Ranked: ${rank} — ${RANK_LABELS[rank]}`);
  } catch (err) {
    toast(`Rank error: ${err.message}`, true);
  }
}

async function postSummary(content, renderedEl, editBtn, saveBtn) {
  if (!currentNodeId) return;
  saveBtn.textContent = "Saving…";
  try {
    const r = await fetch(`${FLASK}/nodes/${currentNodeId}/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, author: "user" }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    // switch back to render mode with updated content
    renderedEl.innerHTML = renderMarkdown(content);
    renderedEl.style.display = "block";
    document.getElementById("summary-textarea").style.display = "none";
    editBtn.textContent = "Edit";
    saveBtn.style.display = "none";
    saveBtn.textContent = "Save";
    summaryEditMode = false;
    toast("Summary saved");
  } catch (err) {
    saveBtn.textContent = "Save";
    toast(`Save error: ${err.message}`, true);
  }
}

async function captureCurrentTab() {
  if (!currentNodeId) return;
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderMarkdown(md) {
  if (!md) return "<em style='color:#555'>No summary yet.</em>";
  if (typeof marked !== "undefined") {
    const html = marked.parse(md, { async: false });
    if (typeof html === "string") return html;
  }
  return md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\n/g, "<br>");
}

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

// ── Controls ─────────────────────────────────────────────────────────────────

document.getElementById("back-btn").addEventListener("click", () => {
  showListView();
  loadNodes(document.getElementById("sort-select").value);
});

document.getElementById("sort-select").addEventListener("change", e => {
  loadNodes(e.target.value);
});

document.getElementById("capture-btn").addEventListener("click", captureCurrentTab);

// ── Init ─────────────────────────────────────────────────────────────────────

checkFlask().then(ok => {
  if (ok) loadNodes("unranked");
  else {
    document.getElementById("list-view").innerHTML =
      `<div class="empty-msg">Flask not running.<br>Start: python tools/screening_app.py</div>`;
  }
});
