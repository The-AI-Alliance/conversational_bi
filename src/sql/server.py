from google import genai
from fastmcp import FastMCP

mcp = FastMCP("mcp-server")


@mcp.tool()
def hello_world() -> str:
    """Returns a hello world greeting."""
    return "hello world!"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
