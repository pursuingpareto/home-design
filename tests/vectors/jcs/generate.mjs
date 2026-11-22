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

// Independent ECMAScript implementation of rule vs02b-walls-1 (wall-rules.md; ASM-001 §4-6; D065,
// D066, D076, D078-D080): walls in every perimeter bay of each story, and each wall's framing from
// the default definition and the openings on it. Exact IEEE formulas as written, left to right; the
// rule reads no roof value, so every coordinate must be bit-identical to Python (ASM-001 §9).
const EPS = 1e-6;
const byCodeUnits = (a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0);
function generateWalls(snapshot) {
  const byId = new Map();
  for (const e of snapshot.entities) if (!byId.has(e.id)) byId.set(e.id, e);
  const b = snapshot.building;
  const fp = byId.get(b.footprint_id);
  const levels = b.level_ids.map((id) => byId.get(id));
  const frame = byId.get(b.frame_system_id);
  const grid = byId.get(frame.grid_id);
  const system = byId.get(b.wall_system_id);
  const p = frame.parameters;
  const def = byId.get(system.default_assembly_definition_id);
  const fr = def.layers.find((l) => l.framing !== null).framing;
  const material = byId.get(fr.framing_material_id).name;
  const xs = grid.x_lines.map((l) => [l.id, fp.origin_m[0] + fp.width_m * l.fraction]);
  const ys = grid.y_lines.map((l) => [l.id, fp.origin_m[1] + fp.depth_m * l.fraction]);
  const L = p.knee_brace_leg_m;
  const wallKeyOf = new Map(snapshot.entities.filter((e) => e.kind === "Wall").map((w) => [w.id, w.generation_key]));
  const openings = snapshot.entities.filter((e) => e.kind === "Opening").sort((a, c) => (a.id < c.id ? -1 : a.id > c.id ? 1 : 0));
  const walls = [];
  const pieces = [];
  levels.forEach((level, i) => {
    const zLo = level.elevation_m, H = level.story_height_m;
    const braced = i === 0 ? p.knee_braces_level_1 : p.knee_braces_eave;
    const bays = [];
    for (const [yId, y] of [ys[0], ys[ys.length - 1]])
      for (let a = 0; a + 1 < xs.length; a++) bays.push({ axis: "x", line: yId, a: xs[a], b: xs[a + 1], fixed: y });
    for (const [xId, x] of [xs[0], xs[xs.length - 1]])
      for (let a = 0; a + 1 < ys.length; a++) bays.push({ axis: "y", line: xId, a: ys[a], b: ys[a + 1], fixed: x });
    for (const bay of bays) {
      const key = `wall/axis-${bay.axis}/${bay.line}/${bay.a[0]}-${bay.b[0]}/level-${i}`;
      const A = bay.a[1], B = bay.b[1], W = B - A;
      const pt = (along, z) => (bay.axis === "x" ? [along, bay.fixed, z] : [bay.fixed, along, z]);
      walls.push({ generation_key: key, level_index: i, start_m: pt(A, zLo), end_m: pt(B, zLo), height_m: H });
      const add = (k, kind, openingId, start, end, label) => pieces.push({
        generation_key: k, wall_key: key, piece_kind: kind, opening_id: openingId, start_m: start, end_m: end, section_label: label, material_name: material,
      });
      const vert = (k, kind, openingId, u, va, vb, label) => { if (vb - va > EPS) add(k, kind, openingId, pt(A + u, zLo + va), pt(A + u, zLo + vb), label); };
      const horiz = (k, kind, openingId, sa, sb, v, label) => { if (sb - sa > EPS) add(k, kind, openingId, pt(sa, zLo + v), pt(sb, zLo + v), label); };
      const top = (u) => (braced && u < L - EPS ? (H - L) + u : braced && u > W - L + EPS ? (H - L) + (W - u) : H);
      const mine = openings.filter((o) => wallKeyOf.get(o.wall_id) === key);
      if (fr.type === "BUCK") {
        const sec = byId.get(fr.buck_section_id), bw = sec.actual_width_m, label = sec.nominal_label;
        for (const o of mine) {
          const { offset_m: off, width_m: w, sill_height_m: s, height_m: h } = o;
          const win = o.opening_kind === "WINDOW";
          const v0 = win ? s - bw : 0, v1 = s + h + bw;
          const pre = `${key}/opening/${o.id}/`;
          vert(pre + "buck-jamb/start", "BUCK_JAMB", o.id, off - bw / 2, v0, v1, label);
          vert(pre + "buck-jamb/end", "BUCK_JAMB", o.id, off + w + bw / 2, v0, v1, label);
          horiz(pre + "buck-head", "BUCK_HEAD", o.id, A + off, A + (off + w), s + h + bw / 2, label);
          if (win) horiz(pre + "buck-sill", "BUCK_SILL", o.id, A + off, A + (off + w), s - bw / 2, label);
        }
        continue;
      }
      const stud = byId.get(fr.stud_section_id), header = byId.get(fr.header_section_id), girt = byId.get(fr.girt_section_id);
      const t = stud.actual_width_m, d = header.actual_depth_m, S = fr.stud_spacing_m, T = fr.jack_threshold_width_m;
      const rects = mine.map((o) => {
        const { offset_m: off, width_m: w, sill_height_m: s, height_m: h } = o;
        const j = w > T + EPS ? 1 : 0;
        return { o, j, u0: off - (1 + j) * t, u1: off + w + (1 + j) * t, v0: o.opening_kind === "WINDOW" ? s - t : 0, v1: s + h + d };
      });
      for (const { o, j } of rects) {
        const { offset_m: off, width_m: w, sill_height_m: s, height_m: h } = o;
        const pre = `${key}/opening/${o.id}/`;
        const ks = j === 0 ? off - t / 2 : off - 3 * t / 2, ke = j === 0 ? off + w + t / 2 : off + w + 3 * t / 2;
        vert(pre + "king/start", "KING", o.id, ks, 0, top(ks), stud.nominal_label);
        vert(pre + "king/end", "KING", o.id, ke, 0, top(ke), stud.nominal_label);
        if (j === 1) {
          vert(pre + "jack/start", "JACK", o.id, off - t / 2, 0, s + h, stud.nominal_label);
          vert(pre + "jack/end", "JACK", o.id, off + w + t / 2, 0, s + h, stud.nominal_label);
          horiz(pre + "header", "HEADER", o.id, A + (off - t), A + (off + w + t), s + h + d / 2, header.nominal_label);
        } else {
          horiz(pre + "header", "HEADER", o.id, A + off, A + (off + w), s + h + d / 2, header.nominal_label);
        }
        if (o.opening_kind === "WINDOW") horiz(pre + "rough-sill", "ROUGH_SILL", o.id, A + off, A + (off + w), s - t / 2, stud.nominal_label);
      }
      const over = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0);
      for (let k = 1; A + k * S < B - EPS; k++) {
        const pk = k * S, lo = pk - t / 2, hi = pk + t / 2;
        const r = rects.find((x) => over(lo, hi, x.u0, x.u1) > EPS);
        if (!r) { vert(`${key}/stud/s${k}`, "STUD", null, pk, 0, top(pk), stud.nominal_label); continue; }
        if (over(lo, hi, r.u0, r.u0 + t) > EPS || over(lo, hi, r.u1 - t, r.u1) > EPS) continue;
        const pre = `${key}/opening/${r.o.id}/cripple/s${k}/`;
        vert(pre + "above", "CRIPPLE", r.o.id, pk, r.v1, top(pk), stud.nominal_label);
        const onJack = r.j === 1 && (over(lo, hi, r.u0 + t, r.u0 + 2 * t) > EPS || over(lo, hi, r.u1 - 2 * t, r.u1 - t) > EPS);
        if (r.o.opening_kind === "WINDOW" && !onJack) vert(pre + "below", "CRIPPLE", r.o.id, pk, 0, r.v0, stud.nominal_label);
      }
      const n = fr.girt_count;
      for (let gi = 1; gi <= n; gi++) {
        const v = H * (gi / (n + 1)), tg = girt.actual_width_m;
        const cuts = rects.filter((x) => over(v - tg / 2, v + tg / 2, x.v0, x.v1) > EPS)
          .sort((a, c) => a.u0 - c.u0 || (a.o.id < c.o.id ? -1 : a.o.id > c.o.id ? 1 : 0));
        let start = A, name = `${key}/girt/g${gi}/start`;
        for (const c of cuts) {
          horiz(name, "GIRT", null, start, A + c.u0, v, girt.nominal_label);
          start = A + c.u1; name = `${key}/girt/g${gi}/after/${c.o.id}`;
        }
        horiz(name, "GIRT", null, start, B, v, girt.nominal_label);
      }
    }
  });
  return { walls: walls.sort(byCodeUnits), wall_framing: pieces.sort(byCodeUnits) };
}
const fixtureWalls = generateWalls(fixture);
// The same house with the stud infill default (ASM-001 §9): only WallSystem.default_assembly_definition_id differs.
const studFixture = JSON.parse(JSON.stringify(fixture));
studFixture.entities.find((e) => e.kind === "WallSystem").default_assembly_definition_id =
  studFixture.entities.find((e) => e.kind === "AssemblyDefinition" && e.label === "stud-infill").id;
