const statusEl = document.getElementById("status");
const sendBtn = document.getElementById("send-btn");
const utteranceEl = document.getElementById("utterance");

async function refreshStatus() {
    try {
        const resp = await fetch("/status");
        const data = await resp.json();
        const webhook = data.webhook_configured ? "webhook ready" : "set GROK_BOT_WEBHOOK_URL and KEY";
        statusEl.textContent = `${webhook} · MCP port ${data.mcp_port}`;
    } catch (e) {
        statusEl.textContent = "Backend error";
    }
}

sendBtn.addEventListener("click", async () => {
    const text = utteranceEl.value.trim();
    if (!text) {
        statusEl.textContent = "Type something first.";
        return;
    }
    statusEl.textContent = "Sending…";
    try {
        const resp = await fetch("/utterance", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        const data = await resp.json();
        if (!resp.ok) {
            statusEl.textContent = data.detail || "Request failed";
            return;
        }
        statusEl.textContent = data.accepted
            ? "Chief of staff run started. Reply comes back via speak()."
            : `Webhook rejected (${data.status_code}): ${data.detail}`;
    } catch (e) {
        statusEl.textContent = "Backend error";
    }
});

document.querySelectorAll("#controls button").forEach((button) => {
    button.addEventListener("click", async () => {
        const name = button.getAttribute("data-tool");
        const arguments = {};
        if (button.hasAttribute("data-emotion")) arguments.emotion = button.getAttribute("data-emotion");
        if (button.hasAttribute("data-mode")) arguments.mode = button.getAttribute("data-mode");
        try {
            const resp = await fetch(`/tools/${name}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, arguments }),
            });
            const data = await resp.json();
            statusEl.textContent = data.result || JSON.stringify(data);
        } catch (e) {
            statusEl.textContent = "Tool call failed";
        }
    });
});

refreshStatus();
