"""Shared AI prompts for environment analysis."""

ENVIRONMENT_SCAN_PROMPT = (
    "Analyze this image for environmental context. "
    "Return ONLY valid JSON with this exact structure: "
    '{"people_count": <integer>, '
    '"environment_type": "<one of: train, bus, subway, tram, club, bar, restaurant, cafe, park, street, office, shop, stadium, waiting_room, unknown>", '
    '"crowd_density": "<one of: empty, sparse, moderate, dense, packed>", '
    '"ambient_conditions": {"lighting": "<one of: bright, normal, dim, dark>", "estimated_time": "<one of: day, night, unknown>"}, '
    '"notable_observations": ["<string>", ...], '
    '"detections": [{"object_name": "<str>", "confidence": <0.0-1.0>, "bbox": null}], '
    '"metrics": {"brightness": <float>, "sharpness": <float>}}'
)
