# TD-50X MIDI Interface · v0.1

Local-first prototype for PD-140DS → TD-50X → Python MIDI engine → WebSocket → browser. No cloud, accounts, browser Web MIDI, or input emulation. Dependency installation requires internet; runtime does not.

## Current checkpoint

Raw TD-50X head hits with CC16 and CC88 have been verified from user-shared browser output. The experimental classifier and four-ring visualization are implemented. User-labelled tests across taped rings and three strengths exposed strength-dependent ring errors. The default distance now uses CC16 alone. A fresh fixed-location test agreed with the intended ring labels on 55 of 60 hits; imperfect strike placement means this is label agreement, not a precise accuracy measurement. The user reports that the visualization keeps up during fast rolls; latency and event completeness have not been measured. The user also verified that unplugging reports a disconnect without crashing, and that refreshing sources and connecting after plugging back in resumes snare capture. The planned macOS hardware checks for the v0.1 technical prototype are complete; ring estimation remains experimental. Automated tests do not establish hardware accuracy.

## Requirements and setup

- macOS first; portable Python and browser architecture also targets Windows (not yet tested there).
- Python 3.10+ (tested here with 3.13.1), Node 20.19+ or 22.12+ (tested with 24.14.0).
- Roland TD-50X available as an operating-system MIDI input. PD-140DS connected to the module's digital trigger input.

From the repository root:

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd frontend
npm ci
```

On Windows use `py -m venv backend/.venv` and `backend\.venv\Scripts\python` instead of `backend/.venv/bin/python`.

If macOS compilation of `python-rtmidi` reports missing C++ standard headers even though Command Line Tools are installed, supply the active SDK include directory for that install:

```sh
CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1" backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

## Run locally

Terminal 1, from the repository root:

```sh
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```sh
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Keep the backend running independently of the browser. Use a **single backend worker**; do not enable reload during hardware acceptance tests. Closing/refreshing the UI does not stop capture. The backend retains the latest 50 hits in memory and sends them on browser reconnect. Restarts clear history.

The engine selects an input containing `TD-50X` on startup. If the module appears later, use **Refresh sources**, choose its input, and **Connect**. After unplugging, the one-second device monitor marks it disconnected; refresh and reconnect manually after reconnecting the hardware.

Play one or more head hits at a known ring, then **click that ring on the snare** to copy only the current batch as labelled JSON and clear it for the next round. Enter/Space also activates a focused ring. The chosen `confirmed_ring` stays separate from the classifier's `estimated_ring`. Each ring-click export contains exactly one confirmed batch; previous rounds are never included. Paste the copied JSON somewhere before the next ring click replaces the clipboard. If clipboard access fails, the hits remain available to retry. Hits received while copying stay in the next batch. Empty or rim-only batches cannot be labelled as head strikes. Labels apply to head hits; other articulations remain raw diagnostic data.

**Clear history** discards the current batch as a mistake. WebSocket reconnects do not resurrect copied or discarded hits.

**Copy history** copies only current unconfirmed hits without clearing them. Timing is relative to the batch's oldest hit, with hits newest first; device names and absolute timestamps are omitted. The table shows the latest 50 pending hits, but copying preserves every received hit in the batch. Data stays in page memory only. A full reload restores the backend's latest 50 unlabelled hits; clear these before starting a fresh test. Clicking rings does not automatically alter calibration or retrain the classifier.

## Ring visualization

Four concentric zones are labelled CENTER, INNER, MIDDLE and OUTER. Each live head hit pulses its estimated zone for 180 ms; velocity controls brightness. New hits replace the current pulse instead of queuing animations. UI updates are batched once per display frame, so multiple hits in one frame share the most recent head pulse; the history still receives each event, subject to the documented queue limits.

The latest head estimate, raw CC16, velocity and confidence appear beside the snare. A subtle `?` flags confidence below 70% (this is a display cue, not a CC16 classification boundary). Estimates also appear in the inspector, history and copied JSON. Reconnected historical hits do not pulse. Missing CC16 produces UNKNOWN and no ring pulse. Ring sizes are illustrative and never imply exact physical distance or an X/Y point.

Strike a known approximate zone, compare the estimate, then click the actual ring to label that batch for sharing. Unlabelled history is diagnostic data, not training data.

## Interpretation and limitations

