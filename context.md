# Project Specification
# ForexMind AI
## An Autonomous Multi-Agent AI Forex Market Analyst (Free-Tier First)

> **Project Status:** Planning Phase
>
> **Goal:** Build an AI system that behaves like an experienced team of professional forex analysts. Instead of placing trades automatically, it analyzes the live EUR/USD market, collaborates across multiple specialized AI agents, reasons over technical and fundamental information, compares the current market with historical scenarios, and finally provides a BUY, SELL, or WAIT recommendation with detailed justification.

---

# 1. Vision

ForexMind AI is **NOT** a trading bot.

ForexMind AI is **NOT** a signal generator that blindly checks indicators.

ForexMind AI is an AI Market Analyst.

Every recommendation should be backed by:

- Live Market Data
- Market Structure
- Smart Money Concepts
- Classical Technical Analysis
- Price Action
- Candlestick Analysis
- Multiple Technical Indicators
- Historical Similarity
- News & Economic Events
- Risk Analysis
- Multi-Agent Collaboration

The AI should always explain **WHY** it reached its conclusion.

---

# 2. Primary Goal

Whenever the user asks:

> "Should I Buy EUR/USD right now?"

The AI should perform a complete market investigation before answering.

Instead of answering immediately, the system should first collect information, analyze it through multiple specialized agents, compare it against historical data, allow agents to collaborate, and then produce the final recommendation.

---

# 3. Core Principles

## Principle 1

The AI never guesses.

Every recommendation must be supported by evidence.

---

## Principle 2

The AI is allowed to answer:

- BUY
- SELL
- WAIT

WAIT is considered a valid recommendation.

---

## Principle 3

Confidence should depend on evidence.

Example:

Multiple confirmations

↓

Higher confidence

Conflicting signals

↓

Lower confidence

---

## Principle 4

No single strategy should dominate.

The system should combine multiple schools of technical analysis.

---

## Principle 5

Everything should use Free Tier technologies whenever possible.

---

# 4. Supported Trading Methodologies

The AI should understand and analyze all of the following.

## ICT / Smart Money Concepts

- Order Blocks
- Fair Value Gaps
- Liquidity Sweeps
- Liquidity Pools
- Break Of Structure (BOS)
- Change Of Character (CHOCH)
- Premium & Discount Zones
- Market Structure
- Mitigation Blocks
- Breaker Blocks
- Optimal Trade Entry (OTE)
- Institutional Concepts

---

## Classical Price Action

- Trend Analysis
- Trend Lines
- Breakouts
- Pullbacks
- Ranges
- Consolidation
- Rejections
- Continuation Patterns
- Reversal Patterns

---

## Candlestick Analysis

Single Candle

- Hammer
- Hanging Man
- Doji
- Shooting Star
- Marubozu
- Spinning Top

Multiple Candle

- Engulfing
- Harami
- Morning Star
- Evening Star
- Three White Soldiers
- Three Black Crows
- Tweezer Tops
- Tweezer Bottoms

---

## Indicators

Trend

- EMA
- SMA

Momentum

- RSI
- MACD
- Stochastic

Volatility

- ATR
- Bollinger Bands

Volume Related

(Only when reliable forex volume proxies are available.)

---

## Support & Resistance

- Horizontal Levels
- Dynamic Levels
- Psychological Levels
- Swing Highs
- Swing Lows

---

## Elliott Wave

Wave Identification

Impulse

Correction

Wave Validation

Wave Counting

---

## Wyckoff

Accumulation

Distribution

Spring

Upthrust

Markup

Markdown

---

# 5. Market Data

The system should continuously retrieve live market information.

Examples

- Live Price
- OHLC Data
- Spread
- Multiple Timeframes
- Historical Candles

The AI should never rely on screenshots.

Everything should use structured market data.

---

# 6. Timeframe Selection

The user should NOT have to specify a timeframe.

Instead,

The AI should determine the most appropriate timeframe automatically.

Possible logic

Scalping

↓

1m
5m
15m

Intraday

↓

15m
30m
1H

Swing

