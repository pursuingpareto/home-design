// Generates vectors.json: RFC 8785 (JCS) test vectors computed by an ECMAScript
// engine, which RFC 8785 is defined against (Number-to-String, JSON.stringify string
// escaping, UTF-16 code-unit key order). Implementations in other languages must
// reproduce these bytes exactly (D029).
//
// Usage (from the repository root):  node tests/vectors/jcs/generate.mjs
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");

function canonicalize(value) {
  if (value === null || typeof value !== "object") {
    if (typeof value === "number" && !Number.isFinite(value)) {
      throw new Error("non-finite number");
    }
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalize).join(",") + "]";
  }
  // Array.prototype.sort without a comparator compares UTF-16 code units.
  const keys = Object.keys(value).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalize(value[k])).join(",") + "}";
}

const sha256 = (text) => "sha256:" + createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex");

// Inputs are raw JSON files so that literal spelling (1.0, -0, 4.50, escapes) is preserved.
const inputDir = join(here, "inputs");
const documents = readdirSync(inputDir)
  .filter((file) => file.endsWith(".json"))
  .sort()
  .map((file) => ({ name: file.replace(/\.json$/, ""), input: readFileSync(join(inputDir, file), "utf8") }));

// RFC 8785 Appendix B number samples (IEEE-754 bit patterns).
const numberHex = [
  "0000000000000000", "8000000000000000", "0000000000000001", "8000000000000001",
  "7fefffffffffffff", "ffefffffffffffff", "4340000000000000", "c340000000000000",
  "4430000000000000", "44b52d02c7e14af5", "44b52d02c7e14af6", "44b52d02c7e14af7",
  "444b1ae4d6e2ef4e", "444b1ae4d6e2ef4f", "444b1ae4d6e2ef50", "3eb0c6f7a0b5ed8c",
  "3eb0c6f7a0b5ed8d", "41b3de4355555553", "41b3de4355555554", "41b3de4355555555",
  "41b3de4355555556", "41b3de4355555557", "becbf647612f3696", "43143ff3c1cb0959",
];

function doubleFromHex(hex) {
  const view = new DataView(new ArrayBuffer(8));
  view.setBigUint64(0, BigInt("0x" + hex));
  return view.getFloat64(0);
}

// Reference House 001 canonical snapshot: entities sorted by id (D030), then JCS.
const fixturePath = "docs/reference-projects/vermont-timber-house/fixture.snapshot.json";
const fixture = JSON.parse(readFileSync(join(repoRoot, fixturePath), "utf8"));
fixture.entities.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
const fixtureCanonical = canonicalize(fixture);

// Independent ECMAScript implementation of rule vs01-post-beam-1 (generation-rules.md,
// "Numeric evaluation"): exact IEEE formulas, no rounding. Used to check that the
// generated inventory is identical across languages (TIMBER-001 §7, test 3).
function generateInventory(snapshot) {
  const byId = new Map();
  for (const e of snapshot.entities) if (!byId.has(e.id)) byId.set(e.id, e);
  const b = snapshot.building;
  const fp = byId.get(b.footprint_id);
  const [l0, l1] = b.level_ids.map((id) => byId.get(id));
  const frame = byId.get(b.frame_system_id);
  const grid = byId.get(frame.grid_id);
  const xs = grid.x_lines.map((l) => [l.id, fp.origin_m[0] + fp.width_m * l.fraction]);
  const ys = grid.y_lines.map((l) => [l.id, fp.origin_m[1] + fp.depth_m * l.fraction]);
  const z0 = l0.elevation_m, z1 = l1.elevation_m, zEave = l1.elevation_m + l1.story_height_m;
  const post = frame.member_defaults.POST, beam = frame.member_defaults.BEAM;
  const out = [];
  const add = (key, role, start, end, d) =>
    out.push({ generation_key: key, member_role: role, start_m: start, end_m: end, section_id: d.section_id, material_id: d.material_id });
  for (const [xi, x] of xs) for (const [yj, y] of ys) {
    add(`frame/${xi}/${yj}/level-0/post`, "POST", [x, y, z0], [x, y, z1], post);
    add(`frame/${xi}/${yj}/level-1/post`, "POST", [x, y, z1], [x, y, zEave], post);
  }
  for (const [plane, z] of [["plane-L1", z1], ["plane-eave", zEave]]) {
    for (const [yj, y] of ys) for (let i = 0; i + 1 < xs.length; i++)
      add(`frame/axis-x/${yj}/${xs[i][0]}-${xs[i + 1][0]}/${plane}/beam`, "BEAM", [xs[i][1], y, z], [xs[i + 1][1], y, z], beam);
    for (const [xi, x] of xs) for (let j = 0; j + 1 < ys.length; j++)
      add(`frame/axis-y/${xi}/${ys[j][0]}-${ys[j + 1][0]}/${plane}/beam`, "BEAM", [x, ys[j][1], z], [x, ys[j + 1][1], z], beam);
  }
  // String comparison compares UTF-16 code units.
  return out.sort((a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0));
}
const inventoryCanonical = canonicalize(generateInventory(fixture));

