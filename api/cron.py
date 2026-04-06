"""Vercel cron entrypoint for the daily news job."""

from __future__ import annotations

import json
from typing import Callable, Iterable, Tuple

from src.config.settings import load_settings
from src.pipeline.daily_job import run_daily_job

Headers = list[Tuple[str, str]]
StartResponse = Callable[[str, Headers], None]


def _json_response(
    start_response: StartResponse,
    status_code: int,
    payload: dict,
) -> Iterable[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        f"{status_code} {'OK' if status_code < 400 else 'ERROR'}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def app(environ, start_response: StartResponse):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if method != "GET":
        return _json_response(
            start_response,
            405,
            {"success": False, "message": "Method Not Allowed"},
        )

    settings = load_settings()
    auth_header = environ.get("HTTP_AUTHORIZATION", "")
    cron_secret = settings.cron_secret
    if not cron_secret or auth_header != f"Bearer {cron_secret}":
        return _json_response(
            start_response,
            401,
            {"success": False, "message": "Unauthorized"},
        )

    try:
        summary = run_daily_job(settings=settings, trigger="vercel-cron")
    except Exception as exc:
        return _json_response(
            start_response,
            500,
            {"success": False, "message": str(exc)},
        )

    return _json_response(start_response, 200, {"success": True, "summary": summary})
