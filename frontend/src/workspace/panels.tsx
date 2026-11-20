/** Read-only workspace panels: revision bar, preliminary banner, views, schedule, estimate, history (UI-001 §4). */

import { useEffect, useRef } from "react";

import type { EstimateEnvelope, Envelope, RevisionSummary, ScheduleEnvelope } from "../api/types";
import { ARTIFACT_TYPES } from "../api/types";
import { ARTIFACT_LABEL, junctionLabel, roleLabel, typeLabel } from "../display/labels";
import { css, ROLE_COLOR } from "../display/palette";
import { formatLength, type UnitSystem } from "../units/length";
import { approxPerFoot, formatCents } from "../units/money";
import type { Highlight, Pick } from "../views/highlight";
import { Mesh3dView } from "../views/Mesh3dView";
import { pairViews, type ViewState } from "../views/pairing";
import { Plan2dView } from "../views/Plan2dView";
import { lineLabel, type ConnectionCatalog } from "./lineItems";
import { statusOf, type RevisionData } from "./useRevisionData";

/** A pick from a view or the schedule. `toggle` clears the selection when it is picked again (UI-003 §6). */
export type OnSelect = (pick: Pick | null, toggle?: boolean) => void;

export const shortId = (id: string) => id.slice(0, 8);

export function RevisionBar({ data }: { data: RevisionData }) {
  const summary = data.revisions.find((r) => r.revision_id === data.revisionId);
  return (
    <section className="revision-bar" aria-label="Revision">
      <span data-testid="revision-label">
        Revision {summary?.sequence ?? "…"} · <code>{data.revisionId ? shortId(data.revisionId) : "…"}</code>
      </span>
      <span className={data.isHead ? "badge head" : "badge historical"} data-testid="revision-kind">
        {data.isHead ? "Head" : "Historical (not the current head)"}
      </span>
      <ul className="chips" aria-label="Artifact status">
        {ARTIFACT_TYPES.map((type) => {
          const status = statusOf(data, type);
          return (
            <li key={type} className={`chip status-${status.toLowerCase()}`} data-testid={`status-${type}`}>
              {ARTIFACT_LABEL[type]}: {status}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** The envelope's PRELIMINARY_UNVERIFIED warning, never hard-coded text (AC-08). */
export function PreliminaryBanner({ envelopes }: { envelopes: (Envelope | { warnings: Envelope["warnings"] } | null)[] }) {
  const warning = envelopes.flatMap((e) => e?.warnings ?? []).find((w) => w.code === "PRELIMINARY_UNVERIFIED");
  return (
    <div className="preliminary" role="note" data-testid="preliminary-banner">
      <strong>Preliminary</strong> {warning ? warning.message : "Loading suitability…"}
    </div>
  );
}

function stateText(state: ViewState): string {
  switch (state) {
    case "LOADING":
      return "Updating…";
    case "FAILED":
      return "Could not be generated.";
    case "MISSING":
      return "Not available.";
    default:
      return `Not current (${state}).`;
  }
}

function ConnectionsSwitch({ show, onChange }: { show: boolean; onChange: (show: boolean) => void }) {
  return (
    <div className="view-options">
      <label>
        <input type="checkbox" role="switch" checked={show} onChange={(e) => onChange(e.target.checked)} /> Connections
      </label>
      <span className="hint">Markers are symbols of fixed size; they show no joint size or capacity.</span>
    </div>
  );
}

export function ViewsPanel({
  data,
  units,
  highlight,
  showConnections,
  onShowConnections,
  onSelect,
}: {
  data: RevisionData;
  units: UnitSystem;
  highlight: Highlight;
  showConnections: boolean;
  onShowConnections: (show: boolean) => void;
  onSelect: OnSelect;
}) {
  const pairing = pairViews(data.plan, data.mesh);
  const toggle = (pick: Pick | null) => onSelect(pick);
  if (pairing.kind === "unpaired") {
    return (
      <section className="views" aria-label="Plan and 3D views" data-testid="views-unpaired">
        <ConnectionsSwitch show={showConnections} onChange={onShowConnections} />
        <div className="view-placeholder" data-testid="plan-state">
          2D plan: {pairing.mismatch ? "Waiting for matching revisions…" : stateText(pairing.plan)}
        </div>
        <div className="view-placeholder" data-testid="mesh-state">
          3D model: {pairing.mismatch ? "Waiting for matching revisions…" : stateText(pairing.mesh)}
        </div>
      </section>
    );
  }
  return (
    <section className="views" aria-label="Plan and 3D views" data-testid="views-paired" data-source-revision-id={pairing.revisionId}>
      <ConnectionsSwitch show={showConnections} onChange={onShowConnections} />
      <Plan2dView plan={pairing.plan} units={units} highlight={highlight} showConnections={showConnections} onSelect={toggle} />
      <Mesh3dView mesh={pairing.mesh} units={units} highlight={highlight} showConnections={showConnections} onSelect={toggle} />
      <p className="source">
        Both views: revision <code>{shortId(pairing.revisionId)}</code>
        {pairing.head ? " (head)" : " (historical)"}
      </p>
    </section>
  );
}

function RoleCell({ role }: { role: string }) {
  const color = (ROLE_COLOR as Record<string, number>)[role];
  return (
    <span className="role" title={role} data-role={role}>
      {color !== undefined && <span className="swatch" style={{ background: css(color) }} aria-hidden="true" />}
      {roleLabel(role)}
    </span>
  );
}

export function SchedulePanel({ schedule, units, highlight, onSelect }: { schedule: ScheduleEnvelope | null; units: UnitSystem; highlight: Highlight; onSelect: OnSelect }) {
  const payload = schedule?.status === "CURRENT" ? schedule.payload : null;
  const keyOf = new Map(payload?.members.map((m) => [m.member_id, m.generation_key]) ?? []);
  const list = useRef<HTMLDivElement>(null);
  const firstSelected = payload?.connections.find((c) => highlight.connections.has(c.connection_id))?.connection_id ?? null;
  // Scroll the connection list (not the page) to the first selected row (UI-003 §6).
  useEffect(() => {
    const container = list.current;
    const row = firstSelected ? container?.querySelector<HTMLElement>(`tr[data-connection-id="${firstSelected}"]`) : null;
    if (!container || !row) return;
    const header = container.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    container.scrollTop += row.getBoundingClientRect().top - container.getBoundingClientRect().top - header;
  }, [firstSelected]);
  const memberLink = (id: string | undefined) =>
    id ? (
      <button type="button" className="link" data-member-id={id} onClick={(e) => (e.stopPropagation(), onSelect({ kind: "member", id }, false))}>
        {keyOf.get(id) ?? id}
      </button>
    ) : (
      "—"
    );
  return (
    <section className="schedule" aria-labelledby="schedule-heading">
      <h2 id="schedule-heading">Timber schedule</h2>
      {!payload ? (
        <p>{schedule ? `Not available (${schedule.status}).` : "Updating…"}</p>
      ) : (
        <>
          <p className="source">
            Revision <code>{shortId(schedule!.source_revision_id)}</code>. Lengths in {units === "imperial" ? "feet-inches" : "meters"} (stored in {payload.units.length}).
          </p>
          <table data-testid="schedule-aggregates">
            <caption>Totals by role and section</caption>
            <thead>
              <tr>
                <th scope="col">Role</th>
                <th scope="col">Section</th>
                <th scope="col">Count</th>
                <th scope="col">Total length</th>
              </tr>
            </thead>
            <tbody>
              {payload.aggregates.map((a) => (
                <tr key={`${a.role}/${a.nominal_section}`}>
                  <td>
                    <RoleCell role={a.role} />
                  </td>
                  <td>{a.nominal_section}</td>
                  <td>{a.count}</td>
                  <td>{formatLength(a.total_length_m, units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="assumptions">
            {payload.assumptions.map((a) => (
              <li key={a.code}>{a.message}</li>
            ))}
          </ul>
          <div className="scroll">
            <table data-testid="schedule-members">
              <caption>Members ({payload.members.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Generation key</th>
                  <th scope="col">Role</th>
                  <th scope="col">Section</th>
                  <th scope="col">Species</th>
                  <th scope="col">Length</th>
                  <th scope="col">Qty</th>
                </tr>
              </thead>
              <tbody>
                {payload.members.map((m) => {
                  const selected = m.member_id === highlight.member;
                  const related = highlight.related.has(m.member_id);
                  return (
                    <tr
                      key={m.member_id}
                      data-member-id={m.member_id}
                      aria-selected={selected}
                      className={selected ? "selected" : related ? "related" : undefined}
                      onClick={() => onSelect({ kind: "member", id: m.member_id })}
                    >
                      <td>
                        <button type="button" className="link" onClick={(e) => (e.stopPropagation(), onSelect({ kind: "member", id: m.member_id }, false))}>
                          {m.generation_key}
                        </button>
                      </td>
                      <td>
                        <RoleCell role={m.role} />
                      </td>
                      <td>{m.nominal_section}</td>
                      <td>{m.species ?? "—"}</td>
                      <td>{formatLength(m.length_m, units)}</td>
                      <td>{m.quantity}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <table data-testid="schedule-connection-aggregates">
            <caption>Connections by junction and type</caption>
            <thead>
              <tr>
                <th scope="col">Junction</th>
                <th scope="col">Type</th>
                <th scope="col">Count</th>
              </tr>
            </thead>
            <tbody>
              {payload.connection_aggregates.map((a) => (
                <tr key={`${a.junction_class}/${a.connection_type}`} data-junction-class={a.junction_class} data-connection-type={a.connection_type}>
                  <td>{junctionLabel(a.junction_class)}</td>
                  <td>{typeLabel(a.connection_type)}</td>
                  <td>{a.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table data-testid="schedule-connection-types">
            <caption>Connection types in use</caption>
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Family</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {payload.connection_catalog.types.map((t) => (
                <tr key={t.connection_type} data-connection-type={t.connection_type}>
                  <td>{typeLabel(t.connection_type)}</td>
                  <td>{t.family}</td>
                  <td>{t.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="scroll" ref={list}>
            <table data-testid="schedule-connections">
              <caption>Connections ({payload.connections.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Junction</th>
                  <th scope="col">Type</th>
                  <th scope="col">Receiving member</th>
                  <th scope="col">Entering member</th>
                </tr>
              </thead>
              <tbody>
                {payload.connections.map((c) => {
                  const selected = highlight.connections.has(c.connection_id);
                  return (
                    <tr
                      key={c.connection_id}
                      data-connection-id={c.connection_id}
                      aria-selected={selected}
                      className={selected ? "selected" : undefined}
                      title={c.generation_key}
                      onClick={() => onSelect({ kind: "connections", ids: [c.connection_id] })}
                    >
                      <td>{junctionLabel(c.junction_class)}</td>
                      <td>{typeLabel(c.connection_type)}</td>
                      <td>{memberLink(c.member_ids[0])}</td>
                      <td>{memberLink(c.member_ids[1])}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

export function EstimatePanel({
  estimate,
  catalog,
  units,
  onEditPrices,
}: {
  estimate: EstimateEnvelope | null;
  /** The same revision's schedule catalog, for connection descriptions (ART-002 §6.3, §9). */
  catalog: ConnectionCatalog | null;
  units: UnitSystem;
  onEditPrices: (() => void) | null;
}) {
  const payload = estimate?.payload ?? null;
  const missing = estimate?.warnings.filter((w) => w.code !== "PRELIMINARY_UNVERIFIED") ?? [];
  return (
    <section className="estimate" aria-labelledby="estimate-heading" data-testid="estimate">
      <h2 id="estimate-heading">Preliminary estimate</h2>
      {!estimate ? (
        <p>Updating…</p>
      ) : estimate.status === "UNAVAILABLE" ? (
        <p data-testid="estimate-unavailable">
          <strong>Costs not configured.</strong> No total is shown until unit prices are set.
        </p>
      ) : estimate.status !== "CURRENT" || !payload ? (
        <p>Not available ({estimate.status}).</p>
      ) : (
        <>
          <p data-testid="estimate-coverage">
            Coverage: <strong>{payload.coverage}</strong>
            {payload.price_book && (
              <>
                {" "}
                · Prices: {payload.price_book.source}, {payload.price_book.geography}, as of {payload.price_book.as_of} (version {payload.price_book.price_book_version})
              </>
            )}
          </p>
          <table>
            <thead>
              <tr>
                <th scope="col">Item</th>
                <th scope="col">Quantity</th>
                <th scope="col">Unit price</th>
                <th scope="col">Amount</th>
              </tr>
            </thead>
            <tbody>
              {payload.line_items.map((li) => (
                <tr key={li.key} data-key={li.key}>
                  <td>{lineLabel(li, catalog)}</td>
                  <td>{li.kind === "connection" ? `${li.quantity_value} each` : formatLength(li.quantity_value, units)}</td>
                  <td>
                    {li.unit_price_minor === null
                      ? "Not priced"
                      : `${formatCents(li.unit_price_minor)}${li.kind === "connection" ? " each" : "/m"}`}
                    {li.kind === "timber" && li.unit_price_minor !== null && units === "imperial" && <span className="approx"> {approxPerFoot(li.unit_price_minor)}</span>}
                  </td>
                  <td>{li.amount_minor === null ? "—" : formatCents(li.amount_minor)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p data-testid="estimate-total">
            {payload.totals.grand_total_minor !== null
              ? `Total: ${formatCents(payload.totals.grand_total_minor)} ${payload.currency ?? ""}`
              : `No total: ${payload.totals.unpriced_line_count} line(s) unpriced. Priced so far: ${formatCents(payload.totals.priced_amount_minor ?? 0)}.`}
          </p>
        </>
      )}
      {missing.length > 0 && (
        <ul className="warnings">
          {missing.map((w) => (
            <li key={w.code}>{w.message}</li>
          ))}
        </ul>
      )}
      {onEditPrices && (
        <button type="button" onClick={onEditPrices}>
          Set unit prices
        </button>
      )}
    </section>
  );
}

export function HistoryPanel({
  revisions,
  shownRevisionId,
  headRevisionId,
  onOpen,
  onUndo,
  busy,
}: {
  revisions: RevisionSummary[];
  shownRevisionId: string | null;
  headRevisionId: string | null;
  onOpen: (revisionId: string | null) => void;
  onUndo: (revisionId: string) => void;
  busy: boolean;
}) {
  return (
    <section className="history" aria-labelledby="history-heading">
      <h2 id="history-heading">History</h2>
      <ol data-testid="history">
        {revisions.map((r) => {
          const isHead = r.revision_id === headRevisionId;
          return (
            <li key={r.revision_id} aria-current={r.revision_id === shownRevisionId ? "true" : undefined}>
              <span>
                {r.sequence}. {r.command_type ?? "Created"} · <code>{shortId(r.revision_id)}</code> {isHead && <em>(head)</em>}
              </span>
              <button type="button" onClick={() => onOpen(isHead ? null : r.revision_id)} disabled={r.revision_id === shownRevisionId}>
                View
              </button>
              {!isHead && (
                <button type="button" onClick={() => onUndo(r.revision_id)} disabled={busy}>
                  Undo to this revision
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
