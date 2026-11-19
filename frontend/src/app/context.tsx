import { createContext, useContext } from "react";

import type { Api } from "../api/client";
import type { UnitSystem } from "../units/length";

export interface AppContextValue {
  api: Api;
  units: UnitSystem;
  setUnits: (units: UnitSystem) => void;
  /** Called on 401: drop the token and return to sign-in. */
  signOut: () => void;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const value = useContext(AppContext);
  if (!value) throw new Error("AppContext is missing");
  return value;
}
