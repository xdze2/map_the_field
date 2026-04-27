const FLASK = "http://localhost:5001";

const RANK_LABELS = {
  1: "Hell no",
  2: "Not interested",
  3: "What?",
  4: "Boring",
  5: "Interested",
  6: "Excited",
};

let nodes = [];

// ── Flask health check ──────────────────────────────────────────────────────

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

// ── Data loading ────────────────────────────────────────────────────────────

async function loadNodes(sort = "unranked") {
  const empty = document.getElementById("list-empty");
  try {
    const r = await fetch(`${FLASK}/nodes?sort=${sort}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    nodes = await r.json();
    renderList(nodes);
  } catch (err) {
    empty.textContent = `Error: ${err.message}`;
    document.getElementById("list-view").innerHTML = "";
    document.getElementById("list-view").appendChild(empty);
  }
}

// ── List rendering ───────────────────────────────────────────────────────────

function renderList(data) {
  const container = document.getElementById("list-view");
  container.innerHTML = "";

  document.getElementById("count").textContent =
    `${data.length} nodes · ${data.filter(n => n.current_rank).length} ranked`;

  if (data.length === 0) {
    const empty = document.createElement("div");
    empty.id = "list-empty";
    empty.textContent = "No nodes found.";
    container.appendChild(empty);
    return;
  }

  const frag = document.createDocumentFragment();
  for (const node of data) {
    frag.appendChild(makeRow(node));
  }
  container.appendChild(frag);
}

function makeRow(node) {
  const row = document.createElement("div");
  row.className = "node-row";
  row.dataset.nodeId = node.node_id;

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
  meta.className = "node-meta";
  meta.textContent = node.updated_at ? node.updated_at.slice(0, 8) : "";

  row.appendChild(badge);
  row.appendChild(name);
  row.appendChild(meta);

  row.addEventListener("click", () => openNode(node.node_id));
  return row;
}

// ── Navigation ───────────────────────────────────────────────────────────────

function openNode(nodeId) {
  // placeholder — Step 3 will implement the node view
  console.log("open node:", nodeId);
}

// ── Sort control ─────────────────────────────────────────────────────────────

document.getElementById("sort-select").addEventListener("change", e => {
  loadNodes(e.target.value);
});

// ── Init ─────────────────────────────────────────────────────────────────────

checkFlask().then(ok => {
  if (ok) loadNodes("unranked");
  else {
    document.getElementById("list-empty").textContent =
      "Flask not running. Start it with: python tools/screening_app.py";
  }
});
