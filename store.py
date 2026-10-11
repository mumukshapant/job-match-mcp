"""JSON file storage (companies.json, seen_jobs.json). No MCP code in this file."""
# It saves the companies and the jobs that have been seen.

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


def load(filename: str, default):
    path = PROJECT_DIR / filename
    return json.loads(path.read_text()) if path.exists() else default


def save(filename: str, data) -> None:
    (PROJECT_DIR / filename).write_text(json.dumps(data, indent=2, sort_keys=True))