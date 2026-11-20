/**
 * Tessellate a `mesh3d` payload into a Three.js group (artifacts.md §6). Only the documented
 * primitives are drawn: oriented boxes for members, the roof surfaces, and level outlines. No other
 * geometry is computed here (UI-001 §6). Coordinates stay as served: meters, +Z up.
 */

import * as THREE from "three";

import type { Mesh3dPayload, MeshMember } from "../api/types";

// The version 2 roles share one neutral timber tone until UI-003 styles them (MODEL-005 §9).
const NEUTRAL = 0xc9a77c;
export const COLORS = {
  POST: 0x8a5a2b,
  BEAM: 0xb07a3f,
  SILL: NEUTRAL,
  FLOOR_JOIST: NEUTRAL,
  PRINCIPAL_RAFTER: NEUTRAL,
  PURLIN: NEUTRAL,
  KNEE_BRACE: NEUTRAL,
  selected: 0x1f6feb,
  roof: 0x7f8c8d,
  level: 0x444444,
};

const v = (p: readonly number[]) => new THREE.Vector3(p[0] ?? 0, p[1] ?? 0, p[2] ?? 0);

/**
 * World transform of a member's box, whose local axes are (axis, width, depth):
 * - posts (vertical axis): width along +X, depth along +Y;
 * - other members: depth is world +Z; width is horizontal and perpendicular to the axis's plan projection.
 */
export function memberMatrix(member: MeshMember): { matrix: THREE.Matrix4; size: THREE.Vector3 } {
  const start = v(member.axis_start_m);
  const end = v(member.axis_end_m);
  const axis = end.clone().sub(start);
  const length = axis.length();
  const along = axis.clone().normalize();
  const up = new THREE.Vector3(0, 0, 1);
  let widthDir: THREE.Vector3;
  let depthDir: THREE.Vector3;
  const vertical = Math.abs(along.dot(up)) > 1 - 1e-9;
  if (vertical) {
    widthDir = new THREE.Vector3(1, 0, 0);
    depthDir = new THREE.Vector3(0, 1, 0);
    along.set(0, 0, Math.sign(axis.z) || 1);
  } else {
    widthDir = new THREE.Vector3(-along.y, along.x, 0).normalize(); // horizontal, perpendicular to the plan projection
    depthDir = new THREE.Vector3().crossVectors(along, widthDir).normalize();
    if (depthDir.z < 0) depthDir.negate();
  }
  const center = start.clone().add(end).multiplyScalar(0.5);
  const matrix = new THREE.Matrix4().makeBasis(along, widthDir, depthDir).setPosition(center);
  return { matrix, size: new THREE.Vector3(length, member.section_width_m, member.section_depth_m) };
}

export interface MeshScene {
  group: THREE.Group;
  members: Map<string, THREE.Mesh>;
  bounds: THREE.Box3;
  dispose: () => void;
}

export function buildMeshScene(payload: Mesh3dPayload): MeshScene {
  const group = new THREE.Group();
  const members = new Map<string, THREE.Mesh>();
  const disposables: { dispose: () => void }[] = [];

  const unitBox = new THREE.BoxGeometry(1, 1, 1);
  disposables.push(unitBox);
  for (const member of payload.members) {
    const material = new THREE.MeshStandardMaterial({ color: COLORS[member.role] });
    disposables.push(material);
    const mesh = new THREE.Mesh(unitBox, material);
    const { matrix, size } = memberMatrix(member);
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(matrix).multiply(new THREE.Matrix4().makeScale(size.x, size.y, size.z));
    mesh.userData = { memberId: member.member_id, generationKey: member.generation_key, role: member.role };
    mesh.name = member.generation_key;
    members.set(member.member_id, mesh);
    group.add(mesh);
  }

  const roofMaterial = new THREE.MeshStandardMaterial({ color: COLORS.roof, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false });
  disposables.push(roofMaterial);
  for (const surface of payload.envelope.roof.surfaces) {
    const [a, b, c, d] = surface.ring_m.map(v);
    if (!a || !b || !c || !d) continue;
    const geometry = new THREE.BufferGeometry().setFromPoints([a, b, c, a, c, d]);
    geometry.computeVertexNormals();
    disposables.push(geometry);
    const mesh = new THREE.Mesh(geometry, roofMaterial);
    mesh.name = `roof-${surface.id}`;
    mesh.userData = { roof: surface.id };
    group.add(mesh);
  }

  const lineMaterial = new THREE.LineBasicMaterial({ color: COLORS.level });
  disposables.push(lineMaterial);
  for (const z of [...payload.envelope.level_z_m, payload.envelope.z_eave_m]) {
    const points = payload.envelope.footprint_ring_m.map((p) => new THREE.Vector3(p[0] ?? 0, p[1] ?? 0, z));
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    disposables.push(geometry);
    const loop = new THREE.LineLoop(geometry, lineMaterial);
    loop.name = `outline-${z}`;
    group.add(loop);
  }

  group.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(group);
  return { group, members, bounds, dispose: () => disposables.forEach((d) => d.dispose()) };
}

/** Highlight one member (or none). Colors come from COLORS only. */
export function highlight(scene: MeshScene, selected: string | null): void {
  for (const [id, mesh] of scene.members) {
    const material = mesh.material as THREE.MeshStandardMaterial;
    const role = mesh.userData.role as keyof typeof COLORS;
    material.color.setHex(id === selected ? COLORS.selected : COLORS[role]);
  }
}
