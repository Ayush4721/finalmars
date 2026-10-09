const $ = s => document.querySelector(s);
const API = ""; // same origin as FastAPI; set e.g. "http://localhost:8000" if serving the HTML elsewhere

const AGENTS = {
  router: ["Router", "Decides whether this question needs live web research.", "⇄"],
  direct: ["Direct answer", "Answers from the model's own knowledge.", "✦"],
  search: ["Search agent", "Searches the web for sources, URLs and snippets.", "⌕"],
  reader: ["Reader agent", "Opens the best pages and extracts facts, dates and numbers.", "❏"],
  writer: ["Writer agent", "Turns the research notes into the final report.", "✎"],
};
const EXAMPLES = ["What is RAG?", "Latest AI news today", "Explain how a CNN works", "Top news in Mumbai in the last 24 hours"];

const md = s => DOMPurify.sanitize(marked.parse(s || ""));
const txt = v => Array.isArray(v) ? v.map(p => p.text ?? p).join("") : String(v ?? "");
const started = {};

function build() {
  $("#track").innerHTML = Object.entries(AGENTS).map(([id, [name, desc, icon]]) =>
    `<li class="step pending" id="s-${id}" hidden><span class="dot" aria-hidden="true">${icon}</span>
     <div class="body"><div class="head"><b>${name}</b><span class="state"></span></div>
     <p>${desc}</p><div class="out"></div></div></li>`).join("");
}

function setStep(id, status, out) {
  const el = $("#s-" + id);
  el.hidden = false;
  el.className = "step " + status;
  const state = el.querySelector(".state");
  if (status === "running") { started[id] = Date.now(); state.textContent = "Working…"; }
  if (status === "pending") state.textContent = "Waiting";
  if (status === "done") state.textContent = `Done in ${((Date.now() - started[id]) / 1000).toFixed(1)}s`;
  if (out != null) el.querySelector(".out").innerHTML = out;
}

const details = (label, text) => `<details><summary>${label}</summary><div class="md">${md(txt(text))}</div></details>`;

function showAnswer(text) {
  const a = $("#answer");
  a.hidden = false;
  a.innerHTML = `<h2>Final answer</h2><div class="md">${md(txt(text))}</div>`;
  a.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function fail(msg) {
  const e = $("#error");
  e.hidden = false;
  e.textContent = "Something went wrong: " + msg;
  document.querySelectorAll(".step.running").forEach(s => { s.className = "step pending"; s.querySelector(".state").textContent = "Stopped"; });
}

function handle({ node, data }) {
  if (node === "router") {
    const direct = data.route === "DIRECT";
    setStep("router", "done", `<span class="chip ${data.route}">${direct ? "Direct answer" : "Web research"}</span>
      <p class="note">${direct ? "No web search needed. The search, reader and writer agents are skipped."
                                : "This needs current information, so the three research agents take over."}</p>`);
    const next = direct ? ["direct"] : ["search", "reader", "writer"];
    next.forEach(id => setStep(id, "pending"));
    setStep(next[0], "running");
  } else if (node === "direct") {
    setStep("direct", "done");
    showAnswer(data.report);
  } else if (node === "search") {
    setStep("search", "done", details("Sources found", data.search_results));
    setStep("reader", "running");
  } else if (node === "reader") {
    setStep("reader", "done", details("Notes extracted", data.scraped_content));
    setStep("writer", "running");
  } else if (node === "writer") {
    setStep("writer", "done");
    showAnswer(data.report);
  } else if (node === "error") {
    fail(data);
  }
}

async function ask(topic) {
  const btn = $("#go");
  btn.disabled = true;
  $("#run").hidden = false;
  $("#answer").hidden = true;
  $("#error").hidden = true;
  build();
  setStep("router", "running");
  try {
    const res = await fetch(API + "/research/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    if (!res.ok) throw new Error("Server returned " + res.status);
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        if (chunk.startsWith("data: ")) handle(JSON.parse(chunk.slice(6)));
      }
    }
  } catch (e) {
    fail(e.message);
  } finally {
    btn.disabled = false;
  }
}

$("#form").addEventListener("submit", e => {
  e.preventDefault();
  const topic = $("#q").value.trim();
  if (topic) ask(topic);
});

$("#chips").innerHTML = EXAMPLES.map(t => `<button type="button">${t}</button>`).join("");
$("#chips").addEventListener("click", e => {
  if (e.target.matches("button")) { $("#q").value = e.target.textContent; ask(e.target.textContent); }
});

fetch(API + "/health").then(r => r.ok ? r.json() : Promise.reject()).then(() => {
  $("#health").textContent = "Server online"; $("#health").className = "health ok";
}).catch(() => {
  $("#health").textContent = "Server offline. Start it with: uvicorn app:app --reload"; $("#health").className = "health bad";
});