"""CameraService — Information Expert (GRASP): owns picamera2 and the frame queue.

Falls back to a mock capture when running outside Raspberry Pi (CAMERA_MOCK=true or picamera2 absent).
"""
import asyncio
import base64
import io
import logging
import queue
import threading
import uuid
from typing import NamedTuple

from app.config.settings import settings
from app.utils.image import resize_and_encode

logger = logging.getLogger(__name__)


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

    def set_quality(self, quality: int) -> None:
        self._jpeg_quality = max(10, min(95, quality))

    # --- Information Expert: private camera knowledge ---

    @staticmethod
    def _try_import_picamera() -> bool:
        try:
            import picamera2  # noqa: F401
            return True
        except ImportError:
            return False

    def _open_camera(self):
        from picamera2 import Picamera2  # type: ignore
        cam = Picamera2()
        config = cam.create_still_configuration(
            main={"size": (settings.camera_resolution_width, settings.camera_resolution_height)}
        )
        cam.configure(config)
        cam.start()
        return cam

    def _capture_real(self) -> bytes:
        import io as _io
        buf = _io.BytesIO()
        self._camera.capture_file(buf, format="jpeg")
        return buf.getvalue()

    def _capture_mock(self) -> bytes:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (settings.camera_resolution_width, settings.camera_resolution_height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "RasperifyScanner MOCK FRAME", fill=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def _capture_one(self) -> CapturedFrame:
        raw = self._capture_mock() if self._mock else self._capture_real()
        encoded = resize_and_encode(raw, settings.camera_resolution_width, settings.camera_resolution_height, self._jpeg_quality)
        return CapturedFrame(frame_id=str(uuid.uuid4()), frame_base64=encoded)

    # --- Controller interface ---

    def _run(self) -> None:
        if not self._mock:
            self._camera = self._open_camera()
        logger.info("CameraService started (mock=%s)", self._mock)
        while self._running:
            try:
                frame = self._capture_one()
                try:
                    self._queue.put_nowait(frame)
                except queue.Full:
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
            except Exception as exc:
                logger.error("Frame capture error: %s", exc)

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

    def capture_now(self) -> CapturedFrame:
        return self._capture_one()

    def get_latest_frame(self) -> CapturedFrame | None:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    @property
    def is_connected(self) -> bool:
        return self._mock or self._camera is not None


camera_service = CameraService()
