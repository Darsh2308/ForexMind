type Tone = 'supporting' | 'conflicting' | 'neutral'

const markClass: Record<Tone, string> = {
  supporting: 'bg-buy',
  conflicting: 'bg-sell',
  neutral: 'bg-ink-faint',
}

export function EvidenceList({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: Tone
}) {
  if (items.length === 0) return null

  return (
    <div>
      <h3 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
        {title}
      </h3>
      <ul className="mt-1.5 flex flex-col gap-1">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm text-ink">
            <span
              className={`mt-2 h-1.5 w-1.5 flex-none rounded-full ${markClass[tone]}`}
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
