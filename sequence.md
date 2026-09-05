# ForexMind AI — Pipeline Sequence Diagrams

## 1. Main pipeline — "Analyze EUR/USD now"

```mermaid
sequenceDiagram
    actor You as You (User)
    participant Web as Website
    participant BE as Backend
    participant DB as Saved Prices (Database)
    participant TD as Twelve Data (Live Price API)
    participant Bots as 8 Analyst Robots
    participant Combine as Combine & Spot Disagreements
    participant Hist as Compare to Past Setups
    participant Risk as Check Risk
    participant Track as Check Track Record
    participant AI as Final Decision Maker (AI)
    participant Groq as Groq AI
    participant Backup as Backup AI (Ollama)

    You->>Web: Click "Analyze EUR/USD now"
    Web->>BE: Request an analysis
    BE->>DB: Get the latest saved candle prices
    DB-->>BE: Here's the price history

    opt This is a "right now" request
        BE->>TD: What's the current live price?
        TD-->>BE: Here's the live price
    end

    Note over BE,Bots: Same price data handed to 8 robots at once
    par Technical indicators
        BE->>Bots: Analyze
    and Price action
        BE->>Bots: Analyze
    and Candlestick patterns
        BE->>Bots: Analyze
    and Support & resistance
        BE->>Bots: Analyze
    and Smart money footprints
        BE->>Bots: Analyze
    and Elliott Wave
        BE->>Bots: Analyze
    and Wyckoff phases
        BE->>Bots: Analyze
    and News sentiment
        BE->>Bots: Analyze
    end
    Bots-->>BE: 8 separate findings

    BE->>Combine: Merge all 8 findings into one report
    Combine-->>BE: Combined report + any disagreements

    BE->>Hist: Has this exact setup happened before?
    Hist-->>BE: Similarity score

    BE->>Risk: Is the risk/reward reasonable?
    Risk-->>BE: Risk verdict

    BE->>Track: How often did similar setups actually win?
    Track->>DB: Look up past results
    DB-->>Track: Past win/loss history
    Track-->>BE: Confidence adjustment

    Note over BE,AI: Everything above is bundled into one report and handed to the AI
    BE->>AI: Here's everything — what's your call?
    AI->>Groq: Please decide (BUY / SELL / WAIT)
    alt Groq answers
        Groq-->>AI: Decision + reasoning
    else Groq is down
        AI->>Backup: Please decide instead
        alt Backup answers
            Backup-->>AI: Decision + reasoning
        else Backup also down
            AI->>AI: Default to WAIT, explain both failed
        end
    end
    AI-->>BE: Final decision

    opt Decision is BUY or SELL
        BE->>DB: Save decision + full report for later
    end

    BE-->>Web: Here's the recommendation
    Web-->>You: Shows BUY / SELL / WAIT with reasoning
```

## 2. Chat feature — reuses the pipeline above when needed

```mermaid
sequenceDiagram
    actor You as You (User)
    participant Web as Website
    participant Chat as Chat Feature
    participant DB as Saved Prices (Database)
    participant Pipe as Full Analysis Pipeline (diagram above)
    participant AI2 as Chat AI

    You->>Web: Type a question ("Should I buy or sell?")
    Web->>Chat: Send question (+ a recommendation id, if you were viewing one)

    alt You were looking at one specific past call
        Chat->>DB: Get that call's full report
        DB-->>Chat: Report
    else No specific call given
        Chat->>DB: Is there a recent call (last 15 min)?
        alt Yes, recent one exists
            DB-->>Chat: Use that report
        else No recent one
            Chat->>Pipe: Run a fresh analysis right now
            Pipe-->>Chat: Brand new report
        end
    end

    Chat->>AI2: Answer this question using ONLY this report
    AI2-->>Chat: Plain-English answer
    Chat-->>Web: Reply
    Web-->>You: Shows the answer in the chat box
```

One thing not shown in either diagram: the **live chart** doesn't go through this pipeline at all — it just re-reads the database on a timer, and nothing currently refreshes that database automatically. It's a separate, much simpler read-only flow, not part of "the pipeline."
