"""CentroidTracker + PeopleCounter — cross-frame identity and people counting.

Pure-Python (no NumPy) so it runs and tests anywhere. The tracker matches the
current frame's boxes to existing tracks by IoU, carries forward stable track_ids,
and evicts tracks that go unseen for `max_age` frames. PeopleCounter derives:
  - live:       persons in the current frame
  - cumulative: distinct persons confirmed since reset (deduplicated by track_id)

The "when does a track count as a new unique person" rule is intentionally a small,
self-contained method (`PeopleCounter._register`) — it is the main behavioral knob
(sensitivity vs. double-counting) and is easy to tune.
"""
from __future__ import annotations

from app.services.detection.base import Detection


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class _Track:
    __slots__ = ("id", "bbox", "label", "missed", "hits")

    def __init__(self, track_id: int, det: Detection) -> None:
        self.id = track_id
        self.bbox = det.bbox
        self.label = det.label
        self.missed = 0
        self.hits = 1


class CentroidTracker:
    def __init__(self, iou_match_threshold: float = 0.3, max_age: int = 15) -> None:
        self._iou_match = iou_match_threshold
        self._max_age = max_age
        self._tracks: dict[int, _Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Detection]:
        """Assign stable track_ids to `detections` and age out stale tracks."""
        unmatched_track_ids = set(self._tracks.keys())

        # Greedy IoU matching: highest-IoU (detection, track) pairs first.
        pairs: list[tuple[float, int, int]] = []
        for di, det in enumerate(detections):
            for tid, track in self._tracks.items():
                if track.label != det.label:
                    continue
                score = _iou(det.bbox, track.bbox)
                if score >= self._iou_match:
                    pairs.append((score, di, tid))
        pairs.sort(reverse=True)

        matched_dets: dict[int, int] = {}
        used_tracks: set[int] = set()
        for _, di, tid in pairs:
            if di in matched_dets or tid in used_tracks:
                continue
            matched_dets[di] = tid
            used_tracks.add(tid)

        for di, det in enumerate(detections):
            tid = matched_dets.get(di)
            if tid is None:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _Track(tid, det)
            else:
                track = self._tracks[tid]
                track.bbox = det.bbox
                track.missed = 0
                track.hits += 1
                unmatched_track_ids.discard(tid)
            det.track_id = tid

        # Age and evict tracks that were not matched this frame.
        for tid in unmatched_track_ids:
            track = self._tracks[tid]
            track.missed += 1
            if track.missed > self._max_age:
                del self._tracks[tid]

        return detections

    def track_hits(self, track_id: int) -> int:
        track = self._tracks.get(track_id)
        return track.hits if track else 0

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1


class PeopleCounter:
    """Derives live + cumulative people counts from tracked detections."""

    def __init__(self, tracker: CentroidTracker, person_label: str = "person", min_hits: int = 3) -> None:
        self._tracker = tracker
        self._person_label = person_label
        self._min_hits = min_hits
        self._unique_ids: set[int] = set()

    def update(self, tracked: list[Detection]) -> dict[str, int]:
        live = 0
        for det in tracked:
            if det.label != self._person_label:
                continue
            live += 1
            self._register(det)
        return {"live": live, "cumulative": len(self._unique_ids)}

    def _register(self, det: Detection) -> None:
        """Decide whether a tracked person counts toward the cumulative unique total.

        Default rule: a track must be confirmed across `min_hits` frames (debounce)
        before it is counted once. This suppresses single-frame false positives at
        the cost of a few frames of latency. Tune `min_hits` (or add dwell-time /
        line-crossing logic) to trade sensitivity against double-counting.
        """
        if det.track_id is None or det.track_id in self._unique_ids:
            return
        if self._tracker.track_hits(det.track_id) >= self._min_hits:
            self._unique_ids.add(det.track_id)

    @property
    def cumulative(self) -> int:
        return len(self._unique_ids)

    def reset(self) -> None:
        self._unique_ids.clear()
        self._tracker.reset()
