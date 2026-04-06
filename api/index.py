"""Vercel cron entrypoint for the daily news job."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from src.config.settings import load_settings
from src.pipeline.daily_job import run_daily_job


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        settings = load_settings()
        auth_header = self.headers.get("Authorization", "")
        cron_secret = settings.cron_secret

        if not cron_secret or auth_header != f"Bearer {cron_secret}":
            self._send_json(401, {"success": False, "message": "Unauthorized"})
            return

        try:
            summary = run_daily_job(settings=settings, trigger="vercel-cron")
        except Exception as exc:
            self._send_json(500, {"success": False, "message": str(exc)})
            return

        self._send_json(200, {"success": True, "summary": summary})
