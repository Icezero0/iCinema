type WSMessageType = "auth" | "heartbeat" | "command" | "event" | "error" | "ack";

export type WSCommandAction =
  | "room_enter"
  | "room_leave"
  | "room_presence_get"
  | "room_video_runtime_get"
  | "playback_pause"
  | "playback_play"
  | "playback_seek"
  | "room_video_source_set"
  | "user_resource_status";

export type WSEventName =
  | "notification"
  | "room_info"
  | "room_settings"
  | "room_members"
  | "room_user_presence"
  | "session_closed"
  | "message"
  | "playback_pause"
  | "playback_play"
  | "playback_seek"
  | "room_video_source_set"
  | "user_resource_states";

export type WSErrorCode =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "bad_request"
  | "invalid_payload"
  | "internal_error";

export type WSConnectionStatus =
  | "idle"
  | "connecting"
  | "authenticating"
  | "ready"
  | "reconnecting"
  | "closed"
  | "error";

type EnvelopeBase<T extends WSMessageType, P> = {
  v: 1;
  type: T;
  payload: P;
};

type AuthPayload = {
  token: string;
};

type HeartbeatPayload = {
  action: "ping" | "pong";
};

type CommandPayload<T = unknown> = {
  request_id: string;
  action: WSCommandAction;
  data: T;
};

type AckPayload<T = unknown> = {
  request_id?: string | null;
  data?: T;
};

type ErrorPayload = {
  request_id?: string | null;
  code: WSErrorCode;
  reason?: string | null;
  message: string;
  details?: unknown;
};

type EventPayload<T = unknown> = {
  event: WSEventName;
  data: T;
};

export type WSAuthEnvelope = EnvelopeBase<"auth", AuthPayload>;
export type WSHeartbeatEnvelope = EnvelopeBase<"heartbeat", HeartbeatPayload>;
export type WSCommandEnvelope<T = unknown> = EnvelopeBase<"command", CommandPayload<T>>;
export type WSAckEnvelope<T = unknown> = EnvelopeBase<"ack", AckPayload<T>>;
export type WSErrorEnvelope = EnvelopeBase<"error", ErrorPayload>;
export type WSEventEnvelope<T = unknown> = EnvelopeBase<"event", EventPayload<T>>;

export type WSEnvelope =
  | WSAuthEnvelope
  | WSHeartbeatEnvelope
  | WSCommandEnvelope
  | WSAckEnvelope
  | WSErrorEnvelope
  | WSEventEnvelope;

type EventHandler<T = unknown> = (payload: T, envelope: WSEventEnvelope<T>) => void;
type StatusHandler = (status: WSConnectionStatus) => void;
type EnvelopeHandler = (envelope: WSEnvelope) => void;

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
  timeoutId: number;
};

const WS_PROTOCOL_VERSION = 1;
const HEARTBEAT_INTERVAL_MS = 25_000;
const HEARTBEAT_TIMEOUT_MS = 10_000;
const REQUEST_TIMEOUT_MS = 10_000;
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 15_000;
const DEFAULT_BACKEND_PORT = "8000";

function deriveApiOriginFromLocation() {
  if (typeof window === "undefined") {
    return `http://localhost:${DEFAULT_BACKEND_PORT}`;
  }

  const url = new URL(window.location.origin);
  if (url.port) {
    url.port = DEFAULT_BACKEND_PORT;
  }

  return url.origin;
}

function deriveWSOrigin() {
  const apiOrigin = import.meta.env.VITE_API_ORIGIN ?? deriveApiOriginFromLocation();

  if (apiOrigin.startsWith("https://")) {
    return apiOrigin.replace("https://", "wss://");
  }

  if (apiOrigin.startsWith("http://")) {
    return apiOrigin.replace("http://", "ws://");
  }

  return apiOrigin;
}

function buildWSUrl() {
  const wsOrigin = import.meta.env.VITE_WS_ORIGIN ?? deriveWSOrigin();
  const endpoint = import.meta.env.VITE_WS_ENDPOINT ?? "/ws";
  return `${wsOrigin}${endpoint}`;
}

