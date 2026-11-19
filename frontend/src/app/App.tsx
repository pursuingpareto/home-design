import { useCallback, useMemo, useState } from "react";

import { createApi } from "../api/client";
import { readToken, writeToken } from "../auth/token";
import { SignIn } from "../auth/SignIn";
import { ProjectsPage } from "../projects/ProjectsPage";
import type { UnitSystem } from "../units/length";
import { Workspace } from "../workspace/Workspace";
import { AppContext } from "./context";
import { readUnits, writeUnits } from "./preferences";
import { navigate, useRoute } from "./routing";

export function App() {
  const route = useRoute();
  const [token, setToken] = useState<string | null>(() => readToken());
  const [units, setUnitsState] = useState<UnitSystem>(() => readUnits());
  const tokenRef = useMemo(() => ({ current: token }), []); // eslint-disable-line react-hooks/exhaustive-deps
  tokenRef.current = token;
  const api = useMemo(() => createApi({ token: () => tokenRef.current }), [tokenRef]);

  const signOut = useCallback(() => {
    writeToken(null);
    setToken(null);
  }, []);
  const setUnits = useCallback((next: UnitSystem) => {
    writeUnits(next);
    setUnitsState(next);
  }, []);
  const context = useMemo(() => ({ api, units, setUnits, signOut }), [api, units, setUnits, signOut]);

  if (!token) {
    return (
      <SignIn
        onSignedIn={(t) => {
          writeToken(t);
          setToken(t);
          if (route.name === "sign-in") navigate({ name: "projects" });
        }}
      />
    );
  }

  return (
    <AppContext.Provider value={context}>
      <header className="app-header">
        <span className="brand">Home Design</span>
        <div role="group" aria-label="Units">
          {(["imperial", "metric"] as const).map((u) => (
            <button key={u} type="button" aria-pressed={units === u} onClick={() => setUnits(u)}>
              {u === "imperial" ? "ft-in" : "m"}
            </button>
          ))}
        </div>
        <button type="button" onClick={signOut}>
          Sign out
        </button>
      </header>
      {route.name === "workspace" ? (
        <Workspace key={`${route.projectId}/${route.revisionId ?? "head"}`} projectId={route.projectId} revisionId={route.revisionId} />
      ) : (
        <ProjectsPage />
      )}
    </AppContext.Provider>
  );
}
