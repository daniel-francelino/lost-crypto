# Lost Crypto app — instructions for Claude Code

The operator console of Lost Crypto: a client-rendered TanStack Start app that talks only to the FastAPI backend in `../api`. The rules are in `docs/`; read them as binding.

@AGENTS.md

## How to work here

1. **Start with the documents.** `docs/README.md` is the map; `docs/06-screens.md` says what each screen does, `docs/09-roadmap.md` says what is next.
2. **lost-ui first.** Before writing a component use the skill in `.claude/skills/lost-ui` (catalog, recipes, props in `references/api/`). Import by path: `lost-ui/templates/auth/login-page`, `lost-ui/ui/sonner`, `lost-ui/app/app`. Ask for what is missing in `docs/lost-ui-requests.md` instead of rebuilding it.
3. **Names come from the contract.** Routes, enums, query keys and API shapes come from `docs/` or `../api/docs/openapi.json`. `npm run check:consistency` compares `src/lib/shared/enums.ts` with the OpenAPI enums; `npm run api:types` regenerates the types.
4. **Money is a string.** No `Number()`, `parseFloat`, unary `+` or arithmetic on it; only `lib/shared/format.ts` and chart helpers convert (lint-enforced).
5. **Modules do not import each other**; shared code goes to `shared` (lint-enforced). Routes only assemble screens.
6. **Never** read or print `.env*`, store a token anywhere script can read it, use the backend's `API_TOKEN`, or add a live-trading shortcut (`docs/07-ux-rules.md`).
7. **Prove it:** run `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` and say exactly what was and was not run. Layout is checked in a real browser (and at 360 px), not only in jsdom.
8. **Language:** code, files, routes and documents in English; UI copy in Brazilian Portuguese. Talk to the user in the language they use.
9. Docs change with the code (same change). A "To verify" item you resolve is rewritten as a fact.
