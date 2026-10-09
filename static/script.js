const $ = (selector) => document.querySelector(selector);
const form = $("#researchForm");
const topicInput = $("#topicInput");
const researchButton = $("#researchButton");
const buttonText = $("#buttonText");
const reportContent = $("#reportContent");
const emptyState = $("#emptyState");
const errorBox = $("#errorBox");
const reportMeta = $("#reportMeta");
const resultTopic = $("#resultTopic");
const reportFooter = $("#reportFooter");
const routeBadge = $("#routeBadge");
const livePill = $("#livePill");
const progressBar = $("#progressBar");
const activityLog = $("#activityLog");
const dialog = $("#infoDialog");
let isRunning = false;
let latestReport = "";
let runController = null;
const historyItems = [];

const agentAliases = {
  router: ["router", "route", "classif"],
  search: ["search", "research", "tavily", "web"],
  scrape: ["scrape", "extract", "fetch", "source"],
  writer: ["writer", "write", "report", "synth", "answer", "final"]
};
const agentDescriptions = {
  router: "Classifying the question and selecting a route.",
  search: "Searching for relevant web information.",
  scrape: "Extracting useful information from source pages.",
  writer: "Synthesizing findings into a readable report."
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

// Lightweight Markdown renderer; escapes raw HTML before formatting.
function renderMarkdown(markdown) {
  let source = escapeHtml(String(markdown || "").replace(/\r\n/g, "\n"));
  const codeBlocks = [];
  source = source.replace(/```([\w-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code>${code.trimEnd()}</code></pre>`);
    return `@@CODEBLOCK${idx}@@`;
  });
  source = source
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const lines = source.split("\n");
  let out = [], inUl = false, inOl = false, paragraph = [];
  const flushParagraph = () => {
    if (paragraph.length) {
      out.push(`<p>${paragraph.join("<br>")}</p>`);
      paragraph = [];
    }
  };
  const closeLists = () => {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  };
  for (const line of lines) {
    const ul = line.match(/^\s*[-*]\s+(.+)/);
    const ol = line.match(/^\s*\d+[.)]\s+(.+)/);
    if (line.startsWith("@@CODEBLOCK") && line.endsWith("@@")) {
      flushParagraph(); closeLists();
      const index = Number(line.match(/\d+/)[0]);
      out.push(codeBlocks[index] || "");
    } else if (/^<h[1-3]>/.test(line) || line.startsWith("<blockquote>")) {
      flushParagraph(); closeLists(); out.push(line);
    } else if (ul) {
      flushParagraph(); if (inOl) { out.push("</ol>"); inOl = false; }
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li>${ul[1]}</li>`);
    } else if (ol) {
      flushParagraph(); if (inUl) { out.push("</ul>"); inUl = false; }
      if (!inOl) { out.push("<ol>"); inOl = true; }
      out.push(`<li>${ol[1]}</li>`);
    } else if (!line.trim()) {
      flushParagraph(); closeLists();
    } else {
      closeLists(); paragraph.push(line);
    }
  }
  flushParagraph(); closeLists();
  return out.join("\n");
}

function logActivity(message, kind = "info") {
  const empty = activityLog.querySelector(".log-empty");
  if (empty) empty.remove();
  const entry = document.createElement("div");
  entry.className = "log-entry";
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  entry.innerHTML = `<span class="log-dot" style="${kind === "error" ? "background:#ff788b" : kind === "done" ? "background:#2de0a2" : ""}"></span><div><time>${time}</time>${escapeHtml(message)}</div>`;
  activityLog.prepend(entry);
  while (activityLog.children.length > 30) activityLog.lastElementChild.remove();
}

function normalizeNodeName(name) {
  const lower = String(name || "").toLowerCase();
  for (const [agent, aliases] of Object.entries(agentAliases)) {
    if (aliases.some(alias => lower.includes(alias))) return agent;
  }
  return null;
}

