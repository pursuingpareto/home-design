/**
 * Tessellate a `mesh3d` payload into a Three.js group (artifacts.md §6). Only the documented
 * primitives are drawn: oriented boxes for members, the roof surfaces, and level outlines, plus a
 * fixed-size glyph per distinct connection position (D062). Since VS-02b also each wall's layers,
 * tessellated around its voids, an outline and a pick surface per void, and a box per wall framing
 * piece (UI-004 §5). No other geometry is computed here (UI-001 §6). Coordinates stay as served:
 * meters, +Z up.
 */

import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

import type { Mesh3dPayload, MeshMember } from "../api/types";
import { FRAMING_GROUPS, framingGroupOf, type FramingGroup, type LayerFunction, type Role } from "../display/labels";
import { FRAMING_COLOR, glyphColor, LAYER_COLOR, OPENING_COLOR, ROLE_COLOR, SELECTION_COLOR } from "../display/palette";
import type { Highlight, Pick } from "./highlight";
import { groupMarkers, type Glyph } from "./markers";
import { framingMatrix, tessellate, wallFrame, type MeshPiece } from "./walls";

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

/** One layer of one wall: a single mesh of the layer's boxes around the wall's voids (UI-004 §5.1). */
export interface WallSolid {
  wallId: string;
  layer: string;
  function: LayerFunction;
  mesh: THREE.Mesh;
}

export interface WallOpening {
  openingId: string;
  wallId: string;
  /** A thin outline on the wall's exterior face: a symbol, not a frame or glazing (D069). */
  outline: THREE.LineLoop;
  /** An invisible surface across the void, so a hole can be hovered and picked. */
  surface: THREE.Mesh;
}

/** The framing boxes of one group: instance `i` is `pieces[i]` (UI-004 §18). */
export interface FramingBoxes {
  group: FramingGroup;
  mesh: THREE.InstancedMesh;
  pieces: MeshPiece[];
}

export interface MeshScene {
  group: THREE.Group;
  members: Map<string, THREE.Mesh>;
  markers: MeshMarkers;
  walls: { solids: WallSolid[]; openings: WallOpening[]; layers: THREE.Group };
  framing: { boxes: FramingBoxes[]; group: THREE.Group };
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

  const walls = buildWalls(payload, disposables);
  const framing = buildFraming(payload, disposables);
  group.add(walls.layers, framing.group);

  group.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(group); // members, walls, roof, and outlines; markers lie inside
  const markers = buildMarkers(payload, disposables);
  group.add(markers.mesh, markers.labels);
  group.updateMatrixWorld(true);
  return { group, members, markers, walls, framing, bounds, dispose: () => disposables.forEach((d) => d.dispose()) };
}

/** Each wall's layers as opaque solids around its voids, and an outline and pick surface per void. */
function buildWalls(payload: Mesh3dPayload, disposables: { dispose: () => void }[]): MeshScene["walls"] {
  const layers = new THREE.Group();
  layers.name = "wall-layers";
  const solids: WallSolid[] = [];
  const openings: WallOpening[] = [];
  const outlineMaterial = new THREE.LineBasicMaterial({ color: OPENING_COLOR });
  const surfaceMaterial = new THREE.MeshBasicMaterial({ visible: false, side: THREE.DoubleSide });
  disposables.push(outlineMaterial, surfaceMaterial);
  for (const wall of payload.walls) {
    const frame = wallFrame(wall);
    const basis = new THREE.Matrix4().makeBasis(frame.u, frame.v, frame.w).setPosition(frame.origin);
    const rects = tessellate(frame.length, wall.height_m, wall.voids);
    for (const layer of wall.layers) {
      const thickness = layer.outer_m - layer.inner_m;
      const boxes = rects.map((r) => {
        const box = new THREE.BoxGeometry(r.u[1] - r.u[0], r.v[1] - r.v[0], thickness);
        box.translate((r.u[0] + r.u[1]) / 2, (r.v[0] + r.v[1]) / 2, (layer.inner_m + layer.outer_m) / 2);
        return box;
      });
      const geometry = boxes.length > 0 ? (mergeGeometries(boxes) ?? new THREE.BufferGeometry()) : new THREE.BufferGeometry();
      boxes.forEach((b) => b.dispose());
      geometry.applyMatrix4(basis);
      const material = new THREE.MeshStandardMaterial({ color: LAYER_COLOR[layer.function] });
      disposables.push(geometry, material);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = `${wall.generation_key}/${layer.name}`;
      mesh.userData = { wallId: wall.wall_id, layer: layer.name, function: layer.function };
      solids.push({ wallId: wall.wall_id, layer: layer.name, function: layer.function, mesh });
      layers.add(mesh);
    }
    const face = Math.max(...wall.layers.map((l) => l.outer_m), 0);
    for (const hole of wall.voids) {
      const [u0 = 0, u1 = 0] = hole.u_m;
      const [v0 = 0, v1 = 0] = hole.v_m;
      const corners = [
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      ].map(([u, v]) => new THREE.Vector3(u, v, face).applyMatrix4(basis));
      const lineGeometry = new THREE.BufferGeometry().setFromPoints(corners);
      const surfaceGeometry = new THREE.PlaneGeometry(u1 - u0, v1 - v0).translate((u0 + u1) / 2, (v0 + v1) / 2, face).applyMatrix4(basis);
      disposables.push(lineGeometry, surfaceGeometry);
      const outline = new THREE.LineLoop(lineGeometry, outlineMaterial.clone());
      disposables.push(outline.material as THREE.Material);
      outline.name = `opening-${hole.opening_id}`;
      outline.userData = { openingId: hole.opening_id };
      outline.raycast = () => {}; // the surface is picked, not the outline
      const surface = new THREE.Mesh(surfaceGeometry, surfaceMaterial);
      surface.userData = { openingId: hole.opening_id, wallId: wall.wall_id };
      openings.push({ openingId: hole.opening_id, wallId: wall.wall_id, outline, surface });
      layers.add(outline, surface);
    }
  }
  return { solids, openings, layers };
}