const studWalls = generateWalls(studFixture);

// Independent ECMAScript implementation of the GEOM-001 and ART-002 views (artifacts.md §5-6, D048,
// D060, geometry.md "Numeric evaluation"). Only tan(pitch)-derived values may differ from other
// implementations, within 1e-12 m. Walls, openings, and wall framing (ART-003 §5-6) read no roof
// value and must be bit-identical.
const byKey = (a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0);
const byId = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const VERTICAL = new Set(["STUD", "KING", "JACK", "CRIPPLE", "BUCK_JAMB"]);

// ART-003 §5.1 (D083): the framing layer centered on the reference plane, the others stacked outward
// (earlier layers) and inward (later layers) from it.
function layerSpans(layers) {
  const k = layers.findIndex((l) => l.framing !== null);
  const spans = layers.map(() => null);
  spans[k] = { inner_m: -(layers[k].thickness_m / 2), outer_m: layers[k].thickness_m / 2 };
  for (let j = k - 1; j >= 0; j--) { const inner = spans[j + 1].outer_m; spans[j] = { inner_m: inner, outer_m: inner + layers[j].thickness_m }; }
  for (let j = k + 1; j < layers.length; j++) { const outer = spans[j - 1].inner_m; spans[j] = { inner_m: outer - layers[j].thickness_m, outer_m: outer }; }
  return spans;
}

