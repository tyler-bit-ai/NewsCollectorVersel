"""Local entrypoint for the Vercel-targeted daily news job."""

from __future__ import annotations

from src.config.settings import load_settings


def main() -> None:
    settings = load_settings()

    try:
        from src.pipeline.daily_job import run_daily_job
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Daily pipeline is not implemented yet. Complete the pipeline tasks first."
        ) from exc

    result = run_daily_job(settings=settings, trigger="local")
    print(result)


if __name__ == "__main__":
    main()
