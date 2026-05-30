const endpointInput = document.querySelector("#endpointInput");
const modelSelect = document.querySelector("#modelSelect");
const thinkToggle = document.querySelector("#thinkToggle");
const refreshButton = document.querySelector("#refreshButton");
const clearButton = document.querySelector("#clearButton");
const messagesEl = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const stopButton = document.querySelector("#stopButton");
const statusText = document.querySelector("#statusText");

let messages = [];
let controller = null;

const urlEndpoint = new URLSearchParams(window.location.search).get("endpoint");
const settings = {
  endpoint: urlEndpoint || localStorage.getItem("remoteOllama.endpoint") || "http://localhost:11435",
  model: localStorage.getItem("remoteOllama.model") || "qwen3:8b",
  think: localStorage.getItem("remoteOllama.think") === "true",
};

endpointInput.value = settings.endpoint;
thinkToggle.checked = settings.think;

function endpoint() {
  return endpointInput.value.trim().replace(/\/+$/, "");
}

function setStatus(text, mode = "") {
  statusText.textContent = text;
  statusText.className = mode;
}

function persistSettings() {
  localStorage.setItem("remoteOllama.endpoint", endpoint());
  localStorage.setItem("remoteOllama.model", modelSelect.value);
  localStorage.setItem("remoteOllama.think", String(thinkToggle.checked));
}

function emptyState() {
  if (messages.length > 0 || messagesEl.children.length > 0) return;

  const empty = document.createElement("div");
  empty.className = "empty";
  empty.textContent = "All installed VM models appear in the selector. Keep Ollama private on the VM and reach it through the SSH tunnel.";
  messagesEl.append(empty);
}

function clearEmptyState() {
  const empty = messagesEl.querySelector(".empty");
  if (empty) empty.remove();
}

function renderMessage(role, content = "", model = "") {
  clearEmptyState();

  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = role === "user" ? "You" : model || modelSelect.value;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  wrapper.append(meta, bubble);
  messagesEl.append(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  return bubble;
}

function renderAssistantBubble(bubble, content, thinking) {
  bubble.textContent = "";

  if (thinking) {
    const thinkingEl = document.createElement("div");
    thinkingEl.className = "thinking";
    thinkingEl.textContent = thinking;
    bubble.append(thinkingEl);
  }

  const contentEl = document.createElement("div");
  contentEl.textContent = content || "Waiting for response...";
  bubble.append(contentEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function loadModels() {
  setStatus("Connecting to VM", "");
  refreshButton.disabled = true;

  try {
    const response = await fetch(`${endpoint()}/api/tags`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const names = (data.models || []).map((model) => model.name).sort();

    modelSelect.textContent = "";
    for (const name of names) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      modelSelect.append(option);
    }

    const preferred = names.includes(settings.model)
      ? settings.model
      : names.includes("qwen3:8b")
        ? "qwen3:8b"
        : names[0];

    if (preferred) modelSelect.value = preferred;
    setStatus(`${names.length} VM models ready`, "ready");
    persistSettings();
  } catch (error) {
    setStatus("VM connection failed", "error");
    console.error(error);
  } finally {
    refreshButton.disabled = false;
    emptyState();
  }
}

async function sendMessage(text) {
  persistSettings();

  const selectedModel = modelSelect.value;
  messages.push({ role: "user", content: text });
  renderMessage("user", text);

  const assistantBubble = renderMessage("assistant", "", selectedModel);
  let assistantContent = "";
  let assistantThinking = "";
  let buffer = "";

  controller = new AbortController();
  sendButton.disabled = true;
  stopButton.disabled = false;
  promptInput.disabled = true;
  setStatus(`Running ${selectedModel}`, "ready");

  try {
    const response = await fetch(`${endpoint()}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: selectedModel,
        messages,
        stream: true,
        think: thinkToggle.checked,
        options: { temperature: 0.35 },
      }),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

    const decoder = new TextDecoder();
    const reader = response.body.getReader();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;

        const chunk = JSON.parse(line);
        assistantContent += chunk.message?.content || "";
        assistantThinking += chunk.message?.thinking || chunk.thinking || "";
        renderAssistantBubble(assistantBubble, assistantContent, assistantThinking);
      }
    }

    if (assistantContent || assistantThinking) {
      messages.push({ role: "assistant", content: assistantContent || assistantThinking });
    }

    renderAssistantBubble(assistantBubble, assistantContent, assistantThinking);
    setStatus(`${selectedModel} ready`, "ready");
  } catch (error) {
    if (error.name === "AbortError") {
      setStatus("Stopped", "");
    } else {
      renderAssistantBubble(assistantBubble, `Error: ${error.message}`, "");
      setStatus("Request failed", "error");
    }
  } finally {
    controller = null;
    sendButton.disabled = false;
    stopButton.disabled = true;
    promptInput.disabled = false;
    promptInput.focus();
  }
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = promptInput.value.trim();
  if (!text || controller) return;

  promptInput.value = "";
  promptInput.style.height = "";
  sendMessage(text);
});

promptInput.addEventListener("input", () => {
  promptInput.style.height = "";
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 220)}px`;
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    composer.requestSubmit();
  }
});

stopButton.addEventListener("click", () => {
  if (controller) controller.abort();
});

clearButton.addEventListener("click", () => {
  messages = [];
  messagesEl.textContent = "";
  emptyState();
  promptInput.focus();
});

refreshButton.addEventListener("click", loadModels);
endpointInput.addEventListener("change", loadModels);
modelSelect.addEventListener("change", persistSettings);
thinkToggle.addEventListener("change", persistSettings);

loadModels();
