import { getAccessToken } from "../../../shared/auth/tokens";

export {
  ACCESS_TOKEN_STORAGE_KEY,
  clearAccessToken,
  getAccessToken,
  storeAccessToken,
} from "../../../shared/auth/tokens";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class AdminApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function createAuthorizedHeaders(
  additionalHeaders: Record<string, string> = {},
): Headers {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new AdminApiError("Authentication is required.", 401);
  }

  return new Headers({
    Accept: "application/json",
    Authorization: `Bearer ${accessToken}`,
    ...additionalHeaders,
  });
}

export async function fetchAdminResource<T>(
  organizationId: string,
  resourcePath: `/${string}`,
  signal?: AbortSignal,
): Promise<T> {
  const organizationPath = encodeURIComponent(organizationId);
  const path = `/organizations/${organizationPath}/admin${resourcePath}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: createAuthorizedHeaders(),
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
    headers: createAuthorizedHeaders({
      "Content-Type": "application/json",
    }),
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
