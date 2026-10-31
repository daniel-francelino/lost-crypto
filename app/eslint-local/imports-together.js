const CRLF = String.fromCharCode(13, 10);
const LF = String.fromCharCode(10);

/** The imports of a file are one block: no blank line inside it, one blank line after it. */
export default {
  meta: { type: "layout", fixable: "whitespace", schema: [] },
  create(context) {
    const source = context.sourceCode;
    return {
      Program(program) {
        const imports = program.body.filter((node) => node.type === "ImportDeclaration");
        for (let index = 1; index < imports.length; index++) {
          const previous = imports[index - 1];
          const current = imports[index];
          if (current.loc.start.line - previous.loc.end.line < 2) continue;
          const gap = source.text.slice(previous.range[1], current.range[0]);
          if (gap.trim() !== "") continue;
          const lineBreak = gap.includes(CRLF) ? CRLF : LF;
          context.report({
            node: current,
            message: "No blank line between imports.",
            fix: (fixer) =>
              fixer.replaceTextRange([previous.range[1], current.range[0]], lineBreak),
          });
        }
        const last = imports.at(-1);
        const next = last && program.body[program.body.indexOf(last) + 1];
        if (last && next && next.loc.start.line - last.loc.end.line < 2) {
          const lineBreak = source.text.includes(CRLF) ? CRLF : LF;
          context.report({
            node: next,
            message: "Leave one blank line after the imports.",
            fix: (fixer) => fixer.insertTextAfterRange([last.range[1], last.range[1]], lineBreak),
          });
        }
      },
    };
  },
};
