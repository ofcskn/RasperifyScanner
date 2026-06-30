# RasperifyScanner — Architecture & Algorithms

## System Description

RasperifyScanner runs on a **Raspberry Pi 4 Model B** and continuously captures
environment frames from a CSI camera. Each frame flows through a **two-stage
pipeline** that runs **entirely on the device by default**, and results are
streamed live to a **React Native (Expo)** app:

- **Stage 1 — detection (fast, per frame):** a YOLO neural network finds people
  and objects and draws bounding boxes; a tracker turns those boxes into stable
  identities and counts people.
- **Stage 2 — scene analysis (slower, on an interval):** a local Ollama vision
  model writes a structured JSON description of the scene.

Cloud vision providers (Gemini, OpenAI) remain available behind `allow_cloud`,
but are off by default so no image ever leaves the Pi.

---

## Glossary (the new vocabulary)

| Term | Plain meaning |
|---|---|
| **YOLO** | A single-pass object-detection neural network. We ship `yolov8n` (nano) — the smallest variant — so it runs on the Pi's CPU. |
| **ONNX** | A portable neural-network file format. `models/yolo.onnx` is the exported YOLO model. |
| **ONNX Runtime** | The engine that executes an `.onnx` file. It can use a GPU/NPU if one is present, otherwise the CPU. |
| **COCO labels** | The 80 standard object classes YOLO recognizes (person, car, dog, chair…). Index 0 = `person`. |
| **Letterbox** | Resizing a frame to the model's square input (640×640) while preserving aspect ratio by padding the edges — so objects aren't stretched. |
| **Bounding box / bbox** | `[x1, y1, x2, y2]` rectangle around an object, stored normalized to 0–1 of the frame so it scales to any display size. |
| **Confidence** | The model's certainty for a detection (0–1). |
| **NMS (Non-Max Suppression)** | Keeps the single best box when several overlap on the same object. |
| **IoU (Intersection over Union)** | Overlap ratio of two boxes (0–1). Used by NMS and by the tracker to decide "same object". |
| **Track / track ID** | A persistent identity for an object across frames. Lets us count *unique* people instead of re-counting the same person every frame. |
| **Ollama** | A local LLM server that runs vision models (e.g. `moondream`) over HTTP on the Pi itself. |
| **Event** | A stored, broadcastable log entry for something noteworthy (e.g. a person-count alert). |

---

## GRASP Principle Assignments

GRASP = a set of object-design guidelines (who should be responsible for what).
The classes below each own one clear responsibility.

| Class | GRASP Pattern | Responsibility |
|-------|---------------|----------------|
| `NetworkAdapterManager` | Information Expert + Pure Fabrication | Probes USB/Ethernet/WiFi interfaces; reports the active adapter |
| `CameraService` | Information Expert | Owns the camera handle and frame queue; the only class that captures frames |
| `DetectionService` | Information Expert + Indirection | Owns the YOLO detector, tracker, and people counter (Stage 1) |
| `OnnxYoloDetector` | Polymorphism + Protected Variations | Concrete detector behind the `Detector` interface — backends can be swapped |
| `CentroidTracker` / `PeopleCounter` | Pure Fabrication | Frame-to-frame identity matching and unique-person counting |
| `AnalysisPipelineController` | Controller + Creator | Orchestrates the full pipeline; creates `Analysis` ORM objects |
| `MultiAIProviderService` | Indirection | Hides Stage-2 provider selection (Ollama / Gemini / OpenAI) from callers |
| `OllamaProvider` / `AIProvider` (ABC) | Polymorphism + Protected Variations | Local and cloud vision providers swap transparently |
| `record_event` (events service) | Pure Fabrication | One place that persists and broadcasts events |
| `SchedulerService` | Pure Fabrication | APScheduler wrapper that drives interval analyses |
| `ConnectionService` | Controller | WebSocket client registry and broadcasting |
| `AuthService` | Pure Fabrication | JWT lifecycle |

---

## Data Flow