↓

4H
Daily

Long-Term Context

↓

Weekly

The AI should combine multiple timeframes whenever necessary.

---

# 7. Multi-Agent Architecture

Instead of one giant LLM,

ForexMind AI should contain multiple specialized agents.

---

## Agent 1

Market Data Agent

Responsibilities

- Retrieve live price
- Retrieve candles
- Retrieve OHLC
- Manage market sessions

---

## Agent 2

Technical Analysis Agent

Responsibilities

Analyze

- EMA
- RSI
- MACD
- ATR
- Bollinger Bands

Return structured findings.

---

## Agent 3

Price Action Agent

Responsibilities

Detect

- Trends
- Breakouts
- Pullbacks
- Consolidation
- Rejections

---

## Agent 4

SMC Agent

Responsibilities

Detect

- Order Blocks
- BOS
- CHOCH
- Liquidity Sweeps
- FVG
- Mitigation
- Premium/Discount

---

## Agent 5

Candlestick Agent

Responsibilities

Detect

Single Candle Patterns

Multi Candle Patterns

No LLM required.

Everything should be mathematical.

---

## Agent 6

Support & Resistance Agent

Responsibilities

Identify

Major Levels

Dynamic Levels

Strong Zones

---

## Agent 7

Elliott Wave Agent

Responsibilities

Attempt wave counting.

Estimate probability.

---

## Agent 8

Wyckoff Agent

Responsibilities

Determine

Accumulation

Distribution

Spring

Upthrust

---

## Agent 9

News Agent

Responsibilities

Collect

- Economic Calendar
- High Impact Events
- Central Bank News
- Currency News

Generate

Bullish

Bearish

Neutral

Sentiment

---

## Agent 10

Historical Similarity Agent

Responsibilities

Compare

Current Market

↓

Historical Markets

Find similar setups.

Return

Similarity Score

Historical Win Rate

---

## Agent 11

Risk Analysis Agent

Responsibilities

Evaluate

Risk

Reward

Volatility

ATR

Expected Movement

---

## Agent 12

Reasoning Agent (LLM)

Responsibilities

Receive all outputs.

Reason.

Resolve conflicts.

Generate final recommendation.

---

## Agent 13

Evaluation Agent

Responsibilities

Monitor every recommendation after it is generated.

Determine

WIN

LOSS

EXPIRED

Automatically.

---

## Agent 14

Learning Agent

Responsibilities

Update statistics.

Detect

Changing Market Behaviour

Improve future confidence scores.

---

# 8. Agent Collaboration

The agents should NOT work independently.

Workflow

Market Data

↓

All Analysis Agents

↓

Cross Validation

↓

Discussion

↓

Consensus Building

↓

Reasoning Agent

↓

Recommendation

---

# 9. Recommendation Output

The final answer should include

Recommendation

BUY

SELL

WAIT

Confidence

Entry

Stop Loss

Take Profit

Reasoning

Supporting Evidence

Conflicting Evidence

Historical Similarity

Risk Reward

Important News

Trade Quality Score

---

# 10. Historical Memory

Every recommendation should be stored.

Example

Recommendation

↓

Market Snapshot

↓

Indicators

↓

Patterns

↓

News

↓

Recommendation

↓

Confidence

↓

Entry

↓

SL

↓

TP

↓

Timestamp

↓

Status

Pending

---

Later

Evaluation Agent

↓

WIN

LOSS

EXPIRED

---

# 11. Learning Philosophy

The AI should NOT learn by modifying the LLM.

Instead,

The system should continuously build statistical knowledge.

Example

Bullish BOS

+

Order Block

+

London Session

↓

Last 30 Days

↓

74% Win Rate

The LLM should use these statistics during reasoning.

---

# 12. Market Regime Awareness

Markets change.

Strategies become stronger.

Strategies become weaker.

The system should detect this.

Historical information should NOT have equal importance.

Recent market behaviour should influence confidence more heavily than older data.

Long-term knowledge should remain available.

---

# 13. Pattern Detection Philosophy

Pattern detection should NOT be done by the LLM.

