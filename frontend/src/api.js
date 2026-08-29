function csrfToken() {
  return document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("csrftoken="))
    ?.split("=")[1];
}

export async function request(path, options = {}) {
  const method = options.method || "GET";
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body) headers["Content-Type"] = "application/json";
  if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(method) && csrfToken()) {
    headers["X-CSRFToken"] = csrfToken();
  }
  const response = await fetch(path, { ...options, method, headers, credentials: "include" });
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || Object.values(data).flat().join(" ") || "Request failed.");
    error.status = response.status;
    error.details = data;
    throw error;
  }
  return data;
}

function filteredListPath(resource, filters = {}) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim()) query.set(key, value);
  });
  const queryString = query.toString();
  return `/api/${resource}/${queryString ? `?${queryString}` : ""}`;
}

export const api = {
  csrf: () => request("/api/auth/csrf/"),
  currentUser: () => request("/api/auth/me/"),
  dashboardSummary: () => request("/api/dashboard/summary/"),
  describeCron: (cronRule) => request(`/api/describe-cron/?cron_rule=${encodeURIComponent(cronRule)}`),
  health: () => request("/api/health/"),
  recreateMissingCronFiles: () => request("/api/health/cron-files/recreate/", { method: "POST" }),
  login: (credentials) => request("/api/auth/login/", { method: "POST", body: JSON.stringify(credentials) }),
  logout: () => request("/api/auth/logout/", { method: "POST" }),
  jobFilterOptions: () => request("/api/jobs/filter-options/"),
  list: (resource, page, filters) => request(page || filteredListPath(resource, filters)),
  save: (resource, payload, id) => request(`/api/${resource}/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  }),
  remove: (resource, id) => request(`/api/${resource}/${id}/`, { method: "DELETE" }),
};
