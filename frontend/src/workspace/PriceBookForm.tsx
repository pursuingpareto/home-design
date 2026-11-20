/**
 * Price-book form (UI-001 §5.1; artifacts.md §8.2). Not a model command: no revision, no preview.
 *
 * - Rows come from the estimate's line items, plus stored rows that match none (kept, marked unused,
 *   with their stored unit).
 * - Timber prices are typed per foot (imperial) or per meter (metric) and parsed exactly to cents; the
 *   book stores whole cents per meter, so per-foot prices are converted and rounded half-even, and the
 *   stored value is shown before saving. Connection prices are per piece ("each", ART-002 §7.3, §9):
 *   whole cents, never converted. An untouched row keeps its stored value exactly.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError, type Api } from "../api/client";
import type { EstimatePayload, PriceBook, PriceRow, StoredPriceBook } from "../api/types";
import { ErrorNotice } from "../app/ErrorNotice";
import type { UnitSystem } from "../units/length";
import { approxPerFoot, centsPerMeter, formatCents, parseMoney, priceInputText } from "../units/money";
import { describeDetail, placeDetails } from "./commands";
import { lineLabel, type ConnectionCatalog } from "./lineItems";

type Unit = PriceRow["unit"];

interface Row {
  key: string;
  label: string;
  unit: Unit;
  unused: boolean;
  stored: number | null; // whole cents per meter ("m") or per piece ("each") in the current book
  text: string;
  dirty: boolean;
}

export type RowResult = { kind: "blank" } | { kind: "price"; unitPriceMinor: number } | { kind: "invalid"; error: string };

export function rowResult(row: Pick<Row, "unit" | "stored" | "text" | "dirty">, units: UnitSystem): RowResult {
  if (!row.dirty) return row.stored === null ? { kind: "blank" } : { kind: "price", unitPriceMinor: row.stored };
  if (row.text.trim() === "") return { kind: "blank" };
  const parsed = parseMoney(row.text);
  if (!parsed.ok) return { kind: "invalid", error: parsed.error };
  return { kind: "price", unitPriceMinor: Number(row.unit === "each" ? parsed.cents : centsPerMeter(parsed.cents, units)) };
}

/** Text for a row's input: per foot or meter for "m" rows, per piece for "each" rows. */
export function rowText(stored: number | null, unit: Unit, units: UnitSystem): string {
  if (stored === null) return "";
  return unit === "each" ? (stored / 100).toFixed(2) : priceInputText(stored, units);
}

/** The book to PUT, or null when a row is invalid. Blank rows are left out (partial coverage). */
export function buildBook(meta: { source: string; geography: string; as_of: string }, rows: Pick<Row, "key" | "unit" | "stored" | "text" | "dirty">[], units: UnitSystem): { book: PriceBook; keys: string[] } | null {
  const out: PriceBook["rows"] = [];
  for (const row of rows) {
    const result = rowResult(row, units);
    if (result.kind === "invalid") return null;
    if (result.kind === "price") out.push({ key: row.key, unit: row.unit, unit_price_minor: result.unitPriceMinor });
  }
  return { book: { currency: "USD", as_of: meta.as_of, source: meta.source.trim(), geography: meta.geography.trim(), rows: out }, keys: out.map((r) => r.key) };
}

export function initialRows(estimate: EstimatePayload, stored: StoredPriceBook | null, units: UnitSystem, catalog: ConnectionCatalog | null = null): Row[] {
  const prices = new Map((stored?.book.rows ?? []).map((r) => [r.key, r.unit_price_minor]));
  const rows: Row[] = estimate.line_items.map((li) => {
    const price = prices.get(li.key) ?? null;
    return { key: li.key, label: lineLabel(li, catalog), unit: li.quantity_unit, unused: false, stored: price, text: rowText(price, li.quantity_unit, units), dirty: false };
  });
  for (const row of stored?.book.rows ?? []) {
    if (!rows.some((r) => r.key === row.key)) {
      rows.push({ key: row.key, label: row.key, unit: row.unit, unused: true, stored: row.unit_price_minor, text: rowText(row.unit_price_minor, row.unit, units), dirty: false });
    }
  }
  return rows;
}

