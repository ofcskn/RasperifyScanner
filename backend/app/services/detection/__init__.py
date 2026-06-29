"""On-device object/person detection (Stage 1).

Mirrors the AIProvider pattern (Polymorphism + Indirection, GRASP): a pluggable
`Detector` backend, a tracker that maintains live + cumulative people counts, and
a `DetectionService` singleton that the live broadcaster calls per frame.
"""
