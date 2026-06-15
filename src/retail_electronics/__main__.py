"""Entry point: python -m retail_electronics starts the MCP server."""

import asyncio
import os

from retail_electronics.config import MCP_HOST, MCP_PORT
from retail_electronics.server import create_server


def main() -> None:
    server = create_server()
    port = int(os.getenv("PORT", MCP_PORT))
    print(f"Starting Electronics Retail Analytics MCP server on {MCP_HOST}:{port}")
    asyncio.run(
        server.run_async(
            transport="streamable-http",
            host=MCP_HOST,
            port=port,
        )
    )


main()
