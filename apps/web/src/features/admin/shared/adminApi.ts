const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class AdminApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function fetchAdminResource<T>(
  organizationId: string,
  resourcePath: `/${string}`,
  signal?: AbortSignal,
): Promise<T> {
  const organizationPath = encodeURIComponent(organizationId);
  const path = `/organizations/${organizationPath}/admin${resourcePath}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new AdminApiError(
      `Admin request failed with status ${response.status}.`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export async function createAdminResource<TResponse, TBody>(
  organizationId: string,
  resourcePath: `/${string}`,
  body: TBody,
  signal?: AbortSignal,
): Promise<TResponse> {
  const organizationPath = encodeURIComponent(organizationId);
  const path = `/organizations/${organizationPath}/admin${resourcePath}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: JSON.stringify(body),
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new AdminApiError(
      `Admin request failed with status ${response.status}.`,
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}
