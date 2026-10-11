# Job Match MCP

Greenhouse-focused job matcher: discover boards, filter recent US roles, score them against your resume with an LLM, and optionally email a daily digest.

## What it does

- **MCP tools** (Cursor): list Greenhouse jobs, score one job, find matches across companies, send email
- **Daily run** (`run_daily.py` + GitHub Actions): Brave Search discovery → score new jobs → Gmail digest

## Setup (local)

1. Install [uv](https://github.com/astral-sh/uv) and clone this repo.
2. Create project-root `.env` (never commit it):

```env
ANTHROPIC_API_KEY=...
BRAVE_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
EMAIL_TO=you@example.com
DAILY_COMPANIES=databricks,stripe
DAILY_TITLE_KEYWORDS=data engineer
DAILY_MIN_SCORE=60
DAILY_MAX_JOBS=5
```

3. Put your resume text in `resume.txt` (gitignored).
4. Run the MCP server: `uv run python server.py`

### Cursor

Point MCP at this project (see [`.cursor/mcp.json`](.cursor/mcp.json)):

```json
{
  "mcpServers": {
    "resume-match-finder": {
      "command": "uv",
      "args": ["run", "python", "server.py"]
    }
  }
}
```

## Daily email (GitHub Actions)

Workflow: [`.github/workflows/daily.yml`](.github/workflows/daily.yml).

Add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | LLM scoring |
| `BRAVE_API_KEY` | Company discovery |
| `GMAIL_ADDRESS` | SMTP from |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `EMAIL_TO` | Recipients (comma-separated OK) |
| `RESUME_TXT` | Full resume text |

Optional: `DAILY_COMPANIES`, `DAILY_TITLE_KEYWORDS`, `DAILY_MIN_SCORE`, `DAILY_MAX_JOBS`.

Local one-shot: `uv run python run_daily.py`

## Notes

- Filters: title keywords, skips senior/intern-style titles, USA-looking locations, recent postings, already-scored job ids.
