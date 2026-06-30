"""OnnxYoloDetector — concrete Detector running a YOLOv8/YOLO11-n model via ONNX Runtime.

Design notes for Raspberry Pi:
- onnxruntime + numpy are imported lazily so the module loads (and the rest of the
  app boots) even when they are not installed; `available` reports the real state.
- Execution providers are tried in priority order. On a Pi 4B only
  "CPUExecutionProvider" exists, but listing NPU/GPU providers first means the same
  code transparently uses a Hailo/Coral/CUDA backend if one is ever present — the
  "CPU/NPU/GPU fallback" requirement.
- Letterboxing uses PIL (already a dependency); post-processing is plain NumPy, so
  OpenCV is not required for the detection path.
"""
from __future__ import annotations

import base64
import io
import logging

from app.services.detection.base import Detection, Detector
from app.services.detection.coco_labels import COCO_LABELS

logger = logging.getLogger(__name__)

# Providers in descending preference. Missing providers are silently skipped by ORT.
_PREFERRED_PROVIDERS = [
    "CUDAExecutionProvider",
    "ROCMExecutionProvider",
    "OpenVINOExecutionProvider",
    "CPUExecutionProvider",
]
_PAD_COLOR = (114, 114, 114)


class OnnxYoloDetector(Detector):
    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        target_labels: list[str] | None = None,
        input_size: int = 640,
        num_threads: int = 0,
    ) -> None:
        self._model_path = model_path
        self._conf = conf_threshold
        self._iou = iou_threshold
        self._target = set(target_labels) if target_labels else None
        self._input_size = input_size
        self._num_threads = num_threads
        self._session = None
        self._input_name: str | None = None
        self._np = None
        self._load()

    # --- lifecycle ---

    def _load(self) -> None:
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as exc:
            logger.warning(
                "OnnxYoloDetector: numpy/onnxruntime not installed (%s) — detector unavailable. "
                "Run scripts/setup_local.py or pip install onnxruntime numpy.",
                exc,
            )
            return
        import os

        if not os.path.exists(self._model_path):
            logger.warning(
                "OnnxYoloDetector: model not found at %s — detector unavailable. "
                "Run scripts/setup_local.py to download it.",
                self._model_path,
            )
            return
        try:
            # On a CPU-only Pi, ORT otherwise grabs every core for inference and
            # starves the capture thread / event loop. Resolve 0 -> "cores - 1"
            # (min 1) so the system stays responsive while YOLO runs.
            sess_options = ort.SessionOptions()
            threads = self._num_threads
            if threads <= 0:
                threads = max(1, (os.cpu_count() or 2) - 1)
            sess_options.intra_op_num_threads = threads
            sess_options.inter_op_num_threads = 1
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                self._model_path, sess_options=sess_options, providers=_PREFERRED_PROVIDERS
            )
            self._input_name = self._session.get_inputs()[0].name
            shape = self._session.get_inputs()[0].shape
            # Static square models expose their input size; fall back to the default.
            if isinstance(shape[-1], int) and shape[-1] > 0:
                self._input_size = int(shape[-1])
            self._np = np
            logger.info(
                "OnnxYoloDetector loaded %s (input=%d, intra_op_threads=%d, providers=%s)",
                self._model_path, self._input_size, threads, self._session.get_providers(),
            )
        except Exception as exc:  # pragma: no cover - depends on ORT/model
            logger.error("OnnxYoloDetector failed to load %s: %s", self._model_path, exc)
            self._session = None

    @property
    def name(self) -> str:
        return "onnx-yolo"

    @property
    def available(self) -> bool:
        return self._session is not None

    def set_thresholds(self, conf: float | None = None, iou: float | None = None) -> None:
        if conf is not None:
            self._conf = max(0.0, min(1.0, conf))
        if iou is not None:
            self._iou = max(0.0, min(1.0, iou))

    # --- inference ---

    def detect(self, frame_base64: str) -> list[Detection]:
        if self._session is None:
            return []
        np = self._np
        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(frame_base64))).convert("RGB")
        orig_w, orig_h = img.size
        tensor, scale, pad_x, pad_y = self._letterbox(img, np)

        outputs = self._session.run(None, {self._input_name: tensor})
        preds = outputs[0]  # (1, 84, 8400) for YOLOv8/YOLO11

        return self._postprocess(preds, np, scale, pad_x, pad_y, orig_w, orig_h)

    def _letterbox(self, img, np):
        from PIL import Image

        size = self._input_size
        orig_w, orig_h = img.size
        scale = min(size / orig_w, size / orig_h)
        new_w, new_h = round(orig_w * scale), round(orig_h * scale)
        resized = img.resize((new_w, new_h), Image.BILINEAR)
        canvas = Image.new("RGB", (size, size), _PAD_COLOR)
        pad_x, pad_y = (size - new_w) // 2, (size - new_h) // 2
        canvas.paste(resized, (pad_x, pad_y))

        arr = np.asarray(canvas, dtype=np.float32) / 255.0  # HWC, RGB, 0..1
        arr = arr.transpose(2, 0, 1)[np.newaxis, ...]  # 1,C,H,W
        return np.ascontiguousarray(arr), scale, pad_x, pad_y

    def _postprocess(self, preds, np, scale, pad_x, pad_y, orig_w, orig_h) -> list[Detection]:
        # preds: (1, 84, N) -> (N, 84): [cx, cy, w, h, 80 class scores]
        p = np.squeeze(preds, axis=0)
        if p.shape[0] < p.shape[1]:
            p = p.transpose(1, 0)
        boxes_xywh = p[:, :4]
        scores_all = p[:, 4:]
        class_ids = scores_all.argmax(axis=1)
        confidences = scores_all[np.arange(scores_all.shape[0]), class_ids]

        keep = confidences >= self._conf
        boxes_xywh, class_ids, confidences = boxes_xywh[keep], class_ids[keep], confidences[keep]
        if boxes_xywh.shape[0] == 0:
            return []

        # xywh (input space) -> xyxy (input space) -> undo letterbox -> original pixels
        cx, cy, w, h = boxes_xywh[:, 0], boxes_xywh[:, 1], boxes_xywh[:, 2], boxes_xywh[:, 3]
        x1 = (cx - w / 2 - pad_x) / scale
        y1 = (cy - h / 2 - pad_y) / scale
        x2 = (cx + w / 2 - pad_x) / scale
        y2 = (cy + h / 2 - pad_y) / scale
        xyxy = np.stack([x1, y1, x2, y2], axis=1)

        idxs = self._nms(xyxy, confidences, class_ids, np)

        detections: list[Detection] = []
        for i in idxs:
            cid = int(class_ids[i])
            label = COCO_LABELS[cid] if 0 <= cid < len(COCO_LABELS) else str(cid)
            if self._target is not None and label not in self._target:
                continue
            nx1 = float(np.clip(xyxy[i, 0] / orig_w, 0.0, 1.0))
            ny1 = float(np.clip(xyxy[i, 1] / orig_h, 0.0, 1.0))
            nx2 = float(np.clip(xyxy[i, 2] / orig_w, 0.0, 1.0))
            ny2 = float(np.clip(xyxy[i, 3] / orig_h, 0.0, 1.0))
            detections.append(
                Detection(label=label, confidence=float(confidences[i]), bbox=[nx1, ny1, nx2, ny2])
            )
        return detections

    def _nms(self, boxes, scores, class_ids, np) -> list[int]:
        """Class-aware greedy NMS in NumPy (avoids an OpenCV dependency)."""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
        order = scores.argsort()[::-1]
        keep: list[int] = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            if order.size == 1:
                break
            rest = order[1:]
            xx1 = np.maximum(x1[i], x1[rest])
            yy1 = np.maximum(y1[i], y1[rest])
            xx2 = np.minimum(x2[i], x2[rest])
            yy2 = np.minimum(y2[i], y2[rest])
            inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
            union = areas[i] + areas[rest] - inter
            iou = np.where(union > 0, inter / union, 0.0)
            # Suppress only same-class overlaps; different classes may overlap freely.
            same_class = class_ids[rest] == class_ids[i]
            suppress = (iou > self._iou) & same_class
            order = rest[~suppress]
        return keep
