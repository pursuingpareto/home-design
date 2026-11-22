/**
 * Server data for one revision of a project (UI-001 §10). When the revision changes, everything is
 * reset first, so nothing from the previous revision can be shown under the new one (AC-07).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import type { Api } from "../api/client";
import type {
  ArtifactStatus,
  AssemblyScheduleEnvelope,
  ArtifactType,
  EstimateEnvelope,
  Manifest,
  MeshEnvelope,
  PlanEnvelope,
  ProjectResponse,
  RevisionSummary,
  ScheduleEnvelope,
  Snapshot,
} from "../api/types";

export interface RevisionData {
  project: ProjectResponse | null;
  revisions: RevisionSummary[];
  revisionId: string | null; // the revision being shown (head when the route names none)
  isHead: boolean;
  manifest: Manifest | null;
  plan: PlanEnvelope | null;
  mesh: MeshEnvelope | null;
  schedule: ScheduleEnvelope | null;
  assemblies: AssemblyScheduleEnvelope | null; // the assembly schedule panel, and the views' joins (UI-004 §7, §10; D086)
  estimate: EstimateEnvelope | null;
  snapshot: Snapshot | null; // head only: current parameter values for editing
  error: unknown;
}

const EMPTY: Omit<RevisionData, "project" | "revisions"> = {
  revisionId: null,
  isHead: false,
  manifest: null,
  plan: null,
  mesh: null,
  schedule: null,
  assemblies: null,
  estimate: null,
  snapshot: null,
  error: null,
};

export function statusOf(data: RevisionData, type: ArtifactType): ArtifactStatus | "LOADING" {
  const envelope = {
    plan2d: data.plan,
    mesh3d: data.mesh,
    timber_schedule: data.schedule,
    assembly_schedule: data.assemblies,
    preliminary_estimate: data.estimate,
  }[type];
  if (envelope) return envelope.status;
  const entry = data.manifest?.artifacts.find((a) => a.artifact_type === type);
  return entry ? (entry.status as ArtifactStatus) : "LOADING";
}

export function useRevisionData(api: Api, projectId: string, routeRevisionId: string | null, onError: (e: unknown) => void) {
  const [data, setData] = useState<RevisionData>({ project: null, revisions: [], ...EMPTY });
  const generation = useRef(0);

  const load = useCallback(async () => {
    const mine = ++generation.current;
    const current = () => mine === generation.current;
    setData((d) => ({ ...d, ...EMPTY }));
    try {
      const [project, revisions] = await Promise.all([api.getProject(projectId), api.listRevisions(projectId)]);
      if (!current()) return;
      const revisionId = routeRevisionId ?? project.head_revision_id;
      const isHead = revisionId === project.head_revision_id;
      setData((d) => ({ ...d, project, revisions, revisionId, isHead }));
      const update = (patch: Partial<RevisionData>) => current() && setData((d) => ({ ...d, ...patch }));
      const manifest = api.manifest(projectId, revisionId).then((manifest) => update({ manifest }));
      const artifacts = Promise.all([
        api.artifact(projectId, "plan2d", revisionId).then((plan) => update({ plan })),
        api.artifact(projectId, "mesh3d", revisionId).then((mesh) => update({ mesh })),
        api.artifact(projectId, "timber_schedule", revisionId).then((schedule) => update({ schedule })),
        api.artifact(projectId, "assembly_schedule", revisionId).then((assemblies) => update({ assemblies })),
      ]).then(() => api.artifact(projectId, "preliminary_estimate", revisionId).then((estimate) => update({ estimate })));
      const snapshot = isHead ? api.getRevision(projectId, revisionId).then((snapshot) => update({ snapshot })) : Promise.resolve();
      await Promise.all([manifest, artifacts, snapshot]);
    } catch (error) {
      if (current()) {
        setData((d) => ({ ...d, error }));
        onError(error);
      }
    }
  }, [api, projectId, routeRevisionId, onError]);

  /** Re-read the estimate only (after a price-book change; artifacts.md §8.2). */
  const reloadEstimate = useCallback(async () => {
    const revisionId = data.revisionId;
    if (!revisionId) return;
    setData((d) => ({ ...d, estimate: null }));
    try {
      const manifest = await api.manifest(projectId, revisionId);
      setData((d) => ({ ...d, manifest }));
      const estimate = await api.artifact(projectId, "preliminary_estimate", revisionId);
      setData((d) => (d.revisionId === revisionId ? { ...d, estimate } : d));
    } catch (error) {
      onError(error);
    }
  }, [api, projectId, data.revisionId, onError]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, reload: load, reloadEstimate };
}
