/** `{}` in JSX renders nothing: remove it. */
export default {
  meta: { type: "suggestion", fixable: "code", schema: [] },
  create(context) {
    return {
      JSXExpressionContainer(node) {
        if (node.expression.type !== "JSXEmptyExpression") return;
        if (context.sourceCode.getCommentsInside(node).length > 0) return;
        context.report({
          node,
          message: "Empty JSX expression: remove it.",
          fix: (fixer) => fixer.remove(node),
        });
      },
    };
  },
};
