import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

// Compile the pure state module in memory; no browser, DOM or screen access.
const source = readFileSync(new URL('../src/lib/hitHistory.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const { HitHistory, exportHistory, copyRingBatch } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const hit = (sequence, time = sequence * 10, articulation = 'head') => ({
  sequence, timestamp: new Date(time).toISOString(), device: 'Test MIDI',
  channel: 10, note: articulation === 'head' ? 38 : 40, note_name: articulation === 'head' ? 'D1' : 'E1',
  articulation, velocity: 64, position_cc16: 50, velocity_prefix_cc88: 0,
  estimated_ring: 'INNER', confidence: .6,
})
const clipboard = () => {
  const copies = []
  return { copies, write: async text => { copies.push(JSON.parse(text)) } }
}

test('ring click copies the current labelled round before clearing it', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  history.add(hit(2))
  const copies = []
  const batch = await copyRingBatch(history, 'OUTER', async text => {
    assert.equal(history.count, 2)
    copies.push(JSON.parse(text))
  }, 25)
  assert.equal(batch.confirmed_ring, 'OUTER')
  assert.deepEqual(batch.hits.map(hit => hit.sequence), [2, 1])
  assert.equal(copies[0].confirmed_batches.length, 1)
  assert.equal(copies[0].confirmed_batches[0].confirmed_ring, 'OUTER')
  assert.equal(copies[0].confirmed_batches[0].hits.length, 2)
  assert.deepEqual(copies[0].hits, [])
  assert.equal(history.count, 0)
  assert.deepEqual(exportHistory(history).confirmed_batches, [])
})

test('a later copy never includes a previous completed round', async () => {
  const history = new HitHistory()
  const clip = clipboard()
  history.add(hit(1))
  await copyRingBatch(history, 'CENTER', clip.write, 15)
  history.add(hit(2))
  history.add(hit(3))
  await copyRingBatch(history, 'INNER', clip.write, 35)
  assert.deepEqual(clip.copies.map(copy => copy.confirmed_batches.map(batch => batch.confirmed_ring)), [['CENTER'], ['INNER']])
  assert.equal(clip.copies[1].confirmed_batches[0].hits.length, 2)
  assert.deepEqual(exportHistory(history).hits, [])
})

test('clipboard failure preserves the batch for retry', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  await assert.rejects(copyRingBatch(history, 'CENTER', async () => { throw Error('Clipboard denied') }, 15))
  assert.equal(history.count, 1)
  history.mergeSnapshot([hit(2), hit(1)])
  assert.equal(history.count, 2)
  const clip = clipboard()
  await copyRingBatch(history, 'CENTER', clip.write, 25)
  assert.equal(clip.copies[0].confirmed_batches[0].hits.length, 2)
  assert.equal(history.count, 0)
})

test('hits arriving during a slow clipboard write belong to the next round', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  let complete
  let copied
  const writing = copyRingBatch(history, 'CENTER', text => {
    copied = JSON.parse(text)
    return new Promise(resolve => { complete = resolve })
  }, 15)
  history.add(hit(2))
  assert.equal(history.count, 2)
  complete()
  await writing
  assert.equal(copied.confirmed_batches[0].hits.length, 1)
  assert.deepEqual(history.hits.map(hit => hit.sequence), [2])
  const clip = clipboard()
  await copyRingBatch(history, 'OUTER', clip.write, 25)
  assert.equal(clip.copies[0].confirmed_batches[0].hits.length, 1)
})

test('clear discards mistakes and copies only hits from the fresh round', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  history.discard(15)
  history.add(hit(2))
  assert.equal(exportHistory(history).hits.length, 1)
  const clip = clipboard()
  await copyRingBatch(history, 'MIDDLE', clip.write, 25)
  assert.equal(clip.copies[0].confirmed_batches[0].hits.length, 1)
  assert.equal(history.count, 0)
})

test('empty, repeated and rim-only clicks leave the clipboard untouched', async () => {
  const history = new HitHistory()
  const clip = clipboard()
  assert.equal(await copyRingBatch(history, 'CENTER', clip.write, 5), null)
  history.add(hit(1))
  await copyRingBatch(history, 'CENTER', clip.write, 15)
  assert.equal(await copyRingBatch(history, 'OUTER', clip.write, 16), null)
  history.add(hit(2, 20, 'rim'))
  assert.equal(await copyRingBatch(history, 'INNER', clip.write, 25), null)
  assert.equal(clip.copies.length, 1)
  assert.equal(history.count, 1)
})

test('reconnect cannot resurrect copied or discarded hits or duplicate pending hits', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  await copyRingBatch(history, 'CENTER', clipboard().write, 15)
  history.add(hit(2))
  history.discard(25)
  history.add(hit(3))
  history.mergeSnapshot([hit(4), hit(3), hit(2), hit(1)])
  assert.deepEqual(history.hits.map(hit => hit.sequence), [4, 3])
})

test('copy includes the entire batch even when only 50 hits appear in the table', async () => {
  const history = new HitHistory()
  for (let index = 1; index <= 1000; index++) history.add(hit(index))
  assert.equal(history.recent.length, 50)
  const clip = clipboard()
  await copyRingBatch(history, 'OUTER', clip.write, 10001)
  assert.equal(clip.copies[0].confirmed_batches[0].hits.length, 1000)
  assert.equal(history.count, 0)
})

test('copy separates the actual label from estimates and omits identifying metadata', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  history.add(hit(2))
  const clip = clipboard()
  await copyRingBatch(history, 'OUTER', clip.write, 25)
  const exported = clip.copies[0]
  assert.equal(exported.label_applies_to, 'head_hits')
  assert.equal(exported.confirmed_batches[0].confirmed_ring, 'OUTER')
  assert.equal(exported.confirmed_batches[0].hits[0].estimated_ring, 'INNER')
  assert.deepEqual(exported.confirmed_batches[0].hits.map(hit => hit.time_ms), [10, 0])
  for (const item of exported.confirmed_batches[0].hits) {
    assert.equal(item.device, undefined)
    assert.equal(item.timestamp, undefined)
    assert.equal(item.sequence, undefined)
    assert.equal(item.velocity_prefix_cc88, 0)
  }
  assert.deepEqual(exported.hits, [])
})

test('copy reads the incoming buffer, including hits not yet rendered', async () => {
  const history = new HitHistory()
  history.add(hit(1))
  const displayed = history.recent
  history.add(hit(2))
  assert.equal(displayed.length, 1)
  assert.equal((await copyRingBatch(history, 'INNER', clipboard().write, 25)).hits.length, 2)
})
