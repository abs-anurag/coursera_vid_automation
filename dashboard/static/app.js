async function post(path) {
  await fetch(path, { method: "POST" });
}

async function refresh() {
  const status = await fetch("/api/status").then((r) => r.json());
  document.getElementById("course").textContent = status.course || "—";
  document.getElementById("progress").textContent =
    `${status.videos_completed} / ${status.videos_total} videos`;
  document.getElementById("bar").style.width = `${status.percent}%`;
  document.getElementById("current").textContent = status.current || "—";
  document.getElementById("type").textContent = status.type || "—";
  document.getElementById("status").textContent = status.status || "STOPPED";
  document.getElementById("agent").textContent = status.status || "STOPPED";
  document.getElementById("elapsed").textContent = status.elapsed || "00:00";

  const events = await fetch("/api/events").then((r) => r.json());
  const log = document.getElementById("log");
  log.innerHTML = "";
  for (const event of events.events || []) {
    const item = document.createElement("li");
    const stamp = (event.created_at || "").slice(11, 19);
    item.textContent = `${stamp} ${event.message}`;
    log.appendChild(item);
  }
}

document.getElementById("pause").onclick = () => post("/api/pause");
document.getElementById("resume").onclick = () => post("/api/resume");
document.getElementById("stop").onclick = () => post("/api/stop");
document.getElementById("continue").onclick = () => post("/api/continue");

refresh();
setInterval(refresh, 1500);
