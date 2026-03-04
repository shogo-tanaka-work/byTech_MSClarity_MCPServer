"""
Microsoft Clarity MCP Server
Python implementation using MCP protocol
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from .api_client import ClarityAPIClient


class ClarityMCPServer:
    """Microsoft Clarity MCP Server"""

    def __init__(self, api_token: Optional[str] = None):
        """Initialize the MCP server

        Args:
            api_token: Microsoft Clarity API token
        """
        self.api_client = ClarityAPIClient(api_token)
        self.server_info = {
            "name": "@microsoft/clarity-mcp-server",
            "version": "1.0.0"
        }

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                }
            },
            "serverInfo": self.server_info
        }

    async def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": [
                {
                    "name": "get-clarity-data",
                    "description": "Fetch Microsoft Clarity analytics data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "numOfDays": {
                                "type": "integer",
                                "description": "Number of days to retrieve (1-3)",
                                "minimum": 1,
                                "maximum": 3
                            },
                            "dimensions": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": self.api_client.AVAILABLE_DIMENSIONS
                                },
                                "description": "Array of dimensions to filter by (max 3)",
                                "maxItems": 3
                            },
                            "metrics": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
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
                        },
                        "required": ["numOfDays"]
                    }
                }
            ]
        }

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "get-clarity-data":
            return await self._handle_get_clarity_data(tool_args)
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method '{tool_name}' not found"
                }
            }

    async def _handle_get_clarity_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get-clarity-data tool call"""
        try:
            # Extract parameters
            num_of_days = args.get("numOfDays")
            dimensions = args.get("dimensions", [])
            metrics = args.get("metrics", [])
            token = args.get("token")
            context = args.get("context")

            # Validate required parameters
            if not num_of_days:
                return {
                    "error": {
                        "code": -32602,
                        "message": "numOfDays is required"
                    }
                }

            if not isinstance(num_of_days, int) or num_of_days < 1 or num_of_days > 3:
                return {
                    "error": {
                        "code": -32602,
                        "message": "numOfDays must be an integer between 1 and 3"
                    }
                }

            # Validate and filter dimensions
            if dimensions:
                dimensions = self.api_client.validate_dimensions(dimensions)
                if len(dimensions) == 0:
                    print("Warning: All provided dimensions were invalid")

            # Fetch data from Clarity API
            data = await self.api_client.fetch_clarity_data(
                num_of_days=num_of_days,
                dimensions=dimensions,
                context=context,
                api_token=token
            )

            # Check for API errors
            if "error" in data:
                return {
                    "error": {
                        "code": -32000,
                        "message": data["error"]
                    }
                }

            # Filter metrics if specified
            if metrics:
                if isinstance(data, list):
                    data = self.api_client.filter_metrics(data, metrics)
                else:
                    # Handle case where data is not a list (might be wrapped in another structure)
                    print(f"Warning: Expected list data but got {type(data)}")

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(data, indent=2, ensure_ascii=False)
                    }
                ]
            }

        except Exception as e:
            return {
                "error": {
                    "code": -32000,
                    "message": f"Internal server error: {str(e)}"
                }
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        try:
            method = request.get("method")
            params = request.get("params", {})

            if method == "initialize":
                return await self.handle_initialize(params)
            elif method == "tools/list":
                return await self.handle_tools_list()
            elif method == "tools/call":
                return await self.handle_tools_call(params)
            else:
                return {
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    }
                }

        except Exception as e:
            return {
                "error": {
                    "code": -32000,
                    "message": f"Internal server error: {str(e)}"
                }
            }

    async def start_stdio_server(self):
        """Start the server in stdio mode for MCP"""
        print("Starting Microsoft Clarity MCP Server (stdio mode)...", file=sys.stderr)

        if self.api_client.api_token:
            print("Clarity API token configured via environment variable", file=sys.stderr)
        else:
            print("No Clarity API token configured, it must be provided with each request", file=sys.stderr)

        print(f"Supported metrics: {', '.join(self.api_client.AVAILABLE_METRICS)}", file=sys.stderr)
        print(f"Supported dimensions: {', '.join(self.api_client.AVAILABLE_DIMENSIONS)}", file=sys.stderr)

        import asyncio
        import threading
        import queue

        # Queue for communication between threads
        input_queue = asyncio.Queue()

        def read_stdin():
            """Read from stdin in a separate thread"""
            try:
                for line in sys.stdin:
                    line = line.strip()
                    if line:
                        # Use asyncio.run_coroutine_threadsafe to put item in queue
                        asyncio.run_coroutine_threadsafe(
                            input_queue.put(line),
                            loop
                        )
            except KeyboardInterrupt:
                pass
            finally:
                # Signal end of input
                asyncio.run_coroutine_threadsafe(
                    input_queue.put(None),
                    loop
                )

        # Get the current event loop
        loop = asyncio.get_event_loop()

        # Start stdin reading thread
        stdin_thread = threading.Thread(target=read_stdin, daemon=True)
        stdin_thread.start()

        try:
            while True:
                # Wait for input from queue
                line = await input_queue.get()

                if line is None:  # End of input
                    break

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Send response
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    error_response = {
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                except Exception as e:
                    error_response = {
                        "error": {
                            "code": -32000,
                            "message": f"Internal server error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            print("Server shutting down...", file=sys.stderr)
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
            sys.exit(1)


# Global server instance
_server_instance: Optional[ClarityMCPServer] = None


def get_server(api_token: Optional[str] = None) -> ClarityMCPServer:
    """Get or create server instance"""
    global _server_instance
    if _server_instance is None:
        _server_instance = ClarityMCPServer(api_token)
    return _server_instance


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Microsoft Clarity MCP Server")
    parser.add_argument("--clarity_api_token", help="Clarity API token")

    args = parser.parse_args()

    server = get_server(args.clarity_api_token)
    await server.start_stdio_server()


if __name__ == "__main__":
    asyncio.run(main())
