/** Development sign-in (D050; UI-001 §4, §8). The token is checked against the API before it is kept. */

import { useState, type FormEvent } from "react";

import { ApiError, createApi } from "../api/client";
import { ErrorNotice } from "../app/ErrorNotice";

export function SignIn({ onSignedIn }: { onSignedIn: (token: string) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const candidate = token.trim();
    if (!candidate) return;
    setBusy(true);
    setError(null);
    try {
      await createApi({ token: () => candidate }).listProjects();
      onSignedIn(candidate);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? new ApiError(401, { code: "UNAUTHORIZED", message: "That token is not recognized." }, "") : e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="sign-in">
      <h1>Home Design — VS-01</h1>
      <form onSubmit={submit}>
        <label htmlFor="dev-token">Development token</label>
        <input id="dev-token" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />
        <button type="submit" disabled={busy || !token.trim()}>
          Sign in
        </button>
        <p className="hint">Development sign-in only. Tokens are configured on the server (HOMEDESIGN_DEV_TOKENS).</p>
        <ErrorNotice error={error} />
      </form>
    </main>
  );
}
