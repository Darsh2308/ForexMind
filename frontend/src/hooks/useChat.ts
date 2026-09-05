import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { postChat } from '../api/endpoints'
import type { ChatMessage } from '../types/api'

const MAX_HISTORY_SENT = 10

/**
 * Holds one grounded conversation. State lives only in this component tree
 * (no persistence, no chat-history table on the backend) - a page refresh
 * starts a fresh conversation.
 *
 * `recommendationId` may be null - the backend then grounds itself on the
 * latest recommendation, running a fresh analysis first if none exists yet
 * or it's stale (see /api/chat's "cold chat" mode). Until the first reply
 * comes back, the effective id tracks the `recommendationId` prop directly
 * (so a conversation started before history has loaded still picks up the
 * latest call once it does); after that, it tracks whichever recommendation
 * the most recent reply actually used, so follow-ups stay grounded on that
 * same result even if a newer call appears in the background.
 */
export function useChat(recommendationId: number | null) {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [groundedId, setGroundedId] = useState<number | null>(recommendationId)
  const effectiveId = messages.length === 0 ? recommendationId : groundedId

  const mutation = useMutation({
    mutationFn: (message: string) =>
      postChat(effectiveId, message, messages.slice(-MAX_HISTORY_SENT)),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      setGroundedId(data.recommendation_id)
      if (data.triggered_new_analysis) {
        // A fresh call may have just been saved - refresh the KPI/recent
        // activity data that reads from /api/history.
        void queryClient.invalidateQueries({ queryKey: ['history'] })
      }
    },
  })

  function sendMessage(message: string) {
    const trimmed = message.trim()
    if (!trimmed) return
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])
    mutation.mutate(trimmed)
  }

  return {
    messages,
    sendMessage,
    isPending: mutation.isPending,
    error: mutation.error,
    groundedRecommendationId: effectiveId,
    lastTriggeredNewAnalysis: mutation.data?.triggered_new_analysis ?? false,
  }
}
