from mcp.server import MCPServer

mcp = MCPServer("resume-match-finder")

@mcp.tool()
def ping() -> str:
    """Health check: returns 'pong'."""
    return "pong"

if __name__ == "__main__":
    mcp.run()
