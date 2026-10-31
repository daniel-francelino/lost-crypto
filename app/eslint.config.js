import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

import importsTogether from "./eslint-local/imports-together.js";
import noLiteralZodEnum from "./eslint-local/no-literal-zod-enum.js";
import noMagicStrings from "./eslint-local/no-magic-strings.js";
import noEmptyJsx from "./eslint-local/no-empty-jsx.js";
import noNestedIf from "./eslint-local/no-nested-if.js";
import noComments from "./eslint-local/no-comments.js";

const serverOnly = {
  name: "server-only",
  message:
    "The app is client-rendered and has no server code (docs/01-stack.md). Do not use server-only modules.",
};

const colourSelectors = [
  ["Literal", "value"],
  ["TemplateElement", "value.raw"],
].flatMap(([node, prop]) => [
  {
    selector: `${node}[${prop}=/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]`,
    message: "Use a colour token from styles.css instead of a hex value.",
  },
  {
    selector: String.raw`${node}[${prop}=/-\[#[0-9a-fA-F]{3,8}\]/]`,
    message: "Use a colour token from styles.css instead of an arbitrary hex value.",
  },
  {
    selector: String.raw`${node}[${prop}=/\b(?:bg|text|border|ring|fill|stroke|from|to|via|outline|divide|decoration)-(?:white|black|(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-[0-9]{2,3})\b/]`,
    message:
      "Use a semantic token (bg-primary, text-muted-foreground, bg-success/10…), not pure black/white or the default Tailwind palette.",
  },
]);

const asUnknownAs = {
  selector: 'TSAsExpression > TSAsExpression.expression[typeAnnotation.type="TSUnknownKeyword"]',
  message:
    "Do not cast through `unknown`: type the source or validate the value with zod at the API boundary.",
};

const dateMessage =
  "Use lib/shared/dates (and format for display) instead of the Date API, so dates are handled in one place.";

const rawDate = [
  { selector: "NewExpression[callee.name='Date']", message: dateMessage },
  { selector: "MemberExpression[object.name='Date']", message: dateMessage },
  {
    selector:
      "CallExpression[callee.property.name=/^(toISOString|getTime|toLocaleString|toLocaleDateString|toLocaleTimeString|getTimezoneOffset|setDate|setHours|setMinutes|setMonth|setFullYear|getFullYear|getMonth|getDate|getDay|getHours|getMinutes|getUTCDay|getUTCDate|getUTCHours|getUTCFullYear|getUTCMonth|setUTCDate|setUTCHours)$/]",
    message: dateMessage,
  },
  {
    selector: "MemberExpression[object.name='Intl'][property.name='DateTimeFormat']",
    message: dateMessage,
  },
];

const moneyMessage =
  "Money and quantities are decimal strings (docs/04-api-client.md): no numeric conversion or arithmetic outside lib/shared/format.ts and the chart helpers.";

const rawNumber = [
  { selector: "CallExpression[callee.name='Number']", message: moneyMessage },
  { selector: "CallExpression[callee.name='parseFloat']", message: moneyMessage },
  {
    selector: "CallExpression[callee.object.name='Number'][callee.property.name='parseFloat']",
    message: moneyMessage,
  },
  { selector: "UnaryExpression[operator='+']", message: moneyMessage },
];

const KINDS = ["components", "lib", "hooks"];

const MODULES = [
  "auth",
  "bots",
  "backtests",
  "market-data",
  "strategies",
  "exchanges",
  "system",
  "audit",
];

const boundary = (name, forbidden) => ({
  files: KINDS.map((kind) => `src/${kind}/${name}/**/*.{ts,tsx}`),
  rules: {
    "no-restricted-imports": [
      "error",
      {
        paths: [serverOnly],
        patterns: [
          {
            group: forbidden.flatMap((other) => KINDS.map((kind) => `@/${kind}/${other}/**`)),
            message: `\`${name}\` cannot import from another module: move what is shared into \`shared\` (docs/02-project-structure.md).`,
          },
        ],
      },
    ],
  },
});

const moneyConversion = ["src/lib/shared/format.ts", "src/**/*chart-rows.ts"];

const colourExempt = [];

export default tseslint.config(
  {
    ignores: [
      "dist",
      ".output",
      ".vinxi",
      ".tanstack",
      "src/routeTree.gen.ts",
      "src/lib/shared/api/api.d.ts",
    ],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-hooks/exhaustive-deps": "error",
      "no-restricted-imports": ["error", { paths: [serverOnly] }],
      "react-refresh/only-export-components": ["error", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
      "@typescript-eslint/no-import-type-side-effects": "error",
      "@typescript-eslint/no-useless-empty-export": "error",
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-console": "error",
      "no-empty": "error",
      "@typescript-eslint/no-empty-function": "error",
      "no-var": "error",
      "prefer-const": "error",
      "object-shorthand": ["error", "always"],
      "no-duplicate-imports": ["error", { allowSeparateTypeImports: true }],
      "no-else-return": ["error", { allowElseIf: false }],
      "no-throw-literal": "error",
      "no-self-compare": "error",
      "no-template-curly-in-string": "warn",
      "no-useless-concat": "error",
      "no-useless-return": "error",
      "prefer-object-spread": "error",
      "array-callback-return": "error",
      "default-case-last": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/consistent-type-imports": ["error", { fixStyle: "inline-type-imports" }],
    },
  },
  {
    files: ["src/**/*.tsx"],
    ignores: colourExempt,
    rules: {
      "no-restricted-syntax": ["error", ...colourSelectors, asUnknownAs, ...rawDate, ...rawNumber],
    },
  },
  {
    files: ["src/**/*.ts"],
    ignores: ["src/routeTree.gen.ts", ...moneyConversion],
    rules: { "no-restricted-syntax": ["error", asUnknownAs, ...rawDate, ...rawNumber] },
  },
  {
    files: moneyConversion,
    rules: { "no-restricted-syntax": ["error", asUnknownAs, ...rawDate] },
  },
  {
    files: ["src/lib/shared/dates.ts"],
    rules: { "no-restricted-syntax": ["error", asUnknownAs, ...rawNumber] },
  },
  {
    files: ["src/**/*.test.{ts,tsx}"],
    rules: { "no-restricted-syntax": ["error", asUnknownAs] },
  },
  {
    files: ["src/components/**/*.tsx", "src/routes/**/*.tsx"],
    rules: { "max-lines": ["warn", { max: 600, skipBlankLines: true, skipComments: true }] },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: {
      local: {
        rules: {
          "no-comments": noComments,
          "imports-together": importsTogether,
          "no-nested-if": noNestedIf,
          "no-empty-jsx": noEmptyJsx,
          "no-magic-strings": noMagicStrings,
          "no-literal-zod-enum": noLiteralZodEnum,
        },
      },
    },
    rules: {
      "local/no-comments": "error",
      "local/imports-together": "error",
      "local/no-nested-if": "error",
      "local/no-empty-jsx": "error",
      "local/no-magic-strings": "error",
      "local/no-literal-zod-enum": "error",
    },
  },
  ...MODULES.map((name) =>
    boundary(
      name,
      MODULES.filter((other) => other !== name),
    ),
  ),
  boundary("shared", MODULES),
  eslintPluginPrettier,
);
