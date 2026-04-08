"""Vercel entrypoint with an explicit cron route."""

from __future__ import annotations

from flask import Flask, jsonify, request

from src.config.settings import load_settings
from src.pipeline.daily_job import run_daily_job

app = Flask(__name__)


@app.get("/api/cron")
def run_cron():
    settings = load_settings()
    auth_header = request.headers.get("Authorization", "")
    cron_secret = settings.cron_secret

    if not cron_secret or auth_header != f"Bearer {cron_secret}":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        summary = run_daily_job(settings=settings, trigger="vercel-cron")
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "summary": summary}), 200
