let currentTab = null;

function updateCurrentTab() {
  browser.tabs.query({ active: true }).then(tabs => {
    const tab = tabs.find(t => t.url && !t.url.startsWith("about:") && !t.url.startsWith("moz-extension:"));
    if (tab) {
      currentTab = tab;
      document.getElementById("url").textContent = tab.url;
    }
  });
}

updateCurrentTab();
browser.tabs.onActivated.addListener(updateCurrentTab);
browser.tabs.onUpdated.addListener((_id, change) => {
  if (change.url) updateCurrentTab();
});

document.getElementById("ping").addEventListener("click", () => {
  const status = document.getElementById("status");
  status.textContent = "pinging…";
  fetch("http://localhost:5001/")
    .then(r => { status.textContent = `Flask responded: ${r.status}`; })
    .catch(() => { status.textContent = "Flask not reachable (start it first)"; });
});

document.getElementById("capture").addEventListener("click", () => {
  const status = document.getElementById("status");
  if (!currentTab) { status.textContent = "No active tab found."; return; }

  status.textContent = "capturing…";
  browser.tabs.executeScript(currentTab.id, {
    code: "document.documentElement.outerHTML"
  }).then(([html]) => {
    return fetch("http://localhost:5001/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: currentTab.url, html })
    });
  }).then(r => r.json())
    .then(data => { status.textContent = `Saved → ${data.path}`; })
    .catch(err => { status.textContent = `Error: ${err.message}`; });
});
