const WS_URL = process.env.EXPO_PUBLIC_WS_URL ?? 'ws://192.168.7.2:8000/ws/analysis-stream';

type MessageHandler = (data: unknown) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectDelay = 1000;
  private maxDelay = 30000;
  private shouldReconnect = false;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.shouldReconnect = true;
    this._open();
  }

  disconnect() {
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private _open() {
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        this.handlers.forEach((h) => h(data));
      } catch {
        // ignore non-JSON frames
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        setTimeout(() => this._open(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }
}

export const wsService = new WebSocketService();
