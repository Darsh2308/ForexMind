/** A single pulsing placeholder bar, sized to approximate the real content
 * that will replace it - the point is avoiding layout shift when data
 * arrives, not just showing "something is loading." Respects
 * prefers-reduced-motion via Tailwind's motion-safe: variant. */
export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`rounded bg-line/70 motion-safe:animate-pulse ${className}`}
    />
  )
}