// Independent ECMAScript implementation of the GEOM-001 views (artifacts.md §5-6, D048,
// geometry.md "Numeric evaluation"). Only tan(pitch)-derived values may differ from other
// implementations, within 1e-12 m.
function geometryModel(snapshot) {
  const byId = new Map(snapshot.entities.map((e) => [e.id, e]));
  const b = snapshot.building;
  const fp = byId.get(b.footprint_id);
  const [l0, l1] = b.level_ids.map((id) => byId.get(id));
  const roof = byId.get(b.roof_id);
  const members = snapshot.entities
    .filter((e) => e.kind === "TimberMember")
    .sort((a, b2) => (a.generation_key < b2.generation_key ? -1 : a.generation_key > b2.generation_key ? 1 : 0));
  const [x0, y0] = fp.origin_m;
  const x1 = x0 + fp.width_m, y1 = y0 + fp.depth_m;
  const zEave = l1.elevation_m + l1.story_height_m;
  return {
    byId, fp, l0, l1, roof, members, x0, y0, x1, y1, zEave,
    yRidge: y0 + fp.depth_m / 2,
    ySouth: y0 - roof.eave_overhang_m,
    yNorth: y0 + fp.depth_m + roof.eave_overhang_m,
    ring: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
  };
}

function plan2d(snapshot) {
  const m = geometryModel(snapshot);
  const planes = {
    "level-0": { plane_id: "level-0", level_id: m.l0.id, z_m: m.l0.elevation_m, posts: [], beams: [] },
    "level-1": { plane_id: "level-1", level_id: m.l1.id, z_m: m.l1.elevation_m, posts: [], beams: [] },
    eave: { plane_id: "eave", level_id: null, z_m: m.zEave, posts: [], beams: [] },
  };
  for (const mem of m.members) {
    const k = mem.generation_key;
    const [plane, group] = k.includes("/level-0/post") ? ["level-0", "posts"]
      : k.includes("/level-1/post") ? ["level-1", "posts"]
      : k.includes("/plane-L1/") ? ["level-1", "beams"]
      : ["eave", "beams"];
    planes[plane][group].push(group === "posts"
      ? { member_id: mem.id, generation_key: k, xy_m: mem.start_m.slice(0, 2), section_id: mem.section_id }
      : { member_id: mem.id, generation_key: k, start_xy_m: mem.start_m.slice(0, 2), end_xy_m: mem.end_m.slice(0, 2), section_id: mem.section_id });
  }
  return {
    units: "m",
    planes: [planes["level-0"], planes["level-1"], planes.eave],
    footprint: { origin_m: [m.x0, m.y0], width_m: m.fp.width_m, depth_m: m.fp.depth_m, rotation_rad: m.fp.rotation_rad, ring_m: m.ring },
    roof_plan: {
      ridge_m: { start_xy_m: [m.x0, m.yRidge], end_xy_m: [m.x1, m.yRidge] },
      eave_ring_m: [[m.x0, m.ySouth], [m.x1, m.ySouth], [m.x1, m.yNorth], [m.x0, m.yNorth]],
    },
    dimensions: [
      { id: "footprint-width", start_m: [m.x0, m.y0], end_m: [m.x1, m.y0], value_m: m.fp.width_m },
      { id: "footprint-depth", start_m: [m.x0, m.y0], end_m: [m.x0, m.y1], value_m: m.fp.depth_m },
    ],
  };
}

