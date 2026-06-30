"""Frame preprocessing helpers — Information Expert for image transformations."""
import base64
import io

from PIL import Image


# Clockwise degrees -> PIL Transpose (lossless 90° steps, no interpolation blur).
_ROTATE_OPS = {
    90: Image.Transpose.ROTATE_270,   # PIL ROTATE_* is counter-clockwise
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_90,
}


def resize_and_encode(
    raw_bytes: bytes, width: int = 1280, height: int = 720, quality: int = 85, rotation: int = 0
) -> str:
    """Resize frame to target resolution and return base64-encoded JPEG string.

    `rotation` is a clockwise correction (0/90/180/270) for the physical camera
    mount, applied after the resize. For 90/270 the result is portrait (H x W),
    which is the physically correct orientation for a sideways-mounted camera.
    """
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    op = _ROTATE_OPS.get(rotation % 360)
    if op is not None:
        img = img.transpose(op)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def base64_to_bytes(encoded: str) -> bytes:
    return base64.b64decode(encoded)
