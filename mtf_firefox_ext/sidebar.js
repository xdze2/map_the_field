const FLASK = "http://localhost:5001";

const RANK_LABELS = {
  1: "Hell no",
  2: "Not interested",
  3: "What?",
  4: "Boring",
  5: "Interested",
  6: "Excited",
};

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

// ── View switching ───────────────────────────────────────────────────────────

function showListView() {
  document.getElementById("list-view").style.display = "block";
  document.getElementById("node-view").style.display = "none";
  document.getElementById("list-toolbar").style.display = "flex";
  document.getElementById("back-btn").style.display = "none";
  document.getElementById("topbar-title").textContent = "Map the Field";
}

function showNodeView() {
  document.getElementById("list-view").style.display = "none";
  document.getElementById("node-view").style.display = "block";
  document.getElementById("list-toolbar").style.display = "none";
  document.getElementById("back-btn").style.display = "block";
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
  for (const node of nodes) {
    frag.appendChild(makeRow(node));
  }
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
    // rank interaction wired in Step 4
    rankRow.appendChild(btn);
  }
  container.appendChild(rankRow);

  // ── Summary ──
  container.appendChild(el("div", "section-label", "Summary"));
  const summaryBox = el("div", "summary-box rendered");
  const rendered = el("div", "summary-rendered");
  if (typeof marked !== "undefined" && summary_md) {
    // marked v15+ parse() is async; use marked.parseInline for sync or call parse with async:false
    const html = marked.parse(summary_md, { async: false });
    rendered.innerHTML = typeof html === "string" ? html : summary_md;
  } else {
    rendered.textContent = summary_md || "No summary yet.";
  }
  summaryBox.appendChild(rendered);
  container.appendChild(summaryBox);

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
        const badge = el("span", "history-rank", `${entry.rank} — ${RANK_LABELS[entry.rank]}`);
        top.appendChild(badge);
        top.appendChild(document.createTextNode(" "));
      }
      top.appendChild(el("span", "history-ts", entry.timestamp || entry.ts || ""));
      item.appendChild(top);
      if (entry.note) item.appendChild(el("div", "history-note", entry.note));
      hist.appendChild(item);
    }
    container.appendChild(hist);
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

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

// ── Init ─────────────────────────────────────────────────────────────────────

checkFlask().then(ok => {
  if (ok) loadNodes("unranked");
  else {
    document.getElementById("list-view").innerHTML =
      `<div class="empty-msg">Flask not running.<br>Start: python tools/screening_app.py</div>`;
  }
});
