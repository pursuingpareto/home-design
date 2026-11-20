/**
 * Tessellate a `mesh3d` payload into a Three.js group (artifacts.md §6). Only the documented
 * primitives are drawn: oriented boxes for members, the roof surfaces, and level outlines, plus a
 * fixed-size glyph per distinct connection position (D062). No other geometry is computed here
 * (UI-001 §6). Coordinates stay as served: meters, +Z up.
 */

import * as THREE from "three";

import type { Mesh3dPayload, MeshMember } from "../api/types";
import type { Role } from "../display/labels";
import { glyphColor, ROLE_COLOR, SELECTION_COLOR } from "../display/palette";
import type { Highlight, Pick } from "./highlight";
import { groupMarkers, type Glyph } from "./markers";

export const COLORS = {
  ...ROLE_COLOR,
  selected: SELECTION_COLOR.selected,
  related: SELECTION_COLOR.related,
  roof: 0x7f8c8d,
  level: 0x444444,
};

type MeshMarker = Mesh3dPayload["connections"][number];

// A connection glyph's radius and its count label's size, in meters: fixed display symbols that say
// nothing about a joint's size (D054, D062, AC2-07).
const CONNECTION_MARK_3D_M = 0.12;
const COUNT_LABEL_M = 0.4;
// Members are drawn first (render order 0); the roof is transparent; markers and their counts come
// after both, without depth testing, so they stay visible inside the boxes (D062).
export const MARKER_RENDER_ORDER = 2;

const v = (p: readonly number[]) => new THREE.Vector3(p[0] ?? 0, p[1] ?? 0, p[2] ?? 0);

/**
 * World transform of a member's box, whose local axes are (axis, width, depth), by the one rule of
 * artifacts.md §6 (ART-002 §5.1):
 * - vertical axis (posts): width along +X, depth along +Y;
 * - any other axis: width is horizontal and perpendicular to the axis's plan projection; depth is
 *   along axis × width, taken with a non-negative Z. Beams, sills, joists, and purlins get a vertical
 *   depth; rafters a depth perpendicular to the roof plane; braces a depth in their beam's plane.
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

export interface MeshMarkers {
  /** One instance per glyph; instance `i` is `glyphs[i]`. */
  mesh: THREE.InstancedMesh;
  glyphs: Glyph<MeshMarker>[];
  /** Count labels for glyphs of several connections (absent where the browser has no 2D canvas). */
  labels: THREE.Group;
}

export interface MeshScene {
  group: THREE.Group;
  members: Map<string, THREE.Mesh>;
  markers: MeshMarkers;
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
  const bounds = new THREE.Box3().setFromObject(group); // members, roof, and outlines; markers lie inside
  const markers = buildMarkers(payload, disposables);
  group.add(markers.mesh, markers.labels);
  group.updateMatrixWorld(true);
  return { group, members, markers, bounds, dispose: () => disposables.forEach((d) => d.dispose()) };
}

function buildMarkers(payload: Mesh3dPayload, disposables: { dispose: () => void }[]): MeshMarkers {
  const glyphs = groupMarkers<MeshMarker>(payload.connections, (m) => m.location_m);
  const geometry = new THREE.OctahedronGeometry(CONNECTION_MARK_3D_M);
  const material = new THREE.MeshBasicMaterial({ depthTest: false, depthWrite: false, transparent: true });
  disposables.push(geometry, material);
  const mesh = new THREE.InstancedMesh(geometry, material, Math.max(glyphs.length, 1));
  mesh.count = glyphs.length;
  mesh.name = "connection-markers";
  mesh.renderOrder = MARKER_RENDER_ORDER;
  const at = new THREE.Matrix4();
  glyphs.forEach((glyph, i) => {
    mesh.setMatrixAt(i, at.makeTranslation(v(glyph.position)));
    mesh.setColorAt(i, new THREE.Color(glyphColor(glyph.style)));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.computeBoundingSphere();

  const labels = new THREE.Group();
  labels.name = "connection-counts";
  const textures = new Map<number, THREE.Texture | null>();
  const textureFor = (count: number) => {
    if (!textures.has(count)) {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 64;
      const context = canvas.getContext("2d");
      let texture: THREE.Texture | null = null;
      if (context) {
        context.font = "bold 44px system-ui, sans-serif";
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.lineWidth = 8;
        context.strokeStyle = "#ffffff";
        context.strokeText(String(count), 32, 34);
        context.fillStyle = "#212529";
        context.fillText(String(count), 32, 34);
        texture = new THREE.CanvasTexture(canvas);
        disposables.push(texture);
      }
      textures.set(count, texture);
    }
    return textures.get(count) ?? null;
  };
  for (const glyph of glyphs) {
    if (glyph.markers.length < 2) continue;
    const map = textureFor(glyph.markers.length);
    if (!map) continue;
    const spriteMaterial = new THREE.SpriteMaterial({ map, depthTest: false, depthWrite: false, transparent: true });
    disposables.push(spriteMaterial);
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.position.copy(v(glyph.position)).add(new THREE.Vector3(0, 0, CONNECTION_MARK_3D_M + COUNT_LABEL_M / 2));
    sprite.scale.set(COUNT_LABEL_M, COUNT_LABEL_M, 1);
    sprite.renderOrder = MARKER_RENDER_ORDER + 1;
    sprite.raycast = () => {}; // labels are not picked; their glyph is
    labels.add(sprite);
  }
  return { mesh, glyphs, labels };
}

/** Show or hide the markers (the "Connections" switch, D062). */
export function setMarkersVisible(scene: MeshScene, visible: boolean): void {
  scene.markers.mesh.visible = visible;
  scene.markers.labels.visible = visible;
}

/** Highlight per UI-003 §6. Colors come from the palette only. */
export function highlight(scene: MeshScene, h: Highlight): void {
  for (const [id, mesh] of scene.members) {
    const material = mesh.material as THREE.MeshStandardMaterial;
    const role = mesh.userData.role as Role;
    material.color.setHex(id === h.member ? COLORS.selected : h.related.has(id) ? COLORS.related : COLORS[role]);
  }
  const color = new THREE.Color();
  scene.markers.glyphs.forEach((glyph, i) => {
    const selected = glyph.markers.some((m) => h.connections.has(m.connection_id));
    scene.markers.mesh.setColorAt(i, color.setHex(selected ? COLORS.selected : glyphColor(glyph.style)));
  });
  if (scene.markers.mesh.instanceColor) scene.markers.mesh.instanceColor.needsUpdate = true;
}

/**
 * What a ray picks (D062): a visible marker glyph before any member, since markers are drawn over the
 * members; otherwise the nearest member; otherwise nothing.
 */
export function pick(scene: MeshScene, raycaster: THREE.Raycaster): Pick | null {
  if (scene.markers.mesh.visible) {
    const hit = raycaster.intersectObject(scene.markers.mesh, false)[0];
    const glyph = hit?.instanceId !== undefined ? scene.markers.glyphs[hit.instanceId] : undefined;
    if (glyph) return { kind: "connections", ids: glyph.markers.map((m) => m.connection_id) };
  }
  const member = raycaster.intersectObjects([...scene.members.values()], false)[0];
  const id = member?.object.userData.memberId as string | undefined;
  return id ? { kind: "member", id } : null;
}
