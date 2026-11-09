import hashlib
import json


def calculate_payload_hash(
    payload: list[dict[str, object]],
) -> str:
    """Return a deterministic SHA-256 hash for a JSON API payload."""
    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    payload_bytes = serialized_payload.encode("utf-8")

    return hashlib.sha256(payload_bytes).hexdigest()
