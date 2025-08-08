import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }

type ChatResponse = {
  session_id: string
  messages: Message[]
  awaiting_user: boolean
  missing_slots: string[]
  intent: string | null
}

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem('ab_session_id')
    if (saved) setSessionId(saved)
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

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
      setSessionId(data.session_id)
      localStorage.setItem('ab_session_id', data.session_id)
      setMessages(prev => {
        // server echoes the user message and assistant; avoid double-adding user if we already added
        const assistant = data.messages.find(m => m.role === 'assistant')
        return assistant ? [...prev, assistant] : prev
      })
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

  return (
    <div className="page">
      <div className="chat">
        <header>
          <h1>AgenticBank</h1>
          <span className="sub">Kind and empathetic assistant</span>
        </header>
        <div className="messages" ref={listRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>{m.content}</div>
          ))}
        </div>
        <div className="composer">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button onClick={send} disabled={loading || !input.trim()}>{loading ? '...' : 'Send'}</button>
        </div>
      </div>
    </div>
  )
} 