function setAgent(agent, state, message) {
  const step = document.querySelector(`[data-agent="${agent}"]`);
  if (!step) return;
  step.classList.remove("active", "done", "error");
  if (state) step.classList.add(state);
  const stateLabel = step.querySelector(".agent-state");
  stateLabel.textContent = state === "active" ? "Working…" : state === "done" ? "Completed" : state === "error" ? "Failed" : "Waiting";
  if (message) step.querySelector("p").textContent = message;
  updateProgress();
}
function resetAgents() {
  Object.keys(agentAliases).forEach(agent => setAgent(agent, "", {
    router: "Decides whether your question needs web research.",
    search: "Finds relevant pages and information from the web.",
    scrape: "Extracts useful context from relevant sources.",
    writer: "Organizes the information into a final answer."
  }[agent]));
  progressBar.style.width = "0%";
}
function updateProgress() {
  const steps = [...document.querySelectorAll(".agent-step")];
  const done = steps.filter(s => s.classList.contains("done")).length;
  const active = steps.some(s => s.classList.contains("active"));
  progressBar.style.width = `${Math.min(100, (done / steps.length) * 100 + (active ? 8 : 0))}%`;
}
function setBusy(busy) {
  isRunning = busy;
  researchButton.disabled = busy;
  buttonText.textContent = busy ? "Researching…" : "Start research";
  $("#systemStatus").textContent = busy ? "Research in progress" : "System online";
  livePill.className = `live-pill ${busy ? "busy" : ""}`;
  livePill.innerHTML = busy ? "<span></span> RUNNING" : "<span></span> IDLE";
  if (!busy) researchButton.disabled = false;
}
function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
  logActivity(message, "error");
}
function hideError() { errorBox.hidden = true; errorBox.textContent = ""; }

function findReport(value, depth = 0) {
  if (depth > 5 || value == null) return "";
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.length > 100 && /(\n|\.|#|\*\*)/.test(trimmed)) return trimmed;
    return "";
  }
  if (Array.isArray(value)) {
    for (const item of value) { const found = findReport(item, depth + 1); if (found) return found; }
    return "";
  }
  if (typeof value === "object") {
    const preferred = ["report", "answer", "final_answer", "final_report", "output", "response", "content", "result"];
    for (const key of preferred) {
      if (typeof value[key] === "string" && value[key].trim().length > 30) return value[key].trim();
    }
    for (const [key, item] of Object.entries(value)) {
      if (/report|answer|writer|final/i.test(key)) {
        const found = findReport(item, depth + 1);
        if (found) return found;
      }
    }
  }
  return "";
}
function showReport(topic, report, route = "RESEARCH") {
  latestReport = report || "";
  emptyState.hidden = true;
  reportContent.hidden = false;
  reportContent.innerHTML = renderMarkdown(latestReport || "The research stream finished, but the graph did not return a recognizable report field. Check the activity log for the node updates, or confirm that the final graph node returns a `report` or `answer` value.");
  reportMeta.hidden = false;
  resultTopic.textContent = topic;
  reportFooter.hidden = false;
  routeBadge.textContent = route;
  routeBadge.className = "route-badge " + (String(route).toUpperCase().includes("DIRECT") ? "direct" : String(route).toUpperCase().includes("RESEARCH") ? "research" : "");
  $("#reportHeading").textContent = "Research report";
  $("#reportSubheading").textContent = "Results from your research pipeline";
}
function markAllDone() {
  Object.keys(agentAliases).forEach(agent => {
    const step = document.querySelector(`[data-agent="${agent}"]`);
    if (!step.classList.contains("done") && !step.classList.contains("error")) setAgent(agent, "done");
  });
  progressBar.style.width = "100%";
  livePill.className = "live-pill done";
  livePill.innerHTML = "<span></span> COMPLETE";
}

