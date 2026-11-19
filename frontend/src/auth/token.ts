/**
 * Development bearer token (D050; UI-001 §8, item 7). Held in sessionStorage, so it is cleared with
 * the tab, and sent only as an Authorization header. Never logged or put in a URL.
 */

const KEY = "homedesign.devToken";

export function readToken(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(KEY, token);
    else sessionStorage.removeItem(KEY);
  } catch {
    // Storage may be unavailable (private mode); the token then lives only in memory for this page.
  }
}