function createRequestId(prefix: string) {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

class WSProtocolError extends Error {
  code?: WSErrorCode;
  reason?: string | null;
  requestId?: string | null;
  details?: unknown;

  constructor(
    message: string,
    code?: WSErrorCode,
    requestId?: string | null,
    reason?: string | null,
    details?: unknown,
  ) {
    super(message);
    this.name = "WSProtocolError";
    this.code = code;
    this.requestId = requestId;
    this.reason = reason;
    this.details = details;
  }
}

class WSClient {
  private ws: WebSocket | null = null;
  private token = "";
  private status: WSConnectionStatus = "idle";
  private shouldReconnect = false;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private heartbeatTimeoutTimer: number | null = null;
  private lastPingAt = 0;
  private lastPongAt = 0;
  private connectPromise: Promise<void> | null = null;
  private authRequestId: string | null = null;

  private pendingRequests = new Map<string, PendingRequest>();
  private eventHandlers = new Map<WSEventName, Set<EventHandler>>();
  private statusHandlers = new Set<StatusHandler>();
  private envelopeHandlers = new Set<EnvelopeHandler>();

  get connectionStatus() {
    return this.status;
  }

  onStatusChange(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    handler(this.status);
    return () => this.statusHandlers.delete(handler);
  }

  onEnvelope(handler: EnvelopeHandler) {
    this.envelopeHandlers.add(handler);
    return () => this.envelopeHandlers.delete(handler);
  }

  onEvent<T = unknown>(event: WSEventName, handler: EventHandler<T>) {
    const bucket = this.eventHandlers.get(event) ?? new Set<EventHandler>();
    bucket.add(handler as EventHandler);
    this.eventHandlers.set(event, bucket);

    return () => {
      bucket.delete(handler as EventHandler);
      if (bucket.size === 0) {
        this.eventHandlers.delete(event);
      }
    };
  }

  async connect(token: string) {
    if (!token) {
      throw new Error("WS access token is required");
    }

    if (
      this.ws &&
      (this.status === "connecting" ||
        this.status === "authenticating" ||
        this.status === "ready") &&
      this.token === token
    ) {
      return this.connectPromise ?? Promise.resolve();
    }

    if (this.ws && this.token !== token) {
      this.disconnect();
    }

    this.token = token;
    this.shouldReconnect = true;
    this.connectPromise = this.openConnection();
    return this.connectPromise;
  }

  disconnect() {
    this.shouldReconnect = false;
    this.connectPromise = null;
    this.authRequestId = null;

    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();
    this.rejectAllPending(new WSProtocolError("WebSocket disconnected"));

    if (this.ws) {
      const current = this.ws;
      this.ws = null;
      current.close();
    }

    this.updateStatus("closed");
  }

  async command<TResponse = unknown, TData = Record<string, unknown>>(
    action: WSCommandAction,
    data: TData,
    timeoutMs = REQUEST_TIMEOUT_MS,
  ) {
    if (!this.ws || this.status !== "ready") {
      throw new Error("WebSocket connection is not ready");
    }

    const request_id = createRequestId(action);
    const payload: CommandPayload<TData> = {
      request_id,
      action,
      data,
    };

    const envelope: WSCommandEnvelope<TData> = {
      v: WS_PROTOCOL_VERSION,
      type: "command",
      payload,
    };

    return new Promise<TResponse>((resolve, reject) => {
      const timeoutId = window.setTimeout(() => {
        this.pendingRequests.delete(request_id);
        reject(new WSProtocolError(`WS command timed out: ${action}`));
      }, timeoutMs);

      this.pendingRequests.set(request_id, {
        resolve: (value) => resolve(value as TResponse),
        reject,
        timeoutId,
      });

      this.sendEnvelope(envelope);
    });
  }

  sendHeartbeat() {
    if (!this.ws || this.status !== "ready") return;

    this.lastPingAt = Date.now();
    this.armHeartbeatTimeout();

    const envelope: WSHeartbeatEnvelope = {
      v: WS_PROTOCOL_VERSION,
      type: "heartbeat",
      payload: { action: "ping" },
    };

    this.sendEnvelope(envelope);
  }

  private async openConnection() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.updateStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    const url = buildWSUrl();
    const ws = new WebSocket(url);
    this.ws = ws;

    return new Promise<void>((resolve, reject) => {
      const handleOpen = () => {
        this.authenticate().then(resolve).catch(reject);
      };

      const handleMessage = (event: MessageEvent<string>) => {
        this.handleMessage(event.data);
      };

      const handleError = () => {
        this.updateStatus("error");
      };

      const handleClose = () => {
        const wasManual = !this.shouldReconnect;
        this.stopHeartbeat();
        this.ws = null;
        this.connectPromise = null;
        this.authRequestId = null;
        this.rejectAllPending(new WSProtocolError("WebSocket connection closed"));
        this.updateStatus("closed");

        if (!wasManual) {
          this.scheduleReconnect();
        }
      };

      ws.addEventListener("open", handleOpen, { once: true });
      ws.addEventListener("message", handleMessage);
      ws.addEventListener("error", handleError);
      ws.addEventListener("close", handleClose, { once: true });
    });
  }

  private async authenticate() {
    if (!this.ws) {
      throw new Error("WebSocket is not available for authentication");
    }

    this.updateStatus("authenticating");
    const requestId = createRequestId("auth");
    this.authRequestId = requestId;

    const envelope: WSAuthEnvelope = {
      v: WS_PROTOCOL_VERSION,
      type: "auth",
      payload: {
        token: this.token,
      },
    };

    return new Promise<void>((resolve, reject) => {
      const timeoutId = window.setTimeout(() => {
        if (this.authRequestId === requestId) {
          this.authRequestId = null;
        }
        reject(new WSProtocolError("WebSocket authentication timed out"));
      }, REQUEST_TIMEOUT_MS);

      this.pendingRequests.set(requestId, {
        resolve: () => {
          window.clearTimeout(timeoutId);
          this.authRequestId = null;
          this.reconnectAttempts = 0;
          this.updateStatus("ready");
          this.lastPongAt = Date.now();
          this.startHeartbeat();
          this.sendHeartbeat();
          resolve();
        },
        reject: (reason) => {
          window.clearTimeout(timeoutId);
          this.authRequestId = null;
          reject(reason);
        },
        timeoutId,
      });

      this.sendEnvelope(envelope);
    });
  }

  private sendEnvelope(envelope: WSEnvelope) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not open");
    }

    this.ws.send(JSON.stringify(envelope));
  }

  private handleMessage(raw: string) {
    let envelope: WSEnvelope;

    try {
      envelope = JSON.parse(raw) as WSEnvelope;
    } catch {
      return;
    }

    this.envelopeHandlers.forEach((handler) => handler(envelope));

    switch (envelope.type) {
      case "ack":
        this.handleAck(envelope);
        break;
      case "error":
        this.handleErrorEnvelope(envelope);
        break;
      case "event":
        this.handleEventEnvelope(envelope);
        break;
      case "heartbeat":
        this.handleHeartbeatEnvelope(envelope);
        break;
      default:
        break;
    }
  }

  private handleAck(envelope: WSAckEnvelope) {
    const requestId = envelope.payload.request_id ?? this.authRequestId;
    if (!requestId) return;

    const pending = this.pendingRequests.get(requestId);
    if (!pending) return;

    window.clearTimeout(pending.timeoutId);
    this.pendingRequests.delete(requestId);
    pending.resolve(envelope.payload.data);
  }

  private handleErrorEnvelope(envelope: WSErrorEnvelope) {
    const requestId = envelope.payload.request_id ?? this.authRequestId;
    const isUnauthorized = envelope.payload.code === "unauthorized";
    const error = new WSProtocolError(
      envelope.payload.message,
      envelope.payload.code,
      requestId,
      envelope.payload.reason,
      envelope.payload.details,
    );

    if (requestId) {
      const pending = this.pendingRequests.get(requestId);
      if (pending) {
        window.clearTimeout(pending.timeoutId);
        this.pendingRequests.delete(requestId);
        pending.reject(error);
        if (isUnauthorized) {
          this.disconnect();
        }
        return;
      }
    }

    if (isUnauthorized) {
      this.disconnect();
    }
  }

  private handleEventEnvelope(envelope: WSEventEnvelope) {
    const handlers = this.eventHandlers.get(envelope.payload.event);
    handlers?.forEach((handler) => handler(envelope.payload.data, envelope));
  }

  private handleHeartbeatEnvelope(envelope: WSHeartbeatEnvelope) {
    if (envelope.payload.action === "pong") {
      this.lastPongAt = Date.now();
      this.clearHeartbeatTimeout();
      return;
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = window.setInterval(() => {
      this.sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer != null) {
      window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    this.clearHeartbeatTimeout();
    this.lastPingAt = 0;
    this.lastPongAt = 0;
  }

  private armHeartbeatTimeout() {
    this.clearHeartbeatTimeout();

    this.heartbeatTimeoutTimer = window.setTimeout(() => {
      const waitingForPong =
        this.lastPingAt > 0 &&
        (this.lastPongAt === 0 || this.lastPongAt < this.lastPingAt);

      if (!waitingForPong) return;

      if (this.ws) {
        this.ws.close();
      }
    }, HEARTBEAT_TIMEOUT_MS);
  }

  private clearHeartbeatTimeout() {
    if (this.heartbeatTimeoutTimer != null) {
      window.clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect) return;

    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** (this.reconnectAttempts - 1),
      RECONNECT_MAX_MS,
    );

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;

      const token = localStorage.getItem("access_token") || this.token;
      if (!token || !this.shouldReconnect) return;

      void this.connect(token).catch(() => {
        // reconnect 失败时，close handler 会继续安排下一次重连
      });
    }, delay);
  }

  private rejectAllPending(reason: unknown) {
    this.pendingRequests.forEach((pending) => {
      window.clearTimeout(pending.timeoutId);
      pending.reject(reason);
    });
    this.pendingRequests.clear();
  }

  private updateStatus(status: WSConnectionStatus) {
    this.status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }
}

export { WSProtocolError };
export default new WSClient();
