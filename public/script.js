/* global marked, hljs */
(() => {
  "use strict";
  const $ = sel => document.querySelector(sel);
  const chat = $("#chat");
  const input = $("#input");
  const form = $("#input-area");
  const typing = $("#typing");
  const sidebar = $("#sidebar");
  const historyList = $("#history-list");
  let ws;
  let currentId = null;
  let messages = []; // {role, content, id}

  const md = new marked.Marked({
    highlight: (code, lang) => hljs.highlightAuto(code, [lang]).value
  });

  /* ---------- theme ---------- */
  const themeCss = $("#hljs-css");
  function setTheme(dark) {
    document.body.classList.toggle("dark", dark);
    document.body.classList.toggle("light", !dark);
    themeCss.href = dark ? "highlight-dark.css" : "highlight-light.css";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }
  $("#theme-toggle").onclick = () => setTheme(!document.body.classList.contains("dark"));
  (() => setTheme(localStorage.getItem("theme") !== "light"))();

  /* ---------- sidebar toggle ---------- */
  $("#menu-toggle").onclick = () => sidebar.classList.toggle("open");
  $("#collapse-btn").onclick = () => sidebar.classList.toggle("collapsed");
  sidebar.querySelectorAll("a,button").forEach(el => el.addEventListener("click", () => {
    if (window.innerWidth <= 768) sidebar.classList.remove("open");
  }));

  /* ---------- settings button ---------- */
  $("#settings-btn").onclick = () => {
    alert("Settings panel not yet implemented.");
  };

  /* ---------- utils ---------- */
  function genId() { return crypto.randomUUID(); }
  function scrollBottom() { chat.scrollTop = chat.scrollHeight; }

  /* ---------- WS ---------- */
  function connect() {
    ws = new WebSocket(`ws://${location.host}/api/stream`);
    ws.onopen = () => console.log("WS open");
    ws.onclose = () => setTimeout(connect, 2000);
    ws.onmessage = async e => {
      const d = JSON.parse(e.data);
      if (d.token !== undefined) {
        const last = messages[messages.length - 1];
        if (last && last.role === "assistant") {
          last.content += d.token;
          renderMessage(last);
        }
      } else if (d.done) {
        typing.hidden = true;
        save();
      }
    };
  }
  connect();

  /* ---------- render ---------- */
  function renderMessage(m) {
    const welcome = $(".welcome-message");
    if (welcome) welcome.remove();

    let div = $(`[data-id="${m.id}"]`);
    if (!div) {
      div = document.createElement("div");
      div.className = "message " + m.role;
      div.dataset.id = m.id;
      div.innerHTML = `
        <div class="content"></div>
        <div class="controls">
          <button class="copy" title="Copy">📋</button>
          <button class="regen" title="Regenerate">🔁</button>
          <button class="edit" title="Edit">✏️</button>
          <button class="delete" title="Delete">🗑️</button>
        </div>`;
      chat.appendChild(div);
    }
    div.querySelector(".content").innerHTML = md.parse(m.content);
    scrollBottom();
  }

  /* ---------- interact ---------- */
  function addMessage(role, content, id = genId()) {
    const m = { role, content, id };
    messages.push(m);
    renderMessage(m);
    return m;
  }
  async function send() {
    const text = input.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    input.value = "";
    autoHeight();
    addMessage("user", text);
    typing.hidden = false;
    save();
    const history = messages.slice(0, -1).map(({ role, content }) => ({ role, content }));
    ws.send(JSON.stringify({ action: "stream", message: text, history }));
    addMessage("assistant", ""); // start empty
  }
  form.addEventListener("submit", e => { e.preventDefault(); send(); });
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", autoHeight);
  function autoHeight() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  }

  /* ---------- message controls ---------- */
  chat.addEventListener("click", e => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const msgEl = btn.closest(".message");
    const id = msgEl.dataset.id;
    const idx = messages.findIndex(m => m.id === id);
    if (btn.classList.contains("copy")) navigator.clipboard.writeText(messages[idx].content);
    if (btn.classList.contains("delete")) { messages.splice(idx, 1); msgEl.remove(); save(); }
    if (btn.classList.contains("edit")) {
      const newText = prompt("Edit:", messages[idx].content);
      if (newText != null) { messages[idx].content = newText; renderMessage(messages[idx]); save(); }
    }
    if (btn.classList.contains("regen")) {
      const userIdx = idx - 1;
      if (userIdx >= 0 && messages[userIdx].role === "user") {
        messages.splice(idx, 1); msgEl.remove();
        messages.splice(userIdx, 1); $(`[data-id="${messages[userIdx]?.id}"]`)?.remove();
        addMessage("user", messages[userIdx].content);
        typing.hidden = false;
        const hist = messages.slice(0, -1).map(({ role, content }) => ({ role, content }));
        ws.send(JSON.stringify({ action: "stream", message: messages[userIdx].content, history: hist }));
        addMessage("assistant", "");
      }
    }
  });

  /* ---------- history ---------- */
  async function loadHistory() {
    const list = await (await fetch("/api/history")).json();
    historyList.innerHTML = "";
    list.forEach(c => {
      const d = document.createElement("div");
      d.className = "history-item";
      d.innerHTML = `<span>${c.name || "Untitled"}</span>`;
      d.dataset.id = c.id;
      historyList.appendChild(d);
    });
  }
  loadHistory();
  historyList.addEventListener("click", e => {
    const it = e.target.closest(".history-item");
    if (it) openChat(it.dataset.id);
  });
  $("#new-chat").onclick = () => { currentId = null; messages = []; chat.innerHTML = ""; save(true); };
  async function openChat(id) {
    const data = await (await fetch(`/api/history/${id}`)).json();
    if (data.error) return;
    currentId = id;
    messages = data.messages || [];
    chat.innerHTML = "";
    messages.forEach(renderMessage);
    scrollBottom();
  }
  async function save(isNew = false) {
    if (isNew || !currentId) currentId = genId();
    const payload = { id: currentId, name: messages.find(m => m.role === "user")?.content.slice(0, 50) || "New chat", messages };
    await fetch("/api/history/" + currentId, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    loadHistory();
  }

  /* ---------- export/import ---------- */
  $("#export-btn").onclick = async () => {
    const data = await (await fetch("/api/export")).json();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    a.download = "chat_export.json";
    a.click();
  };
  $("#import-file").addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;
    await fetch("/api/import", { method: "POST", body: await file.text(), headers: { "Content-Type": "application/json" } });
    loadHistory();
    location.reload();
  });
})();