function mesh3d(snapshot) {
  const m = geometryModel(snapshot);
  const t = Math.tan(m.roof.pitch_rad);
  const zRidge = m.zEave + (m.fp.depth_m / 2) * t;
  const zEdge = m.zEave - m.roof.eave_overhang_m * t;
  return {
    units: "m",
    members: m.members.map((mem) => {
      const s = m.byId.get(mem.section_id);
      return { member_id: mem.id, generation_key: mem.generation_key, role: mem.member_role, primitive: "oriented_box",
        axis_start_m: mem.start_m, axis_end_m: mem.end_m, section_width_m: s.actual_width_m, section_depth_m: s.actual_depth_m };
    }),
    envelope: {
      footprint_ring_m: m.ring,
      level_z_m: [m.l0.elevation_m, m.l1.elevation_m],
      z_eave_m: m.zEave,
      roof: {
        kind: "gable", ridge_axis: m.roof.ridge_axis, pitch_rad: m.roof.pitch_rad,
        ridge_start_m: [m.x0, m.yRidge, zRidge], ridge_end_m: [m.x1, m.yRidge, zRidge],
        surfaces: [
          { id: "south", ring_m: [[m.x0, m.ySouth, zEdge], [m.x1, m.ySouth, zEdge], [m.x1, m.yRidge, zRidge], [m.x0, m.yRidge, zRidge]] },
          { id: "north", ring_m: [[m.x0, m.yNorth, zEdge], [m.x0, m.yRidge, zRidge], [m.x1, m.yRidge, zRidge], [m.x1, m.yNorth, zEdge]] },
        ],
      },
    },
  };
}
const plan2dCanonical = canonicalize(plan2d(fixture));

// Independent ECMAScript implementation of timber_schedule (artifacts.md §7, EST-001 §3):
// naive sqrt length, one aggregate per (role, nominal_section) summed in generation_key order.
function timberSchedule(snapshot) {
  const byId = new Map(snapshot.entities.map((e) => [e.id, e]));
  const members = snapshot.entities
    .filter((e) => e.kind === "TimberMember")
    .sort((a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0));
  const totals = new Map();
  const rows = members.map((m) => {
    const s = byId.get(m.section_id), mat = byId.get(m.material_id);
    const dx = m.end_m[0] - m.start_m[0], dy = m.end_m[1] - m.start_m[1], dz = m.end_m[2] - m.start_m[2];
    const length = Math.sqrt(dx * dx + dy * dy + dz * dz);
    const key = m.member_role + "\u0000" + s.nominal_label;
    const t = totals.get(key) || { role: m.member_role, nominal_section: s.nominal_label, count: 0, total_length_m: 0 };
    t.count += 1; t.total_length_m += length; totals.set(key, t);
    return { member_id: m.id, generation_key: m.generation_key, role: m.member_role, nominal_section: s.nominal_label,
      section_id: s.id, material_id: mat.id, species: mat.species, grade: mat.grade, length_m: length, quantity: 1 };
  });
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const aggregates = [...totals.values()].sort((a, b) => cmp(a.role, b.role) || cmp(a.nominal_section, b.nominal_section));
  return {
    units: { length: "m", count: "1" }, length_basis: "reference_axis",
    assumptions: [
      { code: "REFERENCE_AXIS_LENGTH", message: "Lengths are reference-axis distances, not fabrication cut lengths." },
      { code: "NO_CONNECTIONS", message: "Joinery and machining are not included." },
    ],
    members: rows, aggregates,
  };
}
const scheduleCanonical = canonicalize(timberSchedule(fixture));

