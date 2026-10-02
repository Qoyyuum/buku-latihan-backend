const API_URL: string =
  (import.meta.env.PUBLIC_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

const HEADLESS = `${API_URL}/_allauth/app/v1`;
const TOKEN_KEY = "bl_session_token";

export interface AuthError {
  code: string;
  message: string;
  param?: string;
}

export interface AuthResponse {
  status: number;
  errors?: AuthError[];
  meta?: {
    is_authenticated?: boolean;
    session_token?: string;
    access_token?: string;
  };
  data?: unknown;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

/** Fetch wrapper adding the allauth session token header. */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("X-Session-Token", token);
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 || res.status === 410) setToken(null);
  return res;
}

/** Same wrapper rooted at the headless API. */
export function headlessFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("X-Session-Token", token);
  return fetch(`${HEADLESS}${path}`, { ...init, headers });
}

export function post(path: string, body: unknown): Promise<Response> {
  return headlessFetch(path, { method: "POST", body: JSON.stringify(body) });
}

export async function login(
  username: string,
  password: string,
): Promise<AuthResponse> {
  const res = await post("/auth/login", { username, password });
  const data = (await res.json()) as AuthResponse;
  const token = data.meta?.session_token;
  if (token) setToken(token);
  return data;
}

export async function logout(): Promise<void> {
  await headlessFetch("/auth/session", { method: "DELETE" });
  setToken(null);
}

export function requireAuth(): void {
  if (!getToken()) window.location.href = "/login";
}

/** Render allauth's {errors:[...]} shape as a readable string. */
export function errorMessage(data: AuthResponse | null): string {
  const first = data?.errors?.[0];
  return first?.message ?? "Something went wrong. Please try again.";
}