Dedicated algorithms should detect:

Candlestick Patterns

Indicators

SMC

Trend

Support

Resistance

Etc.

The LLM should receive structured information.

Example

Trend

Bullish

EMA20 > EMA50

Hammer

Detected

Liquidity Sweep

Detected

FVG

Present

RSI

62

News

Bullish EUR

The LLM reasons over facts.

---

# 14. Recommendation Evaluation

The AI should automatically evaluate itself.

Example

Recommendation

BUY

Entry

1.1650

SL

1.1630

TP

1.1690

↓

Evaluation Agent watches live market.

↓

If TP hit

WIN

If SL hit

LOSS

If timeout

EXPIRED

No user interaction required.

---

# 15. Continuous Improvement

Every completed recommendation becomes historical evidence.

The system should maintain rolling statistics.

Examples

Last 30 Days

Last 90 Days

Last 365 Days

Lifetime

The AI should prefer recent performance when assigning confidence.

---

# 16. Free-Tier Requirement

The entire project should prioritize free and open-source technologies.

Every architectural decision should first consider:

- Open-source models
- Free APIs
- Self-hosted components
- Local execution
- No mandatory paid services

Paid services should only be considered if no practical free alternative exists.

---

# 17. High-Level System Flow

User

↓

Market Data Collection

↓

Market Analysis

↓

Specialized Agents

↓

Agent Collaboration

↓

Historical Comparison

↓

News Analysis

↓

Risk Analysis

↓

Reasoning Agent

↓

Recommendation

↓

Recommendation Storage

↓

Evaluation Agent

↓

Outcome Detection

↓

Historical Database

↓

Learning Agent

↓

Updated Statistics

↓

Future Recommendations

---

# 18. Future Expansion (Not in Initial Scope)

Possible future enhancements include:

- Additional currency pairs
- Commodities
- Indices
- Cryptocurrency markets
- Portfolio-level analysis
- Personalized risk profiles
- Broker integrations (optional)
- Mobile application
- Voice interaction

---

# 19. Open Questions (Need Clarification Before Implementation)

The following decisions have **not** been finalized and require your input. Nothing should be assumed until these are answered.

## A. Currency Scope
- Should Version 1 analyze **only EUR/USD**, or should the architecture be designed from day one to support multiple currency pairs?

---

## B. Recommendation Horizon
When the AI recommends a trade, what is the intended holding period?

Examples:
- Scalping (minutes)
- Intraday (hours)
- Swing (days)

Or should the AI determine this automatically based on market conditions?

---

## C. Risk Management Rules
Should the AI:
- Calculate Stop Loss and Take Profit dynamically?
- Use fixed Risk:Reward ratios?
- Adapt Risk:Reward to market structure?

No decision has been made yet.

---

## D. Economic News Sources
Which free news and economic calendar sources should be used?

This needs to be finalized based on available free APIs or data feeds.

---

## E. Historical Market Data Source
Which free provider should be the primary source for historical OHLC data?

This decision affects storage, backtesting, and similarity analysis.

---

## F. LLM Strategy
Should all reasoning be performed by:
- One central LLM?
- Multiple reasoning agents using different open-source models?
- A hierarchical planner + specialist architecture?

Architecture not finalized.

---

## G. Similarity Engine
How should historical similarity be calculated?

Possible approaches include:
- Rule-based feature matching
- Vector embeddings
- Time-series similarity
- Machine learning models

Not yet decided.

---

## H. Confidence Scoring
How should the final confidence score be calculated?

Should it be:
- Rule-based
- Statistical
- Learned from historical outcomes
- A hybrid approach

Not finalized.

---

## I. Evaluation Timeout
When should a recommendation be marked as **EXPIRED** if neither TP nor SL is reached?

This should depend on the intended trade horizon and requires a defined policy.

---

## J. Agent Communication
How should agents collaborate?

Possible approaches:
- Sequential pipeline
- Shared blackboard memory
- Planner agent coordinating specialists
- Debate/consensus mechanism

This architecture is still open for discussion.

---