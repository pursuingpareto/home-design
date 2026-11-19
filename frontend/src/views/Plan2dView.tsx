/**
 * 2D plan from a `plan2d` payload (artifacts.md §5; UI-001 §4, §6). Renders only what the payload
 * says. Dimension labels come from `value_m`, never from drawn lengths (FR-03, AC-01).
 */

import { useState } from "react";

import type { Plan2dPayload } from "../api/types";
import { formatLength, type UnitSystem } from "../units/length";

type PlaneId = Plan2dPayload["planes"][number]["plane_id"];

const PLANE_LABEL: Record<PlaneId, string> = { "level-0": "Level 0", "level-1": "Level 1", eave: "Eave" };
const DIMENSION_OFFSET_M = 1.2; // placement of dimension strings outside the eave line (display only)
const POST_MARK_M = 0.2032; // post marker size; a symbol, not a measured section

export interface Plan2dViewProps {
  plan: Plan2dPayload;
  units: UnitSystem;
  selected: string | null;
  onSelect: (memberId: string | null) => void;
}

type XY = readonly number[];
const pt = (p: XY) => `${p[0] ?? 0},${-(p[1] ?? 0)}`; // SVG y grows downward; plan +Y is north (up)

export function Plan2dView({ plan, units, selected, onSelect }: Plan2dViewProps) {
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

  return (
    <figure className="plan2d">
      <div className="plane-tabs" role="group" aria-label="Plan plane">
        {plan.planes.map((p) => (
          <button key={p.plane_id} type="button" aria-pressed={p.plane_id === planeId} onClick={() => setPlaneId(p.plane_id)}>
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
        {plane?.beams.map((beam) => (
          <line
            key={beam.member_id}
            data-member-id={beam.member_id}
            className={beam.member_id === selected ? "beam selected" : "beam"}
            x1={beam.start_xy_m[0]}
            y1={-(beam.start_xy_m[1] ?? 0)}
            x2={beam.end_xy_m[0]}
            y2={-(beam.end_xy_m[1] ?? 0)}
            onClick={() => onSelect(beam.member_id)}
          >
            <title>{beam.generation_key}</title>
          </line>
        ))}
        {plane?.posts.map((post) => (
          <rect
            key={post.member_id}
            data-member-id={post.member_id}
            className={post.member_id === selected ? "post selected" : "post"}
            x={(post.xy_m[0] ?? 0) - POST_MARK_M / 2}
            y={-(post.xy_m[1] ?? 0) - POST_MARK_M / 2}
            width={POST_MARK_M}
            height={POST_MARK_M}
            onClick={() => onSelect(post.member_id)}
          >
            <title>{post.generation_key}</title>
          </rect>
        ))}
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
