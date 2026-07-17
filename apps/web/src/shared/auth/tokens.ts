export const ACCESS_TOKEN_STORAGE_KEY = "secure-knowledge.access-token";

export function storeAccessToken(accessToken: string): void {
  const normalizedToken = accessToken.trim();
  if (!normalizedToken) {
    throw new Error("Access token cannot be empty.");
  }
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, normalizedToken);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function getAccessToken(): string | null {
  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  return accessToken?.trim() || null;
}
