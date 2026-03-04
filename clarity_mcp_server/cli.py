#!/usr/bin/env python3
"""
CLI entry point for Microsoft Clarity MCP Server
"""

import argparse
import asyncio
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .server import main as server_main
from .http_server import create_app


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Microsoft Clarity MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start MCP server in stdio mode
  clarity-mcp-server --clarity_api_token your-token-here

  # Start HTTP server
  clarity-mcp-server --http --host 0.0.0.0 --port 8000 --clarity_api_token your-token-here

  # Start HTTP server with environment variable
  export CLARITY_API_TOKEN=your-token-here
  clarity-mcp-server --http
        """
    )

    parser.add_argument(
        "--clarity_api_token",
        help="Microsoft Clarity API token"
    )

    parser.add_argument(
        "--http",
        action="store_true",
        help="Start HTTP server instead of stdio MCP server"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind HTTP server to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind HTTP server to (default: 8000)"
    )

    args = parser.parse_args()

    if args.http:
        # Start HTTP server
        import uvicorn

        app = create_app(args.clarity_api_token)

        print("Starting Microsoft Clarity MCP HTTP Server...")
        print(f"Host: {args.host}")
        print(f"Port: {args.port}")
        print(f"API Token: {'configured' if args.clarity_api_token or os.getenv('CLARITY_API_TOKEN') else 'not configured'}")

        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # Start stdio MCP server
        print("Starting Microsoft Clarity MCP Server (stdio mode)...")

        # Run the async main function, passing token directly
        asyncio.run(server_main(args.clarity_api_token))


if __name__ == "__main__":
    main()
