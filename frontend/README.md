# MindForge Risk Assessor — front end

Vite + React 18 + TypeScript + Tailwind v4, with hand-written shadcn-style components
over Radix primitives.

```bash
npm run dev            # dev server on :5173, proxies /api to the backend on :8000
npm run build          # type-check, then build to dist/
npm run lint           # ESLint (flat config, typescript-eslint + react-hooks)
npm run format         # Prettier, write
npm run format:check   # Prettier, verify only
```

From the repository root, `make dev` runs this and the backend together, and
`make lint-web` runs the lint and format checks.

## Notes

- **Tailwind v4, CSS-first.** Design tokens live in `@theme` in `src/index.css`; there
  is no `tailwind.config.js`. Dark mode is a `.dark` class that redefines the same
  tokens, so no component knows which theme is active.
- **Recharts is loaded lazily** (`DimensionRadarLazy`). It is ~285 kB of the build and
  nothing renders it until an assessment returns, so it stays off the critical path.
- **`src/lib/api.ts` mirrors the backend's pydantic models in zod.** A schema change on
  either side surfaces as a parse failure rather than as `undefined` at render time.
- **Streaming uses `fetch` + `ReadableStream`, not `EventSource`**, because the
  assessment request is a POST with a JSON body.
