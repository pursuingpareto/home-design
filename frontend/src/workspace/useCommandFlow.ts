/**
 * Preview → impact dialog → confirm, for consequential commands (dependencies.md §5; UI-001 §5).
 *
 * - The same command (same `command_id`) is previewed and committed; in-transit failures retry it.
 * - An expired or invalid preview is never confirmed silently: the command is previewed again and the
 *   user confirms again.
 * - A revision conflict reloads the head and asks for a fresh preview.
 * - Routine commands may be applied directly, without a preview (UI-002 §5).
 */

import { useCallback, useState } from "react";

import { ApiError, commitWithRetry, type Api } from "../api/client";
import type { Command, CommitResponse, PreviewResponse } from "../api/types";

export type FlowState =
  | { step: "idle"; failed?: { command: Command; error: unknown } } // a closed error stays on its fields
  | { step: "previewing"; command: Command }
  | { step: "review"; command: Command; preview: PreviewResponse; notice?: string }
  | { step: "committing"; command: Command; preview: PreviewResponse }
  | { step: "applying"; command: Command }
  | { step: "error"; command: Command; error: ApiError | unknown; notice?: string };

export interface CommandFlowOptions {
  api: Api;
  projectId: string;
  onCommitted: (result: CommitResponse, command: Command) => void;
  onConflict: () => void;
  onUnauthorized: () => void;
}

export function useCommandFlow({ api, projectId, onCommitted, onConflict, onUnauthorized }: CommandFlowOptions) {
  const [state, setState] = useState<FlowState>({ step: "idle" });

  const fail = useCallback(
    (command: Command, error: unknown, notice?: string) => {
      if (error instanceof ApiError && error.status === 401) onUnauthorized();
      setState({ step: "error", command, error, notice });
    },
    [onUnauthorized],
  );

  const preview = useCallback(
    async (command: Command, notice?: string) => {
      setState({ step: "previewing", command });
      try {
        const result = await api.preview(projectId, command);
        setState({ step: "review", command, preview: result, notice });
      } catch (error) {
        if (error instanceof ApiError && error.code === "REVISION_CONFLICT") {
          onConflict();
          fail(command, error, "The project changed since you started. It has been reloaded; preview your change again.");
        } else {
          fail(command, error);
        }
      }
    },
    [api, projectId, fail, onConflict],
  );

  const confirm = useCallback(async () => {
    if (state.step !== "review" || state.preview.is_noop) return;
    const { command, preview: current } = state;
    setState({ step: "committing", command, preview: current });
    try {
      const { body } = await commitWithRetry(api, projectId, command, current.preview_token);
      setState({ step: "idle" });
      onCommitted(body, command);
    } catch (error) {
      if (error instanceof ApiError && (error.code === "PREVIEW_EXPIRED" || error.code === "PREVIEW_INVALID")) {
        await preview(command, "The preview expired or no longer matched, so it was refreshed. Review the impact and confirm again.");
      } else if (error instanceof ApiError && error.code === "REVISION_CONFLICT") {
        onConflict();
        fail(command, error, "Someone else changed the project first. It has been reloaded; preview your change again.");
      } else {
        fail(command, error);
      }
    }
  }, [state, api, projectId, onCommitted, onConflict, preview, fail]);

  /**
   * Commit a routine command without a preview (dependencies.md §4.1; UI-002 §5). The commit still
   * validates fully. Resolves with the result, or null when it failed (the state then holds the error).
   */
  const apply = useCallback(
    async (command: Command): Promise<CommitResponse | null> => {
      setState({ step: "applying", command });
      try {
        const { body } = await commitWithRetry(api, projectId, command, null);
        setState({ step: "idle" });
        onCommitted(body, command);
        return body;
      } catch (error) {
        if (error instanceof ApiError && error.code === "REVISION_CONFLICT") {
          onConflict();
          fail(command, error, "Someone else changed the project first. It has been reloaded; apply your change again.");
        } else {
          fail(command, error);
        }
        return null;
      }
    },
    [api, projectId, onCommitted, onConflict, fail],
  );

  const cancel = useCallback(() => setState((s) => (s.step === "error" ? { step: "idle", failed: { command: s.command, error: s.error } } : { step: "idle" })), []);

  return { state, preview, confirm, apply, cancel };
}
