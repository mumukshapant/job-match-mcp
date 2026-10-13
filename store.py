"""Postgres storage on Neon (companies, seen jobs). No MCP code in this file."""

import os
import psycopg


def _connect() -> psycopg.Connection:
    # prepare_threshold=None: Neon's pooled URL goes through PgBouncer,
    # so skip server-side prepared statements to avoid errors.
    return psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)


def load_companies() -> dict[str, str]:
    with _connect() as conn:
        rows = conn.execute("SELECT token, name FROM companies").fetchall()
    return {token: name for token, name in rows}


def save_companies(companies: dict[str, str]) -> None:
    if not companies:
        return
    with _connect() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO companies (token, name) VALUES (%s, %s) "
            "ON CONFLICT (token) DO NOTHING",
            list(companies.items()),
        )


def load_seen() -> set[int]:
    with _connect() as conn:
        return {row[0] for row in conn.execute("SELECT job_id FROM seen_jobs")}


def add_seen(job_ids) -> None:
    ids = [(int(j),) for j in job_ids]
    if not ids:
        return
    with _connect() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO seen_jobs (job_id) VALUES (%s) ON CONFLICT (job_id) DO NOTHING",
            ids,
        )