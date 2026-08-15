# ForexMind AI — Development Plan

> Companion to `context.md` (the spec). This document turns that spec into an execution-ordered, phase-wise build plan.

---

## 0. Locked Architectural Decisions

These were open questions in `context.md` §19 and are now resolved for V1:

| Question | Decision |
|---|---|
| Currency scope | **EUR/USD only.** No multi-pair abstraction in V1 — build the simplest thing that works for one pair. |
| LLM strategy | **Single central Reasoning LLM** (Agent 12). All other agents are deterministic/mathematical, no LLM. |
| Agent collaboration | **Shared blackboard.** Every agent writes structured findings to one shared state object per analysis run; the Reasoning Agent reads the full blackboard at the end. No agent-to-agent chat, no debate loop. |
| Market data provider | **Twelve Data** (free tier: 800 req/day, live + historical forex OHLC, multiple timeframes) for both live and historical candles. |

### Defaults applied to the still-open questions (override anytime)

| Question | Default applied | Rationale |
|---|---|---|
| Recommendation horizon | AI determines automatically from volatility/structure per §6 timeframe logic (scalp/intraday/swing), not user-specified. | Matches §6 philosophy already in the spec. |
| Risk management (SL/TP) | **Structure-based, dynamic.** SL beyond the invalidating swing/order block, TP at next liquidity/S-R level; R:R is a *result* of structure, not a fixed input. | Consistent with SMC-heavy methodology; a fixed R:R would contradict "no single strategy dominates." |
| News source | **Finnhub free tier** (forex news + economic calendar in one free API key) as primary; **FRED** as a secondary macro-data supplement. | Both free, no scraping/ToS risk, single API covers most needs. |
| Historical similarity engine | **Rule-based weighted feature-vector matching** for V1 (trend state, RSI bucket, active patterns, session, normalized ATR) — cosine/weighted distance against stored snapshots. | No training data exists yet to justify ML; explainable and free. Embeddings/ML are a documented V2 upgrade path. |
| Confidence scoring | **Hybrid**: rule-based agreement score (how many agents confirm vs conflict) combined with recency-weighted historical win-rate from the Learning Agent once enough data exists. Pure rule-based until statistics are mature (see Phase 14). | Matches §11/§12 exactly — "confidence depends on evidence" + "recent behaviour weighted more." |
| Evaluation timeout | Timeout = function of the determined horizon: scalp → few hours, intraday → 1–2 sessions, swing → 5–10 days. Table lives in the Evaluation Agent config, tunable without code changes. | Ties timeout directly to the horizon decision above instead of a magic constant. |

### Tech stack (Phase 0 output, previewed here for context)

- **Language:** Python 3.11+ (best ecosystem for indicators, data science, and agent orchestration)
- **Orchestration:** LangGraph (open-source, free) — its shared-state graph model *is* the blackboard pattern
- **Storage:** SQLite for V1 (zero-config, free, file-based; upgrade path to Postgres later if needed)
- **Scheduling:** APScheduler (polling market data, running the Evaluation Agent)
- **API layer:** FastAPI (serves the "should I buy EUR/USD" endpoint + recommendation history)
- **LLM (Reasoning Agent):** Groq free tier (fast hosted inference on open-source models, e.g. Llama 3.3 70B) as primary, with local Ollama (same model family) as an offline/fallback option
- **Indicators:** `pandas` + `pandas-ta` (free, no TA-Lib compilation headaches)

---

## Phase 0 — System Architecture & Project Setup

**Goal:** Nothing analytical yet. Stand up the skeleton everything else plugs into.

- Repo scaffolding: `agents/`, `data/`, `storage/`, `api/`, `orchestration/`, `tests/`
- Python environment + dependency management (`pyproject.toml` / `requirements.txt`)
- SQLite schema v1: `candles`, `recommendations`, `agent_snapshots`, `news_events`, `evaluation_results`
- Twelve Data API key provisioning + a thin, rate-limit-aware client wrapper (800 req/day budget)
- Blackboard data contract: define the shared-state schema every agent reads/writes (a single `MarketContext` object — see Phase 8 for full spec, but the *shape* must exist before any agent is coded, since Phase 1+ agents all target this contract)
- Logging + config management (env-based, no secrets committed)
- Test harness setup (pytest) and a "golden fixture" of sample OHLC data for deterministic agent testing without hitting the live API
- CI: lint + test on push (free GitHub Actions tier)

**Exit criteria:** Empty pipeline runs end-to-end — fetch one candle from Twelve Data, write it to SQLite, log it — with tests green.

---

## Phase 1 — Market Data Agent (Agent 1) [DONE]

