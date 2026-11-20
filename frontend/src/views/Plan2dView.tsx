/**
 * 2D plan from a `plan2d` payload (artifacts.md §5; UI-001 §4, §6). Renders only what the payload
 * says. Dimension labels come from `value_m`, never from drawn lengths (FR-03, AC-01).
 *
 * Roles have their own colors and line weights (UI-003 §4). Knee braces project onto their beams'
 * lines (ART-002 §4.1), so they are drawn after the beams, thinner and dashed. Connection markers are
 * drawn last, one glyph per distinct point (D062).
 */

import { useState } from "react";

import type { Plan2dPayload } from "../api/types";
import type { Role } from "../display/labels";
import { css, glyphColor, MIXED_COLOR, ROLE_COLOR, SELECTION_COLOR } from "../display/palette";
import { formatLength, type UnitSystem } from "../units/length";
import type { Highlight, Pick } from "./highlight";
import { Legend, typesOf } from "./Legend";
import { glyphTitle, groupMarkers } from "./markers";

type PlaneId = Plan2dPayload["planes"][number]["plane_id"];
type Plane = Plan2dPayload["planes"][number];
type PlanMarker = Plane["connections"][number];
type LinearArray = "sills" | "joists" | "rafters" | "purlins" | "beams" | "braces";

const PLANE_LABEL: Record<PlaneId, string> = { "level-0": "Level 0", "level-1": "Level 1", eave: "Eave", roof: "Roof" };
const ROLE_OF: Record<LinearArray | "posts", Role> = {
  posts: "POST",
  beams: "BEAM",
  sills: "SILL",
  joists: "FLOOR_JOIST",
  braces: "KNEE_BRACE",
  rafters: "PRINCIPAL_RAFTER",
  purlins: "PURLIN",
};
// Drawing order: the other linear roles first, then beams, then braces above the beams (UI-003 §4).
const LINEAR_ARRAYS = ["sills", "joists", "rafters", "purlins", "beams", "braces"] as const satisfies readonly LinearArray[];
const DIMENSION_OFFSET_M = 1.2; // placement of dimension strings outside the eave line (display only)
const POST_MARK_M = 0.2032; // post marker size; a symbol, not a measured section
// Connection marker diameter and count label size: symbols of fixed size, not joint sizes (AC2-07).
const CONNECTION_MARK_M = 0.14;
const COUNT_TEXT_M = 0.22;

export interface Plan2dViewProps {
  plan: Plan2dPayload;
  units: UnitSystem;
  highlight: Highlight;
  showConnections: boolean;
  onSelect: (pick: Pick | null) => void;
}

type XY = readonly number[];
const pt = (p: XY) => `${p[0] ?? 0},${-(p[1] ?? 0)}`; // SVG y grows downward; plan +Y is north (up)

