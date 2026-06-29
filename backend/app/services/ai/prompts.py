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

# Tuned for small local vision models (moondream/llava): one short instruction,
# an explicit schema, and a worked example. Small models drift without an example
# and tend to add prose — we pair this with Ollama's format="json" mode and a
# tolerant parser. detections/bbox are left to the on-device YOLO detector, so the
# model only needs to describe the scene and estimate the crowd.
OLLAMA_ENVIRONMENT_SCAN_PROMPT = (
    "You are a security camera scene analyst. Look at the image and respond with a "
    "SINGLE JSON object and nothing else. Use exactly these keys:\n"
    '{"people_count": integer, '
    '"environment_type": one of [train, bus, subway, tram, club, bar, restaurant, cafe, park, street, office, shop, stadium, waiting_room, unknown], '
    '"crowd_density": one of [empty, sparse, moderate, dense, packed], '
    '"ambient_conditions": {"lighting": one of [bright, normal, dim, dark], "estimated_time": one of [day, night, unknown]}, '
    '"notable_observations": array of short strings describing anything notable or anomalous, '
    '"metrics": {"brightness": number 0-1, "sharpness": number 0-1}}\n'
    'Example: {"people_count": 2, "environment_type": "office", "crowd_density": "sparse", '
    '"ambient_conditions": {"lighting": "normal", "estimated_time": "day"}, '
    '"notable_observations": ["a person near the door"], "metrics": {"brightness": 0.6, "sharpness": 0.7}}'
)
