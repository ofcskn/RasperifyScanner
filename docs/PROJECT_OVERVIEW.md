# RasperifyScanner — Architecture Overview

## System Description

RasperifyScanner runs on a **Raspberry Pi 4 Model B** and continuously captures environment frames via a CSI camera. Frames are analyzed by AI models and results are streamed to a **React Native (Expo)** mobile app in real time.

## GRASP Principle Assignments

| Class | GRASP Pattern | Responsibility |
|-------|---------------|----------------|
| `NetworkAdapterManager` | Information Expert + Pure Fabrication | Probes USB/Ethernet/WiFi interfaces; returns active adapter |
| `CameraService` | Information Expert | Owns picamera2 and frame queue; only class that knows how to capture |
| `FrameCaptureController` | Controller | Receives capture trigger; delegates to CameraService |
| `AnalysisPipelineController` | Controller + Creator | Orchestrates full pipeline; creates Analysis ORM objects |
| `MultiAIProviderService` | Indirection | Hides primary/fallback provider selection from callers |
| `AIProvider` (ABC) | Polymorphism + Protected Variations | Abstract interface — Gemini and OpenAI swap transparently |
| `NetworkAdapter` (ABC) | Polymorphism + Protected Variations | Shields system from USB/WiFi/Ethernet differences |
| `SchedulerService` | Pure Fabrication | APScheduler wrapper — no domain concept |
| `AuthService` | Pure Fabrication | JWT lifecycle — no domain concept |
| `ConnectionService` | Controller | WebSocket client registry and broadcasting |

## Data Flow

```
Scheduler (interval) ──► AnalysisPipelineController
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              CameraService         frame_base64 (from POST)
                    │
                    ▼
          MultiAIProviderService
            ├── GeminiProvider (primary)
            └── OpenAIProvider (fallback)
                    │
                    ▼
              SQLite (Analysis, DetectionResult, IntensityMetric)
                    │
                    ▼
           ConnectionService.broadcast() ──► WebSocket clients
```

## Network Layer

Three adapters are supported simultaneously (FastAPI binds to `0.0.0.0`):

- **USB-C OTG** (`usb0`, `192.168.7.2`) — direct Pi-to-Mac connection
- **Ethernet** (`eth0`) — wired LAN
- **WiFi** (`wlan0`) — wireless LAN

`NetworkAdapterManager` probes all three and reports the first active one in `/api/v1/health`.
