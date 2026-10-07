import { useCallback, useEffect, useState } from 'react'
import type { EngineStatus } from '../types/midi'

export function Connection({ status, online }: { status: EngineStatus | null; online: boolean }) {
  const [devices, setDevices] = useState<string[]>([])
  const [selected, setSelected] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const refresh = useCallback(async () => {
    try {
      const response = await fetch('/api/midi/devices')
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not enumerate MIDI inputs')
      setDevices(data.devices)
      setSelected(previous => data.devices.includes(previous) ? previous : (data.devices.find((name: string) => name.toUpperCase().includes('TD-50X')) ?? data.devices[0] ?? ''))
      setError(null)
    } catch (e) { setError(e instanceof Error ? e.message : 'Device lookup failed') }
  }, [])
  useEffect(() => { if (online) void refresh() }, [online, refresh])
  async function connect() {
    setBusy(true)
    try {
      const response = await fetch('/api/midi/connect', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({device: selected})})
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Connection failed')
      setError(null)
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed') }
    finally { setBusy(false) }
  }
  return <section className="connection">
    <div><h2>Connection</h2><p><span className={`status-dot ${online && status?.connected ? 'connected' : ''}`} />MIDI: {status?.device ?? 'No input selected'} · {online && status?.connected ? 'Connected' : 'Disconnected'}</p></div>
    <div className="controls"><label htmlFor="source">MIDI source</label><select id="source" value={selected} onChange={event => setSelected(event.target.value)} disabled={!online || busy}>
      {!devices.length && <option value="">No MIDI inputs found</option>}
      {devices.map(device => <option key={device}>{device}</option>)}
    </select><button onClick={() => void refresh()} disabled={!online || busy}>Refresh sources</button><button className="primary" onClick={() => void connect()} disabled={!online || !selected || busy}>{busy ? 'Connecting…' : 'Connect'}</button></div>
    {(error || status?.error) && <p className="error" role="alert">{error || status?.error}</p>}
  </section>
}
