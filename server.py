# This is the MCP server .
from concurrent.futures import ThreadPoolExecutor

import anthropic
import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import greenhouse
import matcher

mcp = MCPServer("resume-match-finder") #define mcp server name here

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

#capability 3: find_matching_jobs
SENIOR_TITLES = ["staff", "principal", "director", "manager", "head of", "intern"]
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def find_matching_jobs(
    companies: list[str],
    title_keywords: list[str] | None = None,
    skip_senior_titles: bool = True,
    min_score: int = 80,
    max_jobs: int = 5,
) -> dict:
    """Find and score Greenhouse jobs across companies, sorted by match %.

    Pipeline: list jobs -> title filters -> drop duplicate titles -> newest first ->
    score up to max_jobs in parallel (Tool 2) -> keep those >= min_score -> sort.

    companies: Greenhouse board tokens, e.g. ["stripe", "airbnb"].
    title_keywords: optional title substrings, e.g. ["data engineer"].
    skip_senior_titles: skip Staff/Principal/Director/Manager/Head of/Intern titles (default True).
    min_score: minimum match_percentage to include (default 80).
    max_jobs: max jobs to score in total (default 5). Each scored job calls LLM API.
    """
    if not companies:
        raise ToolError("Pass at least one company board token, e.g. companies=['stripe'].")
    if max_jobs < 1:
        raise ToolError("max_jobs must be at least 1.")

    # 1) Collect filtered, de-duplicated job candidates from the job board
    candidates: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for company in companies:
        board_token = company.strip().lower()
        if not board_token:
            continue
        try:
            jobs = greenhouse.fetch_jobs(board_token)
        except (ValueError, httpx.HTTPError) as error:
            errors.append(f"{board_token}: {error}")
            continue
        if title_keywords:
            jobs = greenhouse.filter_by_title(jobs, title_keywords)

        # drop titles that contain words in SENIOR_TITLES list
        if skip_senior_titles:
            jobs = [j for j in jobs if not greenhouse.filter_by_title([j], SENIOR_TITLES)]
        
        for job in jobs:
            key = (board_token, job["title"].strip().lower())
            if key in seen:  # DEDUPLICATE: same title posted in several locations: score it once. Avoid duplicate scoring of the same job.
                continue
            seen.add(key)
            candidates.append({"company": board_token, "id": job["id"], "updated_at": job["updated_at"]})

    # Newest postings first, so max_jobs picks recent jobs across all companies
    candidates.sort(key=lambda c: c["updated_at"], reverse=True)
    to_score = candidates[:max_jobs]

    # 2) Score candidates in parallel: each call mostly waits on the network
    def score_one(cand: dict) -> dict:
        try:
            job = greenhouse.fetch_job_description(cand["company"], cand["id"])
            result = matcher.match(job["description"])
        except (ValueError, httpx.HTTPError, anthropic.AnthropicError) as error:
            return {"error": f"{cand['company']}/{cand['id']}: {error}"}
        return {"company": cand["company"], "job_id": cand["id"],
                "title": job["title"], "url": job["url"], **result}

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(score_one, to_score))

    errors += [r["error"] for r in results if "error" in r]
    scored = [r for r in results if "error" not in r]

    # 3) Filter by min_score and sort highest first
    matches = [m for m in scored if m["match_percentage"] >= min_score]
    matches.sort(key=lambda m: m["match_percentage"], reverse=True)

    return {
        "candidates_found": len(candidates),
        "scored": len(scored),
        "returned": len(matches),
        "matches": matches,
        "errors": errors,
    }
if __name__ == "__main__":
    mcp.run()
