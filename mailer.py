"""Builds and sends the job-matches email through Gmail. No MCP code in this file."""

import html
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _recipients() -> list[str]:
    """EMAIL_TO may be a single address or comma-separated list."""
    raw = os.environ.get("EMAIL_TO") or os.environ.get("GMAIL_ADDRESS") or ""
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def build_html(matches: list[dict]) -> str:
    rows = "".join(
        "<tr>"
        f"<td><b>{m.get('match_percentage', '?')}%</b></td>"
        f"<td>{html.escape(m.get('company', ''))}</td>"
        f"<td><a href=\"{html.escape(m.get('url', ''))}\">{html.escape(m.get('title', ''))}</a></td>"
        f"<td>{html.escape(', '.join(m.get('missing_required', [])) or '-')}</td>"
        "</tr>"
        for m in matches
    )
    return (
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Match</th><th>Company</th><th>Job</th><th>Missing (required)</th></tr>"
        f"{rows}</table>"
    )


def build_text(matches: list[dict]) -> str:
    return "\n".join(
        f"{m.get('match_percentage', '?')}% | {m.get('company', '')} | "
        f"{m.get('title', '')} | {m.get('url', '')}"
        for m in matches
    )


def send_matches(matches: list[dict]) -> str:
    sender = os.environ.get("GMAIL_ADDRESS")
    password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
    to_list = _recipients()
    if not sender or not password:
        raise ValueError("Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.")
    if not to_list:
        raise ValueError("Set EMAIL_TO (or GMAIL_ADDRESS) in .env.")
    if not matches:
        raise ValueError("No matches to send.")

    matches = sorted(matches, key=lambda m: m.get("match_percentage", 0), reverse=True)
    msg = EmailMessage()
    msg["Subject"] = (
        f"{len(matches)} job match(es), top score {matches[0].get('match_percentage', '?')}%"
    )
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg.set_content(build_text(matches))
    msg.add_alternative(build_html(matches), subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
    return f"Sent {len(matches)} match(es) to {', '.join(to_list)}."
