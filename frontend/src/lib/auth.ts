export const AUTH_COOKIE_NAME = "start-ai-session";
export const AUTH_COOKIE_VALUE = "authenticated";
export const AUTH_TOKEN_COOKIE_NAME = "start-ai-token";
export const REMEMBER_ME_KEY = "start-ai-remember-me";
export const LAST_EMAIL_KEY = "start-ai-last-email";
export const PENDING_ANALYSIS_KEY = "start-ai-pending-analysis";
export const PENDING_ANALYSIS_STALE_MS = 1000 * 60 * 20;

export type PendingAnalysisRecord = {
  id: string;
  createdAt: string;
  videoFilename?: string;
};

function readFromStorage(storage: Storage, key: string) {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function writeToStorage(storage: Storage, key: string, value: string) {
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function removeFromStorage(storage: Storage, key: string) {
  try {
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function getStoredAuthToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return readFromStorage(localStorage, "start-ai-token") ?? readFromStorage(sessionStorage, "start-ai-token");
}

export function buildAuthCookie(persistent = true) {
  const maxAge = 60 * 60 * 24 * 30;
  const persistence = persistent ? `; Max-Age=${maxAge}` : "";
  return `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}; Path=/${persistence}; SameSite=Lax`;
}

export function buildExpiredAuthCookie() {
  return `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function buildTokenCookie(token: string, persistent = true) {
  const maxAge = 60 * 60 * 24 * 30;
  const persistence = persistent ? `; Max-Age=${maxAge}` : "";
  return `${AUTH_TOKEN_COOKIE_NAME}=${encodeURIComponent(token)}; Path=/${persistence}; SameSite=Lax`;
}

export function buildExpiredTokenCookie() {
  return `${AUTH_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function savePendingAnalysis(record: PendingAnalysisRecord) {
  if (typeof window === "undefined") {
    return;
  }

  writeToStorage(localStorage, PENDING_ANALYSIS_KEY, JSON.stringify(record));
}

export function clearPendingAnalysis() {
  if (typeof window === "undefined") {
    return;
  }

  removeFromStorage(localStorage, PENDING_ANALYSIS_KEY);
}

export function readPendingAnalysis(): PendingAnalysisRecord | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = readFromStorage(localStorage, PENDING_ANALYSIS_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<PendingAnalysisRecord>;
    if (typeof parsed?.id === "string" && typeof parsed?.createdAt === "string") {
      return {
        id: parsed.id,
        createdAt: parsed.createdAt,
        videoFilename: typeof parsed.videoFilename === "string" ? parsed.videoFilename : undefined,
      };
    }
  } catch {
    // Fall through to legacy string support.
  }

  return {
    id: rawValue,
    createdAt: new Date(0).toISOString(),
  };
}

export function isPendingAnalysisStale(createdAt: string, now = Date.now()) {
  const createdAtMs = new Date(createdAt).getTime();
  if (Number.isNaN(createdAtMs)) {
    return true;
  }

  return now - createdAtMs > PENDING_ANALYSIS_STALE_MS;
}

export function getLocalStorageItem(key: string) {
  if (typeof window === "undefined") {
    return null;
  }
  return readFromStorage(localStorage, key);
}

export function getSessionStorageItem(key: string) {
  if (typeof window === "undefined") {
    return null;
  }
  return readFromStorage(sessionStorage, key);
}

export function setLocalStorageItem(key: string, value: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return writeToStorage(localStorage, key, value);
}

export function setSessionStorageItem(key: string, value: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return writeToStorage(sessionStorage, key, value);
}

export function removeLocalStorageItem(key: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return removeFromStorage(localStorage, key);
}

export function removeSessionStorageItem(key: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return removeFromStorage(sessionStorage, key);
}
