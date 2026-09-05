import type { LlmProvider } from '../types/api'

const copy: Record<LlmProvider, { label: string; tone: string }> = {
  groq: { label: 'Answered by Groq', tone: 'bg-buy-soft text-buy' },
  ollama: { label: 'Answered by local Ollama fallback', tone: 'bg-wait-soft text-wait' },
  fallback: {
    label: 'No LLM reachable — hard-coded fallback',
    tone: 'bg-sell-soft text-sell',
  },
}

export function LlmProviderBadge({
  provider,
}: {
  provider: LlmProvider | null | undefined
}) {
  if (!provider) return null
  const { label, tone } = copy[provider]

  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-1 font-mono text-xs ${tone}`}
      title="Which backend produced this recommendation — matters for trust, not just debugging."
    >
      {label}
    </span>
  )
}
