import { useHealth } from '../hooks/useHealth'

/**
 * Phase 6: surfaces the backend's own Phase 17 monitoring (GET /health)
 * instead of leaving it API-only. Shows status plus the 24h alert count -
 * clicking through to see *which* alerts fired would need a new
 * GET /api/alerts endpoint that doesn't exist yet, so this stays a plain
 * status readout rather than a link to a detail view with nothing behind it.
 */
export function HealthStatus() {
  const health = useHealth()

  const ok = health.data?.status === 'ok'
  const alertCount = health.data?.status === 'ok' ? health.data.alerts_last_24h : null

  const label = health.isLoading
    ? 'checking backend…'
    : health.isError
      ? 'backend unreachable'
      : ok
        ? `backend ok · ${alertCount} alert${alertCount === 1 ? '' : 's'} (24h)`
        : 'backend degraded'

  return (
    <span
      className="flex items-center gap-1.5 font-mono text-xs text-ink-faint"
      title={
        health.isError && health.error instanceof Error ? health.error.message : label
      }
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          health.isLoading ? 'bg-ink-faint' : ok ? 'bg-buy' : 'bg-sell'
        }`}
      />
      {label}
    </span>
  )
}
