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

// Independent ECMAScript implementation of rule vs02-frame-1 (generation-rules.md; TIMBER-002 §5;
// D058 datum axes): exact IEEE formulas, no rounding. Used to check that the generated inventory
// agrees across languages (TIMBER-002 §8): bit-identical, except principal rafter and purlin z
// values, which depend on tan(pitch_rad) and must agree within 1e-12 m.
function generateInventory(snapshot) {
  const byId = new Map();
  for (const e of snapshot.entities) if (!byId.has(e.id)) byId.set(e.id, e);
  const b = snapshot.building;
  const fp = byId.get(b.footprint_id);
  const [l0, l1] = b.level_ids.map((id) => byId.get(id));
  const roof = byId.get(b.roof_id);
  const frame = byId.get(b.frame_system_id);
  const grid = byId.get(frame.grid_id);
  const p = frame.parameters;
  const xs = grid.x_lines.map((l) => [l.id, fp.origin_m[0] + fp.width_m * l.fraction]);
  const ys = grid.y_lines.map((l) => [l.id, fp.origin_m[1] + fp.depth_m * l.fraction]);
  const z0 = l0.elevation_m, z1 = l1.elevation_m, zEave = l1.elevation_m + l1.story_height_m;
  const yS = fp.origin_m[1], yN = fp.origin_m[1] + fp.depth_m, yRidge = fp.origin_m[1] + fp.depth_m / 2;
  const t = Math.tan(roof.pitch_rad);
  const zRidge = zEave + (fp.depth_m / 2) * t;
  const out = [];
  const add = (key, role, start, end) => {
    const d = frame.member_defaults[role];
    out.push({ generation_key: key, member_role: role, start_m: start, end_m: end, section_id: d.section_id, material_id: d.material_id });
  };
  for (const [xi, x] of xs) for (const [yj, y] of ys) {
    add(`frame/${xi}/${yj}/level-0/post`, "POST", [x, y, z0], [x, y, z1]);
    add(`frame/${xi}/${yj}/level-1/post`, "POST", [x, y, z1], [x, y, zEave]);
  }
  // Bay-lines along X (each Y line) and along Y (each X line) on one plane.
  const bayLines = (plane, z) => {
    const lines = [];
    for (const [yj, y] of ys) for (let i = 0; i + 1 < xs.length; i++)
      lines.push({ prefix: `frame/axis-x/${yj}/${xs[i][0]}-${xs[i + 1][0]}/${plane}`, a: xs[i], b: xs[i + 1], axis: "x", fixed: y, z });
    for (const [xi, x] of xs) for (let j = 0; j + 1 < ys.length; j++)
      lines.push({ prefix: `frame/axis-y/${xi}/${ys[j][0]}-${ys[j + 1][0]}/${plane}`, a: ys[j], b: ys[j + 1], axis: "y", fixed: x, z });
    return lines;
  };
  const point = (line, along, z) => (line.axis === "x" ? [along, line.fixed, z] : [line.fixed, along, z]);
  for (const line of bayLines("plane-L0", z0)) add(`${line.prefix}/sill`, "SILL", point(line, line.a[1], z0), point(line, line.b[1], z0));
  const L = p.knee_brace_leg_m;
  for (const [plane, z, braced] of [["plane-L1", z1, p.knee_braces_level_1], ["plane-eave", zEave, p.knee_braces_eave]]) {
    for (const line of bayLines(plane, z)) {
      add(`${line.prefix}/beam`, "BEAM", point(line, line.a[1], z), point(line, line.b[1], z));
      if (!braced) continue;
      add(`${line.prefix}/brace/${line.a[0]}`, "KNEE_BRACE", point(line, line.a[1], z - L), point(line, line.a[1] + L, z));
      add(`${line.prefix}/brace/${line.b[0]}`, "KNEE_BRACE", point(line, line.b[1], z - L), point(line, line.b[1] - L, z));
    }
  }
  const s = p.joist_spacing_m;
  for (let i = 0; i + 1 < xs.length; i++) {
    const [xaId, xa] = xs[i], [xbId, xb] = xs[i + 1];
    for (let j = 0; j + 1 < ys.length; j++)
      for (let k = 1; xa + k * s < xb - 1e-6; k++) {
        const xk = xa + k * s;
        add(`frame/axis-y/${xaId}-${xbId}/j${k}/${ys[j][0]}-${ys[j + 1][0]}/plane-L1/joist`, "FLOOR_JOIST", [xk, ys[j][1], z1], [xk, ys[j + 1][1], z1]);
      }
  }
  for (const [xi, x] of xs) {
    add(`frame/roof/${xi}/south/principal-rafter`, "PRINCIPAL_RAFTER", [x, yS, zEave], [x, yRidge, zRidge]);
    add(`frame/roof/${xi}/north/principal-rafter`, "PRINCIPAL_RAFTER", [x, yN, zEave], [x, yRidge, zRidge]);
  }
  const n = p.purlins_per_slope;
  for (const [slope, yE] of [["south", yS], ["north", yN]])
    for (let i = 1; i <= n; i++) {
      const f = i / (n + 1);
      const yi = yE + (yRidge - yE) * f, zi = zEave + (zRidge - zEave) * f;
      for (let a = 0; a + 1 < xs.length; a++)
        add(`frame/roof/${xs[a][0]}-${xs[a + 1][0]}/${slope}/p${i}/purlin`, "PURLIN", [xs[a][1], yi, zi], [xs[a + 1][1], yi, zi]);
    }
  // String comparison compares UTF-16 code units.
  return out.sort((a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0));
}
const inventoryCanonical = canonicalize(generateInventory(fixture));

