import type { MarketContextSection } from '../types/api'
import { StructuredValue } from './StructuredValue'

export function AgentSectionPanel({
  title,
  advisory,
  data,
  defaultOpen = false,
}: {
  title: string
  advisory?: boolean
  data: MarketContextSection
  defaultOpen?: boolean
}) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-lg border border-line bg-raised open:pb-4"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 select-none">
        <span
          className="text-ink-faint transition-transform group-open:rotate-90"
          aria-hidden="true"
        >
          ▸
        </span>
        <h2 className="font-medium text-ink">{title}</h2>
        {advisory && (
          <span className="rounded-md bg-accent-soft px-2 py-0.5 font-mono text-[10px] tracking-wide text-ink-faint uppercase">
            Advisory only
          </span>
        )}
      </summary>
      <div className="border-t border-line px-4 pt-3">
        <StructuredValue value={data} />
      </div>
    </details>
  )
}
