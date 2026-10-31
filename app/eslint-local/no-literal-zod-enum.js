/** `z.enum(["a", "b"])` repeats a list that should be a constant: use `z.nativeEnum(Constant)`. */
export default {
  meta: { type: "suggestion", schema: [] },
  create(context) {
    return {
      CallExpression(node) {
        const callee = node.callee;
        if (
          callee.type !== "MemberExpression" ||
          callee.object.name !== "z" ||
          callee.property.name !== "enum"
        ) {
          return;
        }
        const list = node.arguments[0];
        if (
          list?.type === "ArrayExpression" &&
          list.elements.some((item) => item?.type === "Literal")
        ) {
          context.report({
            node,
            message: "Use z.nativeEnum(Constant) instead of a list of texts.",
          });
        }
      },
    };
  },
};
