const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
}

export interface RegistrationData {
  email: string;
  password: string;
  displayName: string;
}

export class AuthApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function responseError(
  response: Response,
  fallbackMessage: string,
): Promise<AuthApiError> {
  let message = fallbackMessage;
  try {
    const payload: unknown = await response.json();
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      message = payload.detail;
    }
  } catch {
    // The status-specific fallback is safe when the API has no JSON body.
  }
  return new AuthApiError(message, response.status);
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams({
    username: email.trim(),
    password,
  });
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    body,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  if (!response.ok) {
    throw await responseError(response, "Unable to sign in.");
  }

  return (await response.json()) as TokenResponse;
}

export async function register(
  data: RegistrationData,
): Promise<UserResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    body: JSON.stringify({
      email: data.email.trim(),
      password: data.password,
      display_name: data.displayName.trim() || null,
    }),
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw await responseError(response, "Unable to create your account.");
  }

  return (await response.json()) as UserResponse;
}