```
Camera (≈2 fps) ──► CameraService ──► frame (base64 JPEG)
                                          │
        ┌─────────────────────────────────┼──────────────────────────────┐
        ▼ live (every frame)                                              ▼ scheduled (interval)
  _live_frame_broadcaster                                       AnalysisPipelineController.run()
        │                                                                 │
        ▼                                                       motion gate (skip if still)
  DetectionService.process()                                              │
   YOLO ► tracker ► counter                                    Stage 1: DetectionService.snapshot()
        │                                                       Stage 2: MultiAIProviderService.analyze()
        ▼                                                                 │   ├─ OllamaProvider (default)
  WS "live_frame":                                                        │   ├─ GeminiProvider (if allow_cloud)
   thumbnail + boxes + counts                                            │   └─ OpenAIProvider (if allow_cloud)
                                                                          ▼
                                                       SQLite: Analysis, DetectionResult,
                                                               IntensityMetric, Event
                                                                          │
                                                       WS "analysis_complete" / "event"
                                                                          ▼
                                                                  Mobile / web app
```

Two paths share the same detector:

- **Live path** (`main.py:_live_frame_broadcaster`): runs Stage-1 detection on
  every captured frame (in a thread-pool executor so it never blocks the async
  event loop) and broadcasts a `live_frame` message with a thumbnail, boxes, and
  counts — this is what the app's **Live** tab draws.
- **Scheduled path** (`AnalysisPipelineController.run`): on each interval, runs
  Stage 1 **and** Stage 2, persists the result, and broadcasts `analysis_complete`.

---

## Stage 1 — Detection algorithm

The boundary type throughout is a **base64 JPEG string** (the same format the
camera and WebSocket use), so detector backends can be swapped without touching
callers. The shipped backend is `OnnxYoloDetector`.

### Per-frame detection (`OnnxYoloDetector.detect`)

1. **Decode** the base64 JPEG to an RGB image; remember its original size.
2. **Letterbox** to 640×640 (configurable via `detection_input_size`), preserving
   aspect ratio with gray padding, then normalize to a `1×3×640×640` float tensor.
3. **Run ONNX Runtime inference** → a raw `(1, 84, 8400)` tensor: 8400 candidate
   boxes, each with 4 box coordinates + 80 class scores.
4. **Post-process:** for each candidate take the highest-scoring class; drop
   anything below `detection_conf_threshold` (default **0.35**); convert box
   coordinates back to the original frame; run **class-aware NMS** (default IoU
   **0.45**) to remove duplicate boxes — only boxes of the *same* class suppress
   each other, so an overlapping person and chair both survive.
5. **Map** each class index to its COCO label, optionally filter to
   `detection_target_labels` (empty = keep all 80 classes), and normalize each
   bbox to 0–1.

Output is a list of detections: `{label, confidence, bbox, track_id}` (track_id
filled in by the tracker, below).

**Hardware acceleration is automatic.** ONNX Runtime is asked for execution
providers in priority order CUDA → ROCm → OpenVINO → **CPU**; missing ones are
skipped, so the same code uses an accelerator if present and the Pi's CPU
otherwise. `onnxruntime`/`numpy` are imported lazily — if they're absent the app
still boots and reports `detector.available: false`.

### Graceful degradation

YOLO on a Pi 4 CPU takes roughly 0.5–1.5 s/frame. If a frame's inference exceeds
`detection_frame_budget_seconds` (default 1.0 s), `DetectionService` **skips** the
next few frames and reuses the last result (tagged `degraded: true`) so video
keeps streaming instead of stuttering. The app shows a "Reduced frame rate (CPU
busy)" pill when this happens.

---

## Tracking & counting algorithm

Detection alone can't count people — without identity, the same person is a "new"
person in every frame. Two small, pure-Python classes solve this.

### `CentroidTracker` — frame-to-frame identity (by IoU)

Despite the name, it matches by **box overlap (IoU)**, not centroid distance:

1. For every (new detection, existing track) pair **of the same label**, compute
   IoU.
2. Keep pairs scoring ≥ `counting_iou_match` (default **0.3**), sort by IoU
   descending, and assign **greedily** — each detection and each track used at
   most once.
3. **Lifecycle of a track:**
   - *New:* an unmatched detection gets a fresh incrementing **track ID** (starts
     at 1) with `hits = 1`.
   - *Matched:* the track's box is updated, `hits += 1`, miss counter reset.
   - *Lost:* a track not matched this frame increments its miss counter; it is
     evicted once unseen for more than `counting_max_age` frames (default **15**).

This is what keeps a moving person on a stable ID instead of flickering into new
ones.

### `PeopleCounter` — live and cumulative counts

- **Live count** = number of `person` boxes in the current frame (`counts.live`).
- **Cumulative count** = number of *distinct* track IDs ever confirmed
  (`counts.cumulative`).