// Walls, openings, and pieces from the stored records, shared by the plan and the mesh below.
function wallModel(snapshot) {
  const ids = new Map(snapshot.entities.map((e) => [e.id, e]));
  const fp = ids.get(snapshot.building.footprint_id);
  const walls = snapshot.entities.filter((e) => e.kind === "Wall").sort(byKey).map((w) => {
    const alongX = w.end_m[0] !== w.start_m[0];
    // Away from the footprint: compared with its center line, independently of the key (ART-003 §4.2).
    const outward = alongX
      ? (w.start_m[1] < fp.origin_m[1] + fp.depth_m / 2 ? [0.0, -1.0] : [0.0, 1.0])
      : (w.start_m[0] < fp.origin_m[0] + fp.width_m / 2 ? [-1.0, 0.0] : [1.0, 0.0]);
    const def = ids.get(w.assembly_definition_id);
    const spans = layerSpans(def.layers);
    const openings = snapshot.entities.filter((e) => e.kind === "Opening" && e.wall_id === w.id)
      .sort((a, b) => a.offset_m - b.offset_m || byId(a, b));
    return { w, along: alongX ? 0 : 1, outward, def, spans, openings };
  });
  const wallOf = new Map();
  for (const x of walls) for (const pid of x.w.framing_ids) wallOf.set(pid, x);
  const pieces = snapshot.entities.filter((e) => e.kind === "WallFramingPiece").sort(byKey);
  return { ids, walls, wallOf, pieces };
}
const pieceDims = (p, s) => (p.piece_kind === "HEADER"
  ? { in_plane: s.actual_depth_m, through: s.actual_width_m }
  : { in_plane: s.actual_width_m, through: s.actual_depth_m });

