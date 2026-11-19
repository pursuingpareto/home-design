/**
 * Preview → impact dialog → confirm, for consequential commands (dependencies.md §5; UI-001 §5).
 *
 * - The same command (same `command_id`) is previewed and committed; in-transit failures retry it.
 * - An expired or invalid preview is never confirmed silently: the command is previewed again and the
 *   user confirms again.
 * - A revision conflict reloads the head and asks for a fresh preview.
 */

import { useCallback, useState } from "react";

import { ApiError, commitWithRetry, type Api } from "../api/client";
import type { Command, CommitResponse, PreviewResponse } from "../api/types";

export type FlowState =
  | { step: "idle" }
  | { step: "previewing"; command: Command }
  | { step: "review"; command: Command; preview: PreviewResponse; notice?: string }
  | { step: "committing"; command: Command; preview: PreviewResponse }
  | { step: "error"; command: Command; error: ApiError | unknown; notice?: string };

export interface CommandFlowOptions {
  api: Api;
  projectId: string;
  onCommitted: (result: CommitResponse) => void;
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
      onCommitted(body);
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

  const cancel = useCallback(() => setState({ step: "idle" }), []);

  return { state, preview, confirm, cancel };
}
