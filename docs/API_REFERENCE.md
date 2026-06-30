# RasperifyScanner — API Reference

Base URL: `http://<pi-ip>:8000/api/v1`

Interactive docs: `http://<pi-ip>:8000/docs`

---

## Authentication

### POST /auth/login
```json
{ "username": "admin", "password": "yourpassword" }
```
Returns `{ access_token, refresh_token, token_type }`. Access token expires in 15 min.

### POST /auth/refresh
```json
{ "refresh_token": "..." }
```
Returns a new token pair. The mobile client refreshes automatically on a 401 and
retries the request.

---

## Analysis

All endpoints require `Authorization: Bearer <access_token>`.

### POST /analyze
Submit a frame for the full two-stage pipeline (Stage 1 detection + Stage 2 scene
analysis). If `frame_base64` is omitted, the server captures a frame itself.
```json
{ "frame_base64": "<base64 JPEG>", "prompt": "optional custom prompt" }
```
Returns `202` with the analysis result, including detections (real YOLO bounding
boxes), `counts`, metrics, and the scene description.

### GET /results
Paginated analysis history. Query params: `page` (default 1), `page_size` (default 20).

### GET /results/{id}
Single analysis result with detections and intensity metrics.

---

## Config

Live runtime configuration. Backed by `config/scanner.yml`; changes are applied to
the running services and persisted to the YAML file.

### GET /config
Returns the current configuration:
```json
{
  "camera_source": "picamera2",
  "detection_enabled": true,
  "detection_conf_threshold": 0.35,
  "detection_iou_threshold": 0.45,
  "counting_min_hits": 3,
  "counting_person_alert_threshold": 0,
  "ollama_enabled": true,
  "ollama_model": "moondream",
  "analysis_default_interval_seconds": 30,
  "allow_cloud": false,
  "store_frames": true
}
```

### PATCH /config
Partial update — send only the keys you want to change. Validated and applied live
where possible (detection toggle/thresholds take effect immediately; an
`ollama_model` or `allow_cloud` change reloads the AI provider stack):
```json
{ "detection_conf_threshold": 0.5, "analysis_default_interval_seconds": 60 }
```
Validated bounds: thresholds 0–1, `counting_min_hits` ≥ 1,
`counting_person_alert_threshold` ≥ 0, `analysis_default_interval_seconds` ≥ 5.

---

## Events

Persisted operational log (count alerts, camera/model failures and recoveries).

### GET /events
Paginated, newest first. Query params: `page` (default 1), `page_size` (1–100,
default 20), optional `kind` filter.
```json
{
  "items": [
    {
      "id": 12,
      "kind": "person_threshold",
      "severity": "warning",
      "message": "Live person count 4 exceeded threshold 3",
      "data_json": { "people_count": 4, "threshold": 3, "frame_id": "uuid" },
      "created_at": "2026-06-30T09:15:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

## Schedules

### GET /schedules — list all schedules
### POST /schedules — create schedule
```json
{ "name": "every 30s", "interval_seconds": 30, "enabled": true }
```
### PATCH /schedules/{id} — update (partial)
### DELETE /schedules/{id} — delete

---

## Camera

### POST /camera/connect — start the camera (begin capturing/streaming)
### POST /camera/disconnect — stop the camera and release the device

---

## Health

### GET /health
Returns system status (no auth required):
```json
{
  "status": "ok",
  "camera_connected": true,
  "camera_source": "picamera2",
  "active_adapter": "usb",
  "adapters": [
    { "name": "usb", "interface": "usb0", "up": true, "ip": "10.12.194.1" },
    { "name": "ethernet", "interface": "eth0", "up": false, "ip": null },
    { "name": "wifi", "interface": "wlan0", "up": true, "ip": "192.168.1.42" }
  ],
  "detector": { "backend": "onnx-yolo", "available": true, "enabled": true },
  "ollama": {
    "enabled": true, "reachable": true, "model": "moondream",
    "model_present": true, "host": "http://localhost:11434"
  },
  "cpu_percent": 12.5,
  "memory_percent": 43.2,
  "uptime_seconds": 3600
}
```

`detector` reflects the Stage-1 YOLO backend; `ollama` reflects the Stage-2 local
model. See [LOCAL_AI_SETUP.md](LOCAL_AI_SETUP.md) for what to do when either is
unavailable.

---

## WebSocket

### WS /ws/analysis-stream
Connect to receive real-time messages as JSON. Each message has an `event` field:

**`live_frame`** — emitted ~1/s while the camera is on and a client is connected.
Carries the live preview thumbnail, Stage-1 boxes, and counts:
```json
{
  "event": "live_frame",
  "frame_id": "uuid",
  "frame_thumbnail": "<base64 JPEG>",
  "detections": [
    { "label": "person", "confidence": 0.91, "bbox": [0.31, 0.12, 0.48, 0.77], "track_id": 4 }
  ],
  "counts": { "live": 1, "cumulative": 3 },
  "detector": "onnx-yolo",
  "degraded": false,
  "frame_size": { "width": 1280, "height": 720 }
}
```
`bbox` is `[x1, y1, x2, y2]` normalized to 0–1 of the frame; `degraded: true`
means detection is skipping frames to keep up (see graceful degradation).

**`analysis_complete`** — emitted when a scheduled or on-demand analysis finishes:
```json
{
  "event": "analysis_complete",
  "id": 42,
  "frame_id": "uuid",
  "provider": "ollama",
  "detections": [{ "label": "person", "confidence": 0.95, "bbox": [0.3, 0.1, 0.5, 0.8], "track_id": null }],
  "counts": { "live": 2, "cumulative": 5 },
  "metrics": { "brightness": 0.7 },
  "environment_scan": { "people_count": 2, "summary": "..." },
  "ai_degraded": false
}
```

**`event`** — emitted whenever an event is recorded (mirrors `GET /events` rows):
```json
{
  "event": "event",
  "id": 12,
  "kind": "person_threshold",
  "severity": "warning",
  "message": "Live person count 4 exceeded threshold 3",
  "data": { "people_count": 4, "threshold": 3 },
  "created_at": "2026-06-30T09:15:00Z"
}
```
</content>
