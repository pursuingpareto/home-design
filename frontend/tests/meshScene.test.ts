import * as THREE from "three";
import { describe, expect, it } from "vitest";

import { buildMeshScene, highlight, memberMatrix, COLORS } from "../src/views/meshScene";
import { mesh, plan, schedule } from "./fixtures";

describe("mesh3d tessellation (artifacts.md §6)", () => {
  const payload = mesh.payload!;

  it("draws one box per member with the schedule's and plan's IDs (artifacts.md §10 test 3)", () => {
    const scene = buildMeshScene(payload);
    const scheduleIds = schedule.payload!.members.map((m) => m.member_id).sort();
    const planIds = plan
      .payload!.planes.flatMap((p) => [...p.posts, ...p.beams, ...p.sills, ...p.joists, ...p.braces, ...p.rafters, ...p.purlins].map((m) => m.member_id))
      .sort();
    expect([...scene.members.keys()].sort()).toEqual(scheduleIds);
    expect(planIds).toEqual(scheduleIds); // every role is in the plan (ART-002 §4.1)
    expect(scheduleIds).toHaveLength(193);
    expect(payload.connections).toHaveLength(312);
    scene.dispose();
  });

  it("gives every role the basis of the artifacts.md §6 rule (ART-002 §13 test 4)", () => {
    const pitch = payload.envelope.roof.pitch_rad;
    const basis = (member: (typeof payload.members)[number]) => {
      const { matrix } = memberMatrix(member);
      const along = new THREE.Vector3(), width = new THREE.Vector3(), depth = new THREE.Vector3();
      matrix.extractBasis(along, width, depth);
      return { along, width, depth };
    };
    const roles = ["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"] as const;
    for (const role of roles) {
      const member = payload.members.find((m) => m.role === role)!;
      const { along, width, depth } = basis(member);
      expect(Math.abs(width.dot(along))).toBeLessThan(1e-12);
      expect(Math.abs(depth.dot(along))).toBeLessThan(1e-12);
      expect(Math.abs(depth.dot(width))).toBeLessThan(1e-12);
      if (role === "POST") {
        expect(width.toArray()).toEqual([1, 0, 0]);
        expect(depth.toArray()).toEqual([0, 1, 0]);
      } else {
        expect(width.z).toBe(0);
        expect(depth.z).toBeGreaterThanOrEqual(0);
      }
      if (role === "BEAM" || role === "SILL" || role === "FLOOR_JOIST" || role === "PURLIN") {
        expect(depth.distanceTo(new THREE.Vector3(0, 0, 1))).toBeLessThan(1e-12); // depth vertical; purlins plumb (D060)
      }
      if (role === "PRINCIPAL_RAFTER") {
        const south = (member.axis_end_m[1] ?? 0) > (member.axis_start_m[1] ?? 0);
        const normal = new THREE.Vector3(0, (south ? -1 : 1) * Math.sin(pitch), Math.cos(pitch));
        expect(depth.distanceTo(normal)).toBeLessThan(1e-12); // perpendicular to the roof plane (D053)
        expect(Math.abs(width.x)).toBeCloseTo(1, 12);
      }
      if (role === "KNEE_BRACE") {
        const inX = member.axis_start_m[1] === member.axis_end_m[1];
        const planeNormal = inX ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
        expect(Math.abs(width.dot(planeNormal))).toBeCloseTo(1, 12); // width across the beam's plane (D058)
        expect(Math.abs(depth.dot(planeNormal))).toBeLessThan(1e-12);
      }
    }
  });

  it("orients posts and beams per the payload rules", () => {
    const post = payload.members.find((m) => m.role === "POST")!;
    const beam = payload.members.find((m) => m.role === "BEAM")!;
    const box = (member: typeof post) => {
      const { matrix, size } = memberMatrix(member);
      const corners = [-0.5, 0.5].flatMap((x) => [-0.5, 0.5].flatMap((y) => [-0.5, 0.5].map((z) => new THREE.Vector3(x * size.x, y * size.y, z * size.z).applyMatrix4(matrix))));
      return new THREE.Box3().setFromPoints(corners).getSize(new THREE.Vector3());
    };
    const postSize = box(post);
    expect(postSize.x).toBeCloseTo(post.section_width_m, 9);
    expect(postSize.y).toBeCloseTo(post.section_depth_m, 9);
    expect(postSize.z).toBeCloseTo(Math.abs((post.axis_end_m[2] ?? 0) - (post.axis_start_m[2] ?? 0)), 9);
    const beamSize = box(beam);
    expect(beamSize.z).toBeCloseTo(beam.section_depth_m, 9); // depth is vertical
    const alongX = Math.abs((beam.axis_end_m[0] ?? 0) - (beam.axis_start_m[0] ?? 0)) > 0;
    expect(alongX ? beamSize.y : beamSize.x).toBeCloseTo(beam.section_width_m, 9);
  });

  it("includes the roof surfaces and level outlines, and bounds match the envelope", () => {
    const scene = buildMeshScene(payload);
    expect(scene.group.getObjectByName("roof-south")).toBeDefined();
    expect(scene.group.getObjectByName("roof-north")).toBeDefined();
    // Bounds hold the ridge and every member axis; the principal rafters' boxes rise above the ridge line.
    const ridge = new THREE.Vector3(...(payload.envelope.roof.ridge_start_m as [number, number, number]));
    expect(scene.bounds.containsPoint(ridge)).toBe(true);
    for (const m of payload.members) {
      expect(scene.bounds.containsPoint(new THREE.Vector3(...(m.axis_end_m as [number, number, number])))).toBe(true);
    }
    highlight(scene, { member: post0(), related: new Set(), connections: new Set() });
    const selected = scene.members.get(post0())!.material as THREE.MeshStandardMaterial;
    expect(selected.color.getHex()).toBe(COLORS.selected);
    scene.dispose();
  });
});

function post0(): string {
  return mesh.payload!.members[0]!.member_id;
}
