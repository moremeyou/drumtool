export type Ring = 'CENTER' | 'INNER' | 'MIDDLE' | 'OUTER' | 'UNKNOWN'
export interface HitEvent {
  sequence: number
  timestamp: string
  device: string
  channel: number
  note: number
  note_name: string
  articulation: string
  velocity: number
  position_cc16: number | null
  velocity_prefix_cc88: number | null
  estimated_ring: Ring
  confidence: number
}
export interface EngineStatus {
  connected: boolean
  device: string | null
  error: string | null
  hits_received: number
  capture_queue_dropped: number
  browser_events_dropped: number
}
export type EngineMessage =
  | {type: 'hit'; hit: HitEvent}
  | {type: 'status'; status: EngineStatus}
  | {type: 'snapshot'; status: EngineStatus; hits: HitEvent[]}
