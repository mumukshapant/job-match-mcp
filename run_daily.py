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
    import mailer
    import server

    companies = _csv_list("DAILY_COMPANIES", "databricks,stripe")
    title_keywords = _csv_list("DAILY_TITLE_KEYWORDS", "data engineer")
    min_score = int(os.environ.get("DAILY_MIN_SCORE", "60"))
    max_jobs = int(os.environ.get("DAILY_MAX_JOBS", "5"))

    _log(
        f"start companies={companies} keywords={title_keywords} "
        f"min_score={min_score} max_jobs={max_jobs}"
    )

    try:
        result = server.find_matching_jobs(
            companies,
            title_keywords=title_keywords or None,
            min_score=min_score,
            max_jobs=max_jobs,
        )
    except Exception as exc:
        _log(f"ERROR find_matching_jobs: {exc}")
        return 1

    matches = result.get("matches") or []
    errors = result.get("errors") or []
    _log(
        f"done candidates={result.get('candidates_found')} scored={result.get('scored')} "
        f"returned={len(matches)} errors={errors}"
    )

    if not matches:
        _log("no matches at/above min_score; skipping email")
        return 0

    try:
        msg = mailer.send_matches(matches)
        _log(msg)
    except Exception as exc:
        _log(f"ERROR send_matches: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
