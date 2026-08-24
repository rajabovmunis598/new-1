const ACCESS_KEY = "munis_access";
const REFRESH_KEY = "munis_refresh";

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function errorMessage(data, fallback) {
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return data.map((item) => errorMessage(item, "")).filter(Boolean).join(" ");
  if (data.detail) return errorMessage(data.detail, fallback);
  if (data.non_field_errors) return errorMessage(data.non_field_errors, fallback);

  const messages = Object.entries(data).flatMap(([field, value]) => {
    const label = field.replaceAll("_", " ");
    const message = errorMessage(value, "");
    return message ? `${label}: ${message}` : [];
  });
  return messages.join(" ") || fallback;
}

class ApiClient {
  constructor() {
    this.refreshPromise = null;
    this.socket = null;
    this.socketTimer = null;
    this.socketAttempts = 0;
    this.socketClosedByUser = false;
  }

  get accessToken() { return sessionStorage.getItem(ACCESS_KEY) || ""; }
  get refreshToken() { return sessionStorage.getItem(REFRESH_KEY) || ""; }
  get authenticated() { return Boolean(this.accessToken && this.refreshToken); }

  saveTokens(payload = {}) {
    const access = payload.access || payload.tokens?.access;
    const refresh = payload.refresh || payload.tokens?.refresh;
    if (access) sessionStorage.setItem(ACCESS_KEY, access);
    if (refresh) sessionStorage.setItem(REFRESH_KEY, refresh);
  }

  clearTokens() {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  }

  async request(path, options = {}, canRefresh = true) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);

    let body = options.body;
    if (body !== undefined && body !== null && !(body instanceof FormData) && typeof body !== "string") {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(path, { ...options, headers, body });
    } catch (error) {
      throw new ApiError("Пайваст ба сервер дастрас нест. Интернет ё серверро санҷед.", 0, error);
    }

    if (response.status === 401 && canRefresh && this.refreshToken && !path.includes("/token/refresh/")) {
      const refreshed = await this.refreshAccess();
      if (refreshed) return this.request(path, options, false);
    }

    if (response.status === 204) return null;
    const type = response.headers.get("content-type") || "";
    const data = type.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const fallback = response.status >= 500
        ? "Дар сервер хатогӣ рӯй дод. Баъдтар дубора кӯшиш кунед."
        : "Дархост иҷро нашуд.";
      throw new ApiError(errorMessage(data, fallback), response.status, data);
    }
    return data;
  }

  async refreshAccess() {
    if (this.refreshPromise) return this.refreshPromise;
    const refresh = this.refreshToken;
    if (!refresh) return false;

    this.refreshPromise = (async () => {
      try {
        const response = await fetch("/api/auth/token/refresh/", {
          method: "POST",
          headers: { "Accept": "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
        });
        if (!response.ok) throw new Error("refresh failed");
        this.saveTokens(await response.json());
        return true;
      } catch (_) {
        this.clearTokens();
        return false;
      } finally {
        this.refreshPromise = null;
      }
    })();
    return this.refreshPromise;
  }

  get(path) { return this.request(path); }
  post(path, body = {}) { return this.request(path, { method: "POST", body }); }
  patch(path, body = {}) { return this.request(path, { method: "PATCH", body }); }
  put(path, body = {}) { return this.request(path, { method: "PUT", body }); }
  delete(path) { return this.request(path, { method: "DELETE" }); }

  async login(credentials) {
    const data = await this.request("/api/auth/login/", { method: "POST", body: credentials }, false);
    this.saveTokens(data);
    return data.user;
  }

  async register(payload) {
    const data = await this.request("/api/auth/register/", { method: "POST", body: payload }, false);
    this.saveTokens(data);
    return data;
  }

  async logout() {
    const refresh = this.refreshToken;
    try {
      if (refresh) await this.post("/api/auth/logout/", { refresh });
    } finally {
      this.disconnectSocket();
      this.clearTokens();
    }
  }

  connectSocket(onEvent, onStatus = () => {}) {
    this.disconnectSocket();
    if (!this.accessToken) return;
    this.socketClosedByUser = false;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/dashboard/?token=${encodeURIComponent(this.accessToken)}`;
    onStatus("connecting");
    this.socket = new WebSocket(url);

    this.socket.addEventListener("open", () => {
      this.socketAttempts = 0;
      onStatus("connected");
    });
    this.socket.addEventListener("message", (event) => {
      try { onEvent(JSON.parse(event.data)); } catch (_) { /* Ignore malformed events. */ }
    });
    this.socket.addEventListener("close", () => {
      this.socket = null;
      if (this.socketClosedByUser || !this.authenticated) {
        onStatus("disconnected");
        return;
      }
      onStatus("reconnecting");
      const wait = Math.min(30000, 1000 * (2 ** this.socketAttempts++));
      this.socketTimer = window.setTimeout(() => this.connectSocket(onEvent, onStatus), wait);
    });
    this.socket.addEventListener("error", () => onStatus("reconnecting"));
  }

  disconnectSocket() {
    this.socketClosedByUser = true;
    if (this.socketTimer) window.clearTimeout(this.socketTimer);
    this.socketTimer = null;
    if (this.socket) this.socket.close();
    this.socket = null;
  }
}

export const api = new ApiClient();

export function results(data) {
  if (Array.isArray(data)) return data;
  return data?.results || [];
}
