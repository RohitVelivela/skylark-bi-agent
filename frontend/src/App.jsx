import React, { useState, useRef } from 'react'
import SidePanel from './components/SidePanel'
import ChatArea from './components/ChatArea'
import TracePanel from './components/TracePanel'

export default function App() {
  const [messages, setMessages]   = useState([])
  const [traces, setTraces]       = useState([])
  const [input, setInput]         = useState('')
  const [streaming, setStreaming] = useState(false)
  const historyRef = useRef([])

  const clearConversation = () => {
    setMessages([])
    setTraces([])
    historyRef.current = []
  }

  const sendMessage = async (text) => {
    const msgText = text.trim()
    if (!msgText || streaming) return

    setStreaming(true)
    setInput('')
    setTraces([]) // fresh traces per turn

    const userId      = `u-${Date.now()}`
    const assistantId = `a-${Date.now()}`

    setMessages(prev => [
      ...prev,
      { id: userId,      role: 'user',      content: msgText },
      { id: assistantId, role: 'assistant', content: '', pending: true },
    ])

    let finalContent   = ''
    let doneSignal     = false

    try {
      const res = await fetch('/api/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message: msgText, history: historyRef.current }),
      })

      if (!res.ok) throw new Error(`Server error ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (!doneSignal) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

            switch (event.type) {
              case 'tool_call':
                setTraces(prev => [
                  ...prev,
                  {
                    id:       `tc-${Date.now()}-${Math.random()}`,
                    type:     'call',
                    name:     event.name,
                    args:     event.args ?? {},
                    resolved: false,
                  },
                ])
                break

              case 'tool_result':
                setTraces(prev => {
                  let patched = false
                  return prev.map(t => {
                    if (!patched && t.name === event.name && t.type === 'call' && !t.resolved) {
                      patched = true
                      return {
                        ...t,
                        resolved:    true,
                        itemCount:   event.item_count,
                        dataQuality: event.data_quality,
                      }
                    }
                    return t
                  })
                })
                break

              case 'message':
                finalContent = event.content
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId
                      ? { ...m, content: event.content, pending: false }
                      : m
                  )
                )
                break

              case 'error':
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId
                      ? { ...m, content: `**Error:** ${event.message}`, pending: false, error: true }
                      : m
                  )
                )
                break

              case 'done':
                doneSignal = true
                break

              default:
                break
            }
          } catch {
            // skip malformed SSE frames
          }

          if (doneSignal) break
        }
      }
    } catch (err) {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, content: `**Connection error:** ${err.message}`, pending: false, error: true }
            : m
        )
      )
    } finally {
      setStreaming(false)
      // ensure no message stays pending (edge-case guard)
      setMessages(prev => prev.map(m => (m.pending ? { ...m, pending: false } : m)))

      if (finalContent) {
        historyRef.current = [
          ...historyRef.current,
          { role: 'user',      content: msgText      },
          { role: 'assistant', content: finalContent },
        ].slice(-40)
      }
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#080d1a]">
      <SidePanel onSend={sendMessage} onClear={clearConversation} streaming={streaming} />
      <ChatArea
        messages={messages}
        input={input}
        setInput={setInput}
        onSend={sendMessage}
        streaming={streaming}
      />
      <TracePanel traces={traces} />
    </div>
  )
}
