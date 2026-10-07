# Job Match MCP — progress notes

## Goal (MVP)

MCP server that, for a list of companies, fetches Greenhouse jobs, scores them against a resume, and can email matches. Greenhouse only. Built step by step.

## Done so far

### 1. Project + deps

- Initialized a uv Python project (`uv init --bare`).
- Deps: `mcp[cli]`, `httpx`, `anthropic`, `pydantic`, `python-dotenv`.
- `pyproject.toml` / `uv.lock` manage the environment; `.venv` is local (gitignored).
- Secrets stay in project-root `.env` (gitignored): `ANTHROPIC_API_KEY`.
- Personal `resume.txt` is gitignored.

### 2. Hello-world MCP server

- `server.py` creates an MCP server (`MCPServer`) and exposes a `ping` tool → `"pong"`.
- Wired into Cursor via [`.cursor/mcp.json`](.cursor/mcp.json) (`uv run python server.py`).
- Verified in Cursor: server Connected, `ping` callable from the agent.

**Import note:** use `from mcp.server import MCPServer`.

### 3. Tool 1: `get_greenhouse_jobs`

**Pieces:**

| File | Role |
|------|------|
| [`greenhouse.py`](greenhouse.py) | HTTP client for Greenhouse boards API + title filter (no MCP) |
| [`server.py`](server.py) | MCP tool that calls `greenhouse` and returns shaped results |

**Behavior:**

- `company` = Greenhouse board token (e.g. `"stripe"`).
- Optional `title_keywords` — case-insensitive substring match on title.
- Optional `limit` (default 3) — caps how many jobs are returned.
- Returns `id`, `title`, `url`, `updated_at` (no job descriptions).

**API used:**

`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs` — public, no auth.

**Verified via MCP:** Stripe + `"data engineer"` → Staff Software Engineer, Risk Data Engineering.

**Cursor tip:** after adding tools, Reload may not restart the process. Cmd+Shift+P → `Developer: Reload Window`.

### 4. Tool 2: `match_resume_to_job`

```
Cursor ─ calls ─▶ match_resume_to_job(company, job_id)
  1. greenhouse.fetch_job_description → JD as plain text (html.unescape + strip tags)
  2. matcher.load_resume              → resume.txt
  3. matcher.evaluate                 → Claude fills a fixed Evaluation form (skills found?, etc.)
  4. matcher.score                    → Python applies weights/caps and computes the %
```

**Pieces:**

| File | Role |
|------|------|
| [`greenhouse.py`](greenhouse.py) | `fetch_job_description(board_token, job_id)` — single job + content |
| [`matcher.py`](matcher.py) | Claude evaluation + Python scoring (no MCP) |
| [`server.py`](server.py) | MCP tool wrapping the above |

**Structured output:** `output_format=Evaluation` forces Claude’s reply to match our Pydantic schema. We never parse free-text JSON by hand.

**Scoring rubric (weights):** skills 40, experience 25, responsibilities 20, education 5, keywords 10.

**Caps:** e.g. years short by 2+ → cap 65; more than a third of required skills missing → cap 70.

**Evidence:** not required and not returned. `matched_skills` is a list of skill names only. Keywords still use literal whole-word search in the resume (Python).

**Untrusted JD text:** three guards so JD content can’t rewrite the score:

1. JD wrapped in `<job_description>` tags,
2. system prompt treats JD/resume as data, not instructions,
3. `%` computed in Python, not by the model.

**Local smoke test (Stripe job 8112043):** ~60% match; blocker `5 years vs 10+ required`.

**Config:** `.env` must live in the **project root** (not `.venv/.env`). `matcher.py` loads `PROJECT_DIR / ".env"`.

## Not done yet

- Tool 3: `find_matching_jobs` (Tool 1 → title filter → Tool 2 → sort / `min_score`)
- Tool 4: `send_job_matches_email`
- `companies.yaml` (friendly name → board token)

## Useful commands

```bash
# Run MCP server (normally started by Cursor)
uv run python server.py

# Tool 1 — list jobs
uv run python -c 'import greenhouse; print(len(greenhouse.fetch_jobs("stripe")))'

# Tool 2 — score one job (uses Anthropic API; use single quotes for zsh)
uv run python -c 'import greenhouse, matcher, json; job = greenhouse.fetch_job_description("stripe", 8112043); print(json.dumps(matcher.match(job["description"]), indent=2))'
```
