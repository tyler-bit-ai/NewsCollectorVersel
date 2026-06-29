"""Core collection and analysis pipeline without notifier side effects."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.analyzers.insight_generator import InsightGenerator
from src.analyzers.summarizer import Summarizer
from src.collectors.google_collector import GoogleCollector
from src.collectors.mofa_0404_collector import Mofa0404Collector
from src.collectors.naver_collector import NaverCollector
from src.collectors.rss_collector import RSSCollector
from src.config.settings import Settings
from src.filters.deduplicator import Deduplicator
from src.filters.keyword_filter import KeywordFilter
from src.filters.persistent_deduplicator import PersistentDeduplicator
from src.filters.time_filter import TimeFilter
from src.utils.time_windows import get_collection_window_kst

logger = logging.getLogger("news_collector")

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
PUBLISHED_CONFIDENCE_ORDER = {
    "exact": 2,
    "date_only": 1,
    "missing": 0,
}


def load_categories(config_path: Path | None = None) -> Dict:
    path = config_path or (CONFIG_DIR / "categories.yaml")
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _apply_recency_boost(articles: List[Dict], now_utc: Optional[datetime] = None) -> None:
    """기사 나이에 따른 신선도 점수를 relevance_score에 더한다 (인플레이스)."""
    now = now_utc or datetime.now(timezone.utc)
    for article in articles:
        published = article.get("published")
        if published and hasattr(published, "astimezone"):
            try:
                days_old = max(0, (now - published.astimezone(timezone.utc)).days)
                recency_boost = max(0, 20 - days_old)
                article["relevance_score"] = int(article.get("relevance_score", 50)) + recency_boost
            except Exception:
                pass


def collect_articles(
    settings: Settings,
    persistent_deduplicator: Optional[PersistentDeduplicator] = None,
) -> Dict[str, List[Dict]]:
    logger.info("=== Starting News Collection ===")

    naver_collector = NaverCollector(
        client_id=settings.api.naver_client_id,
        client_secret=settings.api.naver_client_secret,
        debug_mode=settings.debug_mode,
    )
    google_collector = GoogleCollector(
        api_key=settings.api.google_api_key,
        search_engine_id=settings.api.search_engine_id,
        debug_mode=settings.debug_mode,
    )
    rss_collector = RSSCollector(debug_mode=settings.debug_mode)

    config = load_categories()
    categories = config["categories"]
    filters_config = config["filters"]
    window = get_collection_window_kst(window_hours=settings.time_window_hours)
    logger.info(
        "Collection window (%s): KST %s ~ %s",
        window.label,
        window.start_kst.strftime("%Y-%m-%d %H:%M"),
        window.end_kst.strftime("%Y-%m-%d %H:%M"),
    )

    time_filter = TimeFilter(
        window_hours=settings.time_window_hours,
        start_time=window.start_utc,
        end_time=window.end_utc,
    )
    # global_trend는 일일 뉴스가 아닌 느린 산업 트렌드 토픽이라 더 넓은 롤링 윈도우를
    # 사용한다. force_rolling으로 월요일 주말 갭 구간을 우회해 항상 넓은 윈도우를 유지한다.
    global_trend_window = get_collection_window_kst(
        window_hours=settings.global_trend_window_hours, force_rolling=True
    )
    global_trend_time_filter = TimeFilter(
        window_hours=settings.global_trend_window_hours,
        start_time=global_trend_window.start_utc,
        end_time=global_trend_window.end_utc,
    )
    logger.info(
        "global_trend window (%s): KST %s ~ %s",
        global_trend_window.label,
        global_trend_window.start_kst.strftime("%Y-%m-%d %H:%M"),
        global_trend_window.end_kst.strftime("%Y-%m-%d %H:%M"),
    )
    keyword_filter = KeywordFilter(
        blacklist_domains=filters_config["blacklist_domains"],
        excluded_keywords=filters_config["excluded_keywords"],
        global_trend_rules=filters_config.get("global_trend", {}),
        category_rules=categories,
    )

    collected_data: Dict[str, List[Dict]] = {}
    category_priority = {
        key: category.get("priority", category.get("id", 99))
        for key, category in categories.items()
    }

    for category_key, category_config in categories.items():
        logger.info("[%s] %s", category_config["id"], category_config["name"])
        category_articles: List[Dict] = []
        sources = category_config["sources"]
        keywords = category_config["keywords"]

        for keyword in keywords:
            logger.info("  Keyword: %s", keyword)

            if "naver_news" in sources:
                try:
                    category_articles.extend(
                        naver_collector.collect_from_news(keyword, limit=5)
                    )
                except Exception as exc:
                    logger.error("    Naver News failed: %s", exc)

            if "naver_blog" in sources:
                try:
                    category_articles.extend(
                        naver_collector.collect_from_blog(keyword, limit=5)
                    )
                except Exception as exc:
                    logger.error("    Naver Blog failed: %s", exc)

            if "naver_cafe" in sources:
                try:
                    category_articles.extend(
                        naver_collector.collect_from_cafe(keyword, limit=5)
                    )
                except Exception as exc:
                    logger.error("    Naver Cafe failed: %s", exc)

            if "google_search" in sources:
                try:
                    category_articles.extend(google_collector.collect(keyword, limit=5))
                except Exception as exc:
                    logger.error("    Google Search failed: %s", exc)

        if "rss_feed" in sources:
            for feed_config in category_config.get("rss_feeds", []):
                feed_url = feed_config.get("url", "")
                if not feed_url:
                    continue
                try:
                    category_articles.extend(
                        rss_collector.collect(
                            feed_url=feed_url,
                            source_name=feed_config.get("name", ""),
                            quality_weight=feed_config.get("weight", 1.0),
                            limit=feed_config.get("limit", 20),
                            topic_hint=feed_config.get("topic_hint", ""),
                            article_type=feed_config.get("article_type", "global"),
                        )
                    )
                except Exception as exc:
                    logger.error(
                        "    RSS feed %s failed: %s", feed_config.get("name", feed_url), exc
                    )

        active_time_filter = (
            global_trend_time_filter if category_key == "global_trend" else time_filter
        )
        category_articles = active_time_filter.filter_articles(category_articles)
        category_articles = keyword_filter.filter_articles(
            category_articles, category=category_key
        )
        deduplicator = Deduplicator()
        category_articles = deduplicator.deduplicate_within_category(category_articles)

        if persistent_deduplicator:
            category_articles = persistent_deduplicator.filter_new_only(category_articles)

        _apply_recency_boost(category_articles)

        category_articles = sorted(
            category_articles,
            key=lambda article: (
                int(article.get("relevance_score", 0)),
                PUBLISHED_CONFIDENCE_ORDER.get(
                    str(article.get("published_confidence", "missing")),
                    0,
                ),
                article.get("published") is not None,
                article.get("published"),
            ),
            reverse=True,
        )[: settings.max_articles_per_category]

        for article in category_articles:
            article["category"] = category_key
            article["category_priority"] = category_priority.get(category_key, 99)
            article["content_type"] = category_config.get(
                "content_type",
                "voc" if category_key.startswith("voc_") else "news",
            )

        collected_data[category_key] = category_articles
        logger.info("  Collected: %s articles", len(category_articles))

    logger.info("[Deduplicating across categories...]")
    all_articles = sorted(
        (
            article
            for category_articles in collected_data.values()
            for article in category_articles
        ),
        key=lambda article: (
            int(article.get("category_priority", 99)),
            -int(article.get("relevance_score", 0)),
        ),
    )
    cross_deduplicator = Deduplicator()
    unique_articles = cross_deduplicator.deduplicate_cross_categories(all_articles)

    deduplicated_data: Dict[str, List[Dict]] = {key: [] for key in categories}
    for article in unique_articles:
        deduplicated_data[article["category"]].append(article)

    logger.info("Total unique articles: %s", len(unique_articles))
    return deduplicated_data


def collect_external_alerts(settings: Settings) -> List[Dict]:
    logger.info("=== Collecting 0404 External Alerts ===")

    window = get_collection_window_kst(window_hours=settings.time_window_hours)
    start_date_kst = window.start_kst.strftime("%Y-%m-%d")
    end_date_kst = window.end_kst.strftime("%Y-%m-%d")
    logger.info(
        "[0404] Date window (KST): %s ~ %s",
        start_date_kst,
        end_date_kst,
    )

    collector = Mofa0404Collector(debug_mode=settings.debug_mode)
    return collector.collect_keyword_posts_by_date_range(
        start_date_kst, end_date_kst
    )


def analyze_articles(collected_data: Dict[str, List[Dict]], settings: Settings) -> Dict:
    logger.info("=== Starting AI Analysis ===")

    summarizer = Summarizer(
        api_key=settings.api.openai_api_key,
        base_url=settings.api.openai_base_url,
        model=settings.api.model_basic,
    )
    summary_data = summarizer.analyze(collected_data)

    insight_generator = InsightGenerator(
        api_key=settings.api.openai_api_key,
        base_url=settings.api.openai_base_url,
        model=settings.api.model_advanced,
    )
    insight_data = insight_generator.analyze(summary_data)

    final_data = {**insight_data}
    for category, summaries in summary_data.items():
        final_data[f"section_{category}"] = summaries

    logger.info("AI Analysis completed")
    return final_data
