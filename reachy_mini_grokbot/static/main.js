/**
 * Reachy Mini × Grok Bot - Settings UI
 * Mobile-friendly configuration interface
 */

const API_BASE = '';

// State
let currentConfig = {};
let statusPollInterval = null;

// DOM Elements
const elements = {
    // Status
    currentMode: document.getElementById('current-mode'),
    controlStatus: document.getElementById('control-status'),
    lastPoll: document.getElementById('last-poll'),
    geminiStatus: document.getElementById('gemini-status'),
    offlineBanner: document.getElementById('offline-banner'),
    
    // Auth
    authToken: document.getElementById('auth-token'),
    toggleAuth: document.getElementById('toggle-auth'),
    
    // API Keys
    geminiKey: document.getElementById('gemini-key'),
    geminiKeyStatus: document.getElementById('gemini-key-status'),
    testGemini: document.getElementById('test-gemini'),
    controlToken: document.getElementById('control-token'),
    controlTokenStatus: document.getElementById('control-token-status'),
    controlUrl: document.getElementById('control-url'),
    xaiKey: document.getElementById('xai-key'),
    xaiKeyStatus: document.getElementById('xai-key-status'),
    deepgramKey: document.getElementById('deepgram-key'),
    deepgramKeyStatus: document.getElementById('deepgram-key-status'),
    
    // Service Account
    saFile: document.getElementById('sa-file'),
    saPaste: document.getElementById('sa-paste'),
    saStatus: document.getElementById('sa-status'),
    uploadSa: document.getElementById('upload-sa'),
    
    // Voice Settings
    ttsProvider: document.getElementById('tts-provider'),
    sttProvider: document.getElementById('stt-provider'),
    ttsVoice: document.getElementById('tts-voice'),
    customVocab: document.getElementById('custom-vocab'),
    
    // Actions
    saveConfig: document.getElementById('save-config'),
    saveStatus: document.getElementById('save-status'),
    
    // Chat
    utterance: document.getElementById('utterance'),
    sendBtn: document.getElementById('send-btn'),
    utteranceStatus: document.getElementById('utterance-status'),
    
    // Tool status
    toolStatus: document.getElementById('tool-status'),
};

// Utility functions
function showMessage(element, message, type = 'info') {
    element.textContent = message;
    element.className = `status-message show ${type}`;
    setTimeout(() => {
        element.classList.remove('show');
    }, 5000);
}

function updateStatusBadge(element, isSet, maskedValue = null) {
    if (isSet) {
        element.textContent = maskedValue || 'set';
        element.className = 'status-badge set';
    } else {
        element.textContent = 'not set';
        element.className = 'status-badge not-set';
    }
}

function formatTimeAgo(isoString) {
    if (!isoString) return '--';
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 5) return 'just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return date.toLocaleTimeString();
}

// API calls
async function fetchStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        // Update mode
        const mode = data.current_mode || 'idle';
        elements.currentMode.textContent = mode;
        elements.currentMode.className = `status-value mode-badge ${mode}`;
        
        // Update control status
        if (data.control_reachable !== undefined) {
            elements.controlStatus.textContent = data.control_reachable ? '✓ Connected' : '✗ Offline';
            elements.controlStatus.style.color = data.control_reachable ? 'var(--success)' : 'var(--error)';
            elements.offlineBanner.style.display = data.is_offline ? 'block' : 'none';
        } else if (data.control_configured) {
            elements.controlStatus.textContent = 'Configured';
            elements.controlStatus.style.color = 'var(--text-muted)';
        } else {
            elements.controlStatus.textContent = 'Not configured';
            elements.controlStatus.style.color = 'var(--warning)';
        }
        
        // Update last poll
        elements.lastPoll.textContent = formatTimeAgo(data.last_poll_time);
        
        // Update Gemini status
        if (data.gemini_configured) {
            elements.geminiStatus.textContent = '✓ Ready';
            elements.geminiStatus.style.color = 'var(--success)';
        } else {
            elements.geminiStatus.textContent = '✗ Not set';
            elements.geminiStatus.style.color = 'var(--warning)';
        }
        
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

