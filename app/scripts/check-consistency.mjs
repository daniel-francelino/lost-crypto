import { existsSync, readFileSync } from "node:fs";

const OPENAPI = "../api/docs/openapi.json";
const ENUMS = "src/lib/shared/enums.ts";

if (!existsSync(OPENAPI) || !existsSync(ENUMS)) {
  console.log("check:consistency: openapi.json or enums.ts not found, nothing to compare.");
  process.exit(0);
}

const schemas = JSON.parse(readFileSync(OPENAPI, "utf8")).components.schemas;
const source = readFileSync(ENUMS, "utf8");

const constants = new Map();
for (const match of source.matchAll(/export const (\w+) = \{([^}]*)\} as const;/g)) {
  const values = [...match[2].matchAll(/:\s*"([^"]+)"/g)].map((item) => item[1]);
  constants.set(match[1], new Set(values));
}

const problems = [];
for (const [name, values] of constants) {
  const schema = schemas[name];
  if (!schema || !schema.enum) continue;
  const api = new Set(schema.enum);
  const missing = [...api].filter((value) => !values.has(value)).sort();
  const extra = [...values].filter((value) => !api.has(value)).sort();
  if (missing.length > 0)
    problems.push(`${name}: values in the API but not in enums.ts: ${missing}`);
  if (extra.length > 0)
    problems.push(`${name}: values in enums.ts that the API does not have: ${extra}`);
}

if (problems.length > 0) {
  console.error(`check:consistency failed:\n- ${problems.join("\n- ")}`);
  process.exit(1);
}
console.log(`check:consistency: ${constants.size} constants match ${OPENAPI}.`);
