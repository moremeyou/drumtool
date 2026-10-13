import React from 'react'
import ReactDOM from 'react-dom/client'
import { Connection } from './components/Connection'
import { HistoryActions } from './components/HistoryActions'
import { Snare } from './components/Snare'
import { useMidi } from './hooks/useMidi'
import './styles.css'

function Prototype() {
  const { status, online, hits, head, batchCount, headCount, confirming, feedback, clearHistory, confirmRing, copyPayload } = useMidi()
  const current = hits[0]
  return <main>
    <header><div><p className="eyebrow">TD-50X / LOCAL MIDI ENGINE</p><h1>Snare lab <span>v0.1</span></h1></div><p className="engine-state">Engine {online ? 'online' : 'offline'}<br /><small>Experimental ring estimates</small></p></header>
    <Connection status={status} online={online} />
    <Snare hit={head} pendingHeadCount={headCount} confirming={confirming} onConfirm={confirmRing} feedback={feedback} />
    <section><div className="section-heading"><h2>Current hit</h2><span>{status?.hits_received ?? 0} hits captured</span></div>
      {!current ? <div className="empty"><h3>Waiting for a snare hit</h3><p>{online && status?.connected ? 'Strike the snare to inspect incoming MIDI values.' : 'Connect the TD-50X to inspect incoming MIDI values.'}</p></div> : <dl className="inspector">
        <div><dt>Articulation</dt><dd>{current.articulation}</dd></div><div><dt>MIDI note · channel</dt><dd>{current.note_name} ({current.note}) · {current.channel}</dd></div>
        <div><dt>Velocity</dt><dd>{current.velocity}</dd></div><div><dt>CC16 · raw position signal</dt><dd>{current.position_cc16 ?? '—'}</dd></div>
        <div><dt>CC88 · raw prefix</dt><dd>{current.velocity_prefix_cc88 ?? '—'}</dd></div>
        <div><dt>Estimated ring · confidence</dt><dd>{current.estimated_ring}{current.estimated_ring !== 'UNKNOWN' && current.confidence < .7 ? ' ?' : ''} · {Math.round(current.confidence * 100)}%</dd></div>
      </dl>}
      <p className="note">CC16 is a raw position signal. It does not describe exact physical distance or an X/Y position.</p>
    </section>
    <section><div className="section-heading"><h2>Current batch · {batchCount} hits</h2><span>Newest first · showing {hits.length} of {batchCount}</span></div>
      <HistoryActions pendingCount={batchCount} confirming={confirming} getPayload={copyPayload} onClear={clearHistory} />
      <p className="batch-help">Click the actual ring to copy this batch with its label, then clear it. Paste before the next ring click.</p>
      <div className="table-scroll"><table><thead><tr><th>Time</th><th>Articulation</th><th>Note</th><th>Ch</th><th>Velocity</th><th>CC16</th><th>CC88</th><th>Estimated ring</th><th>Confidence</th></tr></thead><tbody>
        {hits.map(hit => <tr key={`${hit.timestamp}-${hit.sequence}`}><td>{new Date(hit.timestamp).toLocaleTimeString([], {hour12: false})}</td><td>{hit.articulation}</td><td>{hit.note_name} / {hit.note}</td><td>{hit.channel}</td><td>{hit.velocity}</td><td>{hit.position_cc16 ?? '—'}</td><td>{hit.velocity_prefix_cc88 ?? '—'}</td><td>{hit.estimated_ring}{hit.estimated_ring !== 'UNKNOWN' && hit.confidence < .7 ? ' ?' : ''}</td><td>{Math.round(hit.confidence * 100)}%</td></tr>)}
        {!hits.length && <tr><td colSpan={9} className="empty-row">Incoming normalized hits will appear here.</td></tr>}
      </tbody></table></div>
      {current && <details><summary>Latest normalized event · JSON</summary><pre>{JSON.stringify(current, null, 2)}</pre></details>}
    </section>
    <footer><span>PD-140DS → TD-50X → CoreMIDI → WebSocket</span><span>Queue drops: {status?.capture_queue_dropped ?? 0} capture / {status?.browser_events_dropped ?? 0} browser</span></footer>
  </main>
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Prototype /></React.StrictMode>)
