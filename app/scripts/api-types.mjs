import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const input = resolve("../api/docs/openapi.json");
const output = resolve("src/lib/shared/api/api.d.ts");
const bin = resolve("node_modules/openapi-typescript/bin/cli.js");

execFileSync(process.execPath, [bin, input, "-o", output], { stdio: "inherit" });