**Goal:** Reliable, structured live + historical EUR/USD data.

- Live price + spread retrieval
- OHLC retrieval across all timeframes needed (1m/5m/15m/30m/1H/4H/Daily/Weekly)
- Historical candle backfill into SQLite (bounded by Twelve Data free-tier history depth)
- Market session detection (Sydney/Tokyo/London/New York, overlap windows)
- Output: writes a `MarketDataSnapshot` section onto the blackboard contract from Phase 0

**Exit criteria:** Given a timestamp, the system can reconstruct the exact multi-timeframe OHLC state at that moment (needed later for backtesting and historical similarity).

---

## Phase 2 — Technical Analysis Agent (Agent 2) [DONE]

**Goal:** Deterministic indicator computation.

- EMA, SMA (trend)
- RSI, MACD, Stochastic (momentum)
- ATR, Bollinger Bands (volatility)
- Structured output per timeframe (e.g. `{trend: bullish, EMA20>EMA50: true, RSI: 62, MACD_cross: bullish, ATR: 0.0021}`)
- Unit tests against the golden fixture with hand-verified expected values

**Exit criteria:** Indicator outputs match a hand-calculated reference within floating-point tolerance.

---

## Phase 3 — Price Action & Candlestick Agents (Agents 3, 5) [DONE]

**Goal:** Classical chart-reading, fully mathematical (no LLM per spec).

- Price Action Agent: trend classification, breakout detection, pullback detection, range/consolidation detection, rejection detection
- Candlestick Agent: single-candle library (Hammer, Hanging Man, Doji, Shooting Star, Marubozu, Spinning Top) + multi-candle library (Engulfing, Harami, Morning/Evening Star, Three White Soldiers/Black Crows, Tweezer Top/Bottom)
- Both agents output boolean/enum flags + the candle index where each pattern triggered

**Exit criteria:** Pattern detectors validated against a curated set of known historical EUR/USD examples (manually labeled).

---

## Phase 4 — Support & Resistance Agent (Agent 6) [DONE]

**Goal:** Level identification.

- Swing high/low detection (pivot-based)
- Horizontal level clustering (merge nearby swing points into zones)
- Psychological levels (round numbers, e.g. 1.1000, 1.1050)
- Dynamic levels (moving averages acting as S/R)
- Output: ranked list of nearby levels with strength score (touch count, recency, confluence with round numbers)

**Exit criteria:** Levels visually validated against a plotted chart for a known date range.

---

## Phase 5 — SMC / ICT Agent (Agent 4) [DONE]

**Goal:** The most complex deterministic agent — institutional concepts.

- Market structure state machine (tracking swing structure to detect BOS / CHOCH)
- Order block identification (last opposing candle before impulsive move)
- Fair Value Gap (FVG) detection (3-candle imbalance)
- Liquidity pool identification (equal highs/lows, obvious stop clusters)
- Liquidity sweep detection (wick through a pool + rejection)
- Mitigation block / breaker block detection
- Premium/Discount zone calculation (relative to the current dealing range)
- Optimal Trade Entry (OTE) zone calculation (typically the 62–79% retracement of the most recent impulse leg)

**Exit criteria:** Validated against manually-annotated known SMC setups (build a small labeled test set — this agent is the highest bug-risk one, budget extra review time).

---

## Phase 6 — Elliott Wave & Wyckoff Agents (Agents 7, 8) [DONE]

**Goal:** The two most probabilistic/subjective classical methodologies — treat outputs as advisory signals with an explicit confidence/probability, not hard facts.

- Elliott Wave: impulse/correction wave labeling attempt, wave count validation rules (e.g. wave 3 not shortest), probability score for the current count
- Wyckoff: phase detection (accumulation/distribution/markup/markdown), spring/upthrust detection
- Both agents must output a **confidence** alongside their read, since these methodologies are inherently more ambiguous than SMC or indicators — this confidence feeds the Reasoning Agent's conflict-resolution logic later

**Exit criteria:** Outputs are directionally sane on well-known historical examples; agents never block a recommendation on their own (advisory weight only).

---

## Phase 7 — Automatic Timeframe Selection (§6 logic) [DONE]

**Goal:** Remove timeframe choice from the user entirely.

- Volatility/session-based logic to classify current conditions into scalp/intraday/swing/long-term-context buckets
- Determines which timeframe combination Phases 1–6's agents should actually run against for a given request (e.g. combine 15m + 1H + 4H for an intraday read)
- This is a small, rules-based dispatcher — not an agent of its own in the original numbering, but it's a hard dependency for Phase 8's orchestration