async function runResearch(topic) {
  if (isRunning) return;
  hideError();
  latestReport = "";
  resetAgents();
  reportContent.hidden = true;
  reportMeta.hidden = true;
  reportFooter.hidden = true;
  emptyState.hidden = true;
  $("#reportHeading").textContent = "Research in progress";
  $("#reportSubheading").textContent = "Your agents are working on this topic";
  routeBadge.textContent = "RUNNING";
  routeBadge.className = "route-badge";
  setBusy(true);
  setAgent("router", "active");
  logActivity(`Started research: ${topic}`);
  runController = new AbortController();

  let receivedAny = false;
  let lastUsefulPayload = null;
  try {
    const response = await fetch("/research/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
      body: JSON.stringify({ topic }),
      signal: runController.signal
    });
    if (!response.ok) {
      let detail = `Request failed with status ${response.status}.`;
      try { const body = await response.json(); detail = body.detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    if (!response.body) throw new Error("Streaming is not supported by this browser. Try a current version of Chrome or Edge.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        const dataLine = block.split(/\r?\n/).find(line => line.startsWith("data:"));
        if (!dataLine) continue;
        const raw = dataLine.slice(5).trim();
        if (!raw) continue;
        let event;
        try { event = JSON.parse(raw); } catch (_) { logActivity(raw); continue; }
        receivedAny = true;
        if (event.node === "error") throw new Error(typeof event.data === "string" ? event.data : JSON.stringify(event.data));
        const node = String(event.node || "agent");
        const agent = normalizeNodeName(node);
        const payload = event.data;
        lastUsefulPayload = event;
        const extracted = findReport(payload);
        if (extracted) latestReport = extracted;
        if (agent) {
          setAgent(agent, "active", agentDescriptions[agent]);
          logActivity(`${node} started or returned an update.`);
          // In update-mode, an emitted node update generally means that node has completed.
          setAgent(agent, "done", agentDescriptions[agent]);
          const next = { router: "search", search: "scrape", scrape: "writer" }[agent];
          if (next) {
            const nextStep = document.querySelector(`[data-agent="${next}"]`);
            if (!nextStep.classList.contains("done")) setAgent(next, "active", agentDescriptions[next]);
          }
        } else {
          logActivity(`Received update from ${node}.`);
        }
      }
    }
    if (buffer.trim()) {
      const dataLine = buffer.split(/\r?\n/).find(line => line.startsWith("data:"));
      if (dataLine) {
        try {
          const event = JSON.parse(dataLine.slice(5).trim());
          if (event.node === "error") throw new Error(event.data);
          lastUsefulPayload = event;
          const extracted = findReport(event.data);
          if (extracted) latestReport = extracted;
          logActivity(`Received final update from ${event.node || "pipeline"}.`);
        } catch (e) {
          if (e.message && !e.message.includes("Unexpected")) throw e;
        }
      }
    }
    if (!receivedAny) throw new Error("The server closed the stream without sending any updates. Check that research_graph.stream() emits node updates.");
    if (!latestReport && lastUsefulPayload) latestReport = findReport(lastUsefulPayload) || "";
    markAllDone();
    showReport(topic, latestReport, "RESEARCH");
    historyItems.unshift({ topic, report: latestReport, time: new Date() });
    logActivity("Research stream completed.", "done");
  } catch (error) {
    if (error.name === "AbortError") {
      logActivity("Research request cancelled.");
    } else {
      showError(error.message || "Something went wrong while running research.");
      $("#reportHeading").textContent = "Research could not be completed";
      $("#reportSubheading").textContent = "Check your backend logs and try again";
      emptyState.hidden = true;
    }
    if (!latestReport) {
      reportContent.hidden = true;
      reportMeta.hidden = true;
      reportFooter.hidden = true;
    }
  } finally {
    setBusy(false);
    runController = null;
    if (!errorBox.hidden) {
      livePill.className = "live-pill";
      livePill.innerHTML = "<span></span> ERROR";
    }
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) { topicInput.focus(); return; }
  runResearch(topic);
});
document.querySelectorAll(".suggestion-chip").forEach(button => {
  button.addEventListener("click", () => {
    topicInput.value = button.dataset.topic || "";
    topicInput.focus();
  });
});
$("#copyButton").addEventListener("click", async () => {
  if (!latestReport) return;
  try {
    await navigator.clipboard.writeText(latestReport);
    $("#copyButton").textContent = "Copied!";
    setTimeout(() => $("#copyButton").textContent = "Copy report", 1600);
  } catch (_) { showError("Clipboard access was blocked by your browser. Select and copy the report text manually."); }
});
$("#downloadButton").addEventListener("click", () => {
  const topic = resultTopic.textContent || "research";
  const blob = new Blob([`Topic: ${topic}\n\n${latestReport}`], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "research-report"}.txt`;
  anchor.click();
  URL.revokeObjectURL(url);
});
$("#clearLogButton").addEventListener("click", () => {
  activityLog.innerHTML = '<div class="log-empty">Activity log cleared.</div>';
});
$("#themeToggle").addEventListener("click", () => {
  document.body.classList.toggle("light");
});
$("#closeDialog").addEventListener("click", () => dialog.close());
document.querySelectorAll(".nav-item").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item === button));
    const view = button.dataset.view;
    const content = {
      home: ["Home", "Enter a topic in the research bar to run your LangGraph workflow. Results stream from your FastAPI endpoint."],
      history: ["Recent topics", historyItems.length ? historyItems.slice(0, 8).map((item, i) => `${i + 1}. ${item.topic}`).join("\n") : "No completed research sessions in this page yet. Your history is kept in memory until you refresh the page."],
      about: ["About this project", "A multi-agent research interface for your FastAPI backend. The router decides how to handle a question, research tools gather context, and your graph can produce a structured report. The exact agents shown here are a visual guide; emitted node names come from your own graph."],
      api: ["Backend endpoints", "GET  /health — check API status\nPOST /route — classify a topic\nPOST /research — run the full pipeline and return a report\nPOST /research/stream — stream graph node updates as server-sent events\n\nThis frontend uses POST /research/stream. All requests are sent to the same origin serving this page."]
    };
    $("#dialogTitle").textContent = content[view][0];
    $("#dialogBody").textContent = content[view][1];
    dialog.showModal();
  });
});
window.addEventListener("beforeunload", () => {
  if (runController) runController.abort();
});
