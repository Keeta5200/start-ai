export const AUTH_COOKIE_NAME = "start-ai-session";
export const AUTH_COOKIE_VALUE = "authenticated";
export const AUTH_TOKEN_COOKIE_NAME = "start-ai-token";

export function buildAuthCookie() {
  const maxAge = 60 * 60 * 24 * 30;
  return `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

export function buildExpiredAuthCookie() {
  return `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function buildTokenCookie(token: string) {
  const maxAge = 60 * 60 * 24 * 30;
  return `${AUTH_TOKEN_COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

export function buildExpiredTokenCookie() {
  return `${AUTH_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}
