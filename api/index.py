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


@app.get("/api/debug/lgu")
def debug_lgu():
    """LGU 로밍 공지 스크래핑 진단용(발송 없음). cron_secret으로 보호."""
    import time as _time

    import requests as _requests

    settings = load_settings()
    auth_header = request.headers.get("Authorization", "")
    if settings.cron_secret and auth_header != f"Bearer {settings.cron_secret}":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    from src.collectors.roaming_notices_collector import (
        _LGU_LIST_URL,
        _UA_VARIANTS,
        _collect_lgu,
    )

    results = []
    for url in [_LGU_LIST_URL, _LGU_LIST_URL + "?pageNo=1"]:
        for ua in _UA_VARIANTS:
            started = _time.time()
            try:
                resp = _requests.get(
                    url,
                    headers={"User-Agent": ua, "Accept-Language": "ko,en;q=0.8"},
                    timeout=20,
                )
                results.append(
                    {
                        "url": url,
                        "ua": ua[:40],
                        "status": resp.status_code,
                        "len": len(resp.text or ""),
                        "has_row": "c-cell-subject" in (resp.text or ""),
                        "head": (resp.text or "")[:120],
                        "elapsed": round(_time.time() - started, 2),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {"url": url, "ua": ua[:40], "error": repr(exc)[:200], "elapsed": round(_time.time() - started, 2)}
                )
    try:
        rows = _collect_lgu(3)
        collect = [{"posted_at": r["posted_at"], "title": r["title"][:50]} for r in rows]
    except Exception as exc:  # noqa: BLE001
        collect = repr(exc)[:200]
    return jsonify({"success": True, "egress": results, "collect_lgu": collect})
