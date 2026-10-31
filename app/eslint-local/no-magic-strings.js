const CONSTANTS_FILE = "src/lib/shared/enums.ts";
const STORED_KEYS_FILE = "src/lib/shared/stored-keys.ts";

const STATUS_WORDS = new Set([
  "running",
  "stopped",
  "paused",
  "paper",
  "testnet",
  "live",
  "admin",
  "viewer",
  "queued",
  "completed",
  "failed",
]);

const STORAGE = new Set(["localStorage", "sessionStorage"]);
const COMPARISONS = new Set(["===", "!==", "==", "!="]);

export default {
  meta: { type: "suggestion", schema: [] },
  create(context) {
    const file = context.filename.split("\\").join("/");
    const isConstants = file.endsWith(CONSTANTS_FILE);
    const isStored = file.endsWith(STORED_KEYS_FILE);
    return {
      Literal(node) {
        if (typeof node.value !== "string") return;
        const parent = node.parent;
        if (
          !isConstants &&
          parent.type === "BinaryExpression" &&
          COMPARISONS.has(parent.operator) &&
          STATUS_WORDS.has(node.value)
        ) {
          context.report({
            node,
            message:
              "Compare with the constant (BotState, ExecutionMode, Role, JobStatus…), not with text. Roles go through can().",
          });
        }
        if (
          parent.type === "ArrayExpression" &&
          parent.elements[0] === node &&
          parent.parent.type === "Property" &&
          parent.parent.key.name === "queryKey"
        ) {
          context.report({
            node,
            message: "Use QueryKey (lib/shared/api/query-keys) as the first element of a queryKey.",
          });
        }
      },
      Identifier(node) {
        if (isStored || !STORAGE.has(node.name)) return;
        context.report({
          node,
          message:
            "Use readStored/writeStored (lib/shared/stored-keys), never the browser storage directly. Tokens are never stored (docs/05-authentication.md).",
        });
      },
    };
  },
};