/** One box per wall framing piece, as one instanced mesh per framing group (UI-004 §5.2, §18). */
function buildFraming(payload: Mesh3dPayload, disposables: { dispose: () => void }[]): MeshScene["framing"] {
  const group = new THREE.Group();
  group.name = "wall-framing";
  const outward = new Map(payload.walls.map((w) => [w.wall_id, w.outward_xy]));
  const unitBox = new THREE.BoxGeometry(1, 1, 1);
  disposables.push(unitBox);
  const boxes: FramingBoxes[] = [];
  for (const framingGroup of FRAMING_GROUPS) {
    const pieces = payload.wall_framing.filter((p) => framingGroupOf(p.piece_kind) === framingGroup);
    if (pieces.length === 0) continue;
    const material = new THREE.MeshStandardMaterial({ color: 0xffffff });
    disposables.push(material);
    const mesh = new THREE.InstancedMesh(unitBox, material, pieces.length);
    mesh.name = `wall-framing-${framingGroup}`;
    const color = new THREE.Color(FRAMING_COLOR[framingGroup]);
    pieces.forEach((piece, i) => {
      const { matrix, size } = framingMatrix(piece, outward.get(piece.wall_id) ?? [0, 0]);
      mesh.setMatrixAt(i, matrix.multiply(new THREE.Matrix4().makeScale(size.x, size.y, size.z)));
      mesh.setColorAt(i, color);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
    mesh.computeBoundingBox();
    boxes.push({ group: framingGroup, mesh, pieces });
    group.add(mesh);
  }
  return { boxes, group };
}

/** Show or hide the wall layers with their openings, and the wall framing (D066's two switches). */
export function setWallsVisible(scene: MeshScene, layers: boolean, framing: boolean): void {
  scene.walls.layers.visible = layers;
  scene.framing.group.visible = framing;
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
  for (const solid of scene.walls.solids) {
    (solid.mesh.material as THREE.MeshStandardMaterial).color.setHex(h.walls.has(solid.wallId) ? COLORS.selected : LAYER_COLOR[solid.function]);
  }
  for (const opening of scene.walls.openings) {
    (opening.outline.material as THREE.LineBasicMaterial).color.setHex(h.openings.has(opening.openingId) ? COLORS.selected : OPENING_COLOR);
  }
  for (const boxes of scene.framing.boxes) {
    boxes.pieces.forEach((piece, i) => {
      const hex = h.pieces.has(piece.piece_id) ? COLORS.selected : h.relatedPieces.has(piece.piece_id) ? COLORS.related : FRAMING_COLOR[boxes.group];
      boxes.mesh.setColorAt(i, color.setHex(hex));
    });
    if (boxes.mesh.instanceColor) boxes.mesh.instanceColor.needsUpdate = true;
  }
}

/** A pick with what was hit, for tooltips: the layer of a wall, or the framing piece. */
export type Hit = { pick: Pick; layer?: string; piece?: MeshPiece };

/**
 * What a ray picks (D062, UI-004 §5.3): a visible marker glyph before anything else, since markers are
 * drawn over everything; otherwise the nearest visible member, wall layer (its wall), opening surface,
 * or framing box; otherwise nothing. Objects a switch hides are not picked.
 */
export function pickHit(scene: MeshScene, raycaster: THREE.Raycaster): Hit | null {
  if (scene.markers.mesh.visible) {
    const hit = raycaster.intersectObject(scene.markers.mesh, false)[0];
    const glyph = hit?.instanceId !== undefined ? scene.markers.glyphs[hit.instanceId] : undefined;
    if (glyph) return { pick: { kind: "connections", ids: glyph.markers.map((m) => m.connection_id) } };
  }
  const targets: THREE.Object3D[] = [...scene.members.values()];
  if (scene.walls.layers.visible) targets.push(...scene.walls.solids.map((s) => s.mesh), ...scene.walls.openings.map((o) => o.surface));
  if (scene.framing.group.visible) targets.push(...scene.framing.boxes.map((b) => b.mesh));
  const hit = raycaster.intersectObjects(targets, false)[0];
  if (!hit) return null;
  const data = hit.object.userData as { memberId?: string; wallId?: string; openingId?: string; layer?: string };
  if (data.memberId) return { pick: { kind: "member", id: data.memberId } };
  if (data.openingId) return { pick: { kind: "opening", id: data.openingId } };
  if (data.wallId) return { pick: { kind: "wall", id: data.wallId }, layer: data.layer };
  const boxes = scene.framing.boxes.find((b) => b.mesh === hit.object);
  const piece = boxes && hit.instanceId !== undefined ? boxes.pieces[hit.instanceId] : undefined;
  return piece ? { pick: { kind: "pieces", ids: [piece.piece_id] }, piece } : null;
}

export function pick(scene: MeshScene, raycaster: THREE.Raycaster): Pick | null {
  return pickHit(scene, raycaster)?.pick ?? null;
}
