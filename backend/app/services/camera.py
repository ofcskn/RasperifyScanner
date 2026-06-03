"""CameraService — Information Expert (GRASP): owns picamera2 and the frame queue.

Falls back to a mock capture when running outside Raspberry Pi (CAMERA_MOCK=true or picamera2 absent).

KEY: uses create_video_configuration (continuous streaming), NOT create_still_configuration.
Still configuration is designed for single-shot captures and stalls when called in a loop,
which caused the "No Signal" issue on the Pi.
"""
import io
import logging
import queue
import threading
import time
import uuid
from typing import NamedTuple

from app.config.settings import settings
from app.utils.image import resize_and_encode

logger = logging.getLogger(__name__)

# Seconds between captures in the _run() loop. 0.5 s ≈ 2 fps, which comfortably
# feeds the 1-fps live broadcaster without hammering the Pi CPU.
_CAPTURE_INTERVAL = 0.5


class CapturedFrame(NamedTuple):
    frame_id: str
    frame_base64: str


class CameraService:
    def __init__(self) -> None:
        self._queue: queue.Queue[CapturedFrame] = queue.Queue(maxsize=settings.camera_frame_queue_size)
        self._running = False
        self._thread: threading.Thread | None = None
        self._camera = None
        self._mock = settings.camera_mock or not self._try_import_picamera()
        self._jpeg_quality: int = settings.camera_jpeg_quality
        self._capture_ok: bool = False

    def set_quality(self, quality: int) -> None:
        self._jpeg_quality = max(10, min(95, quality))

    # --- picamera2 availability probe ---

    @staticmethod
    def _try_import_picamera() -> bool:
        try:
            import picamera2  # noqa: F401
            return True
        except ImportError:
            return False

    # --- camera lifecycle ---

    def _open_camera(self):
        from picamera2 import Picamera2
        cam = Picamera2()
        # Video configuration keeps the sensor in continuous capture mode.
        # RGB888 gives a plain (H, W, 3) uint8 array that PIL handles directly.
        config = cam.create_video_configuration(
            main={
                "size": (settings.camera_resolution_width, settings.camera_resolution_height),
                "format": "RGB888",
            }
        )
        cam.configure(config)
        cam.start()
        # Allow AE/AWB to settle before the first frame is queued.
        time.sleep(1.0)
        return cam

    # --- capture helpers ---

    def _capture_real(self) -> bytes:
        from PIL import Image
        if self._camera is None:
            raise RuntimeError("Camera is not open")
        # capture_array returns (H, W, 3) uint8 in RGB order for RGB888 format.
        array = self._camera.capture_array("main")
        img = Image.fromarray(array)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self._jpeg_quality)
        return buf.getvalue()

    def _capture_mock(self) -> bytes:
        from PIL import Image, ImageDraw
        img = Image.new(
            "RGB",
            (settings.camera_resolution_width, settings.camera_resolution_height),
            color=(30, 30, 30),
        )
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "RasperifyScanner MOCK FRAME", fill=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def _capture_one(self) -> CapturedFrame:
        raw = self._capture_mock() if self._mock else self._capture_real()
        encoded = resize_and_encode(
            raw,
            settings.camera_resolution_width,
            settings.camera_resolution_height,
            self._jpeg_quality,
        )
        return CapturedFrame(frame_id=str(uuid.uuid4()), frame_base64=encoded)

    # --- background capture loop ---

    def _run(self) -> None:
        if not self._mock:
            try:
                self._camera = self._open_camera()
                self._capture_ok = True
            except Exception as exc:
                logger.error("Camera open failed: %s", exc)
                self._capture_ok = False
                return
        logger.info("CameraService started (mock=%s)", self._mock)
        while self._running:
            try:
                frame = self._capture_one()
                self._capture_ok = True
                try:
                    self._queue.put_nowait(frame)
                except queue.Full:
                    # Drop oldest frame to make room for the latest.
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
            except Exception as exc:
                self._capture_ok = False
                logger.error("Frame capture error: %s", exc)
            time.sleep(_CAPTURE_INTERVAL)

    # --- public interface ---

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None
        self._capture_ok = False

    def capture_now(self) -> CapturedFrame:
        """One-shot capture used by the analysis pipeline.

        If live mode is not active (_camera is None) and we're on real hardware,
        opens a temporary camera session, captures one frame, and closes it.
        """
        if not self._mock and self._camera is None:
            cam = None
            try:
                cam = self._open_camera()
                self._camera = cam
                frame = self._capture_one()
                return frame
            finally:
                if cam is not None:
                    try:
                        cam.stop()
                    except Exception:
                        pass
                self._camera = None
        return self._capture_one()

    def get_latest_frame(self) -> CapturedFrame | None:
        """Thread-safe read of the most recent queued frame."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    @property
    def is_connected(self) -> bool:
        # _running must be True (start() was called) in all modes.
        # Without this, mock mode always returned True even before the
        # capture thread was started, making the UI show "Disconnect Camera"
        # on first load and preventing any frames from ever being broadcast.
        if not self._running:
            return False
        return self._mock or self._capture_ok


camera_service = CameraService()