async function fetchConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        currentConfig = await response.json();
        
        // Populate form fields
        if (currentConfig.REACHY_CONTROL_URL) {
            elements.controlUrl.value = currentConfig.REACHY_CONTROL_URL;
        }
        if (currentConfig.TTS_PROVIDER) {
            elements.ttsProvider.value = currentConfig.TTS_PROVIDER;
        }
        if (currentConfig.STT_PROVIDER) {
            elements.sttProvider.value = currentConfig.STT_PROVIDER;
        }
        if (currentConfig.TTS_VOICE) {
            elements.ttsVoice.value = currentConfig.TTS_VOICE;
        }
        if (currentConfig.STT_CUSTOM_VOCABULARY) {
            elements.customVocab.value = currentConfig.STT_CUSTOM_VOCABULARY;
        }
        
        // Update status badges
        updateStatusBadge(elements.geminiKeyStatus, currentConfig.gemini_configured, currentConfig.gemini_key_masked);
        updateStatusBadge(elements.controlTokenStatus, currentConfig.control_configured, currentConfig.control_token_masked);
        updateStatusBadge(elements.xaiKeyStatus, currentConfig.xai_configured, currentConfig.xai_key_masked);
        updateStatusBadge(elements.deepgramKeyStatus, currentConfig.deepgram_configured, currentConfig.deepgram_key_masked);
        updateStatusBadge(elements.saStatus, currentConfig.google_credentials_configured, 
            currentConfig.google_credentials_configured ? 'configured' : null);
        
    } catch (error) {
        console.error('Failed to fetch config:', error);
    }
}

async function saveSecrets() {
    const authToken = elements.authToken.value.trim();
    if (!authToken) {
        showMessage(elements.saveStatus, 'Please enter the setup PIN or control token', 'error');
        return;
    }
    
    const payload = { auth_token: authToken };
    
    // Collect all filled-in secrets
    if (elements.geminiKey.value.trim()) {
        payload.GEMINI_API_KEY = elements.geminiKey.value.trim();
    }
    if (elements.controlToken.value.trim()) {
        payload.REACHY_CONTROL_TOKEN = elements.controlToken.value.trim();
    }
    if (elements.controlUrl.value.trim()) {
        payload.REACHY_CONTROL_URL = elements.controlUrl.value.trim();
    }
    if (elements.xaiKey.value.trim()) {
        payload.XAI_API_KEY = elements.xaiKey.value.trim();
    }
    if (elements.deepgramKey.value.trim()) {
        payload.DEEPGRAM_API_KEY = elements.deepgramKey.value.trim();
    }
    if (elements.customVocab.value.trim()) {
        payload.STT_CUSTOM_VOCABULARY = elements.customVocab.value.trim();
    }
    
    try {
        elements.saveConfig.disabled = true;
        elements.saveConfig.textContent = 'Saving...';
        
        // Save secrets
        const secretsResponse = await fetch(`${API_BASE}/config/secrets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const secretsResult = await secretsResponse.json();
        
        if (secretsResult.error) {
            showMessage(elements.saveStatus, secretsResult.error, 'error');
            return;
        }
        
        // Save non-secret config
        const configPayload = {
            TTS_PROVIDER: elements.ttsProvider.value,
            STT_PROVIDER: elements.sttProvider.value,
            TTS_VOICE: elements.ttsVoice.value,
        };
        
        await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configPayload),
        });
        
        showMessage(elements.saveStatus, 'Settings saved successfully!', 'success');
        
        // Clear sensitive inputs after save
        elements.geminiKey.value = '';
        elements.controlToken.value = '';
        elements.xaiKey.value = '';
        elements.deepgramKey.value = '';
        
        // Refresh config display
        await fetchConfig();
        await fetchStatus();
        
    } catch (error) {
        showMessage(elements.saveStatus, `Save failed: ${error.message}`, 'error');
    } finally {
        elements.saveConfig.disabled = false;
        elements.saveConfig.textContent = 'Save All Settings';
    }
}

async function testGeminiKey() {
    const authToken = elements.authToken.value.trim();
    if (!authToken) {
        showMessage(elements.saveStatus, 'Please enter the setup PIN or control token first', 'error');
        return;
    }
    
    const keyToTest = elements.geminiKey.value.trim() || null;
    
    elements.geminiKeyStatus.textContent = 'Testing...';
    elements.geminiKeyStatus.className = 'status-badge testing';
    elements.testGemini.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/config/test-gemini`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auth_token: authToken, api_key: keyToTest }),
        });
        const result = await response.json();
        
        if (result.error) {
            elements.geminiKeyStatus.textContent = result.error;
            elements.geminiKeyStatus.className = 'status-badge invalid';
        } else if (result.valid) {
            elements.geminiKeyStatus.textContent = '✓ Valid';
            elements.geminiKeyStatus.className = 'status-badge valid';
        } else {
            elements.geminiKeyStatus.textContent = result.status || 'Invalid';
            elements.geminiKeyStatus.className = 'status-badge invalid';
        }
        
    } catch (error) {
        elements.geminiKeyStatus.textContent = 'Test failed';
        elements.geminiKeyStatus.className = 'status-badge invalid';
    } finally {
        elements.testGemini.disabled = false;
    }
}

