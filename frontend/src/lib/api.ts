import { supabase } from "./supabase";

const API_URL = import.meta.env.VITE_API_URL || "";

// FastAPI error payloads have detail as a string, but 422 validation errors
// use an array of {loc, msg} objects — turn either into a readable message.
function extractErrorMessage(payload: unknown, status: number): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        const item = d as { loc?: unknown[]; msg?: unknown };
        if (item && Array.isArray(item.loc) && typeof item.msg === "string") {
          return `${item.loc.join(".")}: ${item.msg}`;
        }
        return null;
      })
      .filter((p): p is string => p !== null);
    if (parts.length) return `Validation failed — ${parts.join("; ")}`;
  }
  return `Request failed (HTTP ${status})`;
}

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  // With FormData the browser must set the Content-Type itself so the multipart
  // boundary is included; forcing application/json makes the body unparseable.
  const isFormData = options.body instanceof FormData;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    // Token expired or invalid - sign out
    const { supabase: sb } = await import("./supabase");
    await sb.auth.signOut();
    window.location.href = "/login";
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => null);
    throw new Error(extractErrorMessage(error, res.status));
  }

  return res.json();
}

export const api = {
  get: <T = unknown>(path: string) => apiFetch<T>(path),
  post: <T = unknown>(path: string, body: unknown) => apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T = unknown>(path: string, body: unknown) => apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T = unknown>(path: string, body: unknown) => apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T = unknown>(path: string, body?: unknown) => apiFetch<T>(path, { method: "DELETE", ...(body ? { body: JSON.stringify(body) } : {}) }),
};
