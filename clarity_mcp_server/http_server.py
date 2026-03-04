"""
HTTP Server for Microsoft Clarity MCP Server
FastAPI-based HTTP endpoints for remote deployment
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .api_client import ClarityAPIClient

logger = logging.getLogger(__name__)


class ClarityDataRequest(BaseModel):
    """Request model for get-clarity-data endpoint"""
    numOfDays: int = Field(..., ge=1, le=3, description="Number of days to retrieve (1-3)")
    dimensions: Optional[List[str]] = Field(None, max_items=3, description="Array of dimensions to filter by (max 3)")
    metrics: Optional[List[str]] = Field(None, description="Array of metrics to retrieve")
    token: Optional[str] = Field(None, description="Clarity API token (optional if set via environment)")
    context: Optional[str] = Field(None, max_length=1024, description="Additional context for the query")


class MCPRequest(BaseModel):
    """MCP protocol request model"""
    action: str = Field(..., description="Action to perform")
    params: Dict[str, Any] = Field(..., description="Action parameters")


class ClarityHTTPServer:
    """HTTP Server for Microsoft Clarity MCP"""

    def __init__(self, api_token: Optional[str] = None):
        """Initialize the HTTP server

        Args:
            api_token: Microsoft Clarity API token
        """
        self.api_client = ClarityAPIClient(api_token)
        self.app = FastAPI(
            title="Microsoft Clarity MCP Server",
            description="MCP Server to fetch Microsoft Clarity analytics data based on data export API",
            version="1.0.0"
        )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "name": "@microsoft/clarity-mcp-server",
                "version": "1.0.0",
                "description": "Microsoft Clarity Data Export MCP Server"
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {"status": "healthy"}

        @self.app.post("/api/clarity-data")
        async def get_clarity_data(request: ClarityDataRequest):
            """Get Clarity data endpoint"""
            try:
                # Extract parameters
                num_of_days = request.numOfDays
                dimensions = request.dimensions or []
                metrics = request.metrics or []
                token = request.token
                context = request.context

                # Validate and filter dimensions
                if dimensions:
                    dimensions = self.api_client.validate_dimensions(dimensions)
                    if len(dimensions) == 0:
                        logger.warning("All provided dimensions were invalid")

                # Fetch data from Clarity API
                data = await self.api_client.fetch_clarity_data(
                    num_of_days=num_of_days,
                    dimensions=dimensions,
                    context=context,
                    api_token=token
                )

                # Check for API errors
                if "error" in data:
                    raise HTTPException(status_code=400, detail=data["error"])

                # Filter metrics if specified
                if metrics:
                    if isinstance(data, list):
                        data = self.api_client.filter_metrics(data, metrics)
                    else:
                        # Handle case where data is not a list
                        logger.warning("Expected list data but got %s", type(data))

                return {"data": data}

            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error processing request")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.post("/mcp")
        async def mcp_endpoint(request: Request):
            """MCP protocol endpoint (for compatibility)"""
            try:
                # Parse request body
                body = await request.json()
                mcp_request = MCPRequest(**body)

                if mcp_request.action == "get-clarity-data":
                    # Convert MCP request to ClarityDataRequest
                    params = mcp_request.params
                    clarity_request = ClarityDataRequest(**params)

                    # Call the clarity data endpoint
                    return await get_clarity_data(clarity_request)

                else:
                    raise HTTPException(status_code=400, detail=f"Unknown action: {mcp_request.action}")

            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error processing MCP request")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/info")
        async def server_info():
            """Server information endpoint"""
            return {
                "server": {
                    "name": "@microsoft/clarity-mcp-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {
                        "get-clarity-data": {
                            "description": "Fetch Microsoft Clarity analytics data",
                            "parameters": {
                                "numOfDays": {
                                    "type": "integer",
                                    "description": "Number of days to retrieve (1-3)",
                                    "minimum": 1,
                                    "maximum": 3
                                },
                                "dimensions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Array of dimensions to filter by (max 3)",
                                    "maxItems": 3
                                },
                                "metrics": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Array of metrics to retrieve"
                                },
                                "token": {
                                    "type": "string",
                                    "description": "Clarity API token (optional if set via environment)"
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Additional context for the query",
                                    "maxLength": 1024
                                }
                            }
                        }
                    }
                },
                "api_info": {
                    "available_metrics": self.api_client.AVAILABLE_METRICS,
                    "available_dimensions": self.api_client.AVAILABLE_DIMENSIONS,
                    "api_base_url": self.api_client.API_BASE_URL
                }
            }


def create_app(api_token: Optional[str] = None) -> FastAPI:
    """Create FastAPI application instance"""
    server = ClarityHTTPServer(api_token)
    return server.app


# For Vercel deployment
app = create_app()


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Microsoft Clarity MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--clarity_api_token", help="Clarity API token")

    args = parser.parse_args()

    # Create app with token
    app = create_app(args.clarity_api_token)

    print(f"Microsoft Clarity MCP HTTP Server starting on {args.host}:{args.port}")
    print("Available endpoints:")
    print("  GET  /         - Server info")
    print("  GET  /health   - Health check")
    print("  GET  /info     - Detailed server information")
    print("  POST /api/clarity-data - Get Clarity data")
    print("  POST /mcp      - MCP protocol endpoint")

    if app.api_client.api_token:
        print("Clarity API token configured via environment variable")
    else:
        print("No Clarity API token configured, it must be provided with each request")

    print(f"Supported metrics: {', '.join(app.api_client.AVAILABLE_METRICS)}")
    print(f"Supported dimensions: {', '.join(app.api_client.AVAILABLE_DIMENSIONS)}")

    uvicorn.run(app, host=args.host, port=args.port)
