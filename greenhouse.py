"""Talks to the Greenhouse Job Board API. No MCP code in this file."""

import httpx
import html
import re

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


# Free-text location.name markers (Greenhouse has no country code on the list API).
_US_COUNTRY = re.compile(
    r"\b(united states|usa|u\.s\.a\.?|u\.s\.?|remote from the us)\b",
    re.IGNORECASE,
)
_US_STATES = re.compile(
    r"(?<![A-Za-z])("
    r"AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    r"MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
    r")(?![A-Za-z])"
)
_US_CITIES = re.compile(
    r"\b("
    r"new york(?: city)?|nyc|san francisco|sf|seattle|sea|chicago|chi|boston|"
    r"los angeles|la|austin|denver|atlanta|miami|dallas|houston|philadelphia|"
    r"phoenix|san diego|san jose|oakland|portland|washington(?:,? d\.?c\.?)?|"
    r"bay area|remote[- ]?us|us[- ]?remote"
    r")\b",
    re.IGNORECASE,
)


def is_usa_location(name: str) -> bool:
    """True if Greenhouse location.name looks US-based. Bare 'Remote' is False."""
    text = " ".join((name or "").split())
    if not text:
        return False
    return bool(_US_COUNTRY.search(text) or _US_STATES.search(text) or _US_CITIES.search(text))


def fetch_job_description(board_token: str, job_id: int) -> dict:
    """Return one job's title, URL, and description as plain text."""
    url = f"{BASE_URL}/{board_token}/jobs/{job_id}"
    response = httpx.get(url, timeout=15.0)

    if response.status_code == 404:
        raise ValueError(f"Job {job_id} not found on the '{board_token}' board.")
    response.raise_for_status()

    job = response.json()
    return {
        "title": job["title"],
        "url": job["absolute_url"],
        "description": html_to_text(job["content"]),
    }


def html_to_text(raw: str) -> str:
    """Turn Greenhouse's escaped HTML into readable plain text."""
    text = html.unescape(raw)                                   # "&lt;p&gt;" -> "<p>"
    text = re.sub(r"<li[^>]*>", "\n- ", text)                   # list items -> "- " bullets
    text = re.sub(r"</(p|div|h\d|li|ul|ol)>|<br\s*/?>", "\n", text)  # block ends -> newlines
    text = re.sub(r"<[^>]+>", "", text)                         # drop all remaining tags
    text = html.unescape(text)                                  # "&amp;" / "&nbsp;" inside text
    text = re.sub(r"[ \t\xa0]+", " ", text)                     # squeeze repeated spaces
    text = re.sub(r"\n\s*\n+", "\n\n", text)                    # squeeze blank lines
    return text.strip()

# check if the board exists
def board_name(board_token: str) -> str | None:
    """The company's name if this Greenhouse board exists, else None."""
    response = httpx.get(f"{BASE_URL}/{board_token}", timeout=10.0)
    return response.json().get("name", board_token) if response.status_code == 200 else None