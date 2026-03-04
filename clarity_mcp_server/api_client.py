"""
Microsoft Clarity API Client
"""

import os
import asyncio
import logging
import httpx
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ClarityAPIClient:
    """Microsoft Clarity API Client"""

    # API Base URL
    API_BASE_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"

    # Available metrics that may be returned by the API
    AVAILABLE_METRICS = [
        "ScrollDepth",
        "EngagementTime",
        "Traffic",
        "PopularPages",
        "Browser",
        "Device",
        "OS",
        "Country/Region",
        "PageTitle",
        "ReferrerURL",
        "DeadClickCount",
        "ExcessiveScroll",
        "RageClickCount",
        "QuickbackClick",
        "ScriptErrorCount",
        "ErrorClickCount"
    ]

    # Available dimensions that can be used in queries
    AVAILABLE_DIMENSIONS = [
        "Browser",
        "Device",
        "Country/Region",
        "OS",
        "Source",
        "Medium",
        "Campaign",
        "Channel",
        "URL"
    ]

    def __init__(self, api_token: Optional[str] = None):
        """Initialize the API client

        Args:
            api_token: Microsoft Clarity API token
        """
        self.api_token = api_token or self._get_api_token_from_env()

    def _get_api_token_from_env(self) -> Optional[str]:
        """Get API token from environment variables"""
        return os.getenv('CLARITY_API_TOKEN') or os.getenv('clarity_api_token')

    async def fetch_clarity_data(
        self,
        num_of_days: int,
        dimensions: Optional[List[str]] = None,
        context: Optional[str] = None,
        api_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch Clarity data from the API

        Args:
            num_of_days: Number of days to retrieve (1-3)
            dimensions: List of dimensions to filter by (max 3)
            context: Additional context for the query
            api_token: Override API token for this request

        Returns:
            Dictionary containing the API response data
        """
        try:
            # Use provided token or instance token
            token = api_token or self.api_token

            if not token:
                return {
                    "error": "No Clarity API token provided. Please provide a token via parameter or set CLARITY_API_TOKEN environment variable."
                }

            # Build parameters for the API request
            params = {
                "numOfDays": str(num_of_days),
                "src": "mcp"
            }

            # Add dimensions if specified (maximum 3 allowed)
            if dimensions:
                for i, dim in enumerate(dimensions[:3]):  # Limit to 3 dimensions
                    params[f"dimension{i + 1}"] = dim

            # Add context if provided
            if context:
                # Truncate context if too long (API limit)
                validated_context = context[:1024] if len(context) > 1024 else context
                params["context"] = validated_context

            # Build the full URL
            query_string = urlencode(params)
            url = f"{self.API_BASE_URL}?{query_string}"

            logger.debug("Making request to Clarity API (numOfDays=%s)", num_of_days)

            # Make the API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {token}'
                    }
                )

                if not response.is_success:
                    logger.error("Clarity API returned status %s", response.status_code)
                    return {
                        "error": f"API request failed with status {response.status_code}"
                    }

                return response.json()

        except httpx.TimeoutException:
            logger.error("Clarity API request timed out")
            return {"error": "Request timeout - the API took too long to respond"}
        except httpx.RequestError as e:
            logger.error("Clarity API request error: %s", e)
            return {"error": "Request error - failed to connect to the API"}
        except Exception as e:
            logger.exception("Unexpected error fetching Clarity data")
            return {"error": "Internal error while fetching data"}

    def validate_dimensions(self, dimensions: List[str]) -> List[str]:
        """Validate and filter dimensions against known valid dimensions

        Args:
            dimensions: List of dimensions to validate

        Returns:
            List of valid dimensions
        """
        valid_dimensions = []
        for dim in dimensions:
            if dim in self.AVAILABLE_DIMENSIONS:
                valid_dimensions.append(dim)
            else:
                logger.warning("Invalid dimension '%s' will be filtered out", dim)

        return valid_dimensions

    def filter_metrics(self, data: List[Dict[str, Any]], metrics: List[str]) -> List[Dict[str, Any]]:
        """Filter data by specified metrics

        Args:
            data: Raw API response data
            metrics: List of metrics to filter by

        Returns:
            Filtered data containing only specified metrics
        """
        if not metrics:
            return data

        filtered_data = []
        for item in data:
            if isinstance(item, dict) and 'metricName' in item:
                metric_name = item['metricName'].lower().replace(' ', '')
                for requested_metric in metrics:
                    requested_clean = requested_metric.lower().replace(' ', '')
                    if metric_name == requested_clean:
                        filtered_data.append(item)
                        break

        return filtered_data
