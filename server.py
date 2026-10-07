# This is the MCP server .
import anthropic
import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import greenhouse
import matcher

mcp = MCPServer("resume-match-finder")

@mcp.tool()
def ping() -> str:
    """Health check: returns 'pong'."""
    return "pong"

#capability 1: get_greenhouse_jobs
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

#capability 2: match_resume_to_job
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def match_resume_to_job(company: str, job_id: int) -> dict:
    """Score how well the resume (resume.txt) matches one Greenhouse job.

    company: the Greenhouse board token, e.g. "stripe".
    job_id: the job's id, as returned by get_greenhouse_jobs.

    Returns match_percentage (0-100) from a fixed rubric: skills 40, experience 25,
    responsibilities 20, education 5, keywords 10. "blockers" lists hard gaps that cap the score.
    """
    board_token = company.strip().lower()
    try:
        job = greenhouse.fetch_job_description(board_token, job_id)
        result = matcher.match(job["description"])
    except (ValueError, httpx.HTTPError, anthropic.AnthropicError) as error:
        raise ToolError(str(error)) from error

    return {"company": board_token, "job_id": job_id, "title": job["title"], "url": job["url"], **result}


if __name__ == "__main__":
    mcp.run()
