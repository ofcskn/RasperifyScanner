# RasperifyScanner

AI-powered environment scanner running on Raspberry Pi 4 Model B. Captures camera frames via CSI module and analyzes them using Google Gemini Vision (primary) or OpenAI GPT-4o (fallback).

```
                     ┌─────────────────────────────────────┐
                     │      Raspberry Pi 4 Model B          │
                     │                                       │
  CSI Camera ───────►│  CameraService  ──►  Pipeline  ──►  DB │
                     │                         │             │
                     │    FastAPI (0.0.0.0:8000)│             │
                     └────────┬────────────────┘             │
                              │                              │
              ┌───────────────┼──────────────────┐          │
              │               │                  │          │
          USB-C OTG       Ethernet            WiFi          │
         (usb0)           (eth0)            (wlan0)         │
              │               │                  │          │
              └───────────────┼──────────────────┘          │
                              │                             │
              ┌───────────────┴──────────────────┐         │
              │         Mac Mini / Mobile App      │         │
              │   Expo React Native (Dashboard,    │         │
              │   History, Settings screens)       │         │
              └────────────────────────────────────┘        │
```

## Quick Start

### Backend (on Pi or Mac with mock camera)

**1. Create and activate the virtual environment**

macOS / Linux:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

Windows:
```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
```

**2. Install dependencies, configure, and run**

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # fill in API keys
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> Keep the virtual environment active for all subsequent commands. Re-run the activate step above whenever you open a new terminal.

### Frontend

```bash
cd frontend
npx expo start
```

### Docker (ARM64)

```bash
docker-compose up --build
```

### Tests

```bash
# activate the virtual environment
cd backend
pytest tests/ -v
```

## Architecture

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for full GRASP-based design.

## Pi USB-C Setup

See [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for USB-C OTG gadget mode configuration.

## API

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) or visit `http://<pi-ip>:8000/docs`.
