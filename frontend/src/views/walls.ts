/**
 * Pure helpers for walls, openings, and wall framing in the views (UI-004 §4, §5). They use the served
 * values only: band corners from the wall's extents, gaps at the openings' served points, framing marks
 * grouped by exact coordinates, and framing boxes by the served orientation rule (artifacts.md §6).
 */

import * as THREE from "three";

import type { Mesh3dPayload, Plan2dPayload } from "../api/types";
import { framingGroupOf, pieceKindLabel, type FramingGroup, type PieceKind } from "../display/labels";

type Plane = Plan2dPayload["planes"][number];
export type PlanWall = Plane["walls"][number];
export type PlanPiece = Plane["wall_framing"][number];
export type MeshWall = Mesh3dPayload["walls"][number];
export type MeshPiece = Mesh3dPayload["wall_framing"][number];
type XY = readonly number[];

/**
 * Display joins the workspace computes from the same revision's assembly schedule (D086) and passes in,
 * so the views read only their payloads and these labels.
 */
export interface WallDetails {
  /** Wall label by `wall_id` ("South wall, Level 0, x0–x1"). */
  walls: ReadonlyMap<string, string>;
  /** Opening label by `opening_id` ("Window 3' 0" × 4' 0", south wall, …"). */
  openings: ReadonlyMap<string, string>;
  /** A piece's nominal section and key by `piece_id`. */
  pieces: ReadonlyMap<string, { section: string; key: string }>;
  /** A layer's material name by layer name, for the definition in use. */
  layerMaterials: ReadonlyMap<string, string>;
}

export const NO_DETAILS: WallDetails = { walls: new Map(), openings: new Map(), pieces: new Map(), layerMaterials: new Map() };

// --- plan ---------------------------------------------------------------------------------------------

const add = (p: XY, d: XY, k: number): [number, number] => [(p[0] ?? 0) + (d[0] ?? 0) * k, (p[1] ?? 0) + (d[1] ?? 0) * k];

/** The four corners of the band between `a` and `b` on a wall's reference line: out, then in. */
export function bandQuad(wall: PlanWall, a: XY, b: XY): [number, number][] {
  const n = wall.outward_xy;
  return [add(a, n, wall.exterior_m), add(b, n, wall.exterior_m), add(b, n, -wall.interior_m), add(a, n, -wall.interior_m)];
}

/** The band's pieces between the openings, in served order: start → first opening, …, last opening → end. */
export function bandSpans(wall: PlanWall): { start: XY; end: XY }[] {
  const spans: { start: XY; end: XY }[] = [];
  let from: XY = wall.start_xy_m;
  for (const opening of wall.openings) {
    spans.push({ start: from, end: opening.start_xy_m });
    from = opening.end_xy_m;
  }
  spans.push({ start: from, end: wall.end_xy_m });
  return spans;
}

export interface FramingMark {
  /** The exact coordinates, joined; unique per mark. */
  key: string;
  vertical: boolean;
  pieces: PlanPiece[];
}

const isVertical = (piece: PlanPiece): piece is Extract<PlanPiece, { xy_m: number[] }> => "xy_m" in piece;

/**
 * Coincident pieces share one mark (D062's rule, UI-004 §4.2): vertical pieces by `xy_m`, horizontal
 * ones by the pair (`start_xy_m`, `end_xy_m`), by exact equality, in order of first appearance.
 */
export function groupFraming(pieces: readonly PlanPiece[]): FramingMark[] {
  const marks = new Map<string, FramingMark>();
  for (const piece of pieces) {
    const vertical = isVertical(piece);
    const key = vertical ? `v:${piece.xy_m.join(",")}` : `h:${piece.start_xy_m.join(",")}/${piece.end_xy_m.join(",")}`;
    const mark = marks.get(key);
    if (mark) mark.pieces.push(piece);
    else marks.set(key, { key, vertical, pieces: [piece] });
  }
  return [...marks.values()];
}

/** One mark's position: a point for vertical pieces, a segment for horizontal ones. */
export function markGeometry(mark: FramingMark): { point: XY } | { start: XY; end: XY } {
  const first = mark.pieces[0]!;
  return isVertical(first) ? { point: first.xy_m } : { start: first.start_xy_m, end: first.end_xy_m };
}

