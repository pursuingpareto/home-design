/** Typed access to the captured Reference House 001 fixtures (backend: homedesign.api.ui_fixtures). */

import raw from "./fixtures/reference-house-001.json";

import type {
  EstimateEnvelope,
  Manifest,
  MeshEnvelope,
  PlanEnvelope,
  PreviewResponse,
  ProjectResponse,
  RevisionSummary,
  ScheduleEnvelope,
  SetFootprintDimensions,
  Snapshot,
  StoredPriceBook,
} from "../src/api/types";

export const fixture = raw as unknown as {
  project: ProjectResponse;
  revisions: RevisionSummary[];
  snapshot: Snapshot;
  manifest: Manifest;
  envelopes: { plan2d: PlanEnvelope; mesh3d: MeshEnvelope; timber_schedule: ScheduleEnvelope; preliminary_estimate: EstimateEnvelope };
  estimate_complete: EstimateEnvelope;
  price_book: StoredPriceBook;
  width_command: SetFootprintDimensions;
  width_preview: PreviewResponse;
};

export const plan = fixture.envelopes.plan2d;
export const mesh = fixture.envelopes.mesh3d;
export const schedule = fixture.envelopes.timber_schedule;
export const estimateNone = fixture.envelopes.preliminary_estimate;
export const estimateComplete = fixture.estimate_complete;
