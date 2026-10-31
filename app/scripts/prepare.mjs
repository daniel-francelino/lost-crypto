import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve("..");
const husky = resolve("node_modules/husky/bin.js");

if (!existsSync(resolve(root, ".git")) || !existsSync(husky)) process.exit(0);

execFileSync(process.execPath, [husky, "app/.husky"], { cwd: root, stdio: "inherit" });