// Independent ECMAScript implementation of the vs02-frame-1 junction rules (CONN-001 §4-5, D059):
// one connection per entering member end. Built from the inventory above, by naming each
// entering and receiving member's key and copying the entering member's endpoint, so the
// locations agree with the inventory exactly. Only rafter-peak and purlin-rafter z values depend
// on tan(pitch_rad) and are compared within 1e-12 m (TIMBER-002 §8).
function generateConnections(snapshot) {
  const byId = new Map();
  for (const e of snapshot.entities) if (!byId.has(e.id)) byId.set(e.id, e);
  const frame = byId.get(snapshot.building.frame_system_id);
  const grid = byId.get(frame.grid_id);
  const yIds = grid.y_lines.map((l) => l.id);
  const members = new Map(generateInventory(snapshot).map((m) => [m.generation_key, m]));
  const out = [];
  const join = (cls, receiving, entering, end) => {
    const r = members.get(receiving), e = members.get(entering);
    if (!r || !e) throw new Error(`no member for ${cls}: ${receiving} / ${entering}`);
    out.push({
      generation_key: `connection/${cls}/${receiving}/${entering}`,
      junction_class: cls,
      connection_type: frame.connection_defaults[cls],
      member_keys: [receiving, entering],
      location_m: end === "start" ? e.start_m : e.end_m,
    });
  };
  const below = { "plane-L1": "level-0", "plane-eave": "level-1" };
  for (const m of members.values()) {
    const k = m.generation_key;
    let g;
    if ((g = k.match(/^frame\/([^/]+)\/([^/]+)\/level-0\/post$/))) {
      // post-sill: the Y sill of the bay starting at the post's Y line, or ending there on the last.
      const j = yIds.indexOf(g[2]);
      const [ya, yb] = j + 1 < yIds.length ? [yIds[j], yIds[j + 1]] : [yIds[j - 1], yIds[j]];
      join("post-sill", `frame/axis-y/${g[1]}/${ya}-${yb}/plane-L0/sill`, k, "start");
    } else if ((g = k.match(/^frame\/axis-x\/([^/]+)\/([^/-]+)-([^/]+)\/(plane-L1|plane-eave)\/beam$/))) {
      join("post-beam", `frame/${g[2]}/${g[1]}/${below[g[4]]}/post`, k, "start");
      join("post-beam", `frame/${g[3]}/${g[1]}/${below[g[4]]}/post`, k, "end");
    } else if ((g = k.match(/^frame\/axis-y\/([^/]+)\/([^/-]+)-([^/]+)\/(plane-L1|plane-eave)\/beam$/))) {
      join("post-beam", `frame/${g[1]}/${g[2]}/${below[g[4]]}/post`, k, "start");
      join("post-beam", `frame/${g[1]}/${g[3]}/${below[g[4]]}/post`, k, "end");
    } else if ((g = k.match(/^(frame\/axis-(x|y)\/([^/]+)\/[^/]+\/(plane-L1|plane-eave))\/brace\/([^/]+)$/))) {
      const station = g[2] === "x" ? `${g[5]}/${g[3]}` : `${g[3]}/${g[5]}`;
      join("brace", `frame/${station}/${below[g[4]]}/post`, k, "start");
      join("brace", `${g[1]}/beam`, k, "end");
    } else if ((g = k.match(/^frame\/axis-y\/([^/-]+)-([^/]+)\/j\d+\/([^/-]+)-([^/]+)\/plane-L1\/joist$/))) {
      join("joist-beam", `frame/axis-x/${g[3]}/${g[1]}-${g[2]}/plane-L1/beam`, k, "start");
      join("joist-beam", `frame/axis-x/${g[4]}/${g[1]}-${g[2]}/plane-L1/beam`, k, "end");
    } else if ((g = k.match(/^frame\/roof\/([^/]+)\/(south|north)\/principal-rafter$/))) {
      const bay = g[2] === "south" ? `${yIds[0]}-${yIds[1]}` : `${yIds[yIds.length - 2]}-${yIds[yIds.length - 1]}`;
      join("rafter-foot", `frame/axis-y/${g[1]}/${bay}/plane-eave/beam`, k, "start");
      if (g[2] === "north") join("rafter-peak", `frame/roof/${g[1]}/south/principal-rafter`, k, "end");
    } else if ((g = k.match(/^frame\/roof\/([^/-]+)-([^/]+)\/(south|north)\/p\d+\/purlin$/))) {
      join("purlin-rafter", `frame/roof/${g[1]}/${g[3]}/principal-rafter`, k, "start");
      join("purlin-rafter", `frame/roof/${g[2]}/${g[3]}/principal-rafter`, k, "end");
    }
  }
  return out.sort((a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0));
}
const connectionsCanonical = canonicalize(generateConnections(fixture));

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
  // MODEL-005 §9 (artifacts.md §5 interim note): posts and beams only until ART-002.
  for (const mem of m.members.filter((x) => x.member_role === "POST" || x.member_role === "BEAM")) {
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
  // Engine family only: the output must be identical on any conforming engine and Node version,
  // and CI checks it with `git diff` (TEST-001 §8), so the exact version must not be recorded here.
  generator: "ECMAScript (Node.js)",
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
      name: "reference-house-001-vs02-frame-1",
      source: fixturePath,
      rule: "vs02-frame-1",
      members: generateInventory(fixture).length,
      canonical_bytes: Buffer.byteLength(inventoryCanonical, "utf8"),
      fingerprint: sha256(inventoryCanonical),
      // Full inventory: rafter and purlin z values are compared within 1e-12 m, the rest exactly.
      inventory: generateInventory(fixture),
      connection_count: generateConnections(fixture).length,
      connections_canonical_bytes: Buffer.byteLength(connectionsCanonical, "utf8"),
      connections_fingerprint: sha256(connectionsCanonical),
      // Full list (CONN-001 §9): rafter-peak and purlin-rafter z values within 1e-12 m, the rest exactly.
      connections: generateConnections(fixture),
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
