const KEPT_COMMENT =
  /^\s*(?:eslint[-\s]|@ts-(?:expect-error|ignore|nocheck)|prettier-ignore|\/\s*<reference|#!)/;

const isBlank = (char) => char === " " || char === "\t";

/**
 * Code explains itself: names, types and small functions carry the meaning, not comments. Only
 * the comments that talk to a tool (eslint directives, `@ts-expect-error`) are kept.
 */
export default {
  meta: { type: "suggestion", fixable: "code", schema: [] },
  create(context) {
    const source = context.sourceCode;
    return {
      Program() {
        for (const comment of source.getAllComments()) {
          if (comment.type === "Shebang" || KEPT_COMMENT.test(comment.value)) continue;
          context.report({
            loc: comment.loc,
            message:
              "Comments are not allowed: make the code explain itself (names, types, small functions).",
            fix(fixer) {
              const text = source.text;
              let [start, end] = comment.range;
              const found = source.getNodeByRangeIndex(start);
              const container = found?.type === "JSXEmptyExpression" ? found.parent : found;
              if (container?.type === "JSXExpressionContainer") {
                [start, end] = container.range;
              }
              let from = start;
              while (from > 0 && isBlank(text[from - 1])) from--;
              let to = end;
              while (to < text.length && isBlank(text[to])) to++;
              const startsLine = from === 0 || text[from - 1] === "\n";
              const endsLine = to >= text.length || text[to] === "\n" || text[to] === "\r";
              if (startsLine && endsLine) {
                if (text[to] === "\r") to++;
                if (text[to] === "\n") to++;
                return fixer.removeRange([from, to]);
              }
              return fixer.removeRange([from, end]);
            },
          });
        }
      },
    };
  },
};
