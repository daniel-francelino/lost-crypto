const FUNCTIONS = new Set(["FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"]);

const isOnlyChild = (outer, inner) => {
  const body = outer.consequent;
  const single =
    body.type === "BlockStatement"
      ? body.body.length === 1 && body.body[0] === inner
      : body === inner;
  return single && !outer.alternate && !inner.alternate;
};

const mergeable = (outer, inner) =>
  isOnlyChild(outer, inner) && outer.parent.type !== "IfStatement";

const wrap = (source, node) => {
  const text = source.getText(node);
  return node.type === "LogicalExpression" && node.operator === "||" ? "(" + text + ")" : text;
};

const merge = (source, fixer, outer, inner) => {
  const test = wrap(source, outer.test) + " && " + wrap(source, inner.test);
  const innerBody = source.getText(inner.consequent);
  const open = outer.consequent.type === "BlockStatement" ? "{" : "";
  const bodyText = inner.consequent.type === "BlockStatement" ? innerBody : "{ " + innerBody + " }";
  return fixer.replaceTextRange(outer.range, "if (" + test + ") " + (open ? bodyText : bodyText));
};

/** An `if` inside another `if` (its body or its `else` block) hides the flow: use early returns or guard clauses. */
export default {
  meta: { type: "suggestion", fixable: "code", schema: [] },
  create(context) {
    return {
      IfStatement(node) {
        let child = node;
        for (let parent = node.parent; parent; child = parent, parent = parent.parent) {
          if (FUNCTIONS.has(parent.type)) return;
          if (parent.type !== "IfStatement") continue;
          const inBody = parent.consequent === child;
          const inElseBlock = parent.alternate === child && child.type !== "IfStatement";
          if (inBody || inElseBlock) {
            context.report({
              node,
              message:
                "Do not nest an if inside another: use a guard clause or extract a function.",
            });
            return;
          }
        }
      },
    };
  },
};