async function uploadServiceAccount() {
    const authToken = elements.authToken.value.trim();
    if (!authToken) {
        showMessage(elements.saveStatus, 'Please enter the setup PIN or control token first', 'error');
        return;
    }
    
    let saJson = '';
    
    // Check for file first
    if (elements.saFile.files.length > 0) {
        const file = elements.saFile.files[0];
        saJson = await file.text();
    } else if (elements.saPaste.value.trim()) {
        saJson = elements.saPaste.value.trim();
    } else {
        showMessage(elements.saveStatus, 'Please select a file or paste the JSON', 'error');
        return;
    }
    
    elements.uploadSa.disabled = true;
    elements.uploadSa.textContent = 'Uploading...';
    
    try {
        const response = await fetch(`${API_BASE}/config/service-account`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                auth_token: authToken,
                service_account_json: saJson,
            }),
        });
        const result = await response.json();
        
        if (result.error) {
            showMessage(elements.saveStatus, result.error, 'error');
            elements.saStatus.textContent = 'Upload failed';
            elements.saStatus.className = 'status-badge invalid';
        } else if (result.saved) {
            showMessage(elements.saveStatus, `Service account uploaded: ${result.client_email}`, 'success');
            elements.saStatus.textContent = 'configured';
            elements.saStatus.className = 'status-badge set';
            elements.saFile.value = '';
            elements.saPaste.value = '';
        }
        
    } catch (error) {
        showMessage(elements.saveStatus, `Upload failed: ${error.message}`, 'error');
    } finally {
        elements.uploadSa.disabled = false;
        elements.uploadSa.textContent = 'Upload Service Account';
    }
}

async function sendUtterance() {
    const text = elements.utterance.value.trim();
    if (!text) {
        showMessage(elements.utteranceStatus, 'Please enter a message', 'error');
        return;
    }
    
    elements.sendBtn.disabled = true;
    elements.sendBtn.textContent = 'Sending...';
    
    try {
        const response = await fetch(`${API_BASE}/utterance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, session_id: 'main' }),
        });
        const result = await response.json();
        
        if (result.accepted) {
            showMessage(elements.utteranceStatus, 'Sent to chief of staff', 'success');
            elements.utterance.value = '';
        } else {
            showMessage(elements.utteranceStatus, result.detail || 'Failed to send', 'error');
        }
        
    } catch (error) {
        showMessage(elements.utteranceStatus, `Error: ${error.message}`, 'error');
    } finally {
        elements.sendBtn.disabled = false;
        elements.sendBtn.textContent = 'Send';
    }
}

async function callTool(tool, args) {
    try {
        const response = await fetch(`${API_BASE}/tools/${tool}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ arguments: args }),
        });
        const result = await response.json();
        showMessage(elements.toolStatus, `${tool}: ${result.result || 'done'}`, 'success');
    } catch (error) {
        showMessage(elements.toolStatus, `${tool} failed: ${error.message}`, 'error');
    }
}

// Event listeners
function setupEventListeners() {
    // Toggle auth token visibility
    elements.toggleAuth.addEventListener('click', () => {
        const input = elements.authToken;
        input.type = input.type === 'password' ? 'text' : 'password';
    });
    
    // Toggle visibility for all password fields
    document.querySelectorAll('.toggle-visibility').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.parentElement.querySelector('input');
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    });
    
    // Save button
    elements.saveConfig.addEventListener('click', saveSecrets);
    
    // Test Gemini
    elements.testGemini.addEventListener('click', testGeminiKey);
    
    // Upload service account
    elements.uploadSa.addEventListener('click', uploadServiceAccount);
    
    // Send utterance
    elements.sendBtn.addEventListener('click', sendUtterance);
    elements.utterance.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendUtterance();
        }
    });
    
    // Robot control buttons
    document.querySelectorAll('[data-tool]').forEach(btn => {
        btn.addEventListener('click', () => {
            const tool = btn.dataset.tool;
            const args = {};
            
            if (btn.dataset.emotion) args.emotion = btn.dataset.emotion;
            if (btn.dataset.mode) args.mode = btn.dataset.mode;
            
            callTool(tool, args);
        });
    });
}

// Initialize
async function init() {
    setupEventListeners();
    await fetchStatus();
    await fetchConfig();
    
    // Poll status every 5 seconds
    statusPollInterval = setInterval(fetchStatus, 5000);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
