from __future__ import annotations

import pandas as pd

from src.tasks.extract_journeys import journeys_to_api_payload


def test_journeys_to_api_payload_shapes_rows_and_conversion_flag() -> None:
    df = pd.DataFrame(
        [
            {
                "conv_id": "c1",
                "user_id": "u1",
                "conv_date": "2023-09-01",
                "conv_time": "12:00:00",
                "revenue": 10.0,
                "session_id": "s1",
                "event_date": "2023-08-31",
                "event_time": "10:00:00",
                "channel_name": "Email",
                "holder_engagement": 1,
                "closer_engagement": 0,
                "impression_interaction": 0,
            },
            {
                "conv_id": "c1",
                "user_id": "u1",
                "conv_date": "2023-09-01",
                "conv_time": "12:00:00",
                "revenue": 10.0,
                "session_id": "s2",
                "event_date": "2023-09-01",
                "event_time": "11:00:00",
                "channel_name": "Direct",
                "holder_engagement": 1,
                "closer_engagement": 1,
                "impression_interaction": 0,
            },
        ]
    )

    payload = journeys_to_api_payload(df)

    assert len(payload) == 2
    assert payload[0]["conversion_id"] == "c1"
    assert payload[0]["session_id"] == "s1"
    assert payload[0]["timestamp"] == "2023-08-31 10:00:00"
    assert payload[0]["channel_label"] == "Email"
    assert payload[0]["conversion"] == 0
    assert payload[1]["conversion"] == 1


def test_journeys_to_api_payload_honors_max_journeys() -> None:
    df = pd.DataFrame(
        [
            {
                "conv_id": "c1",
                "user_id": "u1",
                "conv_date": "2023-09-01",
                "conv_time": "12:00:00",
                "revenue": 10.0,
                "session_id": "s1",
                "event_date": "2023-08-31",
                "event_time": "10:00:00",
                "channel_name": "Email",
                "holder_engagement": 1,
                "closer_engagement": 0,
                "impression_interaction": 0,
            },
            {
                "conv_id": "c2",
                "user_id": "u2",
                "conv_date": "2023-09-01",
                "conv_time": "12:00:00",
                "revenue": 12.0,
                "session_id": "s2",
                "event_date": "2023-08-31",
                "event_time": "12:00:00",
                "channel_name": "Direct",
                "holder_engagement": 0,
                "closer_engagement": 1,
                "impression_interaction": 0,
            },
        ]
    )

    payload = journeys_to_api_payload(df, max_journeys=1)

    journey_ids = {row["conversion_id"] for row in payload}
    assert journey_ids == {"c1"}
