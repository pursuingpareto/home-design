/** Typed access to the captured Reference House 001 fixtures (backend: homedesign.api.ui_fixtures). */

import raw from "./fixtures/reference-house-001.json";

import type {
  AssemblyScheduleEnvelope,
  AssemblySchedulePayload,
  EstimateEnvelope,
  Manifest,
  MeshEnvelope,
  PlanEnvelope,
  PreviewResponse,
  ProjectResponse,
  RevisionSummary,
  ScheduleEnvelope,
  SetFootprintDimensions,
  Command,
  Snapshot,
  StoredPriceBook,
} from "../src/api/types";

interface Envelopes {
  plan2d: PlanEnvelope;
  mesh3d: MeshEnvelope;
  timber_schedule: ScheduleEnvelope;
  assembly_schedule: AssemblyScheduleEnvelope;
  preliminary_estimate: EstimateEnvelope;
}

export const fixture = raw as unknown as {
  project: ProjectResponse;
  revisions: RevisionSummary[];
  snapshot: Snapshot;
  manifest: Manifest;
  envelopes: Envelopes;
  estimate_complete: EstimateEnvelope;
  price_book: StoredPriceBook;
  width_command: SetFootprintDimensions;
  width_preview: PreviewResponse;
  /** UI-003 §11: eave braces off, and `joist-beam` → `JOIST_HANGER`, from the created house. */
  frame_command: Command;
  frame_preview: PreviewResponse;
  type_command: Command;
  type_preview: PreviewResponse;
  /** UI-004 §14: `SetWallAssembly` to stud infill, its committed envelopes, and re-identifying `y1`. */
  assembly_command: Command;
  assembly_preview: PreviewResponse;
  stud_infill_envelopes: Envelopes;
  reidentify_command: Command;
  reidentify_preview: PreviewResponse;
  /** TEST ONLY: the created house's assembly schedule with test-only declared values (backend builder). */
  assembly_schedule_declared: { _note: string; payload: AssemblySchedulePayload };
};

export const plan = fixture.envelopes.plan2d;
export const mesh = fixture.envelopes.mesh3d;
export const schedule = fixture.envelopes.timber_schedule;
export const estimateNone = fixture.envelopes.preliminary_estimate;
export const estimateComplete = fixture.estimate_complete;
export const catalog = schedule.payload!.connection_catalog;
export const assemblies = fixture.envelopes.assembly_schedule;
export const studInfill = fixture.stud_infill_envelopes;
