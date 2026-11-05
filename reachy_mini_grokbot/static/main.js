const currentModeEl = document.getElementById("current-mode");
const offlineBadge = document.getElementById("offline-badge");
const configStatusEl = document.getElementById("config-status");
const utteranceStatusEl = document.getElementById("utterance-status");
const toolStatusEl = document.getElementById("tool-status");
const configSaveStatusEl = document.getElementById("config-save-status");
const sendBtn = document.getElementById("send-btn");
const utteranceEl = document.getElementById("utterance");
const saveConfigBtn = document.getElementById("save-config-btn");

const controlUrlEl = document.getElementById("control-url");
const ttsProviderEl = document.getElementById("tts-provider");
const sttProviderEl = document.getElementById("stt-provider");
const ttsVoiceEl = document.getElementById("tts-voice");
const ttsLanguageEl = document.getElementById("tts-language");

const geminiStatus = document.getElementById("gemini-status");
const controlTokenStatus = document.getElementById("control-token-status");
const googleCredsStatus = document.getElementById("google-creds-status");
const xaiStatus = document.getElementById("xai-status");
const deepgramStatus = document.getElementById("deepgram-status");
const webhookStatus = document.getElementById("webhook-status");

function setSecretStatus(el, configured) {
    el.textContent = configured ? "✓ Configured" : "✗ Not set";
    el.className = configured ? "status-ok" : "status-missing";
}

async function refreshStatus() {
    try {
        const resp = await fetch("/status");
        const data = await resp.json();
        
        currentModeEl.textContent = data.current_mode || "idle";
        
        if (data.is_offline) {
            offlineBadge.style.display = "inline-block";
        } else {
            offlineBadge.style.display = "none";
        }
        
        const parts = [];
        if (data.webhook_configured) parts.push("webhook ready");
        if (data.control_configured) parts.push("control ready");
        parts.push(`MCP port ${data.mcp_port}`);
        configStatusEl.textContent = parts.join(" · ");
        
    } catch (e) {
        configStatusEl.textContent = "Backend error - check if app is running";
    }
}

async function loadConfig() {
    try {
        const resp = await fetch("/config");
        const data = await resp.json();
        
        controlUrlEl.value = data.REACHY_CONTROL_URL || "";
        ttsProviderEl.value = data.TTS_PROVIDER || "gemini";
        sttProviderEl.value = data.STT_PROVIDER || "gemini";
        ttsVoiceEl.value = data.TTS_VOICE || "Kore";
        ttsLanguageEl.value = data.TTS_LANGUAGE || "en";
        
        setSecretStatus(geminiStatus, data.gemini_configured);
        setSecretStatus(controlTokenStatus, data.control_configured);
        setSecretStatus(googleCredsStatus, data.google_credentials_configured);
        setSecretStatus(xaiStatus, data.xai_configured);
        setSecretStatus(deepgramStatus, data.deepgram_configured);
        setSecretStatus(webhookStatus, data.webhook_configured);
        
    } catch (e) {
        console.error("Failed to load config:", e);
    }
}

saveConfigBtn.addEventListener("click", async () => {
    configSaveStatusEl.textContent = "Saving…";
    
    const config = {
        REACHY_CONTROL_URL: controlUrlEl.value.trim() || null,
        TTS_PROVIDER: ttsProviderEl.value || null,
        STT_PROVIDER: sttProviderEl.value || null,
        TTS_VOICE: ttsVoiceEl.value || null,
        TTS_LANGUAGE: ttsLanguageEl.value.trim() || null,
    };
    
    try {
        const resp = await fetch("/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config),
        });
        const data = await resp.json();
        
        if (data.saved) {
            configSaveStatusEl.textContent = `Saved to ${data.path}. Restart app to apply.`;
        } else {
            configSaveStatusEl.textContent = data.reason || "No changes to save.";
        }
    } catch (e) {
        configSaveStatusEl.textContent = "Save failed - check console.";
        console.error(e);
    }
});

sendBtn.addEventListener("click", async () => {
    const text = utteranceEl.value.trim();
    if (!text) {
        utteranceStatusEl.textContent = "Type something first.";
        return;
    }
    utteranceStatusEl.textContent = "Sending…";
    sendBtn.disabled = true;
    
    try {
        const resp = await fetch("/utterance", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        const data = await resp.json();
        
        if (!resp.ok) {
            utteranceStatusEl.textContent = data.detail || "Request failed";
            return;
        }
        utteranceStatusEl.textContent = data.accepted
            ? "Chief of staff run started. Reply comes back via speak()."
            : `Webhook rejected (${data.status_code}): ${data.detail}`;
    } catch (e) {
        utteranceStatusEl.textContent = "Backend error";
    } finally {
        sendBtn.disabled = false;
    }
});

document.querySelectorAll("#controls button").forEach((button) => {
    button.addEventListener("click", async () => {
        const name = button.getAttribute("data-tool");
        const arguments = {};
        if (button.hasAttribute("data-emotion")) arguments.emotion = button.getAttribute("data-emotion");
        if (button.hasAttribute("data-mode")) arguments.mode = button.getAttribute("data-mode");
        
        toolStatusEl.textContent = `Calling ${name}…`;
        
        try {
            const resp = await fetch(`/tools/${name}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, arguments }),
            });
            const data = await resp.json();
            toolStatusEl.textContent = data.result || JSON.stringify(data);
        } catch (e) {
            toolStatusEl.textContent = "Tool call failed";
        }
    });
});

refreshStatus();
loadConfig();
setInterval(refreshStatus, 5000);
