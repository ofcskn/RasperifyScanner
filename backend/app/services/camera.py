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
        self._jpeg_quality: int = settings.camera_jpeg_quality
        self._capture_ok: bool = False
        # Most recent frame captured by the _run() loop. capture_now() reuses this
        # while the live thread owns the camera, so analysis never opens a second
        # picamera2 handle (only one process may hold the Pi camera at a time).
        self._latest: CapturedFrame | None = None

        self._source = settings.camera_source
        self._capture = None  # OpenCV VideoCapture handle, when used
        # Mode is chosen from camera_source: picamera2 (CSI), opencv (USB/RTSP/HTTP),
        # or mock. Mock wins when forced or when the chosen backend is unavailable.
        if settings.camera_mock:
            self._mode = "mock"
            logger.info("CameraService: mock mode enabled via CAMERA_MOCK setting")
        elif self._is_opencv_source(self._source):
            self._mode = "opencv" if self._try_import_cv2() else "mock"
            if self._mode == "mock":
                logger.warning("CameraService: opencv source '%s' but cv2 unavailable — mock mode", self._source)
        elif self._try_import_picamera():
            self._mode = "picamera2"
        else:
            self._mode = "mock"
            logger.warning(
                "CameraService: picamera2 not importable — falling back to mock mode. "
                "Install picamera2 and libcamera bindings, or set CAMERA_SOURCE to a USB/RTSP source."
            )
        self._mock = self._mode == "mock"

    def set_quality(self, quality: int) -> None:
        self._jpeg_quality = max(10, min(95, quality))

    # --- picamera2 availability probe ---

    @staticmethod
    def _try_import_picamera() -> bool:
        try:
            import picamera2  # noqa: F401
            import libcamera  # noqa: F401  # C extension; must be present for picamera2 to work
            return True
        except Exception:
            return False

    @staticmethod
    def _try_import_cv2() -> bool:
        try:
            import cv2  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _is_opencv_source(source: str) -> bool:
        s = (source or "").lower()
        return s.startswith(("usb:", "rtsp://", "http://", "https://", "/dev/video")) or s.isdigit()

    def _cv2_target(self):
        """Resolve camera_source into an OpenCV VideoCapture target (index or URL)."""
        s = self._source
        if s.lower().startswith("usb:"):
            rest = s.split(":", 1)[1]
            return int(rest) if rest.isdigit() else rest
        if s.isdigit():
            return int(s)
        return s  # rtsp:// | http:// | /dev/videoN

    # --- camera lifecycle ---

    def _open_camera(self):
        if self._mode == "opencv":
            return self._open_opencv()
        from picamera2 import Picamera2
        cam = Picamera2()
        # Video configuration keeps the sensor in continuous capture mode.
        # libcamera format names are byte-order reversed vs. the numpy array you
        # get back: "RGB888" yields a BGR array, "BGR888" yields an RGB array.
        # We feed the array straight into PIL (which expects RGB), so we MUST
        # request "BGR888" — otherwise red/blue are swapped, the live preview is
        # tinted, and YOLO misclassifies (e.g. a person reads as a cat/dog).
        config = cam.create_video_configuration(
            main={
                "size": (settings.camera_resolution_width, settings.camera_resolution_height),
                "format": "BGR888",
            }
        )
        cam.configure(config)
        cam.start()
        # Allow AE/AWB to settle before the first frame is queued.
        time.sleep(1.0)
        return cam

    # --- capture helpers ---

    def _open_opencv(self):
        import cv2
        target = self._cv2_target()
        cap = cv2.VideoCapture(target)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_resolution_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_resolution_height)
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open camera source '{self._source}'")
        self._capture = cap
        time.sleep(0.5)  # let the stream/sensor settle
        return cap

    def _capture_real(self) -> bytes:
        from PIL import Image
        if self._mode == "opencv":
            return self._capture_opencv()
        if self._camera is None:
            raise RuntimeError("Camera is not open")
        # capture_array returns (H, W, 3) uint8 in RGB order for RGB888 format.
        array = self._camera.capture_array("main")
        img = Image.fromarray(array)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self._jpeg_quality)
        return buf.getvalue()

    def _capture_opencv(self) -> bytes:
        import cv2
        from PIL import Image
        if self._capture is None:
            raise RuntimeError("OpenCV capture is not open")
        ok, frame_bgr = self._capture.read()
        if not ok or frame_bgr is None:
            raise RuntimeError("OpenCV frame read failed (camera disconnected?)")
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
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
                logger.error(
                    "Camera open failed: %s\n"
                    "  → Ensure the camera ribbon is connected and the camera is enabled.\n"
                    "  → If running in Docker, check that libcamera.so and picamera2 are\n"
                    "    mounted from the host (see docker-compose.yml Pi camera volumes).\n"
                    "  → Set CAMERA_MOCK=true to use a synthetic test feed.",
                    exc,
                )
                self._capture_ok = False
                return
        logger.info("CameraService started (mock=%s)", self._mock)
        while self._running:
            try:
                frame = self._capture_one()
                self._capture_ok = True
                self._latest = frame
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

    def _close_handle(self) -> None:
        if self._mode == "opencv" and self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
            self._capture = None
        if self._camera is not None and self._mode != "opencv":
            try:
                self._camera.stop()
            except Exception:
                pass
            # stop() only halts streaming; close() releases the camera device.
            # Without it the sensor stays held and the next Picamera2() raises
            # "Failed to acquire camera: Device or resource busy".
            try:
                self._camera.close()
            except Exception:
                pass
        self._camera = None

    def stop(self) -> None:
        self._running = False
        self._close_handle()
        self._capture_ok = False
        self._latest = None

    def capture_now(self) -> CapturedFrame:
        """One-shot capture used by the analysis pipeline.

        While the live capture thread is running it owns the camera exclusively,
        so we reuse its most recent frame instead of touching picamera2 from
        another thread or opening a second handle (which raises "Device or
        resource busy"). When live mode is off, we open a temporary session,
        capture one frame, and release the device.
        """
        if self._running and not self._mock:
            if self._latest is not None:
                return self._latest
            # Live thread is still warming up (no frame yet); fall through only
            # if no handle is open, otherwise reuse the shared open handle.
            if self._camera is not None:
                return self._capture_one()

        if not self._mock and self._camera is None:
            try:
                self._camera = self._open_camera()
                return self._capture_one()
            finally:
                self._close_handle()
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