export function Plan2dView({ plan, units, highlight, showConnections, onSelect }: Plan2dViewProps) {
  const [planeId, setPlaneId] = useState<PlaneId>("level-0");
  const plane = plan.planes.find((p) => p.plane_id === planeId) ?? plan.planes[0];
  const ring = plan.roof_plan.eave_ring_m;
  const xs = [...ring, ...plan.footprint.ring_m].map((p) => p[0] ?? 0);
  const ys = [...ring, ...plan.footprint.ring_m].map((p) => p[1] ?? 0);
  const pad = DIMENSION_OFFSET_M + 1.2;
  const minX = Math.min(...xs) - pad;
  const maxX = Math.max(...xs) + 0.6;
  const minY = Math.min(...ys) - pad;
  const maxY = Math.max(...ys) + 0.6;
  const dims = plan.dimensions.map((d) => ({ ...d, label: formatLength(d.value_m, units) }));
  const description = `Plan, ${PLANE_LABEL[plane?.plane_id ?? "level-0"]}. ${dims
    .map((d) => `${d.id === "footprint-width" ? "Width" : "Depth"} ${d.label}`)
    .join(", ")}.`;
  const markers = plane?.connections ?? [];
  const glyphs = showConnections ? groupMarkers<PlanMarker>(markers, (m) => m.xy_m) : [];
  const roles = new Set<Role>(plane ? (Object.keys(ROLE_OF) as (keyof typeof ROLE_OF)[]).filter((a) => plane[a].length > 0).map((a) => ROLE_OF[a]) : []);

  const memberColor = (id: string, role: Role) =>
    css(id === highlight.member ? SELECTION_COLOR.selected : highlight.related.has(id) ? SELECTION_COLOR.related : ROLE_COLOR[role]);
  const memberClass = (base: string, id: string) =>
    `${base}${id === highlight.member ? " selected" : ""}${highlight.related.has(id) ? " related" : ""}`;

  return (
    <figure className="plan2d" data-connection-count={glyphs.reduce((n, g) => n + g.markers.length, 0)} data-glyph-count={glyphs.length}>
      <div className="plane-tabs" role="group" aria-label="Plan plane">
        {plan.planes.map((p) => (
          <button
            key={p.plane_id}
            type="button"
            aria-pressed={p.plane_id === planeId}
            onClick={() => {
              if (p.plane_id !== planeId) onSelect(null); // a plane change clears the selection (UI-003 §6)
              setPlaneId(p.plane_id);
            }}
          >
            {PLANE_LABEL[p.plane_id]}
          </button>
        ))}
      </div>
      <svg
        role="img"
        aria-label={description}
        viewBox={`${minX} ${-maxY} ${maxX - minX} ${maxY - minY}`}
        preserveAspectRatio="xMidYMid meet"
        onClick={(event) => {
          if (event.target === event.currentTarget) onSelect(null);
        }}
      >
        <title>{description}</title>
        <polygon className="eave" points={ring.map(pt).join(" ")} />
        <polygon className="footprint" points={plan.footprint.ring_m.map(pt).join(" ")} />
        <line
          className="ridge"
          x1={plan.roof_plan.ridge_m.start_xy_m[0]}
          y1={-(plan.roof_plan.ridge_m.start_xy_m[1] ?? 0)}
          x2={plan.roof_plan.ridge_m.end_xy_m[0]}
          y2={-(plan.roof_plan.ridge_m.end_xy_m[1] ?? 0)}
        />
        {plane &&
          LINEAR_ARRAYS.flatMap((array) =>
            plane[array].map((member) => (
              <line
                key={member.member_id}
                data-member-id={member.member_id}
                data-array={array}
                data-role={ROLE_OF[array]}
                className={memberClass(array === "beams" ? "beam" : `member ${array}`, member.member_id)}
                stroke={memberColor(member.member_id, ROLE_OF[array])}
                x1={member.start_xy_m[0]}
                y1={-(member.start_xy_m[1] ?? 0)}
                x2={member.end_xy_m[0]}
                y2={-(member.end_xy_m[1] ?? 0)}
                onClick={() => onSelect({ kind: "member", id: member.member_id })}
              >
                <title>{member.generation_key}</title>
              </line>
            )),
          )}
        {plane?.posts.map((post) => (
          <rect
            key={post.member_id}
            data-member-id={post.member_id}
            data-role="POST"
            className={memberClass("post", post.member_id)}
            fill={memberColor(post.member_id, "POST")}
            x={(post.xy_m[0] ?? 0) - POST_MARK_M / 2}
            y={-(post.xy_m[1] ?? 0) - POST_MARK_M / 2}
            width={POST_MARK_M}
            height={POST_MARK_M}
            onClick={() => onSelect({ kind: "member", id: post.member_id })}
          >
            <title>{post.generation_key}</title>
          </rect>
        ))}
        {glyphs.map((glyph) => {
          const ids = glyph.markers.map((m) => m.connection_id);
          const selected = ids.some((id) => highlight.connections.has(id));
          const x = glyph.position[0] ?? 0;
          const y = -(glyph.position[1] ?? 0);
          const mixed = glyph.style === "mixed";
          return (
            <g
              key={glyph.key}
              className={selected ? "connection-glyph selected" : "connection-glyph"}
              data-connection-ids={ids.join(" ")}
              data-connection-count={ids.length}
              data-connection-type={glyph.style}
              onClick={() => onSelect({ kind: "connections", ids })}
            >
              <title>{glyphTitle(glyph)}</title>
              <circle
                cx={x}
                cy={y}
                r={CONNECTION_MARK_M / 2}
                fill={mixed ? "#ffffff" : css(glyphColor(glyph.style))}
                stroke={css(selected ? SELECTION_COLOR.selected : mixed ? MIXED_COLOR : 0xffffff)}
              />
              {ids.length > 1 && (
                <text x={x + CONNECTION_MARK_M * 0.6} y={y - CONNECTION_MARK_M * 0.6} fontSize={COUNT_TEXT_M} fill={css(selected ? SELECTION_COLOR.selected : MIXED_COLOR)}>
                  {ids.length}
                </text>
              )}
            </g>
          );
        })}
        {dims.map((d) => {
          const horizontal = d.id === "footprint-width";
          const offsetY = horizontal ? Math.min(...ys) - DIMENSION_OFFSET_M : 0;
          const offsetX = horizontal ? 0 : Math.min(...xs) - DIMENSION_OFFSET_M;
          const [x1, y1] = horizontal ? [d.start_m[0] ?? 0, offsetY] : [offsetX, d.start_m[1] ?? 0];
          const [x2, y2] = horizontal ? [d.end_m[0] ?? 0, offsetY] : [offsetX, d.end_m[1] ?? 0];
          const mx = (x1 + x2) / 2;
          const my = -(y1 + y2) / 2;
          return (
            <g key={d.id} className="dimension" data-dimension={d.id}>
              <line x1={x1} y1={-y1} x2={x2} y2={-y2} />
              <text
                x={horizontal ? mx : mx - 0.25}
                y={horizontal ? my - 0.25 : my}
                textAnchor="middle"
                transform={horizontal ? undefined : `rotate(-90 ${mx - 0.25} ${my})`}
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
      <Legend testId="plan-legend" roles={roles} types={showConnections ? typesOf(markers) : []} mixed={glyphs.some((g) => g.style === "mixed")} />
      <figcaption>
        {dims.map((d) => (
          <span key={d.id} data-testid={`dim-${d.id}`}>
            {d.id === "footprint-width" ? "Width" : "Depth"}: {d.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
