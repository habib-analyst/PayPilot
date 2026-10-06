const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");

function addMsg(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  // linkify bare URLs (PayPal approval links)
  div.innerHTML = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

async function send(text) {
  addMsg(text, "user");
  input.value = "";
  const typing = addMsg("PayPilot is thinking…", "bot typing");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typing.remove();
    if (!res.ok) throw new Error(data.detail || "request failed");
    addMsg(data.reply, "bot");
    refreshOrders();
  } catch (e) {
    typing.remove();
    addMsg("⚠️ " + e.message, "sys");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const t = input.value.trim();
  if (t) send(t);
});
document.querySelectorAll(".chips button").forEach((b) =>
  b.addEventListener("click", () => send(b.dataset.q))
);
document.getElementById("reset-btn").addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  messagesEl.innerHTML = "";
  addMsg("Conversation reset. What shall we shop for?", "sys");
});

// ---- AG Grid order history ----
const gridOptions = {
  columnDefs: [
    { field: "time", headerName: "Time", width: 170, valueFormatter: (p) => (p.value || "").slice(0, 19).replace("T", " ") },
    { field: "product", headerName: "Product", flex: 1 },
    { field: "total", headerName: "Total", width: 90 },
    { field: "status", headerName: "Status", width: 150 },
  ],
  rowData: [],
};
agGrid.createGrid(document.getElementById("orders-grid"), gridOptions);

async function refreshOrders() {
  try {
    const res = await fetch("/api/orders");
    const data = await res.json();
    gridOptions.api.setGridOption("rowData", data.orders || []);
  } catch { /* ignore */ }
}

addMsg("👋 Hi! I'm PayPilot. Tell me what you want to buy and I'll find it, compare options, and check you out with PayPal — all in this chat.", "bot");
refreshOrders();
