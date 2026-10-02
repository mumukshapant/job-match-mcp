# Job Match MCP — progress notes

## Goal (MVP)

MCP server that, for a list of companies, fetches Greenhouse jobs, scores them against a resume, and can email matches. Greenhouse only. Built step by step.

## Done so far

### 1. Project + deps

- Initialized a uv Python project (`uv init --bare`).
- Added deps: `uv add "mcp[cli]" httpx`.
- `pyproject.toml` / `uv.lock` manage the environment; `.venv` is local (gitignored).

### 2. Hello-world MCP server

- `server.py` creates an MCP server (`MCPServer`) and exposes a `ping` tool → `"pong"`.
- Wired into Cursor via [`.cursor/mcp.json`](.cursor/mcp.json) (`uv run … python server.py`).
- Verified in Cursor: server Connected, `ping` callable from the agent.

**Import note:** use `from mcp.server import MCPServer` (MCP SDK v2 public path).

### 3. Git + GitHub

- `git init`, `.gitignore` (`.venv/`, `__pycache__/`, `.env`, etc.).
- First commit: hello-world MCP.
- Remote: [github.com/mumukshapant/job-match-mcp](https://github.com/mumukshapant/job-match-mcp) (personal account, not Addgene).
- `main` pushed and tracking `origin/main`.

### 4. Tool 1: `get_greenhouse_jobs`

**Pieces:**

| File | Role |
|------|------|
| [`greenhouse.py`](greenhouse.py) | HTTP client for Greenhouse boards API + title filter (no MCP) |
| [`server.py`](server.py) | MCP tool that calls `greenhouse` and returns shaped results |

**Behavior:**

- `company` = Greenhouse board token (e.g. `"stripe"`).
- Optional `title_keywords` — case-insensitive substring match on title.
- Optional `limit` (default 3) — caps how many jobs are returned.
- Returns `id`, `title`, `url`, `updated_at` (no job descriptions yet).

**API used:**

`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs` — public, no auth.

**Verified via MCP:** Stripe + `"data engineer"` → 1 job (Staff Software Engineer, Risk Data Engineering).

**Cursor tip:** after adding tools, Reload may not restart the process. Toggle the MCP source off/on (or restart Cursor) until the new tool appears in the Tools list.

## Not done yet (later)

- `companies.yaml` (friendly name → board token) — currently `company` is the board token itself.
- Tool 2: `match_resume_to_job` (fetch JD, HTML → text, score vs resume).
- Tool 3: `find_matching_jobs` (pipeline).
- Tool 4: `send_job_matches_email` (Gmail SMTP).

## Useful commands

```bash
# Run server (stdio; normally started by Cursor)
uv run python server.py

# Smoke-test Greenhouse helper outside MCP
uv run python -c "import greenhouse; print(len(greenhouse.fetch_jobs('stripe')))"
```
