import type { CSSProperties } from 'react'
import type { ConfirmedRing, HitEvent, Ring } from '../types/midi'

const zones: { ring: Exclude<Ring, 'UNKNOWN'>; radius: number; labelY: number }[] = [
  { ring: 'OUTER', radius: 176, labelY: 49 },
  { ring: 'MIDDLE', radius: 132, labelY: 93 },
  { ring: 'INNER', radius: 88, labelY: 137 },
  { ring: 'CENTER', radius: 44, labelY: 205 },
]

export function Snare({ hit, pendingHeadCount, confirming, onConfirm, feedback }: {
  hit: HitEvent | null
  pendingHeadCount: number
  confirming: boolean
  onConfirm: (ring: ConfirmedRing) => void
  feedback: string
}) {
  const canConfirm = pendingHeadCount > 0 && !confirming
  const zone = zones.find(zone => zone.ring === hit?.estimated_ring)
  const uncertain = hit !== null && hit.confidence < .7
  const confidence = hit ? `${Math.round(hit.confidence * 100)}%` : '—'
  const label = zone ? `${zone.ring}${uncertain ? ' ?' : ''}` : 'UNKNOWN'

  return <section className="snare-panel">
    <div className="section-heading"><h2>Snare · estimated ring</h2><span>Experimental · K = 5 · CC16</span></div>
    <div className="snare-layout">
      <svg className="snare" viewBox="0 0 400 400" role="group" aria-label={`Click a ring to copy and clear the current batch. ${hit ? `Latest head estimate: ${label}, confidence ${confidence}.` : 'Waiting for a head hit.'}`}>
        {zones.map(({ ring, radius }) => <circle key={ring} cx="200" cy="200" r={radius}
          className={`snare-zone zone-${ring.toLowerCase()} ${canConfirm ? 'can-confirm' : ''}`}
          role="button" tabIndex={canConfirm ? 0 : -1} aria-disabled={!canConfirm}
          aria-label={`Copy ${pendingHeadCount} head hits as ${ring} and clear`}
          onClick={() => { if (canConfirm) onConfirm(ring) }}
          onKeyDown={event => {
            if (canConfirm && (event.key === 'Enter' || event.key === ' ')) {
              event.preventDefault()
              onConfirm(ring)
            }
          }}><title>{`Copy this batch as ${ring} and clear`}</title></circle>)}
        {zone && hit && <circle key={`${hit.timestamp}-${hit.sequence}`} cx="200" cy="200"
          r={zone.ring === 'CENTER' ? 44 : zone.radius - 22}
          className={`snare-pulse ${zone.ring === 'CENTER' ? 'pulse-center' : 'pulse-ring'}`}
          style={{ '--pulse-intensity': .2 + .8 * hit.velocity / 127 } as CSSProperties} />}
        {zones.map(({ ring, labelY }) => <text key={ring} x="200" y={labelY} textAnchor="middle" className="snare-label">{ring}</text>)}
      </svg>
      <div className="ring-readout">
        <p className="eyebrow">LATEST HEAD HIT</p>
        <p className={`ring-name ${uncertain ? 'uncertain' : ''}`}>{hit ? label : 'WAITING'}</p>
        <dl>
          <div><dt>Confidence</dt><dd>{zone ? confidence : '—'}</dd></div>
          <div><dt>Raw position signal · CC16</dt><dd>{hit?.position_cc16 ?? '—'}</dd></div>
          <div><dt>Velocity</dt><dd>{hit?.velocity ?? '—'}</dd></div>
        </dl>
        <p className="ring-explanation">{hit && !zone ? 'No recent position signal: this hit has no ring estimate.' : 'Compare the highlighted zone with where you struck. Ring estimates use CC16; velocity controls pulse brightness.'}</p>
        <p className="ring-explanation">Confidence is a neighbour-based heuristic, not a probability of physical location.</p>
        <p className="ring-instruction">{pendingHeadCount ? `Click where you actually struck to copy ${pendingHeadCount} head ${pendingHeadCount === 1 ? 'hit' : 'hits'} with that label, then clear for a fresh batch.` : 'Play one or more hits in a zone, then click that ring to copy and clear.'}</p>
        <p className="ring-explanation">Made a mistake? Clear history discards the current batch.</p>
        <p className="batch-feedback" role="status">{feedback}</p>
      </div>
    </div>
    <p className="note">Estimated radial zone only. Ring sizes are illustrative; no exact distance or X/Y position is inferred.</p>
  </section>
}
