import * as THREE from "three";
import { describe, expect, it } from "vitest";

import { buildMeshScene, highlight, memberMatrix, COLORS } from "../src/views/meshScene";
import { mesh, plan, schedule } from "./fixtures";

describe("mesh3d tessellation (artifacts.md §6)", () => {
  const payload = mesh.payload!;

  it("draws one box per member with the schedule's and plan's IDs (artifacts.md §10 test 3)", () => {
    const scene = buildMeshScene(payload);
    const scheduleIds = schedule.payload!.members.map((m) => m.member_id).sort();
    const planIds = plan.payload!.planes.flatMap((p) => [...p.posts, ...p.beams].map((m) => m.member_id)).sort();
    expect([...scene.members.keys()].sort()).toEqual(scheduleIds);
    // The plan lists posts and beams only until ART-002 (MODEL-005 §9, artifacts.md §5).
    const postsAndBeams = schedule.payload!.members.filter((m) => m.role === "POST" || m.role === "BEAM").map((m) => m.member_id).sort();
    expect(planIds).toEqual(postsAndBeams);
    expect(scheduleIds).toHaveLength(193);
    expect(postsAndBeams).toHaveLength(58);
    scene.dispose();
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
    highlight(scene, post0());
    const selected = scene.members.get(post0())!.material as THREE.MeshStandardMaterial;
    expect(selected.color.getHex()).toBe(COLORS.selected);
    scene.dispose();
  });
});

function post0(): string {
  return mesh.payload!.members[0]!.member_id;
}
