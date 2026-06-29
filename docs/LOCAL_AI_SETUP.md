# Local AI Pipeline — Setup, Configuration & Performance

This system runs **fully offline** after setup. Two stages:

1. **Stage 1 — on-device detection (every frame, fast):** a YOLO-n model via ONNX
   Runtime detects people and objects, with bounding boxes, confidence, and a
   tracker that maintains a **live in-frame count** and a **cumulative unique
   count**.
2. **Stage 2 — local Ollama analysis (interval, slower):** a local Ollama vision
   model (default `moondream`) produces a structured scene/anomaly JSON report.

Nothing is sent to the cloud. Cloud providers (Gemini/OpenAI) remain available but
are **disabled by default** (`allow_cloud: false`).

## 1. One-command setup

From `backend/` (inside your virtualenv):

```bash
python scripts/setup_local.py
```

It will, failing loudly with a fix hint at each step:
1. `pip install -r requirements.txt` (adds `onnxruntime`, `numpy`, `opencv-python-headless`).
2. Ensure the YOLO ONNX model at `backend/models/yolo.onnx`:
   - exports `yolov8n.onnx` automatically if `ultralytics` is installed, **or**
   - downloads from `DETECTION_MODEL_URL` if set, **or**
   - prints exact instructions to export on a dev machine and copy it over.
3. Verify the `ollama` binary is installed.
4. Start / confirm the Ollama service (`OLLAMA_HOST`, default `http://localhost:11434`).
5. `ollama pull <model>` if the configured model is missing.
6. Make a live test call and assert the model responds.

### Getting the detection model manually
On any machine with Python:
```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx imgsz=640
cp yolov8n.onnx /path/to/RasperifyScanner/backend/models/yolo.onnx
```

## 2. Verify end-to-end

```bash
python scripts/verify_pipeline.py
```
Proves: detection runs, people counting updates, Ollama returns valid JSON, and the
pipeline recovers from a simulated detector failure. Checks for missing
deps/models/Ollama are **skipped** with a clear reason rather than failing.

## 3. Run

```bash
# Backend (Pi or dev)
uvicorn main:app --host 0.0.0.0 --port 8000
# Dev on a machine without a camera:
CAMERA_MOCK=true uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd ../frontend && npm install && npx expo start
# Point the app at the backend:
EXPO_PUBLIC_API_URL=http://<pi-ip>:8000/api/v1 \
EXPO_PUBLIC_WS_URL=ws://<pi-ip>:8000/ws/analysis-stream npx expo start
```

Confirm status any time:
```bash
curl http://<pi-ip>:8000/api/v1/health | python3 -m json.tool
# -> includes detector {backend, available} and ollama {reachable, model_present}
```

## 4. Configuration

All knobs live in `config/scanner.yml` (env vars / `.env` override it). Most can be
changed live from the app's **Settings** screen (`PATCH /api/v1/config`), no restart:

| Key | Meaning |
|-----|---------|
| `camera_source` | `picamera2` \| `usb:/dev/video0` \| `rtsp://host:554/stream` |
| `detection_enabled` | turn Stage-1 detection on/off |
| `detection_conf_threshold` / `detection_iou_threshold` | detector thresholds |
| `detection_target_labels` | `[]` = all classes; e.g. `["person"]` for people only |
| `counting_min_hits` | frames a track must persist before it counts as unique |
| `counting_person_alert_threshold` | `>0` raises an event when live count exceeds it |
| `ollama_host` / `ollama_model` | local LLM endpoint + model |
| `analysis_default_interval_seconds` | seconds between Stage-2 analyses |
| `allow_cloud` | `false` = fully local; `true` enables Gemini/OpenAI if keys set |
| `store_frames` | persist frame thumbnails with analyses |

## 5. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `/health` `detector.available: false` | onnxruntime/numpy not installed or model missing — run `scripts/setup_local.py`. |
| `/health` `ollama.reachable: false` | Ollama not running — `ollama serve`; check `OLLAMA_HOST`. |
| `ollama.model_present: false` | `ollama pull <model>` (e.g. `moondream`). |
| Live view but no boxes | detector unavailable, or `detection_enabled: false`, or nothing in frame. |
| "Reduced frame rate (CPU busy)" pill | graceful degradation kicked in — lower resolution or raise `detection_frame_budget_seconds`. |
| Ollama analysis very slow / times out | use a smaller model (`moondream`), raise `ollama_timeout_seconds`, increase the interval, or run Ollama on a faster LAN host via `OLLAMA_HOST`. |
| USB/RTSP camera not opening | install `opencv-python-headless`; verify the device path/URL; check permissions (`video` group). |

## 6. Performance notes (Raspberry Pi 4B)

- **YOLOv8n via ONNX Runtime (CPU):** ~0.5–1.5 s/frame on a Pi 4B. The live
  broadcaster runs ~1 fps; detection runs in a thread-pool executor so it never
  blocks the event loop. Lower `camera_resolution_*` for more speed.
- **Graceful degradation:** if a frame exceeds `detection_frame_budget_seconds`,
  subsequent frames are skipped (last result reused) so video keeps streaming.
- **Ollama on a Pi 4B is slow** (tens of seconds for a vision model). Keep the
  model tiny (`moondream`) and the analysis interval long, or offload Ollama to a
  faster machine on your LAN by setting `OLLAMA_HOST`.
- **CPU/NPU/GPU fallback:** the detector lists CUDA/ROCm/OpenVINO providers ahead
  of CPU, so the same code uses an accelerator automatically if one is present.
- **Memory:** YOLOv8n ONNX is ~6 MB; the heavy cost is the Ollama model. Ensure
  adequate RAM/swap for the chosen vision model.
