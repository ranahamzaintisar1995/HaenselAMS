from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


class IhcClientError(RuntimeError):
    """Raised when the IHC API request or response is invalid."""


@dataclass
class IhcClient:
    api_url: str
    api_key: str | None
    conv_type_id: str
    redistribution_parameter: dict[str, Any] | None = None
    timeout_seconds: int = 30
    _call_count: int = 0

    def score_journeys(self, journeys: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Send one batched compute request to IHC and parse attribution rows.

        Args:
            journeys: Flat list of session-level dictionaries in IHC
                `customer_journeys` format.

        Returns:
            List of attribution result rows parsed from the API response.

        Raises:
            IhcClientError: If API key is missing, request fails, or response
                payload is invalid.
        """
        self._call_count += 1
        unique_journeys = len(
            {
                str(item.get("conversion_id", ""))
                for item in journeys
                if item.get("conversion_id")
            }
        )
        logger.info(
            f"IHC API Request #{self._call_count}: Sending {len(journeys)} sessions across {unique_journeys} journeys to {self.api_url}?conv_type_id={self.conv_type_id}"
        )

        if not self.api_key:
            raise IhcClientError("No API key provided. Set IHC_API_KEY in .env")

        # Build URL with conv_type_id parameter
        url = f"{self.api_url}?conv_type_id={self.conv_type_id}"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        body: dict[str, Any] = {"customer_journeys": journeys}
        if self.redistribution_parameter:
            body["redistribution_parameter"] = self.redistribution_parameter

        try:
            response = requests.post(
                url,
                data=json.dumps(body),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except Exception as e:
            raise IhcClientError(f"Failed to call IHC API: {e}")

        logger.info(f"IHC API Response #{self._call_count}: Status {response.status_code}")

        if response.status_code >= 400:
            raise IhcClientError(
                f"IHC API request failed with status={response.status_code}: {response.text}"
            )

        payload = response.json()
        status_code = payload.get("statusCode") if isinstance(payload, dict) else None
        if isinstance(status_code, int) and status_code >= 400:
            raise IhcClientError(
                f"IHC API request failed with statusCode={status_code}: {payload}"
            )

        parsed = _parse_response(payload)

        if not parsed:
            raise IhcClientError("IHC API response contained no attribution results")

        logger.info(f"IHC API Response #{self._call_count}: Parsed {len(parsed)} attribution rows")
        return parsed

    @property
    def call_count(self) -> int:
        """Return number of IHC API calls sent by this client instance."""
        return self._call_count



def _parse_response(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    """Extract attribution rows from supported API response shapes.

    Args:
        payload: Parsed JSON response payload from IHC API.

    Returns:
        List of attribution dictionaries. Returns empty list when no supported
        result key is present.
    """
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("attribution_customer_journey", "results", "data", "value"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    return []
