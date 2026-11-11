import hashlib
import json
import re

import pytest

from financial_pipeline.pipeline.exchange_rates import calculate_payload_hash


@pytest.fixture
def payload() -> list[dict[str, object]]:
    return [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1625,
        }
    ]


def test_same_payload_produces_same_hash(
    payload: list[dict[str, object]],
) -> None:
    first_hash = calculate_payload_hash(payload)
    second_hash = calculate_payload_hash(payload)

    assert first_hash == second_hash


def test_dictionary_key_order_does_not_change_hash() -> None:
    payload_1 = [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1625,
        }
    ]

    payload_2 = [
        {
            "rate": 1.1625,
            "quote": "USD",
            "base": "EUR",
            "date": "2026-01-15",
        }
    ]

    assert calculate_payload_hash(payload_1) == calculate_payload_hash(payload_2)


def test_changed_value_produces_different_hash(
    payload: list[dict[str, object]],
) -> None:
    modified_payload = [
        {
            **payload[0],
            "rate": 1.20,
        }
    ]

    original_hash = calculate_payload_hash(payload)
    modified_hash = calculate_payload_hash(modified_payload)

    assert original_hash != modified_hash


def test_list_order_changes_hash() -> None:
    payload_1 = [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1625,
        },
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "GBP",
            "rate": 0.8650,
        },
    ]

    payload_2 = list(reversed(payload_1))

    assert calculate_payload_hash(payload_1) != calculate_payload_hash(payload_2)


def test_hash_has_valid_sha256_format(
    payload: list[dict[str, object]],
) -> None:
    result = calculate_payload_hash(payload)

    assert len(result) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", result) is not None


def test_hash_matches_canonical_sha256(
    payload: list[dict[str, object]],
) -> None:
    canonical_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    expected_hash = hashlib.sha256(
        canonical_payload.encode("utf-8"),
    ).hexdigest()

    assert calculate_payload_hash(payload) == expected_hash