export function PriceBookForm({
  api,
  projectId,
  estimate,
  catalog,
  units,
  onSaved,
  onClose,
}: {
  api: Api;
  projectId: string;
  estimate: EstimatePayload;
  catalog: ConnectionCatalog | null;
  units: UnitSystem;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [stored, setStored] = useState<StoredPriceBook | null | undefined>(undefined);
  const [rows, setRows] = useState<Row[]>([]);
  const [meta, setMeta] = useState({ source: "", geography: "", as_of: new Date().toISOString().slice(0, 10) });
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [submittedKeys, setSubmittedKeys] = useState<string[]>([]);

  useEffect(() => {
    api.getPriceBook(projectId).then((book) => {
      setStored(book);
      setRows(initialRows(estimate, book, units, catalog));
      if (book) setMeta({ source: book.book.source, geography: book.book.geography, as_of: book.book.as_of });
    }, setError);
  }, [api, projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Untouched rows follow the display units; typed text is kept as typed.
  useEffect(() => {
    setRows((rs) => rs.map((r) => (r.dirty ? r : { ...r, text: rowText(r.stored, r.unit, units) })));
  }, [units]);

  const lengthLabel = units === "imperial" ? "per linear foot" : "per meter";
  const unitLabel = (unit: Unit) => (unit === "each" ? "each" : lengthLabel);
  const details = error instanceof ApiError ? error.details : [];
  // A row's errors are those at its price or its unit (PRICE_UNIT_MISMATCH, ART-002 §7.3).
  const rowFields = useMemo(
    () => Object.fromEntries(submittedKeys.flatMap((key, k) => [[key, `rows[${k}].unit_price_minor`], [`${key}\u0000unit`, `rows[${k}].unit`]])),
    [submittedKeys],
  );
  const { byField: rowErrors, other } = placeDetails(details, { ...rowFields, source: "source", geography: "geography", as_of: "as_of" } as Record<string, string>);

  async function save(event: FormEvent) {
    event.preventDefault();
    const built = buildBook(meta, rows, units);
    if (!built) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    setSubmittedKeys(built.keys);
    try {
      const loadedVersion = stored?.version ?? 0;
      const result = await api.setPriceBook(projectId, built.book);
      const latest = await api.getPriceBook(projectId);
      setStored(latest);
      setRows(initialRows(estimate, latest, units, catalog));
      setNotice(
        result.version === loadedVersion + 1
          ? `Saved as version ${result.version}.`
          : `Saved as version ${result.version}. Another change was saved after this form was opened; the current book is shown.`,
      );
      onSaved();
    } catch (e) {
      setError(e);
    } finally {
      setSaving(false);
    }
  }

  if (stored === undefined && !error) return <p>Loading price book…</p>;
  return (
    <form className="price-book" onSubmit={save} aria-labelledby="price-book-heading" data-testid="price-book-form">
      <h3 id="price-book-heading">Unit prices</h3>
      <p className="hint">
        Currency: USD. Timber prices are entered {lengthLabel} and stored in whole cents per meter; connection prices are entered and stored per piece. Leave a price
        blank to leave that item unpriced.
        {stored && ` Current book: version ${stored.version}.`}
      </p>
      {(["source", "geography"] as const).map((field) => (
        <div className="field" key={field}>
          <label htmlFor={`pb-${field}`}>{field === "source" ? "Source" : "Geography"}</label>
          <input id={`pb-${field}`} required value={meta[field]} onChange={(e) => setMeta((m) => ({ ...m, [field]: e.target.value }))} />
          {(rowErrors[field] ?? []).map((d, i) => (
            <p className="field-error" key={i}>
              {describeDetail(d)}
            </p>
          ))}
        </div>
      ))}
      <div className="field">
        <label htmlFor="pb-as-of">Prices as of</label>
        <input id="pb-as-of" type="date" required value={meta.as_of} onChange={(e) => setMeta((m) => ({ ...m, as_of: e.target.value }))} />
      </div>
      <table>
        <thead>
          <tr>
            <th scope="col">Item</th>
            <th scope="col">Price</th>
            <th scope="col">Stored</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const result = rowResult(row, units);
            const id = `pb-row-${index}`;
            return (
              <tr key={row.key} data-key={row.key}>
                <td>
                  <label htmlFor={id}>{row.label}</label>
                  {row.unused && <span className="badge"> unused: matches no line item</span>}
                </td>
                <td>
                  <input
                    id={id}
                    inputMode="decimal"
                    value={row.text}
                    aria-invalid={result.kind === "invalid"}
                    onChange={(e) => setRows((rs) => rs.map((r, i) => (i === index ? { ...r, text: e.target.value, dirty: true } : r)))}
                  />
                  <span className="unit"> {unitLabel(row.unit)}</span>
                  {result.kind === "invalid" && <p className="field-error">{result.error}</p>}
                  {[...(rowErrors[row.key] ?? []), ...(rowErrors[`${row.key}\u0000unit`] ?? [])].map((d, i) => (
                    <p className="field-error" key={i}>
                      {describeDetail(d)}
                    </p>
                  ))}
                </td>
                <td data-testid={`stored-${row.key}`}>
                  {result.kind === "price" && row.unit === "each" ? (
                    `${formatCents(result.unitPriceMinor)} each`
                  ) : result.kind === "price" ? (
                    <>
                      {formatCents(result.unitPriceMinor)}/m
                      {units === "imperial" && <span className="approx"> {approxPerFoot(result.unitPriceMinor)}</span>}
                    </>
                  ) : (
                    "Not priced"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {other.length > 0 && (
        <ul className="field-error">
          {other.map((d, i) => (
            <li key={i}>
              <code>{d.path || "(book)"}</code>: {describeDetail(d)}
            </li>
          ))}
        </ul>
      )}
      <ErrorNotice error={error} />
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      <div className="actions">
        <button type="submit" disabled={saving || rows.some((r) => rowResult(r, units).kind === "invalid")}>
          {saving ? "Saving…" : "Save prices"}
        </button>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </form>
  );
}
