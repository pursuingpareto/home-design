/** Command envelopes (interfaces.md §2) and error-detail placement (D036, D037; UI-001 §5). */

import type { ErrorDetail, SetFootprintDimensions, UndoToRevision } from "../api/types";

export function newCommandId(): string {
  return crypto.randomUUID();
}

export function footprintCommand(projectId: string, baseRevisionId: string, widthM: number, depthM: number): SetFootprintDimensions {
  return {
    command_id: newCommandId(),
    project_id: projectId,
    base_revision_id: baseRevisionId,
    type: "SetFootprintDimensions",
    args: { width_m: widthM, depth_m: depthM },
  };
}

export function undoCommand(projectId: string, baseRevisionId: string, targetRevisionId: string): UndoToRevision {
  return {
    command_id: newCommandId(),
    project_id: projectId,
    base_revision_id: baseRevisionId,
    type: "UndoToRevision",
    args: { target_revision_id: targetRevisionId },
  };
}

/**
 * Attach details to inputs: a detail belongs to an input when its `path` or any `related_paths` entry
 * is that input's argument path (D037: the server adds the argument path for fields it set).
 */
export function placeDetails<F extends string>(
  details: readonly ErrorDetail[],
  fields: Record<F, string>,
): { byField: Partial<Record<F, ErrorDetail[]>>; other: ErrorDetail[] } {
  const byField: Partial<Record<F, ErrorDetail[]>> = {};
  const other: ErrorDetail[] = [];
  for (const detail of details) {
    const paths = [detail.path, ...(detail.related_paths ?? [])];
    const matched = (Object.keys(fields) as F[]).filter((field) => paths.includes(fields[field]));
    if (matched.length === 0) other.push(detail);
    for (const field of matched) (byField[field] ??= []).push(detail);
  }
  return { byField, other };
}

export const DETAIL_TEXT: Readonly<Record<string, string>> = {
  OUT_OF_SUPPORTED_RANGE: "Outside the supported range",
  OUT_OF_RANGE: "Out of range",
  WRONG_TYPE: "Wrong type",
  MISSING_FIELD: "Required",
  UNKNOWN_FIELD: "Not allowed",
  INVALID_TIMESTAMP: "Not a valid date",
  DUPLICATE_PRICE_KEY: "Duplicate price row",
  DANGLING_REFERENCE: "Refers to something that does not exist",
  UNSUPPORTED_VALUE: "Not supported",
  // UI-004 §8.3: the opening fit and the girt fit (MODEL-006 §5.2).
  OPENING_OUTSIDE_WALL: "The opening's framing does not fit inside the wall",
  OPENING_CROSSES_BRACE: "The opening's framing meets a knee brace",
  OPENINGS_OVERLAP: "The opening's framing overlaps another opening's",
  GIRT_CROSSES_BRACE: "A girt would cross a knee brace",
};

/** A short human label for a detail code; the code itself stays visible for support. */
export function describeDetail(detail: ErrorDetail): string {
  return `${DETAIL_TEXT[detail.code] ?? "Invalid"} (${detail.code})`;
}
