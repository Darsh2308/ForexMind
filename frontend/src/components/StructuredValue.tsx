import { Fragment, useState } from 'react'

const ARRAY_PREVIEW_COUNT = 8

/**
 * Renders an arbitrary JSON-ish value (one MarketContextSection) as a
 * readable label/value tree instead of a raw JSON dump - the 11 analysis
 * agents each have their own multi-timeframe nested shape (see
 * StructuredValue's use in AgentSectionPanel), so this recurses generically
 * rather than hand-building bespoke UI per agent.
 */

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bEma\b/, 'EMA')
    .replace(/\bSma\b/, 'SMA')
    .replace(/\bRsi\b/, 'RSI')
    .replace(/\bAtr\b/, 'ATR')
    .replace(/\bMacd\b/, 'MACD')
    .replace(/\bBb\b/, 'BB')
    .replace(/\bFvg\b/, 'FVG')
    .replace(/\bFvgs\b/, 'FVGs')
    .replace(/\bSmc\b/, 'SMC')
    .replace(/\bOte\b/, 'OTE')
}

function formatPrimitive(value: string | number | boolean): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return String(value)
    const abs = Math.abs(value)
    if (abs <= 1) return value.toFixed(2)
    if (abs < 10) return value.toFixed(5)
    return value.toFixed(2)
  }
  return value
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

function ObjectArray({ items, depth }: { items: unknown[]; depth: number }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? items : items.slice(0, ARRAY_PREVIEW_COUNT)
  const hiddenCount = items.length - visible.length

  return (
    <div className="flex flex-col gap-2">
      {visible.map((item, i) => (
        <div key={i} className="rounded-md border border-line bg-paper px-3 py-2 text-sm">
          <StructuredValue value={item} depth={depth + 1} />
        </div>
      ))}
      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="w-fit font-mono text-xs text-accent underline-offset-2 hover:underline"
        >
          Show {hiddenCount} more
        </button>
      )}
    </div>
  )
}

export function StructuredValue({
  value,
  depth = 0,
}: {
  value: unknown
  depth?: number
}) {
  if (isEmpty(value)) {
    return <span className="text-ink-faint">—</span>
  }

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return <span className="text-ink tabular-nums">{formatPrimitive(value)}</span>
  }

  if (Array.isArray(value)) {
    const allPrimitive = value.every((v) => typeof v !== 'object' || v === null)
    if (allPrimitive) {
      return (
        <span className="text-ink">
          {value.map((v) => formatPrimitive(v as string | number | boolean)).join(', ')}
        </span>
      )
    }
    // SMC alone can surface dozens of order blocks/FVGs/liquidity pools per
    // timeframe on a real run - render unbounded and the page becomes an
    // effectively infinite scroll. Show a preview, let the reader ask for
    // the rest instead of always paying for it.
    return <ObjectArray items={value} depth={depth} />
  }

  // Plain object.
  const entries = Object.entries(value as Record<string, unknown>)
  return (
    <dl
      className={`grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 ${depth > 0 ? 'text-[13px]' : 'text-sm'}`}
    >
      {entries.map(([key, v]) => {
        const nested = v !== null && typeof v === 'object' && !isEmpty(v)
        return (
          <Fragment key={key}>
            <dt
              className={`font-mono text-xs whitespace-nowrap text-ink-faint uppercase ${nested ? 'pt-1' : ''}`}
            >
              {humanizeKey(key)}
            </dt>
            <dd className={nested ? 'rounded-md border-l-2 border-line pl-3' : ''}>
              <StructuredValue value={v} depth={depth + 1} />
            </dd>
          </Fragment>
        )
      })}
    </dl>
  )
}
