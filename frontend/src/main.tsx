import React from 'react'
import ReactDOM from 'react-dom/client'
import { Connection } from './components/Connection'
import { useMidi } from './hooks/useMidi'
import './styles.css'

function RawPrototype() {
  const { status, online, hits } = useMidi()
  const current = hits[0]
  return <main>
    <header><div><p className="eyebrow">TD-50X / LOCAL MIDI ENGINE</p><h1>Snare lab <span>v0.1</span></h1></div><p className="engine-state">Engine {online ? 'online' : 'offline'}<br /><small>Raw input checkpoint</small></p></header>
    <Connection status={status} online={online} />
    <section><div className="section-heading"><h2>Current hit</h2><span>{status?.hits_received ?? 0} hits captured</span></div>
      {!current ? <div className="empty"><h3>Waiting for a snare hit</h3><p>Connect the TD-50X to verify raw MIDI before enabling the experimental ring classifier.</p></div> : <dl className="inspector">
        <div><dt>Articulation</dt><dd>{current.articulation}</dd></div><div><dt>MIDI note · channel</dt><dd>{current.note_name} ({current.note}) · {current.channel}</dd></div>
        <div><dt>Velocity</dt><dd>{current.velocity}</dd></div><div><dt>CC16 · raw position signal</dt><dd>{current.position_cc16 ?? '—'}</dd></div>
        <div><dt>CC88 · raw prefix</dt><dd>{current.velocity_prefix_cc88 ?? '—'}</dd></div><div><dt>Estimated ring</dt><dd>Pending calibration stage</dd></div>
      </dl>}
      <p className="note">CC16 is a raw position signal. It does not describe exact physical distance or an X/Y position.</p>
    </section>
    <section><div className="section-heading"><h2>Hit history</h2><span>Newest first · last 50 hits</span></div>
      <div className="table-scroll"><table><thead><tr><th>Time</th><th>Articulation</th><th>Note</th><th>Ch</th><th>Velocity</th><th>CC16</th><th>CC88</th></tr></thead><tbody>
        {hits.map(hit => <tr key={`${hit.timestamp}-${hit.sequence}`}><td>{new Date(hit.timestamp).toLocaleTimeString([], {hour12: false})}</td><td>{hit.articulation}</td><td>{hit.note_name} / {hit.note}</td><td>{hit.channel}</td><td>{hit.velocity}</td><td>{hit.position_cc16 ?? '—'}</td><td>{hit.velocity_prefix_cc88 ?? '—'}</td></tr>)}
        {!hits.length && <tr><td colSpan={7} className="empty-row">Incoming normalized hits will appear here.</td></tr>}
      </tbody></table></div>
      {current && <details><summary>Latest normalized event · JSON</summary><pre>{JSON.stringify(current, null, 2)}</pre></details>}
    </section>
    <footer><span>PD-140DS → TD-50X → CoreMIDI → WebSocket</span><span>Queue drops: {status?.capture_queue_dropped ?? 0} capture / {status?.browser_events_dropped ?? 0} browser</span></footer>
  </main>
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><RawPrototype /></React.StrictMode>)
