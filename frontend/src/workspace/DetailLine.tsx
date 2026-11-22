/** Error details with their paths read as names (UI-004 §8.3), for the dialog and the Walls tab. */

import type { ErrorDetail } from "../api/types";
import { describeDetail } from "./commands";
import { pathLabel, type SnapshotLabels } from "./wallLabels";

/** A detail's text, with the labels of the other records its paths name (UI-004 §8.2: "the other opening is named"). */
export function namedText(detail: ErrorDetail, labels: SnapshotLabels, self: string | null): string {
  const names = [detail.path, ...(detail.related_paths ?? [])]
    .map((path) => /^entities\[([0-9a-f-]{36})\]/.exec(path)?.[1])
    .filter((id): id is string => id !== undefined && id !== self)
    .map((id) => labels.opening(id))
    .filter((name): name is string => name !== undefined);
  const unique = [...new Set(names)];
  return unique.length > 0 ? `${describeDetail(detail)}: with ${unique.join("; ")}` : describeDetail(detail);
}

/** A detail line with its path read as a name, the raw path in its tooltip (UI-004 §8.3). */
export function DetailLine({ detail, labels }: { detail: ErrorDetail; labels: SnapshotLabels }) {
  const name = pathLabel(detail.path, labels);
  return (
    <>
      <code title={detail.path}>{name ?? (detail.path || "(document)")}</code>: {namedText(detail, labels, /^entities\[([0-9a-f-]{36})\]/.exec(detail.path)?.[1] ?? null)}
    </>
  );
}

