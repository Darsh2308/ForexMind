# ForexMind AI — Frontend

The React + TypeScript + Vite client for ForexMind AI. See [`Development.md`](./Development.md)
for the full phase-by-phase plan; see the root [`../Development.md`](../Development.md) and
[`../context.md`](../context.md) for the backend and product spec this UI is built against.

## Getting started

```bash
npm install
cp .env.example .env.local   # point VITE_API_BASE_URL at your running backend
npm run dev
```

The backend (`../README.md`) must be running separately — this app has no server of its own,
it only calls the FastAPI API.

## Scripts

| Command                | Does                                           |
| ---------------------- | ---------------------------------------------- |
| `npm run dev`          | Start the Vite dev server                      |
| `npm run build`        | Type-check (`tsc -b`) and build for production |
| `npm run preview`      | Preview the production build locally           |
| `npm run lint`         | ESLint                                         |
| `npm run typecheck`    | TypeScript only, no build                      |
| `npm run format`       | Prettier, writes                               |
| `npm run format:check` | Prettier, check only (CI-safe)                 |

## Stack

React 18 · TypeScript (strict) · Vite · Tailwind CSS · TanStack Query · React Router ·
lightweight-charts — see `Development.md` §0 for why each was chosen.

## Deployment

1. `npm run build` — static output in `dist/`, no server of its own required. Serve it from
   any static host (Vercel/Netlify free tier, `vite preview`, nginx, etc.).
2. Point it at the backend with `VITE_API_BASE_URL` baked in at build time (Vite inlines
   `import.meta.env.*` into the bundle, so set it before running `npm run build`, not after).
3. On the backend, set `CORS_ORIGINS` to the exact origin the frontend is served from
   (e.g. `CORS_ORIGINS=https://forexmind.example.com`) — this **replaces**, not adds to, the
   `localhost:5173`/`localhost:4173` dev-time default in `forexmind/api/app.py`, so the deployed
   backend only accepts requests from the real deployed frontend.

Verified locally by building for real, serving the build with `vite preview` on a different
port than the dev server, and confirming the backend accepts that origin while rejecting the
old dev origin once `CORS_ORIGINS` is scoped down to just the "deployed" one.