// Independent UUIDv5 (RFC 9562) over the canonical name array, for D041 ID minting.
function uuidv5(namespace, name) {
  const ns = Buffer.from(namespace.replace(/-/g, ""), "hex");
  const hash = createHash("sha1").update(Buffer.concat([ns, Buffer.from(name, "utf8")])).digest();
  const b = hash.subarray(0, 16);
  b[6] = (b[6] & 0x0f) | 0x50;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.toString("hex");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
const D041_NAMESPACE = "6652101f-3d1d-4a2b-bd82-9d87e0207354";
const mintCases = [
  ["entity", "17ac32e0-0b3b-518e-b568-adf98f41bcd0", "00000000-0000-4000-8000-000000000001", "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", "generation/frame/x0/y0/level-0/post"],
  ["revision", "17ac32e0-0b3b-518e-b568-adf98f41bcd0", "00000000-0000-4000-8000-000000000001", "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", null],
  ["entity", "17ac32e0-0b3b-518e-b568-adf98f41bcd0", "00000000-0000-4000-8000-000000000002", "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", "generation/frame/x0/y0/level-0/post"],
  ["entity", "17ac32e0-0b3b-518e-b568-adf98f41bcd0", "00000000-0000-4000-8000-000000000001", "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", "template/9ba359f1-6354-5019-9b3f-d15f8e53523b"],
];

const output = {
  description:
    "RFC 8785 (JCS) vectors generated by an ECMAScript engine via generate.mjs. " +
    "Do not edit by hand; regenerate and review the diff.",
  generator: `node ${process.version}`,
  documents: documents.map(({ name, input }) => {
    const canonical = canonicalize(JSON.parse(input));
    return { name, input, canonical, fingerprint: sha256(canonical) };
  }),
  numbers: numberHex.map((ieee_hex) => ({ ieee_hex, canonical: canonicalize(doubleFromHex(ieee_hex)) })),
  ids: {
    namespace: D041_NAMESPACE,
    cases: mintCases.map((parts) => ({ parts, name: canonicalize(parts), id: uuidv5(D041_NAMESPACE, canonicalize(parts)) })),
  },
  geometry: {
    source: fixturePath,
    plan2d: { canonical_bytes: Buffer.byteLength(plan2dCanonical, "utf8"), fingerprint: sha256(plan2dCanonical) },
    // Full payload: values derived from tan(pitch) are compared within 1e-12 m, the rest exactly.
    mesh3d: { tan: Math.tan(fixture.entities.find((e) => e.kind === "GableRoof").pitch_rad), payload: mesh3d(fixture) },
    timber_schedule: { canonical_bytes: Buffer.byteLength(scheduleCanonical, "utf8"), fingerprint: sha256(scheduleCanonical), aggregates: timberSchedule(fixture).aggregates },
  },
  inventories: [
    {
      name: "reference-house-001-vs01-post-beam-1",
      source: fixturePath,
      rule: "vs01-post-beam-1",
      members: generateInventory(fixture).length,
      canonical_bytes: Buffer.byteLength(inventoryCanonical, "utf8"),
      fingerprint: sha256(inventoryCanonical),
    },
  ],
  snapshots: [
    {
      name: "reference-house-001",
      source: fixturePath,
      canonical_bytes: Buffer.byteLength(fixtureCanonical, "utf8"),
      fingerprint: sha256(fixtureCanonical),
    },
  ],
};

writeFileSync(join(here, "vectors.json"), JSON.stringify(output, null, 2) + "\n");
console.log(`wrote ${output.documents.length} documents, ${output.numbers.length} numbers, 1 inventory, 1 snapshot`);