/** A mark's group, or null when its pieces span groups (drawn in the mixed color). */
export function markGroup(pieces: readonly { piece_kind: PieceKind }[]): FramingGroup | null {
  const groups = new Set(pieces.map((p) => framingGroupOf(p.piece_kind)));
  return groups.size === 1 ? [...groups][0]! : null;
}

/** Tooltip lines: each piece's kind and section with its key from the schedule, or the kind alone. */
export function framingTitle(pieces: readonly { piece_id: string; piece_kind: string }[], details: WallDetails): string {
  return pieces
    .map((p) => {
      const joined = details.pieces.get(p.piece_id);
      return joined ? `${pieceKindLabel(p.piece_kind)} ${joined.section} · ${joined.key}` : pieceKindLabel(p.piece_kind);
    })
    .join("\n");
}

// --- 3D -----------------------------------------------------------------------------------------------

const v3 = (p: readonly number[]) => new THREE.Vector3(p[0] ?? 0, p[1] ?? 0, p[2] ?? 0);

/**
 * A wall framing box's world transform, whose local axes are (axis, in-plane, through-wall), by the
 * served rule (artifacts.md §6, "VS-02b"; ART-003 §6.2): `section_through_wall_m` along the wall's
 * `outward_xy`, `section_in_plane_m` in the wall's plane, perpendicular to the axis.
 */
export function framingMatrix(piece: MeshPiece, outwardXy: readonly number[]): { matrix: THREE.Matrix4; size: THREE.Vector3 } {
  const start = v3(piece.axis_start_m);
  const end = v3(piece.axis_end_m);
  const along = end.clone().sub(start);
  const length = along.length();
  along.normalize();
  const through = new THREE.Vector3(outwardXy[0] ?? 0, outwardXy[1] ?? 0, 0).normalize();
  const inPlane = new THREE.Vector3().crossVectors(through, along).normalize(); // so along × inPlane = through
  const center = start.add(end).multiplyScalar(0.5);
  const matrix = new THREE.Matrix4().makeBasis(along, inPlane, through).setPosition(center);
  return { matrix, size: new THREE.Vector3(length, piece.section_in_plane_m, piece.section_through_wall_m) };
}

export interface Rect {
  u: [number, number];
  v: [number, number];
}

/**
 * A wall face from u = 0 to `length` and v = 0 to `height`, less its voids, as rectangles: the face is
 * split at every void edge in u, and each column at its voids' edges in v (UI-004 §18).
 */
export function tessellate(length: number, height: number, voids: readonly { u_m: readonly number[]; v_m: readonly number[] }[]): Rect[] {
  const us = [...new Set([0, length, ...voids.flatMap((w) => [w.u_m[0] ?? 0, w.u_m[1] ?? 0])])].filter((u) => u >= 0 && u <= length).sort((a, b) => a - b);
  const rects: Rect[] = [];
  for (let i = 0; i + 1 < us.length; i++) {
    const u0 = us[i]!;
    const u1 = us[i + 1]!;
    if (u1 <= u0) continue;
    const mid = (u0 + u1) / 2;
    const cuts = voids
      .filter((w) => (w.u_m[0] ?? 0) < mid && mid < (w.u_m[1] ?? 0))
      .map((w) => [Math.max(0, w.v_m[0] ?? 0), Math.min(height, w.v_m[1] ?? 0)] as [number, number])
      .sort((a, b) => a[0] - b[0]);
    let from = 0;
    for (const [v0, v1] of cuts) {
      if (v0 > from) rects.push({ u: [u0, u1], v: [from, v0] });
      from = Math.max(from, v1);
    }
    if (from < height) rects.push({ u: [u0, u1], v: [from, height] });
  }
  return rects;
}

/** The wall-local frame: origin at the base start, u along the wall, v up, w along `outward_xy`. */
export function wallFrame(wall: MeshWall): { origin: THREE.Vector3; u: THREE.Vector3; v: THREE.Vector3; w: THREE.Vector3; length: number } {
  const origin = v3(wall.base_start_m);
  const u = v3(wall.base_end_m).sub(origin);
  const length = u.length();
  u.normalize();
  return { origin, u, v: new THREE.Vector3(0, 0, 1), w: new THREE.Vector3(wall.outward_xy[0] ?? 0, wall.outward_xy[1] ?? 0, 0).normalize(), length };
}