function geometryModel(snapshot) {
  const byId = new Map(snapshot.entities.map((e) => [e.id, e]));
  const b = snapshot.building;
  const fp = byId.get(b.footprint_id);
  const [l0, l1] = b.level_ids.map((id) => byId.get(id));
  const roof = byId.get(b.roof_id);
  const members = snapshot.entities.filter((e) => e.kind === "TimberMember").sort(byKey);
  const connections = snapshot.entities.filter((e) => e.kind === "Connection").sort(byKey);
  const [x0, y0] = fp.origin_m;
  const x1 = x0 + fp.width_m, y1 = y0 + fp.depth_m;
  const zEave = l1.elevation_m + l1.story_height_m;
  return {
    byId, fp, l0, l1, roof, members, connections, x0, y0, x1, y1, zEave,
    yRidge: y0 + fp.depth_m / 2,
    ySouth: y0 - roof.eave_overhang_m,
    yNorth: y0 + fp.depth_m + roof.eave_overhang_m,
    ring: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
  };
}

// ART-002 §4.1, written as key patterns per role (the Python builder uses key segments).
const PLAN_SLOTS = {
  POST: [[/\/level-0\/post$/, "level-0", "posts"], [/\/level-1\/post$/, "level-1", "posts"]],
  SILL: [[/\/plane-L0\/sill$/, "level-0", "sills"]],
  BEAM: [[/\/plane-L1\/beam$/, "level-1", "beams"], [/\/plane-eave\/beam$/, "eave", "beams"]],
  FLOOR_JOIST: [[/\/plane-L1\/joist$/, "level-1", "joists"]],
  KNEE_BRACE: [[/\/plane-L1\/brace\/[^/]+$/, "level-1", "braces"], [/\/plane-eave\/brace\/[^/]+$/, "eave", "braces"]],
  PRINCIPAL_RAFTER: [[/^frame\/roof\/[^/]+\/(south|north)\/principal-rafter$/, "roof", "rafters"]],
  PURLIN: [[/^frame\/roof\/[^/]+\/(south|north)\/p\d+\/purlin$/, "roof", "purlins"]],
};
const PLAN_ARRAYS = ["posts", "beams", "sills", "joists", "braces", "rafters", "purlins"];

