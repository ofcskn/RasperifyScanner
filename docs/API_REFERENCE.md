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
Returns new token pair.

---

## Analysis

All endpoints require `Authorization: Bearer <access_token>`.

### POST /analyze
Submit a frame for analysis.
```json
{ "frame_base64": "<base64 JPEG>", "prompt": "optional custom prompt" }
```
Returns `202` with analysis result including detections and metrics.

### GET /results
Paginated analysis history.
Query params: `page` (default 1), `page_size` (default 20).

### GET /results/{id}
Single analysis result with detections and intensity metrics.

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

## Health

### GET /health
Returns system status (no auth required):
```json
{
  "status": "ok",
  "camera_connected": true,
  "active_adapter": "usb",
  "adapters": [
    { "name": "usb", "interface": "usb0", "up": true, "ip": "192.168.7.2" },
    { "name": "ethernet", "interface": "eth0", "up": false, "ip": null },
    { "name": "wifi", "interface": "wlan0", "up": true, "ip": "192.168.1.42" }
  ],
  "cpu_percent": 12.5,
  "memory_percent": 43.2,
  "uptime_seconds": 3600
}
```

---

## WebSocket

### WS /ws/analysis-stream
Connect to receive real-time analysis results as JSON:
```json
{
  "event": "analysis_complete",
  "id": 42,
  "frame_id": "uuid",
  "provider": "gemini",
  "detections": [{ "object_name": "cat", "confidence": 0.95, "bbox": null }],
  "metrics": { "brightness": 0.7 }
}
```
