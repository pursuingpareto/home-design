// Generate the committed client contracts from the backend's exports (D028; UI-001 §11, item 2; D062):
// - src/api/schema.d.ts from docs/architecture/schemas/openapi.v1.json;
// - src/api/connectionCatalog.ts from docs/architecture/schemas/connection-catalog.json (UI-003 §10).
// Usage: node scripts/generate-api.mjs [--check]
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const schemas = new URL("../../docs/architecture/schemas/", import.meta.url);

async function schemaTypes() {
  const source = new URL("openapi.v1.json", schemas);
  const header =
    "// Generated from docs/architecture/schemas/openapi.v1.json by scripts/generate-api.mjs. Do not edit by hand.\n\n";
  return header + astToString(await openapiTS(JSON.parse(readFileSync(source, "utf8"))));
}

function connectionCatalog() {
  const catalog = JSON.parse(readFileSync(new URL("connection-catalog.json", schemas), "utf8"));
  const { description: _description, ...data } = catalog;
  return [
    "// Generated from docs/architecture/schemas/connection-catalog.json by scripts/generate-api.mjs. Do not edit by hand.",
    "// The D054 connection catalog, exported from backend/src/homedesign/model/connections.py (D062, UI-003 §10).",
    "// It only limits what the editor offers; the server validates every command (D028).",
    "",
    'import type { components } from "./schema";',
    "",
    'type JunctionClass = components["schemas"]["ConnectionTypeArgs"]["junction_class"];',
    'type ConnectionType = components["schemas"]["ConnectionTypeArgs"]["connection_type"];',
    "",
    "export interface ConnectionCatalogExport {",
    "  catalog_version: string;",
    "  junction_classes: readonly { junction_class: JunctionClass; default: ConnectionType; alternative: ConnectionType }[];",
    '  connection_types: readonly { connection_type: ConnectionType; family: "traditional" | "engineered"; description: string }[];',
    "}",
    "",
    `export const CONNECTION_CATALOG: ConnectionCatalogExport = ${JSON.stringify(data, null, 2)};`,
    "",
  ].join("\n");
}

const outputs = [
  [fileURLToPath(new URL("../src/api/schema.d.ts", import.meta.url)), await schemaTypes()],
  [fileURLToPath(new URL("../src/api/connectionCatalog.ts", import.meta.url)), connectionCatalog()],
];

if (process.argv.includes("--check")) {
  let stale = false;
  for (const [target, text] of outputs) {
    const current = existsSync(target) ? readFileSync(target, "utf8") : "";
    if (current !== text) {
      console.error(`${target} is out of date; run \`npm run generate:api\` and commit the result.`);
      stale = true;
    }
  }
  if (stale) process.exit(1);
} else {
  for (const [target, text] of outputs) {
    writeFileSync(target, text);
    console.log(`Wrote ${target}`);
  }
}
