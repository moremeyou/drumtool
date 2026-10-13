import { useEffect, useRef, useState } from 'react'
import { copyRingBatch, exportHistory, HitHistory } from '../lib/hitHistory'
import type { ConfirmedRing, EngineMessage, EngineStatus, HitEvent } from '../types/midi'

export function useMidi() {
  const [status, setStatus] = useState<EngineStatus | null>(null)
  const [online, setOnline] = useState(false)
  const [hits, setHits] = useState<HitEvent[]>([])
  const [head, setHead] = useState<HitEvent | null>(null)
  const [batchCount, setBatchCount] = useState(0)
  const [headCount, setHeadCount] = useState(0)
  const [confirming, setConfirming] = useState(false)
  const confirmationBusy = useRef(false)
  const [feedback, setFeedback] = useState('')
  const history = useRef(new HitHistory())
  const pendingHead = useRef<HitEvent | null>(null)

  function publishHistory() {
    setHits(history.current.recent)
    setBatchCount(history.current.count)
    setHeadCount(history.current.headCount)
  }

  function resetDisplay() {
    pendingHead.current = null
    setHead(null)
    publishHistory()
  }

  function clearHistory() {
    if (confirmationBusy.current) return
    history.current.discard()
    resetDisplay()
    setFeedback('Current batch discarded as a mistake. Ready for new hits.')
  }

  async function confirmRing(ring: ConfirmedRing) {
    if (confirmationBusy.current || !history.current.headCount) return
    confirmationBusy.current = true
    setConfirming(true)
    setFeedback(`Copying ${ring} batch…`)
    try {
      const batch = await copyRingBatch(history.current, ring, text => navigator.clipboard.writeText(text))
      if (!batch) return
      if (!history.current.headCount) {
        pendingHead.current = null
        setHead(null)
      }
      publishHistory()
      const count = batch.hits.filter(hit => hit.articulation === 'head').length
      setFeedback(`Copied ${ring}: ${count} head ${count === 1 ? 'hit' : 'hits'}. Paste it before copying the next round.`)
    } catch {
      setFeedback('Copy failed; hits kept. Allow clipboard access, then click the ring again.')
    } finally {
      confirmationBusy.current = false
      setConfirming(false)
    }
  }

  useEffect(() => {
    let stopped = false
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout>
    let frame = 0
    function flush() {
      frame = 0
      publishHistory()
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
          history.current.mergeSnapshot(data.hits)
          pendingHead.current = null
          setHead(null) // Historical hits should never pulse on reconnect.
        } else if (data.type === 'status') {
          setStatus(data.status)
          return
        } else {
          if (!history.current.add(data.hit)) return
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
  return {
    status, online, hits, head, batchCount, headCount, confirming, feedback,
    clearHistory, confirmRing, copyPayload: () => exportHistory(history.current),
  }
}
