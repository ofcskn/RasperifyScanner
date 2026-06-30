#!/usr/bin/env python3
"""One-shot local setup + preflight for the fully-offline scanner.

Steps (each fails loudly with an actionable message):
  1. Install Python dependencies from requirements.txt.
  2. Ensure the YOLO ONNX detection model exists (export via ultralytics if
     available, else download from DETECTION_MODEL_URL, else explain how).
  3. Verify the Ollama binary is installed.
  4. Ensure the Ollama service is reachable (start it if not).
  5. Pull the configured vision model if missing.
  6. Run a live test call and assert the model responds.

Run from the backend/ directory:  python scripts/setup_local.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request

# Make `app` importable when run from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}[ OK ]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"{RED}[FAIL]{RESET} {msg}")
    if hint:
        print(f"       → {hint}")
    sys.exit(1)


def step(n: int, title: str) -> None:
    print(f"\n=== Step {n}: {title} ===")


# --- 1. dependencies ------------------------------------------------------

def install_deps() -> None:
    step(1, "Install Python dependencies")
    req = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
    if not os.path.exists(req):
        fail("requirements.txt not found", "Run this script from the backend/ directory.")
    rc = subprocess.call([sys.executable, "-m", "pip", "install", "-r", req])
    if rc != 0:
        fail("pip install failed", "Check the pip output above; you may need a venv or build tools.")
    ok("dependencies installed")


# --- 2. detection model ---------------------------------------------------

def ensure_model() -> None:
    from app.config.settings import settings

    step(2, "Ensure YOLO ONNX detection model")
    path = settings.detection_model_path
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    if os.path.exists(path):
        ok(f"model present at {path}")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Preferred: export from ultralytics if it happens to be installed.
    # YOLO11s (small) is far more accurate than the old nano model on people and
    # odd camera angles, and exports the identical (1,84,8400) ONNX output so the
    # detector's post-processing is unchanged.
    try:
        from ultralytics import YOLO  # type: ignore
        weights = os.getenv("DETECTION_WEIGHTS", "yolo11s.pt")
        print(f"Exporting {weights} -> ONNX via ultralytics ...")
        model = YOLO(weights)
        exported = model.export(format="onnx", imgsz=settings.detection_input_size, opset=12)
        shutil.copy(str(exported), path)
        ok(f"exported model to {path}")
        return
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover
        warn(f"ultralytics export failed: {exc}")

    # Fallback: download a pre-exported ONNX from a configured URL.
    url = os.getenv("DETECTION_MODEL_URL", "").strip()
    if url:
        try:
            print(f"Downloading model from {url} ...")
            urllib.request.urlretrieve(url, path)
            ok(f"downloaded model to {path}")
            return
        except Exception as exc:
            fail(f"model download failed: {exc}", "Check DETECTION_MODEL_URL or network access.")

    fail(
        f"no detection model at {path} and no way to obtain it",
        "Either: pip install ultralytics and re-run (it will export yolov8n.onnx), "
        "or export on a dev machine (yolo export model=yolov8n.pt format=onnx) and copy "
        f"the .onnx to {path}, or set DETECTION_MODEL_URL to a yolov8n.onnx download URL.",
    )


# --- 3-6. Ollama ----------------------------------------------------------

def check_ollama_binary() -> None:
    step(3, "Verify Ollama is installed")
    if shutil.which("ollama") is None:
        fail("ollama binary not found on PATH",
             "Install it: curl -fsSL https://ollama.com/install.sh | sh  (see https://ollama.com).")
    ok("ollama binary found")


def ensure_ollama_service() -> None:
    from app.config.settings import settings
    import httpx

    step(4, "Ensure the Ollama service is running")
    host = settings.ollama_host.rstrip("/")

    def reachable() -> bool:
        try:
            httpx.get(f"{host}/api/tags", timeout=3.0).raise_for_status()
            return True
        except Exception:
            return False

    if reachable():
        ok(f"ollama reachable at {host}")
        return

    print("ollama not reachable — attempting to start `ollama serve` ...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        fail(f"could not start ollama serve: {exc}", "Start it manually in another terminal: ollama serve")
    for _ in range(15):
        time.sleep(1.0)
        if reachable():
            ok(f"ollama started and reachable at {host}")
            return
    fail("ollama did not become reachable", f"Start it manually and confirm {host}/api/tags responds.")


def ensure_model_pulled() -> None:
    from app.config.settings import settings
    import httpx

    step(5, "Ensure the vision model is pulled")
    host = settings.ollama_host.rstrip("/")
    model = settings.ollama_model
    try:
        tags = httpx.get(f"{host}/api/tags", timeout=5.0).json()
        names = [m.get("name", "") for m in tags.get("models", [])]
    except Exception as exc:
        fail(f"could not query installed models: {exc}")
        return
    base = model.split(":")[0]
    if any(n == model or n.split(":")[0] == base for n in names):
        ok(f"model '{model}' already present")
        return
    print(f"pulling '{model}' (this can take a while) ...")
    rc = subprocess.call(["ollama", "pull", model])
    if rc != 0:
        fail(f"ollama pull {model} failed", "Check the model name and your connection, then re-run.")
    ok(f"pulled '{model}'")


def test_model_responds() -> None:
    from app.config.settings import settings
    import httpx

    step(6, "Test that the model responds")
    host = settings.ollama_host.rstrip("/")
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "stream": False,
    }
    try:
        resp = httpx.post(f"{host}/api/chat", json=payload, timeout=settings.ollama_timeout_seconds)
        resp.raise_for_status()
        content = (resp.json().get("message") or {}).get("content", "")
    except Exception as exc:
        fail(f"model test call failed: {exc}", "Confirm the model is pulled and ollama has enough RAM.")
        return
    if not content.strip():
        fail("model returned an empty response", "Try a smaller model (e.g. moondream) or increase RAM/swap.")
    ok(f"model responded: {content.strip()[:60]!r}")


def main() -> None:
    print("RasperifyScanner — local setup & preflight\n" + "=" * 44)
    install_deps()
    ensure_model()
    check_ollama_binary()
    ensure_ollama_service()
    ensure_model_pulled()
    test_model_responds()
    print(f"\n{GREEN}All checks passed. The scanner is ready to run fully offline.{RESET}")
    print("Start it with:  uvicorn main:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
