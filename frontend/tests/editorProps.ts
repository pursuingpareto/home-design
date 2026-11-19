import { vi } from "vitest";

import type { Command, CommitResponse } from "../src/api/types";
import { fixture } from "./fixtures";

/** Editor props with an idle flow: `preview` and `apply` are spies. */
export function editorProps(
  preview = vi.fn<(command: Command) => Promise<void>>(async () => {}),
  apply = vi.fn<(command: Command) => Promise<CommitResponse | null>>(async () => null),
) {
  return {
    projectId: fixture.project.project_id,
    snapshot: fixture.snapshot,
    units: "imperial" as const,
    flow: { state: { step: "idle" as const }, preview, apply },
    onApplied: vi.fn(),
  };
}
