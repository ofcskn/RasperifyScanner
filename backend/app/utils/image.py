"""Frame preprocessing helpers — Information Expert for image transformations."""
import base64
import io

from PIL import Image


def resize_and_encode(raw_bytes: bytes, width: int = 1280, height: int = 720, quality: int = 85) -> str:
    """Resize frame to target resolution and return base64-encoded JPEG string."""
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def base64_to_bytes(encoded: str) -> bytes:
    return base64.b64decode(encoded)
