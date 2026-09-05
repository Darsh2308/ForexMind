import { useEffect, useState } from 'react'

export interface ProgressStep {
  label: string
  /** Roughly how long this stage takes in a typical run, in ms. Cumulative
   * with the steps before it - not a guarantee, just a plausible pace so the
   * wait reads as "working," not "stuck." The backend runs one synchronous
   * call and reports no real progress, so this can only ever approximate it. */
  ms: number
}

/** The graph's actual stages (orchestration/graph.py): one fetch, an 8-way
 * parallel fan-out, a fan-in, three sequential enrichment steps, then the
 * single LLM call. ~15s total, matching the CLI's own "15-30s" estimate. */
export const ANALYZE_STEPS: ProgressStep[] = [
  { label: 'Fetching live market data', ms: 1200 },
  { label: 'Running 8 analysis agents in parallel', ms: 5000 },
  { label: 'Cross-validating findings for conflicts', ms: 1200 },
  { label: 'Comparing history, sizing risk, calibrating confidence', ms: 3600 },
  { label: 'Reasoning Agent synthesizing the call', ms: 4000 },
]

const THRESHOLDS = ANALYZE_STEPS.reduce<number[]>((acc, step, i) => {
  acc.push((acc[i - 1] ?? 0) + step.ms)
  return acc
}, [])

/**
 * Advances an index through `ANALYZE_STEPS` while `active` is true, timed to
 * a typical run. Never reaches "complete" on its own - it holds at the last
 * step if the real call is still pending past the estimate, since claiming
 * done before the response actually arrives would be dishonest.
 */
export function useSimulatedProgress(active: boolean) {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!active) return

    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const nextIndex = THRESHOLDS.findIndex((threshold) => elapsed < threshold)
      setStepIndex(nextIndex === -1 ? ANALYZE_STEPS.length - 1 : nextIndex)
    }

    // Deferred rather than called inline, so the reset for a fresh run
    // happens from a callback (like the interval ticks that follow) instead
    // of synchronously in the effect body.
    const immediate = setTimeout(tick, 0)
    const interval = setInterval(tick, 200)
    return () => {
      clearTimeout(immediate)
      clearInterval(interval)
    }
  }, [active])

  return active ? stepIndex : 0
}
