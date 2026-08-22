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
    throw error;
  }
  return data;
}

export const api = {
  csrf: () => request("/api/auth/csrf/"),
  currentUser: () => request("/api/auth/me/"),
  login: (credentials) => request("/api/auth/login/", { method: "POST", body: JSON.stringify(credentials) }),
  logout: () => request("/api/auth/logout/", { method: "POST" }),
  list: (resource) => request(`/api/${resource}/`),
  save: (resource, payload, id) => request(`/api/${resource}/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  }),
  remove: (resource, id) => request(`/api/${resource}/${id}/`, { method: "DELETE" }),
};