function plan2d(snapshot) {
  const m = geometryModel(snapshot);
  const plane = (plane_id, level_id, z_m) => ({ plane_id, level_id, z_m, ...Object.fromEntries(PLAN_ARRAYS.map((a) => [a, []])), connections: [], walls: [], wall_framing: [] });
  const planes = {
    "level-0": plane("level-0", m.l0.id, m.l0.elevation_m),
    "level-1": plane("level-1", m.l1.id, m.l1.elevation_m),
    eave: plane("eave", null, m.zEave),
    roof: plane("roof", null, m.zEave),
  };
  const planeOf = new Map();
  for (const mem of m.members) {
    const k = mem.generation_key;
    const slot = (PLAN_SLOTS[mem.member_role] || []).find(([re]) => re.test(k));
    if (!slot) throw new Error(`member ${k} matches no plan plane`);
    const [, planeId, array] = slot;
    planeOf.set(mem.id, planeId);
    planes[planeId][array].push(array === "posts"
      ? { member_id: mem.id, generation_key: k, xy_m: mem.start_m.slice(0, 2) }
      : { member_id: mem.id, generation_key: k, start_xy_m: mem.start_m.slice(0, 2), end_xy_m: mem.end_m.slice(0, 2) });
  }
  for (const c of m.connections) {
    planes[planeOf.get(c.member_ids[1])].connections.push({
      connection_id: c.id, generation_key: c.generation_key, junction_class: c.junction_class,
      connection_type: c.connection_type, xy_m: c.location_m.slice(0, 2),
    });
  }
  const wm = wallModel(snapshot);
  const planeOfLevel = (levelId) => (levelId === m.l0.id ? "level-0" : "level-1");
  for (const { w, along, outward, spans, openings } of wm.walls) {
    const start = w.start_m.slice(0, 2);
    const at = (d) => { const q = start.slice(); q[along] = start[along] + d; return q; };
    planes[planeOfLevel(w.level_id)].walls.push({
      wall_id: w.id, generation_key: w.generation_key, start_xy_m: start, end_xy_m: w.end_m.slice(0, 2), outward_xy: outward,
      exterior_m: spans[0].outer_m, interior_m: -spans[spans.length - 1].inner_m,
      openings: openings.map((o) => ({ opening_id: o.id, opening_kind: o.opening_kind, start_xy_m: at(o.offset_m), end_xy_m: at(o.offset_m + o.width_m) })),
    });
  }
  for (const p of wm.pieces) {
    planes[planeOfLevel(wm.wallOf.get(p.id).w.level_id)].wall_framing.push(VERTICAL.has(p.piece_kind)
      ? { piece_id: p.id, piece_kind: p.piece_kind, xy_m: p.start_m.slice(0, 2) }
      : { piece_id: p.id, piece_kind: p.piece_kind, start_xy_m: p.start_m.slice(0, 2), end_xy_m: p.end_m.slice(0, 2) });
  }
  return {
    units: "m",
    planes: [planes["level-0"], planes["level-1"], planes.eave, planes.roof],
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
  const wm = wallModel(snapshot);
  return {
    units: "m",
    members: m.members.map((mem) => {
      const s = m.byId.get(mem.section_id);
      return { member_id: mem.id, generation_key: mem.generation_key, role: mem.member_role, primitive: "oriented_box",
        axis_start_m: mem.start_m, axis_end_m: mem.end_m, section_width_m: s.actual_width_m, section_depth_m: s.actual_depth_m };
    }),
    connections: m.connections.map((c) => ({
      connection_id: c.id, generation_key: c.generation_key, junction_class: c.junction_class,
      connection_type: c.connection_type, location_m: c.location_m,
    })),
    walls: wm.walls.map(({ w, outward, def, spans, openings }) => ({
      wall_id: w.id, generation_key: w.generation_key, primitive: "layered_wall", base_start_m: w.start_m, base_end_m: w.end_m,
      height_m: w.height_m, outward_xy: outward,
      layers: def.layers.map((l, i) => ({ name: l.name, function: l.function, inner_m: spans[i].inner_m, outer_m: spans[i].outer_m })),
      voids: openings.map((o) => ({ opening_id: o.id, opening_kind: o.opening_kind, u_m: [o.offset_m, o.offset_m + o.width_m],
        v_m: [o.sill_height_m, o.sill_height_m + o.height_m] })),
    })),
    wall_framing: wm.pieces.map((p) => {
      const d = pieceDims(p, wm.ids.get(p.section_id));
      return { piece_id: p.id, piece_kind: p.piece_kind, wall_id: wm.wallOf.get(p.id).w.id, axis_start_m: p.start_m, axis_end_m: p.end_m,
        section_in_plane_m: d.in_plane, section_through_wall_m: d.through };
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

// Independent ECMAScript implementation of timber_schedule (artifacts.md §7, EST-001 §3, ART-002 §6):
// naive sqrt length, one aggregate per (role, nominal_section) summed in generation_key order; one
// row per connection without its location, one count per (junction_class, connection_type) in use,
// and the catalog entries of the types in use.
const CATALOG = {
  PEGGED_MORTISE_TENON: ["traditional", "Pegged mortise and tenon."],
  BRIDLE: ["traditional", "Bridle joint."],
  HOUSED_DOVETAIL: ["traditional", "Housed dovetail."],
  STEEL_KNIFE_PLATE: ["engineered", "Concealed steel knife plate with dowels."],
  JOIST_HANGER: ["engineered", "Joist hanger."],
};
function timberSchedule(snapshot) {
  const byId = new Map(snapshot.entities.map((e) => [e.id, e]));
  const members = snapshot.entities.filter((e) => e.kind === "TimberMember").sort(byKey);
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
  const connections = snapshot.entities.filter((e) => e.kind === "Connection").sort(byKey);
  const counts = new Map();
  for (const c of connections) {
    const k = c.junction_class + "\u0000" + c.connection_type;
    const a = counts.get(k) || { junction_class: c.junction_class, connection_type: c.connection_type, count: 0 };
    a.count += 1; counts.set(k, a);
  }
  const connection_aggregates = [...counts.values()].sort((a, b) => cmp(a.junction_class, b.junction_class) || cmp(a.connection_type, b.connection_type));
  const usedTypes = [...new Set(connections.map((c) => c.connection_type))].sort();
  return {
    units: { length: "m", count: "1" }, length_basis: "reference_axis",
    assumptions: [
      { code: "REFERENCE_AXIS_LENGTH", message: "Lengths are reference-axis distances, not fabrication cut lengths." },
      { code: "CONNECTIONS_REPRESENTATIONAL", message: "Connections are listed by type and count only. Types are representational: no capacity, sizes, fasteners, or machining." },
      { code: "UNCLASSED_JOINTS_NOT_COUNTED", message: "Joints without a junction class, such as post splices and sill joints at grid stations, are not counted." },
    ],
    members: rows, aggregates,
    connections: connections.map((c) => ({ connection_id: c.id, generation_key: c.generation_key, junction_class: c.junction_class,
      connection_type: c.connection_type, member_ids: c.member_ids, quantity: 1 })),
    connection_aggregates,
    connection_catalog: {
      catalog_version: "vs02-connections-1",
      types: usedTypes.map((t) => ({ connection_type: t, family: CATALOG[t][0],
        description: `${CATALOG[t][1]} Representational only: no capacity, sizes, or fasteners.` })),
    },
  };
}
const scheduleCanonical = canonicalize(timberSchedule(fixture));

// Independent ECMAScript implementation of the assembly schedule's quantities (ART-003 §4.2-4.6; D071,
// D082), from the walls and pieces this file's own wall rule generates (generateWalls above), so the
// straw bale fixture and the stud infill house are both covered. Areas and lengths are exact IEEE
// formulas as written, summed in row order; nothing depends on tan, so Python must agree bit for bit.
function assemblyQuantities(snapshot, generated) {
  const ids = new Map(snapshot.entities.map((e) => [e.id, e]));
  const def = ids.get(snapshot.entities.find((e) => e.kind === "WallSystem").default_assembly_definition_id);
  const section = new Map(snapshot.entities.filter((e) => e.kind === "Section").map((s) => [s.nominal_label, s]));
  const keyOf = new Map(snapshot.entities.filter((e) => e.kind === "Wall").map((w) => [w.id, w.generation_key]));
  const openings = snapshot.entities.filter((e) => e.kind === "Opening")
    .map((o) => ({ o, key: keyOf.get(o.wall_id) }))
    .sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : byId(a.o, b.o)));
  const len = (s, e) => { const dx = e[0] - s[0], dy = e[1] - s[1], dz = e[2] - s[2]; return Math.sqrt(dx * dx + dy * dy + dz * dz); };
  const walls = generated.walls.map((w) => {
    const along = w.end_m[0] !== w.start_m[0] ? 0 : 1;
    const length = len(w.start_m, w.end_m);
    const gross = length * w.height_m;
    let opening = 0;
    for (const { o, key } of openings) if (key === w.generation_key) opening += o.width_m * o.height_m;
    const net = gross - opening;
    // §4.4: faces summed in key order, less each girt-to-vertical overlap, so a crossing counts once.
    const mine = generated.wall_framing.filter((p) => p.wall_key === w.generation_key);
    let face = 0;
    const rects = mine.map((p) => {
      const ip = pieceDims(p, section.get(p.section_label)).in_plane;
      face += ip * len(p.start_m, p.end_m);
      const h = ip / 2;
      return VERTICAL.has(p.piece_kind)
        ? { kind: p.piece_kind, u: [p.start_m[along] - h, p.start_m[along] + h], v: [Math.min(p.start_m[2], p.end_m[2]), Math.max(p.start_m[2], p.end_m[2])] }
        : { kind: p.piece_kind, u: [Math.min(p.start_m[along], p.end_m[along]), Math.max(p.start_m[along], p.end_m[along])], v: [p.start_m[2] - h, p.start_m[2] + h] };
    });
    for (const g of rects.filter((r) => r.kind === "GIRT")) {
      for (const r of rects.filter((x) => VERTICAL.has(x.kind))) {
        const du = Math.min(g.u[1], r.u[1]) - Math.max(g.u[0], r.u[0]), dv = Math.min(g.v[1], r.v[1]) - Math.max(g.v[0], r.v[0]);
        if (du > EPS && dv > EPS) face -= du * dv;
      }
    }
    return { generation_key: w.generation_key, length_m: length, height_m: w.height_m, gross_area_m2: gross, opening_area_m2: opening,
      net_area_m2: net, framing_face_area_m2: face, framing_fraction: face / net };
  });
  const totals = new Map();
  for (const p of generated.wall_framing) {
    const k = p.piece_kind + "\u0000" + p.section_label;
    const t = totals.get(k) || { piece_kind: p.piece_kind, nominal_section: p.section_label, count: 0, total_length_m: 0 };
    t.count += 1; t.total_length_m += len(p.start_m, p.end_m); totals.set(k, t);
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  let gross = 0, opening = 0, net = 0, face = 0, fill = 0;
  for (const w of walls) { gross += w.gross_area_m2; opening += w.opening_area_m2; net += w.net_area_m2; face += w.framing_face_area_m2; fill += w.net_area_m2 - w.framing_face_area_m2; }
  const kinds = new Map();
  for (const { o } of openings) { const a = kinds.get(o.opening_kind) || { opening_kind: o.opening_kind, count: 0, area_m2: 0 }; a.count += 1; a.area_m2 += o.width_m * o.height_m; kinds.set(o.opening_kind, a); }
  return {
    walls,
    definition_aggregates: [{ assembly_label: def.label, wall_count: walls.length, opening_count: openings.length, gross_area_m2: gross, opening_area_m2: opening, net_area_m2: net }],
    layer_aggregates: def.layers.map((l) => { const area = l.framing !== null ? fill : net; return { assembly_label: def.label, layer: l.name, area_m2: area, volume_m3: area * l.thickness_m }; }),
    framing_aggregates: [...totals.values()].sort((a, b) => cmp(a.piece_kind, b.piece_kind) || cmp(a.nominal_section, b.nominal_section)),
    opening_aggregates: [...kinds.values()].sort((a, b) => cmp(a.opening_kind, b.opening_kind)),
    totals: { wall_count: walls.length, opening_count: openings.length, gross_area_m2: gross, opening_area_m2: opening, net_area_m2: net, framing_face_area_m2: face },
  };
}

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
    timber_schedule: {
      canonical_bytes: Buffer.byteLength(scheduleCanonical, "utf8"),
      fingerprint: sha256(scheduleCanonical),
      aggregates: timberSchedule(fixture).aggregates,
      connection_aggregates: timberSchedule(fixture).connection_aggregates,
    },
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
      // ASM-001 §9: walls and wall framing with the straw bale default, compared bit for bit.
      wall_rule: "vs02b-walls-1",
      walls: fixtureWalls.walls,
      wall_framing: fixtureWalls.wall_framing,
      // ART-003 §9.2: the assembly schedule's quantities from the walls above, compared bit for bit.
      assembly_schedule: assemblyQuantities(fixture, fixtureWalls),
    },
    {
      name: "reference-house-001-stud-infill-vs02b-walls-1",
      source: fixturePath,
      rule: "vs02b-walls-1",
      default_assembly: "stud-infill",
      walls: studWalls.walls,
      wall_framing: studWalls.wall_framing,
      assembly_schedule: assemblyQuantities(studFixture, studWalls),
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
console.log(`wrote ${output.documents.length} documents, ${output.numbers.length} numbers, ${output.inventories.length} inventories, 1 snapshot`);
