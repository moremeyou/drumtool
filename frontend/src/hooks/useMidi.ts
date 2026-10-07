import { useEffect, useRef, useState } from 'react'
import type { EngineMessage, EngineStatus, HitEvent } from '../types/midi'

export function useMidi() {
  const [status, setStatus] = useState<EngineStatus | null>(null)
  const [online, setOnline] = useState(false)
  const [hits, setHits] = useState<HitEvent[]>([])
  const [head, setHead] = useState<HitEvent | null>(null)
  const buffer = useRef<HitEvent[]>([])
  const pendingHead = useRef<HitEvent | null>(null)

  useEffect(() => {
    let stopped = false
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout>
    let frame = 0
    function flush() {
      frame = 0
      setHits([...buffer.current])
      if (pendingHead.current) setHead(pendingHead.current)
      pendingHead.current = null
    }
    function connect() {
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/events`)
      socket.onopen = () => setOnline(true)
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as EngineMessage
        if (data.type === 'snapshot') {
          setStatus(data.status)
          buffer.current = data.hits.slice(0, 50)
          pendingHead.current = null
          setHead(null) // Historical hits should never pulse on reconnect.
        } else if (data.type === 'status') {
          setStatus(data.status)
          return
        } else {
          buffer.current = [data.hit, ...buffer.current].slice(0, 50)
          if (data.hit.articulation === 'head') pendingHead.current = data.hit
        }
        if (!frame) frame = requestAnimationFrame(flush)
      }
      socket.onclose = () => {
        setOnline(false)
        if (!stopped) retry = setTimeout(connect, 1200)
      }
      socket.onerror = () => socket?.close()
    }
    connect()
    return () => { stopped = true; clearTimeout(retry); cancelAnimationFrame(frame); socket?.close() }
  }, [])
  return { status, online, hits, head }
}
