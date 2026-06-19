"""Wrapper to start the MCP server in stdio mode with logs redirected to stderr."""

import asyncio
import sys
import os

# Suppress the ASCII banner that FastMCP prints to stdout (breaks JSON-RPC)
os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"

# Redirect FastMCP logs to stderr so stdout stays clean for JSON-RPC
os.environ.setdefault("FASTMCP_LOG_FILE", "/dev/stderr")

# Ensure project root for dotenv
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from retail_electronics.server import create_server

asyncio.run(create_server().run_async(transport="stdio"))
