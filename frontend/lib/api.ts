const API_BASE = typeof window !== "undefined" ? "" : "";

function getToken() {
  if (typeof window !== "undefined") {
    return localStorage.getItem("token");
  }
  return null;
}

async function fetcher(path: string, options: RequestInit = {}) {
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      // Don't force JSON content-type for FormData — the browser must set
      // multipart/form-data with the correct boundary itself, otherwise
      // Flask's request.files stays empty and uploads fail silently.
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

export const api = {
  register: (body: any) => fetcher("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: any) => fetcher("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => fetcher("/api/auth/me"),
  listAccounts: () => fetcher("/api/accounts"),
  createAccount: (body: any) => fetcher("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
  deleteAccount: (id: number) => fetcher(`/api/accounts/${id}`, { method: "DELETE" }),
  validateAccount: (id: number) => fetcher(`/api/accounts/${id}/validate`, { method: "POST" }),
  listJobs: (accountId?: number) => fetcher(`/api/jobs${accountId ? `?account_id=${accountId}` : ""}`),
  getJob: (id: number) => fetcher(`/api/jobs/${id}`),
  getJobPosts: (id: number) => fetcher(`/api/jobs/${id}/posts`),
  pauseJob: (id: number) => fetcher(`/api/jobs/${id}/pause`, { method: "POST" }),
  resumeJob: (id: number) => fetcher(`/api/jobs/${id}/resume`, { method: "POST" }),
  deleteJob: (id: number) => fetcher(`/api/jobs/${id}`, { method: "DELETE" }),
  uploadCSV: (formData: FormData) => fetcher("/api/upload", { method: "POST", body: formData, headers: {} }),
  stats: () => fetcher("/api/stats"),
  health: () => fetcher("/api/health"),
};
