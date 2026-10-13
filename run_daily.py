"""Daily job: find Greenhouse matches and email them. No MCP / no Cursor required.
1. Reads settings from .env
2. Calls find_matching_jobs (Greenhouse + Claude scoring)
3. If there are matches, calls mailer.send_matches (Gmail)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line)
    with (LOG_DIR / "daily.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _csv_list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]

def main() -> int:
    import discovery
    import greenhouse
    import mailer
    import server
    import store

    title_keywords = _csv_list("DAILY_TITLE_KEYWORDS", "data engineer")
    min_score = int(os.environ.get("DAILY_MIN_SCORE", "40"))
    max_jobs = int(os.environ.get("DAILY_MAX_JOBS", "5"))
    posted_within_days = int(os.environ.get("DAILY_POSTED_WITHIN_DAYS", "5"))

    # 1) Discover companies hiring for these roles; grow the saved watchlist
    companies: dict[str, str] = store.load("companies.json", {})
    for role in title_keywords:
        try:
            found = discovery.discover_boards(role)
        except Exception as exc:
            _log(f"WARN discovery '{role}': {exc}")
            continue
        for token in sorted(found - companies.keys()):
            try:
                name = greenhouse.board_name(token)  # confirm the board really exists
            except Exception:
                name = None
            if name:
                companies[token] = name
                _log(f"new company: {token} ({name})")
    for token in _csv_list("DAILY_COMPANIES", ""):  # optional fixed extras from .env
        companies.setdefault(token.lower(), token)
    store.save("companies.json", companies)

    # 2) Find and score new jobs, skipping ones already scored on earlier days
    seen: set[int] = set(store.load("seen_jobs.json", []))
    _log(f"start boards={len(companies)} keywords={title_keywords} min_score={min_score} "
         f"max_jobs={max_jobs} posted_within_days={posted_within_days} seen={len(seen)}")
    try:
        result = server.find_matching_jobs(
            list(companies),
            title_keywords=title_keywords or None,
            min_score=min_score,
            max_jobs=max_jobs,
            posted_within_days=posted_within_days,
            skip_job_ids=list(seen),
        )
    except Exception as exc:
        _log(f"ERROR find_matching_jobs: {exc}")
        return 1

    matches = result.get("matches") or []
    _log(f"done candidates={result.get('candidates_found')} scored={result.get('scored')} "
         f"returned={len(matches)} errors={len(result.get('errors') or [])}")

    # 3) Email matches, then remember everything scored so it isn't re-scored tomorrow
    if matches:
        try:
            _log(mailer.send_matches(matches))
        except Exception as exc:
            _log(f"ERROR send_matches: {exc}")
            return 1  # don't mark as seen, so tomorrow retries
    else:
        _log("no new matches at/above min_score; skipping email")
    store.save("seen_jobs.json", sorted(seen | set(result.get("scored_job_ids", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
