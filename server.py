# This is the MCP server .
import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import greenhouse

mcp = MCPServer("resume-match-finder")

@mcp.tool()
def ping() -> str:
    """Health check: returns 'pong'."""
    return "pong"

@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def get_greenhouse_jobs(
    company: str,
    title_keywords: list[str] | None = None,
    limit: int = 3,
) -> dict:
    """List open jobs on a company's Greenhouse job board.

    company: the Greenhouse board token
    title_keywords: optional; ["data engineer", "backend"].
    limit: maximum number of jobs to return (default 3).
    """
    board_token = company.strip().lower()

    try:
        jobs = greenhouse.fetch_jobs(board_token)
    except (ValueError, httpx.HTTPError) as error:
        # ToolError = an expected failure: the AI sees this message and can react.
        raise ToolError(str(error)) from error

    if title_keywords:
        jobs = greenhouse.filter_by_title(jobs, title_keywords)

    return {
        "company": board_token,
        "total_matching": len(jobs),
        "returned": min(len(jobs), limit),
        "jobs": [
            {
                "id": job["id"],
                "title": job["title"],
                "url": job["absolute_url"],
                "updated_at": job["updated_at"],
            }
            for job in jobs[:limit]
        ],
    }


if __name__ == "__main__":
    mcp.run()
