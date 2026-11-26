const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

function resolveUrl(endpoint: string) {
  const cleanEndpoint = endpoint.startsWith("/api")
    ? endpoint
    : `/api${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
  return API_BASE ? `${API_BASE}${cleanEndpoint}` : cleanEndpoint;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * The single way the frontend talks to the backend.
 *
 * ``NEXT_PUBLIC_API_URL`` is honoured for every call, so a deployed frontend
 * reaches the real API instead of relying on a dev-only rewrite.
 */
export async function apiFetch(endpoint: string, options: RequestInit = {}, token?: string) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(resolveUrl(endpoint), { ...options, headers });
  } catch (err) {
    throw new ApiError(
      `Could not reach the Ticket Fox API at ${API_BASE || "this origin"}. Is the backend running?`,
      0
    );
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const detail =
      typeof errorData?.detail === "string"
        ? errorData.detail
        : errorData?.detail
          ? JSON.stringify(errorData.detail)
          : "API request failed";
    throw new ApiError(detail, res.status);
  }

  return res.json();
}

