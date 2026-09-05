import { ANALYZE_STEPS } from '../hooks/useSimulatedProgress'

export function AnalyzeProgress({ currentStep }: { currentStep: number }) {
  return (
    <ol className="flex flex-col gap-2" aria-label="Analysis progress" aria-live="polite">
      {ANALYZE_STEPS.map((step, i) => {
        const state = i < currentStep ? 'done' : i === currentStep ? 'active' : 'pending'
        return (
          <li key={step.label} className="flex items-center gap-3">
            <span
              className={`flex h-5 w-5 flex-none items-center justify-center rounded-full text-xs ${
                state === 'done'
                  ? 'bg-buy text-accent-contrast'
                  : state === 'active'
                    ? 'bg-accent text-accent-contrast motion-safe:animate-pulse'
                    : 'bg-accent-soft text-ink-faint'
              }`}
            >
              {state === 'done' ? '✓' : i + 1}
            </span>
            <span
              className={`text-sm ${state === 'pending' ? 'text-ink-faint' : 'text-ink'}`}
            >
              {step.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
