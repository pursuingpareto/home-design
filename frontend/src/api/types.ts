/** Names for the generated OpenAPI types (D028). Nothing here is written by hand except the narrowing. */

import type { components } from "./schema";

type S = components["schemas"];

export type ArtifactType = S["ArtifactEnvelope"]["artifact_type"];
export type ArtifactStatus = S["ArtifactEnvelope"]["status"];
export type Envelope = S["ArtifactEnvelope"];
export type Manifest = S["Manifest"];
export type Plan2dPayload = S["Plan2dPayload"];
export type Mesh3dPayload = S["Mesh3dPayload"];
export type TimberSchedulePayload = S["TimberSchedulePayload"];
export type AssemblySchedulePayload = S["AssemblySchedulePayload"];
export type EstimatePayload = S["PreliminaryEstimatePayload"];
export type ProjectSummary = S["ProjectSummary"];
export type ProjectResponse = S["ProjectResponse"];
export type RevisionSummary = S["RevisionSummary"];
export type CommitResponse = S["CommitResponse"];
export type PreviewResponse = S["PreviewResponse"];
export type Snapshot = S["Snapshot"];
export type PriceBook = S["PriceBook"];
export type PriceRow = S["PriceRow"];
export type StoredPriceBook = S["StoredPriceBook"];
export type PriceBookSet = S["PriceBookSet"];
export type ErrorBody = S["ErrorBody"];
export type ErrorDetail = S["ErrorDetail"];
export type Command = S["CommitRequest"]["command"];
export type SetFootprintDimensions = S["SetFootprintDimensions"];
export type UndoToRevision = S["UndoToRevision"];
export type ScheduleRow = S["ScheduleRow"];
export type MeshMember = S["MeshMember"];

/** An envelope whose payload is typed by its artifact type (artifacts.md §5–8). */
export type TypedEnvelope<P> = Omit<Envelope, "payload"> & { payload?: P | null };
export type PlanEnvelope = TypedEnvelope<Plan2dPayload>;
export type MeshEnvelope = TypedEnvelope<Mesh3dPayload>;
export type ScheduleEnvelope = TypedEnvelope<TimberSchedulePayload>;
export type AssemblyScheduleEnvelope = TypedEnvelope<AssemblySchedulePayload>;
export type EstimateEnvelope = TypedEnvelope<EstimatePayload>;

export interface PayloadByType {
  plan2d: Plan2dPayload;
  mesh3d: Mesh3dPayload;
  timber_schedule: TimberSchedulePayload;
  assembly_schedule: AssemblySchedulePayload;
  preliminary_estimate: EstimatePayload;
}

export const ARTIFACT_TYPES: readonly ArtifactType[] = ["plan2d", "mesh3d", "timber_schedule", "assembly_schedule", "preliminary_estimate"];
