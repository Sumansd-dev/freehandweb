// API Service and WebSocket Client for VaaniWeb

const API_BASE = '/api';

export async function fetchSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error('Failed to fetch system status:', e);
    return null;
  }
}

export async function sendCommand({ text, language, targetUrl, sessionId = 'default' }) {
  const res = await fetch(`${API_BASE}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      language,
      target_url: targetUrl,
      session_id: sessionId
    })
  });
  if (!res.ok) throw new Error(`Failed to send command: ${res.statusText}`);
  return await res.json();
}

export async function confirmAction({ confirmationId, approved, sessionId = 'default' }) {
  const res = await fetch(`${API_BASE}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      confirmation_id: confirmationId,
      approved
    })
  });
  if (!res.ok) throw new Error(`Failed to submit confirmation: ${res.statusText}`);
  return await res.json();
}

export async function stopTask() {
  const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop task: ${res.statusText}`);
  return await res.json();
}

export class WebSocketClient {
  constructor(sessionId = 'default', onEvent, onStatusChange) {
    this.sessionId = sessionId;
    this.onEvent = onEvent;
    this.onStatusChange = onStatusChange;
    this.ws = null;
    this.reconnectTimer = null;
    this.isClosedManually = false;
  }

  connect() {
    this.isClosedManually = false;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${this.sessionId}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to VaaniWeb backend');
        if (this.onStatusChange) this.onStatusChange(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (this.onEvent && payload.type) {
            this.onEvent(payload.type, payload.data);
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Connection closed');
        if (this.onStatusChange) this.onStatusChange(false);
        if (!this.isClosedManually) {
          this.reconnectTimer = setTimeout(() => this.connect(), 2000);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[WebSocket] Error:', err);
      };
    } catch (e) {
      console.error('[WebSocket] Init failed:', e);
      if (this.onStatusChange) this.onStatusChange(false);
    }
  }

  sendMessage(action, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, ...data }));
    }
  }

  disconnect() {
    this.isClosedManually = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) this.ws.close();
  }
}
