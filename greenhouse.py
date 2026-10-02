"""Talks to the Greenhouse Job Board API. No MCP code in this file."""

import httpx

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


def fetch_jobs(board_token: str) -> list[dict]:
    """Return every open job on a company's Greenhouse board (raw API data)."""
    url = f"{BASE_URL}/{board_token}/jobs"
    response = httpx.get(url, timeout=15.0)

    if response.status_code == 404:
        raise ValueError(f"No Greenhouse job board found for '{board_token}'.")
    response.raise_for_status()

    return response.json()["jobs"]


def filter_by_title(jobs: list[dict], keywords: list[str]) -> list[dict]:
    """Keep jobs whose title contains any of the keywords (case-insensitive)."""
    lowered = [k.lower() for k in keywords]
    return [job for job in jobs if any(k in job["title"].lower() for k in lowered)]