**Exit criteria:** Given historical volatility conditions, the dispatcher picks a timeframe set a human analyst would agree with, on a handful of manually reviewed cases.

---

## Phase 8 — Blackboard Orchestration & Cross-Validation (§7/§8 architecture) [DONE]

**Goal:** Wire Phases 1–7 into the actual multi-agent collaboration described in the spec.

- Implement the `MarketContext` blackboard object fully (finalize the schema stubbed in Phase 0, now with every agent's real output shape)
- LangGraph graph definition: Market Data → parallel fan-out to all analysis agents → cross-validation step
- Cross-validation logic: flag agreements and contradictions explicitly (e.g. "Price Action says bullish breakout, but SMC says price is in premium zone approaching a bearish order block" — this conflict must be visible on the blackboard, not silently dropped)
- This phase does **not** yet include News, Historical Similarity, Risk, or the Reasoning Agent — it's the "11 analysis agents talking to one shared state" milestone

**Exit criteria:** One end-to-end run produces a fully populated blackboard with every deterministic agent's findings plus an explicit conflict list, for a real historical timestamp.

---

## Phase 9 — News Agent (Agent 9) [DONE]

**Goal:** Fundamental/sentiment layer.

- Finnhub integration: economic calendar (high-impact EUR/USD-relevant events) + forex news feed
- FRED integration: supplementary macro series (rate differentials, inflation, etc.) where useful
- Sentiment classification: Bullish / Bearish / Neutral for EUR and USD independently, then combined
- Time-relevance logic: an event 3 days ago matters less than one in the next 2 hours — output should include a time-decay weight
- Writes to blackboard alongside the technical findings

**Exit criteria:** Given a known historical high-impact news date (e.g. an ECB rate decision), the agent correctly flags it and assigns a directional sentiment.

---

## Phase 10 — Historical Database & Historical Similarity Agent (Agent 10) [DONE]

**Goal:** "Has this setup happened before, and what happened next?"

- Recommendation/snapshot storage schema finalized (this doubles as the schema needed later for Phase 13/14)
- Feature vector definition: trend state, RSI bucket, active SMC flags, active candlestick patterns, session, normalized ATR, S/R proximity
- Rule-based similarity scoring (weighted distance/cosine) against all stored historical snapshots
- Output: top-N similar historical setups + their eventual outcome (once outcomes exist — early on this will be sparse, which is expected and fine)
- **Note:** this agent's usefulness scales with how much history has been evaluated (Phase 13). Early in the project it will have little to compare against — that's expected, not a bug.

**Exit criteria:** Given two intentionally near-duplicate synthetic setups, the agent returns a high similarity score; given two intentionally opposite setups, a low one.

---

## Phase 11 — Risk Analysis Agent (Agent 11) [DONE]

**Goal:** Structure-based dynamic SL/TP and R:R.

- SL placement: beyond the invalidating structure (swing point / order block / FVG boundary depending on the setup type from Phase 5)
- TP placement: next meaningful liquidity pool or S/R level (from Phase 4/5 outputs)
- ATR-based sanity bounds (reject setups where structure-based SL is unreasonably tight/wide relative to current volatility)
- Expected move / R:R calculation as an output, not an input
- Volatility flag if ATR suggests conditions are abnormal for the chosen horizon

**Exit criteria:** For a handful of known historical setups, the computed SL/TP match what a discretionary SMC trader would plausibly place.

---

## Phase 12 — Reasoning Agent (Agent 12) — the LLM [DONE]

**Goal:** The single point where an LLM touches this system.

- Prompt design: the LLM receives the **entire finalized blackboard** (all structured facts, explicit conflicts from Phase 8, news sentiment, similarity results, risk numbers) — never raw price data or charts
- LLM integration: Groq (primary, free tier) with local Ollama fallback for offline/rate-limit situations
- Output schema enforcement (matches §9 exactly): Recommendation (BUY/SELL/WAIT), Confidence, Entry, SL, TP, Reasoning, Supporting Evidence, Conflicting Evidence, Historical Similarity, Risk:Reward, Important News, Trade Quality Score
- Conflict-resolution logic lives in the prompt: instruct the model explicitly on how to weigh SMC vs classical vs Elliott/Wyckoff (advisory-only per Phase 6) vs news
- WAIT must be reachable and not penalized — validate the prompt doesn't have an implicit bias toward always picking BUY/SELL

**Exit criteria:** For a batch of historical blackboards with known good/bad setups, the Reasoning Agent's calls are directionally sensible and its stated reasoning actually reflects the evidence it was given (spot-check manually).

---

## Phase 13 — Recommendation Storage & Evaluation Agent (Agent 13) [DONE]

**Goal:** Close the loop — automatic outcome detection.

- Every recommendation persisted with full snapshot (per §10): market state, indicators, patterns, news, recommendation, confidence, entry/SL/TP, timestamp, status=Pending
- Evaluation Agent polls live price against open recommendations
- TP hit → WIN, SL hit → LOSS, horizon-based timeout elapsed (Phase 0 default table) → EXPIRED
- Fully automatic, no user interaction

**Exit criteria:** A recommendation generated against historical data with a known subsequent price path is correctly auto-resolved to WIN/LOSS/EXPIRED.

---

## Phase 14 — Learning Agent & Statistics Engine (Agent 14) [DONE]

**Goal:** Rolling, recency-weighted statistical memory (§11/§12).

- Rolling win-rate computation: last 30/90/365 days + lifetime
- Segmented statistics (e.g. "Bullish BOS + Order Block + London session" as a compound feature key, matching the exact example in the spec)
- Recency weighting so recent performance influences confidence more than old data (market regime awareness)
- Feeds back into: (a) Historical Similarity Agent's returned win-rate, (b) Reasoning Agent's confidence calibration (the hybrid scoring from Phase 0's defaults table)

**Exit criteria:** After running the pipeline over a backtest window, the statistics engine produces sane, non-degenerate win-rates per feature segment, and confidence scores visibly shift as more data accumulates.

---

## Phase 15 — End-to-End Integration & Interface [DONE]

**Goal:** The actual "Should I Buy EUR/USD?" experience.

- FastAPI endpoint: single request in → full pipeline run → structured recommendation out
- Simple interface (CLI first; minimal web UI if time allows) to trigger a request and display the full recommendation with evidence, matching §9's output spec
- Recommendation history view (past calls + outcomes)

**Exit criteria:** A live end-to-end request, hitting real Twelve Data + Finnhub + Groq, returns a complete, well-formed recommendation in the expected schema.

---

## Phase 16 — Backtesting & Validation [DONE]

**Goal:** Prove the system works before trusting it.

- Replay the full pipeline across a historical window (bounded by Twelve Data free-tier history depth), generating recommendations as if run live at each point in time
- Auto-evaluate all of them via the Evaluation Agent logic
- Produce an aggregate report: win rate, R:R realized, confidence calibration (do 80%-confidence calls actually win ~80% of the time?)
- This is also where Phase 10's Historical Similarity Agent stops being data-starved

**Exit criteria:** A backtest report exists and confidence calibration is at least directionally reasonable (not wildly overconfident).

---

## Phase 17 — Free-Tier Hardening & Deployment [DONE]

**Goal:** Make it durable within free-tier constraints.

- Rate-limit budgeting across Twelve Data (800/day), Finnhub, and Groq — caching layer to avoid redundant calls
- Graceful degradation if any free API is rate-limited or down (e.g. skip News Agent rather than crash the pipeline)
- Local/self-hosted deployment (single machine, SQLite, no paid infra required)
- Basic monitoring/alerting for pipeline failures

**Exit criteria:** The system survives a full day of normal usage without hitting a hard failure from a rate limit or quota exhaustion.

---

## Phase 18 — Future Expansion (out of scope for V1, per §18)

Explicitly deferred: additional currency pairs, commodities, indices, crypto, portfolio-level analysis, personalized risk profiles, broker integrations, mobile app, voice interaction. Not planned until V1 above is validated end-to-end.

---

## Suggested Build Order Summary

```
Phase 0  → Foundation (no analysis yet)
Phase 1  → Market data
Phase 2  → Indicators
Phase 3  → Price action + candlesticks
Phase 4  → Support/Resistance
Phase 5  → SMC/ICT (highest complexity)
Phase 6  → Elliott Wave + Wyckoff (advisory-weight agents)
Phase 7  → Auto timeframe selection
Phase 8  → Blackboard orchestration (first real "multi-agent" milestone)
Phase 9  → News
Phase 10 → Historical similarity
Phase 11 → Risk analysis
Phase 12 → Reasoning Agent (LLM) — first recommendation ever produced
Phase 13 → Evaluation Agent (closes the loop)
Phase 14 → Learning Agent (statistics feed back into confidence)
Phase 15 → End-to-end interface
Phase 16 → Backtesting/validation
Phase 17 → Free-tier hardening & deployment
Phase 18 → Future expansion (deferred)
```

Each phase has a hard dependency on the ones before it producing a stable structured output — this mirrors §7/§8/§13 of the spec directly (deterministic agents first, LLM only at the very end, evaluation/learning only after recommendations exist to evaluate).
