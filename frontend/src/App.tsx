import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }

type ChatResponse = {
  session_id: string
  messages: Message[]
  awaiting_user: boolean
  missing_slots: string[]
  intent: string | null
  state?: string | null
  plan_review_score?: number | null
  execution_review_score?: number | null
}

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [awaitingUser, setAwaitingUser] = useState(false)
  const [missingSlots, setMissingSlots] = useState<string[]>([])
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem('ab_session_id')
    if (saved) setSessionId(saved)
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const appendAssistantFromResponse = (data: ChatResponse, reset: boolean = false) => {
    const assistants = (data.messages || []).filter(m => m.role === 'assistant')
    setSessionId(data.session_id)
    localStorage.setItem('ab_session_id', data.session_id)
    setAwaitingUser(!!data.awaiting_user)
    setMissingSlots(data.missing_slots || [])
    setMessages(prev => (reset ? assistants : (assistants.length ? [...prev, ...assistants] : prev)))
  }

  const send = useCallback(async () => {
    if (!input.trim()) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content, session_id: sessionId ?? undefined }),
      })
      const data: ChatResponse = await res.json()
      appendAssistantFromResponse(data)
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong.' }])
    } finally {
      setLoading(false)
    }
  }, [input, sessionId])

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const resetConversation = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'cancel', session_id: sessionId ?? undefined }),
      })
      const data: ChatResponse = await res.json()
      // Replace transcript with only the assistant reset message
      appendAssistantFromResponse(data, true)
    } catch (e) {
      setMessages([{ role: 'assistant', content: 'Conversation reset failed. Please refresh and try again.' }])
      setAwaitingUser(false)
      setMissingSlots([])
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  return (
    <div className="page">
      <div className="chat">
        <header>
          <h1>AgenticBank</h1>
          <span className="sub">Kind and empathetic assistant</span>
          <div className="spacer" />
          <button className="reset" onClick={resetConversation} disabled={loading}>Reset</button>
        </header>

        {awaitingUser && missingSlots.length > 0 && (
          <div className="awaiting">
            <span className="hint">Please provide:</span>
            <div className="chips">
              {missingSlots.map((s) => (
                <span key={s} className="chip">{s}</span>
              ))}
            </div>
          </div>
        )}

        <div className="messages" ref={listRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>{m.content}</div>
          ))}
          {loading && (
            <div className="msg assistant typing">Assistant is replying…</div>
          )}
        </div>

        <div className="composer">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={awaitingUser && missingSlots.length ? `Provide: ${missingSlots.join(', ')}` : 'Type your message...'}
            disabled={loading}
          />
          <button onClick={send} disabled={loading || !input.trim()}>{loading ? '...' : 'Send'}</button>
        </div>
      </div>
    </div>
  )
} 