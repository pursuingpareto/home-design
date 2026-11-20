/**
 * Sections (UI-002 §6.4): the catalog, `AddSection` (routine: applied directly), and
 * `SetMemberSection` per role (consequential: previewed). Material editing is deferred (D043).
 */

import { useCallback, useState, type FormEvent } from "react";

import type { Snapshot } from "../../api/types";
import { formatLength, parseLength } from "../../units/length";
import { describeDetail, placeDetails } from "../commands";
import { entitiesOf, envelope, one } from "./model";
import { detailsFor, isBusy, TextField, type EditorProps } from "./shared";

type Role = Extract<Snapshot["entities"][number], { kind: "TimberMember" }>["member_role"];
const ADD_PATHS = { label: "args.nominal_label", width: "args.actual_width_m", depth: "args.actual_depth_m" };

export function SectionsEditor({ projectId, snapshot, units, flow, onApplied, onOpenPrices }: EditorProps & { onOpenPrices: (() => void) | null }) {
  const sections = snapshot ? entitiesOf(snapshot, "Section") : [];
  const frame = snapshot ? one(snapshot, "FrameSystem") : null;
  const defaults = (frame?.member_defaults ?? {}) as Partial<Record<Role, { section_id: string; material_id: string }>>;
  const roles = (Object.keys(defaults) as Role[]).sort();
  const [form, setForm] = useState({ label: "", width: "", depth: "" });
  const [parseErrors, setParseErrors] = useState<Partial<Record<"label" | "width" | "depth", string>>>({});
  const [choice, setChoice] = useState<Partial<Record<Role, string>>>({});
  const addDetails = placeDetails(detailsFor(flow.state, ["AddSection"]), ADD_PATHS).byField;
  const roleDetails = detailsFor(flow.state, ["SetMemberSection"]);
  const busy = isBusy(flow.state);

  const usedBy = useCallback((sectionId: string) => roles.filter((r) => defaults[r]?.section_id === sectionId).join(", ") || "—", [roles, defaults]);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!snapshot) return;
    const label = form.label.trim();
    const width = parseLength(form.width, units);
    const depth = parseLength(form.depth, units);
    setParseErrors({ label: label ? undefined : "Enter a label, such as 10x12.", width: width.ok ? undefined : width.error, depth: depth.ok ? undefined : depth.error });
    if (!label || !width.ok || !depth.ok) return;
    const base = snapshot.revision_id;
    const result = await flow.apply(envelope(projectId, base, "AddSection", { nominal_label: label, actual_width_m: width.meters, actual_depth_m: depth.meters }));
    if (result) {
      onApplied(result, `Added section ${label} (${formatLength(width.meters, units)} × ${formatLength(depth.meters, units)}).`, base);
      setForm({ label: "", width: "", depth: "" });
    }
  }

  function setRole(role: Role) {
    const sectionId = choice[role];
    if (!snapshot || !sectionId) return;
    void flow.preview(envelope(projectId, snapshot.revision_id, "SetMemberSection", { role, section_id: sectionId }));
  }

  return (
    <div className="editor" aria-label="Sections editor" role="group">
      <table data-testid="section-catalog">
        <caption>Section catalog</caption>
        <thead>
          <tr>
            <th scope="col">Label</th>
            <th scope="col">Actual size (width × depth)</th>
            <th scope="col">Used by</th>
          </tr>
        </thead>
        <tbody>
          {sections.map((s) => (
            <tr key={s.id}>
              <td>{s.nominal_label}</td>
              <td>
                {formatLength(s.actual_width_m, units)} × {formatLength(s.actual_depth_m, units)}
              </td>
              <td>{usedBy(s.id)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Section per role</h3>
      <p className="hint">A change applies to every member of that role, never a single member. Material is unchanged.</p>
      {roles.map((role) => {
        const current = defaults[role]?.section_id ?? "";
        const selected = choice[role] ?? current;
        const id = `role-${role}`;
        return (
          <div className="field role-row" key={role}>
            <label htmlFor={id}>{role}</label>
            <select id={id} value={selected} onChange={(e) => setChoice((c) => ({ ...c, [role]: e.target.value }))}>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nominal_label}
                </option>
              ))}
            </select>
            <button type="button" disabled={busy || selected === current} onClick={() => setRole(role)}>
              Preview {role} change
            </button>
          </div>
        );
      })}
      {roleDetails.length > 0 && (
        <p className="field-error" role="alert">
          The section change was rejected: {roleDetails.map(describeDetail).join("; ")}
        </p>
      )}
      <p className="hint" data-testid="pricing-note">
        Prices are keyed by role and section label (for example timber.BEAM.8x12). After a role changes section, its old price no longer applies and the estimate becomes
        partial until you price the new section.{" "}
        {onOpenPrices && (
          <button type="button" className="link" onClick={onOpenPrices}>
            Set unit prices
          </button>
        )}
      </p>

      <form onSubmit={add} aria-label="Add a section">
        <h3>Add a section</h3>
        <TextField id="section-label" label="Label" value={form.label} problems={[parseErrors.label, ...(addDetails.label ?? [])]} onChange={(t) => setForm((f) => ({ ...f, label: t }))} hint="Unique in this project, such as 10x12." />
        <TextField id="section-width" label="Actual width" value={form.width} problems={[parseErrors.width, ...(addDetails.width ?? [])]} onChange={(t) => setForm((f) => ({ ...f, width: t }))} hint={`For example 9 1/2" or 0.2413 m.`} />
        <TextField id="section-depth" label="Actual depth" value={form.depth} problems={[parseErrors.depth, ...(addDetails.depth ?? [])]} onChange={(t) => setForm((f) => ({ ...f, depth: t }))} />
        <p className="hint">Adding a section is routine: it is applied without a preview and changes no members.</p>
        <button type="submit" disabled={busy || !snapshot}>
          Add section
        </button>
      </form>
    </div>
  );
}
