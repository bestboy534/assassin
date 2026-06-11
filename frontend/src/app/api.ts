const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type OrganizationSummary = {
  id: string;
  name: string;
  slug: string;
  role: string;
};

export type AuthSession = {
  user: {
    id: string;
    email: string;
    display_name: string;
    status: string;
  };
  organizations: OrganizationSummary[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      message = (await response.text()) || message;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function registerAccount(input: {
  email: string;
  password: string;
  displayName: string;
  organizationName: string;
}) {
  return request<AuthSession>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      display_name: input.displayName,
      organization_name: input.organizationName,
    }),
  });
}

export function loginAccount(input: { email: string; password: string }) {
  return request<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCurrentSession() {
  return request<AuthSession>("/api/v1/auth/me");
}

export function logoutAccount() {
  return request<{ status: string }>("/api/v1/auth/logout", { method: "POST" });
}
