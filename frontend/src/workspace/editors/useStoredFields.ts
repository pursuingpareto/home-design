/**
 * Editable fields that start from stored values (UI-001 §13, UI-002 §4). Untouched fields resolve to
 * the stored value exactly; typed text is kept across tab switches and reloads until Reset.
 */

import { useCallback, useEffect, useState } from "react";

export interface FieldState {
  text: string;
  dirty: boolean;
}

export type Parsed = { ok: true; value: number } | { ok: false; error: string };

export function useStoredFields<K extends string>(keys: readonly K[], stored: Partial<Record<K, number>> | null, format: (key: K, value: number) => string) {
  const blank = () => Object.fromEntries(keys.map((k) => [k, { text: "", dirty: false }])) as Record<K, FieldState>;
  const [fields, setFields] = useState<Record<K, FieldState>>(blank);
  const signature = stored ? keys.map((k) => `${k}=${stored[k] ?? ""}`).join(";") : "";

  // Refill untouched fields when the stored values or the display format change.
  useEffect(() => {
    if (!stored) return;
    setFields((f) => {
      const next = { ...f };
      for (const k of keys) {
        const value = stored[k];
        if (!next[k].dirty) next[k] = { text: value === undefined ? "" : format(k, value), dirty: false };
      }
      return next;
    });
  }, [signature, format]); // eslint-disable-line react-hooks/exhaustive-deps

  const setText = useCallback((key: K, text: string) => setFields((f) => ({ ...f, [key]: { text, dirty: true } })), []);

  const reset = useCallback(() => {
    setFields(() => {
      const next = blank();
      for (const k of keys) {
        const value = stored?.[k];
        next[k] = { text: value === undefined ? "" : format(k, value), dirty: false };
      }
      return next;
    });
  }, [signature, format]); // eslint-disable-line react-hooks/exhaustive-deps

  /** The value to send: stored when untouched, parsed when edited. */
  const resolve = useCallback(
    (key: K, parse: (text: string) => Parsed): Parsed => {
      const state = fields[key];
      const value = stored?.[key];
      if (!state.dirty && value !== undefined) return { ok: true, value };
      return parse(state.text);
    },
    [fields, stored],
  );

  return { fields, setText, reset, resolve };
}
