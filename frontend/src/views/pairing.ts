/**
 * The only path to rendering 2D and 3D together (artifacts.md §4, §10 test 6; UI-001 §6).
 *
 * The views pair only when both envelopes are CURRENT and share `source_revision_id`. Otherwise each
 * view reports its own status, and neither shows geometry, so older geometry never appears under a
 * newer revision.
 */

import type { Mesh3dPayload, MeshEnvelope, Plan2dPayload, PlanEnvelope } from "../api/types";

export type ViewState = "LOADING" | PlanEnvelope["status"];

export type Pairing =
  | { kind: "paired"; revisionId: string; head: boolean; plan: Plan2dPayload; mesh: Mesh3dPayload }
  | { kind: "unpaired"; plan: ViewState; mesh: ViewState; mismatch: boolean };

export function pairViews(plan: PlanEnvelope | null | undefined, mesh: MeshEnvelope | null | undefined): Pairing {
  const planState: ViewState = plan ? plan.status : "LOADING";
  const meshState: ViewState = mesh ? mesh.status : "LOADING";
  if (!plan || !mesh) return { kind: "unpaired", plan: planState, mesh: meshState, mismatch: false };
  const mismatch = plan.source_revision_id !== mesh.source_revision_id;
  if (mismatch || plan.status !== "CURRENT" || mesh.status !== "CURRENT" || !plan.payload || !mesh.payload) {
    return { kind: "unpaired", plan: planState, mesh: meshState, mismatch };
  }
  return { kind: "paired", revisionId: plan.source_revision_id, head: plan.head && mesh.head, plan: plan.payload, mesh: mesh.payload };
}