- **Debounce:** a track only contributes to the cumulative count once it has
  persisted for `counting_min_hits` frames (default **3**). This suppresses
  single-frame false positives, at the cost of a few frames' latency before a new
  person is counted.

`snapshot()` vs `process()`: the scheduled pipeline calls `snapshot()`, which
detects **without** advancing the live tracker, so periodic analyses don't corrupt
the live cumulative count that the Live tab is showing via `process()`.

---

## Stage 2 — Scene analysis algorithm

`MultiAIProviderService` hides provider choice from the pipeline.

1. **Provider registry (local-first):** Ollama is registered when
   `ollama_enabled`; Gemini/OpenAI are added **only** if `allow_cloud` is true and
   their API key is set (their SDKs are imported lazily, so a default install never
   touches the cloud). The configured `ai_primary_provider` (default `ollama`)
   goes first.
2. **Short-term cache:** identical frames within 60 s reuse the previous result.
3. **Try, retry, fall back:** for each provider in order — skip it if it's in a
   rate-limit cooldown; otherwise retry up to `ai_retry_max` times (default 3)
   with exponential backoff (`ai_retry_backoff_base ** attempt`). A rate-limit
   error (HTTP 429 / `RESOURCE_EXHAUSTED`) benches that provider for 60 s and
   moves to the next. If all providers are exhausted it raises — and the pipeline
   degrades to YOLO-only results rather than failing the frame.

### How `OllamaProvider` works

- Talks to Ollama's HTTP API (`POST {ollama_host}/api/chat`, default host
  `http://localhost:11434`) with `httpx` — no extra SDK.
- Sends the frame in Ollama's native `images` array as base64, after downscaling
  the longest edge to 768 px (JPEG q80) to keep inference fast.
- Forces `format: "json"`, `temperature: 0`, and caps output at
  `ollama_num_predict` tokens so even a tiny model returns parseable, bounded
  JSON. `keep_alive` keeps the model resident in RAM between calls to avoid
  reload cost.
- Parses the JSON into detections, numeric metrics, and an `EnvironmentScan`; if
  parsing fails it keeps the raw response for debugging rather than throwing.

Because a warm `moondream` inference on a Pi 4 CPU measures ~130 s, the timeout
defaults to a generous **300 s** (`ollama_timeout_seconds`). Move Ollama to a
faster LAN host by pointing `ollama_host` at it.

---

## The Pipeline, end to end

`AnalysisPipelineController.run()` ties it together:

1. **Capture** a frame (or accept one supplied via `POST /analyze`).
2. **Motion gate:** compare a 64×64 grayscale version against the previous frame;
   if the mean difference is below `MOTION_THRESHOLD`, skip analysis and return
   `no_motion` — saving CPU on a static scene.
3. **Stage 1:** `detection_service.snapshot()` → real bounding boxes + people
   counts.
4. **Stage 2:** `multi_ai_service.analyze()` → scene JSON (degrades gracefully if
   it fails, setting `ai_degraded: true`).
5. **Persist:** one `Analysis` row plus its `DetectionResult` boxes,
   `IntensityMetric` values, and an optional frame thumbnail (when `store_frames`).
6. **Broadcast** an `analysis_complete` WebSocket message.
7. **Event:** if `counting_person_alert_threshold > 0` and the live count exceeds
   it, call `record_event("person_threshold", severity="warning", …)`.

---

## Events system

An **event** is a persisted operational signal (the `events` table:
`kind`, `severity`, `message`, `data_json`, `created_at`). `record_event(...)` is
the single entry point used across the pipeline, camera, and providers — it writes
the row **and** broadcasts an `event` WebSocket message, so the app's **Events**
tab updates live. Persistence is defensive: a logging failure never breaks the
caller. History is available at `GET /api/v1/events` (paginated, filterable by
`kind`).

---

## Network Layer

Three adapters are supported simultaneously (FastAPI binds to `0.0.0.0`):

- **USB-C OTG** (`usb0`) — direct Pi-to-Mac connection (no router/WiFi needed)
- **Ethernet** (`eth0`) — wired LAN
- **WiFi** (`wlan0`) — wireless LAN

`NetworkAdapterManager` probes all three and reports the first active one in
`GET /api/v1/health`, alongside the new `detector` and `ollama` status blocks.
</content>
