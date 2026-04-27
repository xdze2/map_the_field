browser.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
  document.getElementById("url").textContent = tab.url;
});

document.getElementById("ping").addEventListener("click", () => {
  const status = document.getElementById("status");
  status.textContent = "pinging…";
  fetch("http://localhost:5001/")
    .then(r => { status.textContent = `Flask responded: ${r.status}`; })
    .catch(() => { status.textContent = "Flask not reachable (start it first)"; });
});
