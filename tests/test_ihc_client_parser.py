from __future__ import annotations

from src.ihc_client import _parse_response


def test_parse_response_reads_value_key() -> None:
    payload = {
        "statusCode": 200,
        "value": [
            {"conversion_id": "c1", "session_id": "s1", "ihc": 0.7},
            {"conversion_id": "c1", "session_id": "s2", "ihc": 0.3},
        ],
        "partialFailureErrors": [],
    }

    parsed = _parse_response(payload)

    assert len(parsed) == 2
    assert parsed[0]["session_id"] == "s1"


def test_parse_response_returns_empty_on_unknown_shape() -> None:
    parsed = _parse_response({"statusCode": 200, "unknown": []})
    assert parsed == []