- Channels displayed as 1–16; Mido channel 9 is displayed as channel 10.
- Provisional mapping lives in `backend/app/midi/mapping.json`: numeric notes 38 (head), 40 (rim), 37 (cross-stick), channel 10. Numeric notes are authoritative; the display uses MIDI 60 = C3, making note 38 = D1. Octave labels differ across software. Change the JSON and restart to adjust mapping; these are not universal Roland assignments.
- CC16 and CC88 state is independent per MIDI channel. Each positive Note On consumes both values. A controller must be within 30 ms of that Note On, measured with monotonic receipt time. Missing/stale controllers stay null. Note Off and zero-velocity Note On do not create hits or consume pending controllers.
- The association is a heuristic: simultaneous instruments on one channel can be ambiguous because CC messages have no note identifier. All positive Note Ons remain visible for diagnosis, including unmapped notes.
- CC16 is a **raw position signal**, not exact radial distance or X/Y position. CC88 is retained as a raw prefix; no unverified high-resolution velocity reconstruction is applied.
- Only mapped head hits with recent CC16 are classified. Missing position, rim, cross-stick and unmapped hits retain `UNKNOWN` / `0`; they remain visible in the diagnostic history.
- Classifier: K=5 nearest neighbours over normalized MIDI features, with configurable `feature_weights` and Euclidean distance. The default weights are CC16=1 and velocity=0, so changing velocity at the same CC16 cannot change the ring or confidence. Velocity remains in raw events and controls pulse brightness. Profiles without weights retain the original equal weighting. All 40 supplied labelled samples are in `backend/calibration/pd140ds_default.json`. No position threshold bands are used. Vote ties prefer smaller total neighbour distance, then label order for exact ties. Confidence is the winning vote fraction divided by `(1 + mean neighbour distance)`, rounded to four decimals. It is a heuristic, not a statistical probability; even unanimous neighbours can be wrong outside the calibration conditions. INNER/MIDDLE overlap is real.
- **The current calibration data was captured from one PD-140DS / TD-50X setup and is NOT intended as a universal Roland calibration.** The supplied samples are preserved without filtering, synthetic relabelling, or identifying metadata. Edit the JSON and restart the backend to change calibration, feature weights or K; the classifier implements the replaceable `HitClassifier` protocol.
- Native callback interpretation runs independently of WebSockets. A bounded 2,048-hit handoff and 256-message queue per browser discard oldest queued events on overflow; the UI displays drop counters. This is diagnostic visualization, not a lossless recording system.
- UI updates at most once per animation frame and keeps 50 hits. Fast-roll responsiveness and physical unplug/reconnect have passed user-reported checks. Hardware latency and event completeness remain unmeasured.

## API at this checkpoint

- `GET /api/status`
- `GET /api/midi/devices`
- `POST /api/midi/connect` with `{"device": "TD-50X"}` (use the actual enumerated name)
- `WS /ws/events`: initial `snapshot`, then `hit` and `status` envelopes. Hit timestamps are UTC; `sequence` increments for the backend process lifetime.
- `GET /api/calibration`: the active labelled samples, K, and classifier assumptions.

Bind to loopback. The Vite server proxies HTTP and WebSocket requests to the engine. WebSockets allow local frontend origins on port 5173. No CORS dependency is needed.

## Tests and diagnostics

```sh
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

Automated tests use a fake input backend to test raw event correlation, callback-to-WebSocket delivery, capture with no browser, channel isolation, stale/missing data, rapid sequences, disconnect and manual reconnect. They do not replace the real hardware acceptance test. No simulated input is exposed in the production UI.

For structured verbose logging on macOS:

```sh
cd backend
MIDI_DEBUG=1 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Debug logs retain raw MIDI including Note Off, controller messages, classifier results and normalized events. Normal mode logs connection lifecycle only. Windows PowerShell: set `$env:MIDI_DEBUG="1"` before running the backend.

## Structure

```text
backend/
  app/
    api/broker.py           bounded WebSocket fanout
    classifier/knn.py      replaceable normalized K-nearest-neighbour classifier
    midi/                  CoreMIDI/RtMidi engine, interpretation, mapping
    models/hit.py          normalized event and replaceable classifier protocol
    main.py                FastAPI lifecycle and endpoints
  calibration/             supplied labelled JSON samples
  tests/                   interpretation and integration tests
frontend/
  src/components/          MIDI source controls
  src/hooks/               reconnecting, frame-batched event subscription
  src/types/               event contracts
```

Keyboard/mouse/gamepad emulation, profiles, macros, Tauri, installers, databases, cloud, calibration UI, other-pad visualization and X/Y detection remain out of scope.

## Privacy and contributing

Read [AGENTS.md](AGENTS.md) before changing or publishing this project. All tracked files must remain suitable for a fresh, public clone. Personal information, credentials, private network details, machine-specific paths and local captures do not belong in the repository. Loopback URLs are safe, portable local defaults.

After cloning, enable the local checks:

```sh
git config --local core.hooksPath .githooks
```

Stage intended files, review the diff, then check exactly what will be committed:

```sh
git diff --cached
python3 scripts/check_privacy.py
python3 scripts/check_privacy.py --history
```

The pre-commit hook checks staged blobs; the pre-push hook checks all local Git history, including commit messages and email metadata. GitHub Actions repeats both checks. Use a public alias/neutral author and a privacy-safe noreply email in your repository-local Git configuration. Hooks require `python3` on PATH (including Git Bash on Windows).

The guard detects common credential formats, home paths, email addresses, non-loopback IPs, MAC addresses, private hostnames and risky tracked artifacts. It does not recognize every personal name or sensitive fact; manually review source, filenames, commit metadata, screenshots and any proposed exception. A passing scan is not a guarantee. Public GitHub repository ownership is necessarily associated with the account that hosts it.

Keep local-only material in ignored `local/` or `private/` directories. Never force-add ignored files. Raw MIDI/debug data stays on the local machine and must be reviewed and sanitized before sharing. No telemetry is configured by this app. GitHub runs repository checks after a push; secrets must be prevented before uploading.
