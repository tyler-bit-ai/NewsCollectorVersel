"""진단 전용 (v2, 2cd280d 신규 코드용): global_trend 수집 깔때기 + 드롭 사유 출력.

새 keyword_filter는 relevance_reason 으로 탈락 사유를 기록하므로, 어느 게이트에서
얼마나 떨어지는지 단계별로 보여준다. OpenAI 요약 / 메일은 수행하지 않는다.
"""

from __future__ import annotations

import logging
from collections import Counter

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] [%(name)s] %(message)s")
logging.getLogger("urllib3").setLevel(logging.INFO)

from src.collectors.google_collector import GoogleCollector
from src.config.settings import load_settings
from src.filters.deduplicator import Deduplicator
from src.filters.keyword_filter import KeywordFilter
from src.filters.time_filter import TimeFilter
from src.pipeline.core import PUBLISHED_CONFIDENCE_ORDER, load_categories
from src.utils.time_windows import get_collection_window_kst


def main() -> None:
    settings = load_settings()
    cfg = load_categories()
    categories = cfg["categories"]
    filters_config = cfg["filters"]
    window = get_collection_window_kst(
        window_hours=settings.global_trend_window_hours, force_rolling=True
    )

    print("=" * 74)
    print(f"global_trend WINDOW: 최근 {settings.global_trend_window_hours}시간 (KST {window.start_kst:%Y-%m-%d %H:%M} ~ {window.end_kst:%Y-%m-%d %H:%M})")
    print("time_filter allow_missing_published = 기본값 True (undated 허용)")
    print("=" * 74)

    gc = GoogleCollector(
        api_key=settings.api.google_api_key,
        search_engine_id=settings.api.search_engine_id,
        debug_mode=True,
    )
    tf = TimeFilter(
        window_hours=settings.global_trend_window_hours,
        start_time=window.start_utc,
        end_time=window.end_utc,
    )
    kf = KeywordFilter(
        blacklist_domains=filters_config["blacklist_domains"],
        excluded_keywords=filters_config["excluded_keywords"],
        global_trend_rules=filters_config.get("global_trend", {}),
        category_rules=categories,
    )

    cat = categories["global_trend"]
    raw_all: list[dict] = []
    api_errors: list[tuple[str, str]] = []
    for kw in cat["keywords"]:
        try:
            items = gc.collect(kw, limit=5)
        except Exception as exc:  # noqa: BLE001
            api_errors.append((kw, str(exc)))
            items = []
        print(f"[kw] {kw:<45} -> Google {len(items)}")
        raw_all.extend(items)

    print("-" * 74)
    print(f"Google RAW total: {len(raw_all)}")
    if api_errors:
        print(f"!! {len(api_errors)} keyword API error:")
        for kw, err in api_errors:
            print(f"    - {kw}: {err}")

    # 시간 필터 (core.py 와 동일: allow_missing 기본 True)
    after_time = tf.filter_articles(raw_all)
    undated = [a for a in raw_all if not a.get("published")]
    dated = [a for a in raw_all if a.get("published")]
    in_window = [a for a in dated if tf.is_valid(a["published"])]
    print("-" * 74)
    print("Time filter:")
    print(f"  undated 통과          : {len(undated)}")
    print(f"  dated 중 24h 내 통과  : {len(in_window)}")
    print(f"  dated 중 24h 밖 탈락  : {len(dated) - len(in_window)}")
    print(f"  ==> time filter 통과  : {len(after_time)}")

    # 키워드 필터: 통과/탈락 + relevance_reason 집계
    passed: list[dict] = []
    reason_counter: Counter = Counter()
    for a in after_time:
        ok = kf.validate(a, category="global_trend")
        if ok:
            passed.append(a)
        else:
            reason = a.get("relevance_reason") or "unknown"
            reason_counter[reason] += 1
    print("-" * 74)
    print(f"Keyword filter: {len(passed)} / {len(after_time)} passed")
    if reason_counter:
        print("  탈락 사유(relevance_reason) 집계:")
        for reason, count in reason_counter.most_common():
            print(f"    {count:>3}  {reason}")

    # core.py 와 동일하게 dedup -> relevance_score 정렬 -> cap
    deduped = Deduplicator().deduplicate_within_category(passed)
    ranked = sorted(
        deduped,
        key=lambda article: (
            int(article.get("relevance_score", 0)),
            PUBLISHED_CONFIDENCE_ORDER.get(
                str(article.get("published_confidence", "missing")), 0
            ),
            article.get("published") is not None,
            article.get("published"),
        ),
        reverse=True,
    )[: settings.max_articles_per_category]

    print("=" * 74)
    print(f"FINAL global_trend (cap {settings.max_articles_per_category}): {len(ranked)}")
    for a in ranked:
        pub = a.get("published")
        pub_s = pub.strftime("%Y-%m-%d") if pub else "undated"
        score = a.get("relevance_score", 0)
        print(f"  - [s{score}|{pub_s}] {a.get('title', '')[:66]}")


if __name__ == "__main__":
    main()
