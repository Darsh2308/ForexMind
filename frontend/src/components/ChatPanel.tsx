import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useChat } from '../hooks/useChat'

export function ChatPanel({ recommendationId }: { recommendationId: number | null }) {
  const chat = useChat(recommendationId)
  const [input, setInput] = useState('')
  const hasGroundedCall = chat.groundedRecommendationId !== null

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-line bg-raised p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
          {hasGroundedCall ? 'Ask about this call' : 'Ask ForexMind'}
        </h2>
        {hasGroundedCall && (
          <Link
            to={`/history/${chat.groundedRecommendationId}`}
            className="font-mono text-xs text-accent hover:underline"
          >
            View full analysis &rarr;
          </Link>
        )}
      </div>

      {chat.messages.length === 0 && (
        <p className="text-sm text-ink-faint">
          {hasGroundedCall
            ? 'Ask why this call was made, what a specific indicator means, or whether a level still matters — answers are grounded in this call’s own evidence, not invented.'
            : 'Ask "should I buy or sell EUR/USD right now?" — if there’s no recent call to ground the answer in, a fresh analysis runs first.'}
        </p>
      )}

      {chat.messages.length > 0 && (
        <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {chat.messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                m.role === 'user'
                  ? 'ml-auto bg-accent text-accent-contrast'
                  : 'mr-auto bg-accent-soft text-ink'
              }`}
            >
              {m.content}
            </div>
          ))}
          {chat.isPending && (
            <div className="mr-auto rounded-lg bg-accent-soft px-3 py-2 text-sm text-ink-faint">
              {hasGroundedCall ? 'Thinking…' : 'Running a fresh analysis…'}
            </div>
          )}
        </div>
      )}

      {!chat.isPending && chat.lastTriggeredNewAnalysis && (
        <p className="text-xs text-ink-faint">
          Ran a fresh analysis to answer that.
          {hasGroundedCall && (
            <>
              {' '}
              <Link
                to={`/history/${chat.groundedRecommendationId}`}
                className="text-accent hover:underline"
              >
                View it &rarr;
              </Link>
            </>
          )}
        </p>
      )}

      {chat.error && (
        <p className="rounded-md bg-sell-soft px-3 py-2 text-sm text-sell">
          {chat.error instanceof ApiError
            ? chat.error.message
            : 'Something unexpected went wrong.'}
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          chat.sendMessage(input)
          setInput('')
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={hasGroundedCall ? 'Why did you decide this?' : 'Should I buy or sell right now?'}
          disabled={chat.isPending}
          className="flex-1 rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={chat.isPending || !input.trim()}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-contrast transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </section>
  )
}
