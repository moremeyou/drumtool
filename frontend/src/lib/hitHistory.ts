import type { ConfirmedBatch, ConfirmedRing, HitEvent } from '../types/midi'

/** Current batch only. Completed/discarded rounds never appear in later copies. */
export class HitHistory {
  private pending: HitEvent[] = [] // chronological; the table shows only the latest 50
  private seen = new Set<string>()
  private cutoff = -Infinity

  add(hit: HitEvent) {
    const key = `${hit.timestamp}/${hit.sequence}`
    if (Date.parse(hit.timestamp) <= this.cutoff || this.seen.has(key)) return false
    this.seen.add(key)
    this.pending.push(hit)
    return true
  }

  mergeSnapshot(hits: HitEvent[]) {
    hits.forEach(hit => this.add(hit))
    this.pending.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp) || a.sequence - b.sequence)
  }

  get count() { return this.pending.length }
  get headCount() { return this.pending.filter(hit => hit.articulation === 'head').length }
  get recent() { return this.pending.slice(-50).reverse() }
  get hits() { return this.pending.slice().reverse() }

  private reset(now: number) {
    this.cutoff = Math.max(this.cutoff, now)
    this.pending = []
    this.seen.clear()
  }

  prepare(ring: ConfirmedRing, now = Date.now()) {
    if (!this.headCount) return null
    return { batch: { confirmed_ring: ring, hits: this.hits } as ConfirmedBatch, cutoff: now }
  }

  finish(round: { batch: ConfirmedBatch; cutoff: number }) {
    // Clipboard writing is asynchronous: keep hits that belong to the next round.
    const copied = new Set(round.batch.hits.map(hit => `${hit.timestamp}/${hit.sequence}`))
    this.cutoff = Math.max(this.cutoff, round.cutoff)
    this.pending = this.pending.filter(hit =>
      Date.parse(hit.timestamp) > this.cutoff && !copied.has(`${hit.timestamp}/${hit.sequence}`))
    this.seen = new Set(this.pending.map(hit => `${hit.timestamp}/${hit.sequence}`))
  }

  discard(now = Date.now()) {
    this.reset(now)
  }

}

function shareHits(hits: HitEvent[]) {
  const oldest = hits.reduce((time, hit) => Math.min(time, Date.parse(hit.timestamp)), Infinity)
  // Explicit allowlist keeps device names and absolute timestamps out of exports.
  return hits.map(hit => ({
    time_ms: Date.parse(hit.timestamp) - oldest,
    channel: hit.channel,
    note: hit.note,
    note_name: hit.note_name,
    articulation: hit.articulation,
    velocity: hit.velocity,
    position_cc16: hit.position_cc16,
    velocity_prefix_cc88: hit.velocity_prefix_cc88,
    estimated_ring: hit.estimated_ring,
    confidence: hit.confidence,
  }))
}

export function exportHistory(history: HitHistory, batch?: ConfirmedBatch) {
  return {
    order: 'newest_first',
    label_applies_to: 'head_hits',
    confirmed_batches: batch ? [{ confirmed_ring: batch.confirmed_ring, hits: shareHits(batch.hits) }] : [],
    hits: batch ? [] : shareHits(history.hits),
  }
}

/** Clear only after a successful copy. Failure leaves the current batch intact. */
export async function copyRingBatch(
  history: HitHistory,
  ring: ConfirmedRing,
  writeText: (text: string) => Promise<void>,
  now = Date.now(),
) {
  const round = history.prepare(ring, now)
  if (!round) return null
  await writeText(JSON.stringify(exportHistory(history, round.batch), null, 2))
  history.finish(round)
  return round.batch
}
