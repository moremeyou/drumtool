import { useEffect, useRef, useState } from 'react'
import type { exportHistory } from '../lib/hitHistory'

type Props = {
  pendingCount: number
  confirming: boolean
  getPayload: () => ReturnType<typeof exportHistory>
  onClear: () => void
}

export function HistoryActions({ pendingCount, confirming, getPayload, onClear }: Props) {
  const [message, setMessage] = useState('')
  const [copying, setCopying] = useState(false)
  const reset = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(reset.current), [])

  function announce(text: string) {
    clearTimeout(reset.current)
    setMessage(text)
    reset.current = setTimeout(() => setMessage(''), 5000)
  }

  async function copyHistory() {
    setCopying(true)
    const payload = getPayload()
    const count = payload.hits.length
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      announce(`Copied ${count} unconfirmed hits. Click a ring to copy with its label and clear.`)
    } catch {
      announce('Copy failed. Allow clipboard access in your browser, then try again.')
    } finally {
      setCopying(false)
    }
  }

  return <div className="history-actions">
    <button type="button" onClick={() => void copyHistory()} disabled={!pendingCount || copying || confirming}
      title="Copy only the current hits without a confirmed ring label">
      {copying ? 'Copying…' : 'Copy history'}
    </button>
    <button type="button" onClick={() => { onClear(); announce('Current batch discarded. Ready for a fresh test.')}}
      disabled={!pendingCount || copying || confirming} title="Discard the current batch as a mistake">
      Clear history
    </button>
    <span role="status" aria-live="polite">{message}</span>
  </div>
}
