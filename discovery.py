"""Finds companies with recent Greenhouse postings for a role, via the Brave Search API. No MCP code."""

import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
BOARD_IN_URL = re.compile(r"job-boards\.greenhouse\.io/([a-z0-9-]+)/jobs/\d+", re.IGNORECASE)

# Example : boards = discover_boards("data engineer")
def discover_boards(role: str, pages: int = 2) -> set[str]:
    """Board tokens of companies whose Greenhouse job pages for `role` were indexed in the past month."""
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        raise ValueError("BRAVE_API_KEY is not set in .env.")
    
    tokens: set[str] = set() # Example : {"stripe", "databricks"}
    
    for page in range(pages):  # each page search returns ~20 results; retrieve ~40 results total
        
        response = httpx.get(
            BRAVE_URL,
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            params={"q": f'site:job-boards.greenhouse.io "{role}"', "count": 20, "offset": page, "freshness": "pm"},
            timeout=20.0,
        )
        response.raise_for_status()
        
        results = response.json().get("web", {}).get("results", [])
        
        tokens |= {m.group(1).lower() for r in results if (m := BOARD_IN_URL.search(r.get("url", "")))}
        if len(results) < 20:  # last page
            break
    return tokens