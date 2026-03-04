#!/usr/bin/env python3
"""
Main entry point for Microsoft Clarity MCP Server
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clarity_mcp_server.cli import main

if __name__ == "__main__":
    main()
