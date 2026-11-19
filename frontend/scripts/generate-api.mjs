// Generate src/api/schema.d.ts from the committed OpenAPI document (D028; UI-001 §11, item 2).
// Usage: node scripts/generate-api.mjs [--check]
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const source = new URL("../../docs/architecture/schemas/openapi.v1.json", import.meta.url);
const target = fileURLToPath(new URL("../src/api/schema.d.ts", import.meta.url));
const header =
  "// Generated from docs/architecture/schemas/openapi.v1.json by scripts/generate-api.mjs. Do not edit by hand.\n\n";
const text = header + astToString(await openapiTS(JSON.parse(readFileSync(source, "utf8"))));

if (process.argv.includes("--check")) {
  const current = existsSync(target) ? readFileSync(target, "utf8") : "";
  if (current !== text) {
    console.error(`${target} is out of date; run \`npm run generate:api\` and commit the result.`);
    process.exit(1);
  }
} else {
  writeFileSync(target, text);
  console.log(`Wrote ${target}`);
}
