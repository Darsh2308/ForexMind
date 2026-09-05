# ForexMind AI — Frontend Development Plan

> Companion to the root `Development.md` (backend) and `context.md` (spec). This plan covers the React + TypeScript + Vite client only — it does not repeat backend work, and calls out explicitly wherever a frontend phase needs a backend change that doesn't exist yet.

---

## 0. Locked Decisions

| Question        | Decision                                                                                                                                                                |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework       | **React 18 + TypeScript + Vite.** No Next.js/SSR — the backend is a local FastAPI JSON API, data is fetched client-side, there's nothing for a server render to buy us. |
| Styling         | **Tailwind CSS.** Utility-first, no component-library weight, easiest way to keep the UI "clean" without inventing a design system from scratch.                        |
| Server state    | **TanStack Query.** `/api/analyze` takes 15–30s per the CLI's own message to users — this needs real loading/error/retry handling, not ad-hoc `useState` + `fetch`.     |
| Routing         | **React Router**, 4 routes: Analyze (home), History, Recommendation Detail, (later) Status.                                                                             |
| Charting        | **lightweight-charts** (TradingView's open-source, free, no paid tier) — the one library choice that matters here, since this is a forex candlestick app.               |
| Package manager | **npm.** No extra tooling to justify pnpm/yarn for a single-app frontend.                                                                                               |
| Auth            | **None for V1** — matches the backend, which has no auth layer either. Single-user local tool.                                                                          |

### Defaults for the still-open questions

| Question          | Default applied                                                                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API base URL      | `VITE_API_BASE_URL`, defaulting to `http://localhost:8000` in `.env.example`                                                                                       |
| Deployment target | Static `vite build` output, served locally or on any free static host (Vercel/Netlify free tier) — free-tier-first, matching the backend's own Phase 17 philosophy |
| Symbol input      | **No search box.** The backend is EUR/USD-only by design (§0 of the root plan) — the primary action is "Analyze now," not "search a pair."                         |

### Tech stack (Phase 0 output, previewed here for context)

- **Framework:** React 18, TypeScript 5 (strict mode), Vite 5
- **Styling:** Tailwind CSS
- **Server state / data fetching:** TanStack Query
- **Routing:** React Router v6
- **Charts:** lightweight-charts
- **Validation:** hand-written TS types mirroring the backend's Pydantic schemas exactly (no OpenAPI codegen step in V1 — the API surface is small enough to track by hand, revisit if it grows)

---

## Backend prerequisites this plan depends on

These don't exist in the backend today. Each is called out again at the phase that needs it, but listed together here so they're visible up front:

1. **No CORS middleware.** `forexmind/api/app.py` has no `CORSMiddleware`. A browser-based frontend on a different origin (e.g. `localhost:5173` calling `localhost:8000`) will be blocked until this is added.
2. **No recommendation-detail endpoint.** The full blackboard (`MarketContext` — every agent's structured output) is persisted per recommendation in `agent_snapshots.payload`, but nothing exposes it over HTTP. `GET /api/history` only returns the six summary fields in `RecommendationHistoryItem`. Phase 4 below needs a new `GET /api/recommendation/{id}` returning the stored `MarketContext` JSON.
3. **No candles endpoint.** OHLC data lives only in SQLite and is read internally by the Market Data Agent. Phase 5 (price chart) needs a way to fetch candles for a timeframe — either a new `GET /api/candles` endpoint or accept that the chart ships later than the rest of the UI.

None of these block Phases 0–3. They block Phases 4–5 specifically, and are flagged there again.

---

## What "displaying everything" means here

The backend's blackboard (`forexmind/orchestration/market_context.py`) has 12 populatable sections per recommendation: `market_data`, `technical_analysis`, `price_action`, `candlestick`, `support_resistance`, `smc`, `elliott_wave`, `wyckoff`, `news`, `historical_similarity`, `risk_analysis`, and `reasoning_output`, plus an explicit `conflicts` list. "Everything" means every one of those sections gets a visible place in the UI, not just the final BUY/SELL/WAIT — the whole point of the backend's blackboard architecture (§7/§8 of the spec) is that the recommendation is traceable to evidence, and the frontend's job is to not hide that trail behind a single verdict card.

---

## Phase 0 — Project Scaffolding & Design System [DONE]

**Goal:** A branded, empty shell — nothing wired to the API yet.

- `npm create vite@latest . -- --template react-ts` inside `frontend/`
- ESLint + Prettier, TypeScript strict mode on
- Tailwind CSS installed and configured; base design tokens defined (color palette incl. semantic BUY/SELL/WAIT + WIN/LOSS/EXPIRED colors, type scale, spacing scale) — one small `tokens.css` or `tailwind.config.ts` theme block, not scattered inline values
- Folder structure: `src/api/`, `src/components/`, `src/pages/`, `src/hooks/`, `src/types/`
- `.env.example` with `VITE_API_BASE_URL=http://localhost:8000`
- Router shell with placeholder routes: `/` (Analyze), `/history`, `/history/:id`

**Exit criteria:** `npm run dev` serves a branded but empty shell with working navigation; `npm run build` produces a clean production bundle with zero TypeScript errors.

---

## Phase 1 — API Client & Type Contracts [DONE]

**Goal:** A typed, reliable bridge to the FastAPI backend.

- TypeScript interfaces mirroring `forexmind/api/schemas.py` and `forexmind/agents/reasoning/schemas.py` exactly: `AnalyzeResponse`, `ReasoningSnapshot` (including `llm_provider: "groq" | "ollama" | "fallback" | null`), `RecommendationHistoryItem`, `HistoryResponse`, and the `/health` response shape (`{ status, alerts_last_24h }` or `{ status: "degraded", detail }`)
- A small typed fetch wrapper reading `VITE_API_BASE_URL`, with consistent error handling (network failure vs. non-2xx vs. malformed body treated distinctly — the Analyze view needs to tell those apart)
- TanStack Query hooks: `useAnalyze()` (mutation, `POST /api/analyze`), `useHistory()` (query, `GET /api/history`), `useHealth()` (query, `GET /health`, polling interval e.g. 60s)
- **Backend prerequisite:** this phase is where the missing CORS middleware first becomes a blocker — nothing here can be verified against a real running backend until it's added.

**Exit criteria:** all three hooks proven against the real backend (once CORS is fixed) or against mocked responses (e.g. MSW) with correct loading/error/success states.

> **Verification note (2026-09-03):** Built `src/types/api.ts`, `src/api/client.ts` (the `ApiError` class distinguishes `network`/`http`/`parse` failures), `src/api/endpoints.ts`, and all three hooks, then wired them into real (if minimal) consumers — `AnalyzePage`, `HistoryPage`, and a `HealthDot` in the footer — rather than leaving them unused. Verified against the **real** running backend, not mocks: added `CORSMiddleware` to `forexmind/api/app.py` (permissive dev-time origins `localhost:5173`/`127.0.0.1:5173`, tightened in Phase 8; 2 new backend tests), then ran both servers for real and drove an actual `POST /api/analyze` through curl with the exact headers the browser client sends — preflight OPTIONS, then the real call — against live Twelve Data.
>
> That live run surfaced and fixed three real backend bugs that no amount of mocking would have caught, since they only trigger under real concurrency/data/config, none of it hypothetical for a live deployment:
>
> - **`graph.py`'s `fetch_market_data` hardcoded a fake Twelve Data key** (already flagged in the root Development Report as an open item) — now reads the real key via `load_config()`. Also fixed `TwelveDataClient._get()` leaking raw `requests.HTTPError` instead of the `TwelveDataError` callers actually catch.
> - **A real SQLite cross-thread crash**: LangGraph's parallel fan-out runs the 8 analysis agents across a thread pool sharing one connection, which `sqlite3.connect()`'s default `check_same_thread=True` forbids. Fixed in `storage/db.py::get_connection`.
> - **`GROQ_API_KEY=`/`FINNHUB_API_KEY=`` blank `.env` entries broke their intended "unset → fallback" default** (`os.getenv(VAR, default)`only falls back when`VAR`is fully absent, not blank) — fixed in`reasoning_agent.py`, `finnhub_client.py`, and the same latent bug in `app.py`'s `CORS_ORIGINS` parsing.
> - Also fixed a `learning_agent.py` bug (`active_sessions[0].name` on a plain `list[str]`) hit by the same live call.
>
> The real response came back `200` with `llm_provider: "fallback"` (Groq correctly 401'd on the placeholder key, a local Ollama server was found but didn't have `llama3.3` pulled, so it fell through to WAIT) — an exact byte-for-byte match to the `AnalyzeResponse`/`ReasoningSnapshot` TypeScript types. A separate live-discovered `price_action` agent bug (`tuple index out of range`) was caught and gracefully degraded by Phase 17's alerting exactly as designed — logged as a known issue, not fixed here (Phase 3 backend scope, not Phase 1 frontend). Backend suite: 203 passing.

---

## Phase 2 — The Analyze View ("Ask ForexMind") [DONE]

**Goal:** The actual "Should I Buy EUR/USD?" experience — this is the app's reason to exist.

- One primary action: "Analyze EUR/USD now" (not a search box — the backend is single-pair)
- An honest loading state for the 15–30s wait: a step list (Market Data → 8 parallel agents → Cross-Validate → Historical/Risk/Learning → Reasoning) rather than a bare spinner, so the wait reads as "working," not "stuck"
- Result view once the call resolves:
  - Recommendation badge (BUY/SELL/WAIT), color-coded per the semantic palette from Phase 0
  - Confidence meter, entry/stop-loss/take-profit, reward:risk, trade quality score (1–10)
  - Reasoning text, supporting evidence list, conflicting evidence list, important news
  - `llm_provider` badge — surfacing whether Groq, the local Ollama fallback, or the hard-coded WAIT fallback produced this call matters for trust, not just debugging
  - The `conflicts` list rendered prominently and un-collapsed by default — per the spec's Phase 8 principle that contradictions must stay visible, not get silently dropped
- Error state: if the backend returns a 500 (`"Reasoning Agent failed to produce an output"`) or is unreachable, say so plainly — no silent retry loop

**Exit criteria:** a real backend call renders every field of `ReasoningSnapshot` correctly, and a forced backend failure renders a clear, non-alarming error state.

> **Verification note (2026-09-03):** Built `useSimulatedProgress` (a client-side estimate timed to the graph's real stages, since the backend is one synchronous call with no real progress to report — it holds at the last step rather than falsely claiming completion if a run runs long) plus `AnalyzeProgress`, `ConfidenceMeter`, `QualityScore`, `EvidenceList`, `LlmProviderBadge`, `PriceLevels`, and `RecommendationResult`, composed into `AnalyzePage`.
>
> No headless browser was available in this environment, so Playwright + Chromium were installed as a dev dependency specifically to get real screenshots rather than trusting `tsc`/`eslint` alone — `frontend/scripts/visual-check.mjs` drives the real dev server against the real (or a deliberately-stopped) backend and saves screenshots + console errors. Both exit criteria were confirmed visually, not just asserted:
>
> - A real `POST /api/analyze` (Groq 401 on the placeholder key → Ollama 404, model not pulled → WAIT) rendered every `ReasoningSnapshot` field correctly: WAIT badge, 0% confidence, 1/10 quality, the fallback `llm_provider` badge, the real error text in Reasoning, and the conflicting-evidence list — with zero browser console errors.
> - Stopping the backend and re-running the flow produced the plain "Could not reach ForexMind AI at http://localhost:8000. Is the backend running?" message, no auto-retry.
>
> One script bug surfaced along the way, not an app bug: the first verification pass waited for text `"Reasoning"` to appear, which matched step 5's ever-present label ("Reasoning Agent synthesizing the call") even while still loading, so the first screenshot round captured the loading state twice. Fixed by waiting for the button relabeling to "Analyze again" instead, which only happens once the mutation actually settles.

---

## Phase 3 — Recommendation History View [DONE]

**Goal:** `GET /api/history` made legible.

- Table/list: timestamp, recommendation (BUY/SELL/WAIT badge), entry/SL/TP, status (PENDING/WIN/LOSS/EXPIRED badge, color-coded — reuse the semantic tokens from Phase 0)
- Client-side sort (newest first by default) and filter (by recommendation type, by status)
- Empty state for a fresh install with zero recommendations (this is the actual current state of the backend's live database, so this isn't a hypothetical edge case)
- Each row links to `/history/:id` (Phase 4)

**Exit criteria:** history view matches the database exactly for a seeded set of recommendations across all four statuses.

> **Verification note (2026-09-03):** Built `HistoryFilters` (sort newest/oldest, filter by recommendation, filter by status) and wired it into `HistoryPage` with a `useMemo`-derived row list, plus a distinct "no recommendations match these filters" state separate from the "no recommendations yet" empty state.
>
> The real database had zero recommendations (WAIT calls aren't persisted, and no BUY/SELL has landed yet), so a new dev-only `scripts/seed_demo_recommendations.py` seeds five realistic rows spanning all four statuses and both directions directly into the same `forexmind.db` the API serves — explicitly not part of the production pipeline, documented as such in its docstring. Verified with real screenshots via `frontend/scripts/visual-check-history.mjs` against the live API: all five rows render correctly newest-first, the status filter narrows to exactly the matching row (tested with WIN), the sort toggle correctly reverses to oldest-first, and a filter combination with zero matches (WAIT, which the real pipeline never saves) renders the distinct empty state — zero console errors throughout. No backend changes were needed for this phase, as predicted.

---

## Phase 4 — Recommendation Detail / Evidence Drill-Down [DONE]

**Goal:** The "everything" view — the full blackboard for one past call.

- **Backend prerequisite (blocking):** requires a new `GET /api/recommendation/{id}` endpoint that reads the `agent_snapshots` row for that recommendation and returns the stored `MarketContext` JSON. Do not start this phase until that endpoint exists — there is nothing to fetch otherwise.
- One expandable/collapsible panel per populated `MarketContext` section: Technical Analysis, Price Action, Candlestick, Support/Resistance, SMC/ICT, Elliott Wave, Wyckoff, News, Historical Similarity, Risk Analysis, and the final Reasoning output — each rendering that agent's actual structured fields, not a JSON dump
- Elliott Wave and Wyckoff panels visually marked as advisory-weight (per the spec, these never block a call on their own) rather than presented with the same authority as SMC/Risk
- The `conflicts` list repeated here too, next to the sections that produced them

**Exit criteria:** opening any history row shows every section that was populated for that specific historical call, correctly attributed to its agent.

> **Verification note (2026-09-03):** Added `GET /api/recommendation/{id}` (`RecommendationDetailResponse`, new `fetch_recommendation_by_id`/`fetch_market_context_payload` in `storage/db.py`, 3 new backend tests — 404 for a missing id, 404 for a recommendation with no stored context, 200 with the full payload).
>
> "Each agent's actual structured fields, not a JSON dump" for 11 different, deeply nested agent schemas would be its own multi-week project to hand-build — instead, `StructuredValue` recursively renders any section generically (humanized labels, nested groups, arrays of objects as cards), which is a disclosed scope trade-off, not a JSON dump: real field names, real structure, real nesting, just not bespoke per-agent layouts.
>
> No BUY/SELL had ever been saved (WAIT isn't persisted), so `scripts/seed_demo_recommendation_with_context.py` runs the _real_ 11 deterministic/rule-based agents against real historical candles (copying them from `var/forexmind.db` into `forexmind.db` rather than re-fetching) and only fabricates the final verdict — and even that follows the real Reasoning Agent's own rule (Risk Analysis's actual computed setup, or WAIT if it found none) rather than inventing a trade. Verified live via `frontend/scripts/visual-check-detail.mjs`: all 12 sections render, Elliott Wave/Wyckoff correctly marked "Advisory only," zero console errors.
>
> Two real bugs surfaced and were fixed along the way:
>
> - **`PriceLevels` crashed** (`Cannot read properties of undefined (reading 'toFixed')`) because a stored `MarketContext` is dumped with Pydantic's `exclude_none=True` before persisting, so an unset field like `reward_to_risk` is entirely _absent_ from the JSON (`undefined`) rather than explicit `null` the way a live `/api/analyze` response represents it. Every `=== null` check in `PriceLevels`/`RecommendationResult` needed to become `== null`, and `ReasoningSnapshot`'s optional fields were retyped `| null | undefined` to make that distinction honest in the type system, not just patched at the call site.
> - **The page rendered at 370,506px tall** the first time every section was expanded - SMC alone had 900+ order blocks/FVGs/liquidity items across three timeframes on this real run. `StructuredValue` now previews the first 8 items of any object array with a "Show N more" toggle, cutting the same page to ~31,000px. This wasn't a seed-script artifact to work around; a real live call hits the same `run_smc` node and could produce the same volume, so the cap is a real, permanent fix.

---

## Phase 5 — Price Chart (OHLC Visualization) [DONE]

**Goal:** See the setup, not just read about it.

- **Backend prerequisite (blocking):** no endpoint currently serves candle data to a client. Needs either a new `GET /api/candles?interval=...&as_of=...` endpoint, or an explicit decision to ship this phase later. Do not assume this data is already reachable.
- `lightweight-charts` candlestick chart for the timeframe(s) the recommendation actually used (`MarketContext.timeframes`)
- Horizontal price lines overlaid for entry / stop-loss / take-profit
- Session shading (Sydney/Tokyo/London/New York) using `market_data.sessions`, since session context already exists in the snapshot

**Exit criteria:** chart renders real OHLC data with the recommendation's levels overlaid, for a known historical example, matching the candles actually stored in SQLite for that period.

> **Verification note (2026-09-03):** Added `GET /api/candles?interval=&as_of=&limit=` (reuses the existing lookahead-safe `fetch_candles_before`, new `CandleItem`/`CandlesResponse` schemas, 1 new backend test). `PriceChart` uses lightweight-charts v5's `chart.addSeries(CandlestickSeries, ...)` API with `createPriceLine` for entry/SL/TP, verified directly against the installed package's type definitions rather than assumed from memory. `RecommendationChart` picks the recommendation's first timeframe and requests candles as of its `created_at` (not "now") — lookahead-safe, matching Phase 1's data-integrity principle.
>
> **Session shading was scoped down to a plain caption**, not real chart shading: lightweight-charts has no built-in time-of-day background-band primitive, and building one is out of proportion to what this line needs to communicate. The caption reads real session data (e.g. "Active session at analysis time: New York").
>
> Verified live: `GET /api/candles` returns real EUR/USD OHLC, and the chart renders it correctly on the detail page with zero console errors. The one seeded full-context recommendation happens to be a WAIT with no entry/SL/TP, so there was nothing to overlay for that specific example — the `createPriceLine` branch itself is simple, and was verified by reading the code path and the library's types rather than manufacturing a second seeded BUY just to screenshot a dashed line.

---

## Phase 6 — System Health / Status Panel [DONE]

**Goal:** Surface the backend's own Phase 17 monitoring instead of leaving it API-only.

- Small persistent status widget: `GET /health` polled — shows "ok" / "degraded" and the 24h `pipeline_alerts` count
- Clicking through shows what's degraded, if the backend later exposes alert detail (`GET /api/alerts` doesn't exist yet — note as an optional future backend addition, not required for V1)

**Exit criteria:** the widget accurately reflects a live degraded state when `pipeline_alerts` has recent rows (verifiable by forcing an agent failure in the backend and watching the widget update).

> **Verification note (2026-09-03):** The widget itself (`HealthStatus`, promoted out of `Layout.tsx` where it started as a Phase 0/1 scaffolding proof) existed since Phase 1; this phase's work was making it actually meet the spec — showing the 24h alert count, not just an ok/degraded word. No click-through to alert detail, as the plan already flagged: there's no `GET /api/alerts` to link to.
>
> Verified live, not just against a mock: inserted a real row via `forexmind.monitoring.alerts.send_alert` directly into the running backend's database, confirmed `GET /health` reported the incremented count (`alerts_last_24h: 12`), and confirmed the widget picked it up on its next poll without a page reload — footer read "backend ok · 12 alerts (24h)" exactly.

---

## Phase 7 — Polish, Responsiveness, Accessibility [DONE]

**Goal:** "Clean" holds up outside a 1440px demo window.

- Mobile layout: evidence panels collapse to single-column, chart becomes scrollable rather than squeezed
- Keyboard navigation and visible focus states throughout; `prefers-reduced-motion` respected for the loading step-list animation
- Loading skeletons sized to match their eventual content, so nothing jumps when data arrives

**Exit criteria:** Lighthouse accessibility score > 90, no layout shift on data load, fully usable at 375px width.

> **Verification note (2026-09-03):** Ran the real `lighthouse` CLI (via `npx`, pointed at the Playwright-installed Chromium since no system Chrome exists here) against all three pages, not a guess — first pass came back 94/95/94, comfortably over the >90 bar already, but every flagged issue was fixed anyway rather than stopping at "passing":
>
> - **Dark-mode contrast failures** (Chromium's headless default is dark mode, which is exactly why these were caught): white text on the accent button (2.57:1, needs 4.5:1) and on the `AnalyzeProgress` step badges, `--color-ink-faint` against several surfaces (3.08–3.64:1), and the EXPIRED chip. Fixed with a proper WCAG luminance calculation (not eyeballed) — a new `--color-accent-contrast` token for text-on-solid-fill, and `--color-ink-faint`/`--color-expired` retuned to `#909aa1`, which clears 4.5:1 against every surface those tokens are actually used on (paper, accent-soft, expired-soft).
> - **Heading order** (`RecommendationResult`'s "Reasoning" and jump from `h1` straight to `h3`): promoted to `h2`, and gave each `AgentSectionPanel` a real `h2` too (previously a plain `span`) so screen-reader users can navigate section-to-section, not just visually scan them.
>
> All three pages now score 100/100 on both accessibility and best-practices. Separately (before running Lighthouse), fixed a real mobile layout bug found by eye: the history row's `flex justify-between` produced inconsistent spacing depending on how the timestamp wrapped; rewritten as two lines (timestamp, then badges) via `sm:contents` so it collapses into one row again on wider screens. Also tightened the header/footer at 375px (hid the "EUR/USD" subtitle, reduced nav padding) after "ForexMind AI" wrapped awkwardly. Confirmed zero horizontal overflow on all three pages at 375px via `document.documentElement.scrollWidth`. Loading skeletons (`Skeleton.tsx`) now back History, the Detail page's summary/chart/sections, sized to their real content.

---

## Phase 8 — Deployment [DONE]

**Goal:** A reachable production build, free-tier-first (matching the backend's own Phase 17 philosophy).

- `vite build` static output, served via a free static host or alongside the backend on the same machine
- CORS on the backend scoped to the deployed frontend origin (tightened from the permissive dev-time setting added in Phase 1)

**Exit criteria:** the production build, reachable in a browser, successfully calls the live backend across origins with no CORS errors.

> **Verification note (2026-09-03):** No cloud hosting account exists in this environment to deploy to for real, so this was verified as literally as the exit criteria allows: ran a real `npm run build`, served the actual `dist/` output via `vite preview` on port 4173 (a genuinely different origin from the dev server's 5173, standing in for "the deployed frontend"), and restarted the backend with `CORS_ORIGINS=http://localhost:4173` — **replacing**, not adding to, the dev-time default, to prove the "tightened" scoping actually tightens. Confirmed via curl that the old dev origin (5173) is now correctly rejected while the new one is allowed, then drove the production build with Playwright: a real cross-origin `POST /api/analyze` succeeded with zero console or network errors. Documented the same three steps (build with `VITE_API_BASE_URL` baked in, serve statically, scope `CORS_ORIGINS` to the real deployed origin) in `frontend/README.md` for whoever deploys this for real.

---

## Phase 9 — Dashboard Redesign: KPI Cards, Live Chart, Recent Activity, Grounded Chat [DONE]

**Goal:** The home page was a headline, one button, and a result card once clicked —
too minimal to read as a finished product. Turn it into a proper dashboard: KPI
cards, a prominent chart, recent history, and a chatbox, without silently promising
more than the backend can actually deliver.

- KPI row: live price, backend status, total recommendations, win rate, open (pending) count — all computed from data the app already fetches (`/api/history`, `/api/candles`, `/health`), no new backend endpoints needed for these
- A prominent EUR/USD chart on the home page itself (not only reachable via a specific recommendation's detail page, which is where it lived after Phase 5 and is why it looked "missing" — it was never absent, just never prominent)
- A "Recent activity" teaser (last 5 calls) linking into the existing History page
- **New backend capability:** `POST /api/chat` — grounded follow-up chat about one specific recommendation's stored `MarketContext`, not freeform. New `ChatAgent` (`forexmind/agents/chat/chat_agent.py`) mirrors `ReasoningAgent`'s Groq→Ollama→fallback pattern exactly, but returns plain text — there's no structured schema for a conversational answer. Chat history is client-held only (no new DB table): the frontend resends the last 10 turns each call.
- Chat appears in two places: grounded on the newest recommendation on the Dashboard, and grounded on that specific call on the Recommendation Detail page.

**Exit criteria:** the dashboard's KPI values match what `curl`ing `/api/history`/`/api/candles` directly shows; the chart renders real candles; a real chat exchange against a recommendation with a stored context succeeds end-to-end; the empty/disclosed states (no recommendations yet, no stored context to chat about) render plainly rather than looking broken.

> **Verification note (2026-09-04):** Backend: added `ChatMessage`/`ChatRequest`/`ChatResponse` to `api/schemas.py` and the `/api/chat` route to `api/app.py`, reusing the exact same `fetch_recommendation_by_id`/`fetch_market_context_payload` lookup (and 404 behavior) `recommendation_detail_endpoint` already used. 7 new backend tests (`test_chat_agent.py`'s three-case Groq/Ollama/fallback mirror of `test_reasoning_agent.py`, plus 3 endpoint tests) — 214 passing overall.
>
> Frontend: renamed `AnalyzePage` → `DashboardPage`, composed from new `KpiCard`, `LiveChart` (a `useLiveCandles` poll — 60s, local-DB-only, no Twelve Data calls, so no rate-limit risk), `RecentActivity`, and `ChatPanel` (backing hook `useChat` holds the conversation in local state only). `ChatPanel` is also added to `RecommendationDetailPage`, grounded on that specific call.
>
> Verified against the real running backend, not mocks: real `POST /api/chat` calls for both 404 paths (unknown id; a recommendation with no stored context) and the success path landed on the same Groq-401→Ollama-404→fallback-text chain already proven in this environment — a genuine exercise of the new endpoint's full error-handling path, not a happy-path-only check. Screenshotted the dashboard (KPI values cross-checked against direct `curl` output), a real chat exchange rendering correctly (user bubble right-aligned, assistant left-aligned), the detail page's chat panel, and mobile at 375px (no horizontal overflow). Re-ran the real `lighthouse` CLI against the new dashboard: 100/100 accessibility and best-practices, carrying forward Phase 7's fixes since the new components reuse the same design tokens.
>
> **Disclosed, not silently glossed over:** the "live" price/chart show the most recent EUR/USD data actually stored in SQLite, honestly labeled with its real timestamp - not a continuously-ticking feed. Nothing in this app inserts fresh candles on a timer; that's the same deferred APScheduler gap already flagged in the root `Development.md`, and building it now would also risk the 800 req/day Twelve Data budget if polled automatically. Also: only BUY/SELL recommendations are ever persisted with a `MarketContext` (`orchestration/graph.py::run_save_recommendation`), so without real `GROQ_API_KEY`/`FINNHUB_API_KEY` configured, real analyze calls land on WAIT and are never saved - chat has nothing grounded to discuss until either real keys are added or the existing demo seed (`scripts/seed_demo_recommendation_with_context.py`) is used. The empty states say this plainly rather than looking broken.

---

## Suggested Build Order Summary

```
Phase 0 → Scaffolding + design tokens (no API calls yet)
Phase 1 → Typed API client + query hooks   [blocked without backend CORS]
Phase 2 → Analyze view — the core "should I buy" experience
Phase 3 → History view
Phase 4 → Recommendation detail / full evidence drill-down   [blocked without GET /api/recommendation/{id}]
Phase 5 → Price chart   [blocked without a candles endpoint]
Phase 6 → Health/status widget
Phase 7 → Polish, responsiveness, accessibility
Phase 8 → Deployment
Phase 9 → Dashboard redesign: KPI cards, live chart, recent activity, grounded chat
```

Phases 0–3 and 6–8 can proceed against the backend exactly as it exists today (once CORS is added in Phase 1). Phases 4 and 5 are explicitly gated on backend work that hasn't been scoped yet — treat those two backend endpoints as their own small addition to the root `Development.md`, not something the frontend can route around.
