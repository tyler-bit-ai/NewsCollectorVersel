# TODOs

## Global Trend source expansion — round 2 (industry press)

**What:** Add a 4th wave of trade-press RSS feeds: Light Reading, Capacity Media,
Telecoms.com, Mobile Europe.

**Why:** Round 1 (this change) added TeleGeography, Mobile World Live, and
Telecoms Tech News — feeds whose domains already had unused quality weights
sitting in `rss_collector.py`. Round 2 would be genuinely new sources, roughly
tripling raw volume again, but each new domain needs its own
`excluded_url_patterns`/`excluded_domains` tuning since off-topic content
shapes differ per site (verified during round 1: `_apply_category_rule`'s
`include_keywords` gate on the `content` field, title+snippet only, is what
actually protects relevance — RSS `topic_hint` must never be added to that
match field, see `src/filters/keyword_filter.py:408-420`).

**Pros:** More raw volume, more day-to-day variety in the email digest.

**Cons:** More filter-tuning surface area; each new feed needs a manual
spot-check like the one done for round 1 (see Context) before trusting its
pass-through rate.

**Context:** Round 1 verification method: collect raw articles from each feed,
run them through `KeywordFilter.validate(..., category="global_trend")` with
the real `categories.yaml` config (via `load_categories()`), and manually
review the passed titles for relevance before trusting the numbers. Round 1
result: 8 feeds → 100 raw → 7 passed relevance (up from ~2 with the original
5 feeds). Do the same check for any new feed before merging.

**Depends on / blocked by:** None.

---

## Global Trend source expansion — Google News RSS query source

**What:** Add `news.google.com/rss/search?q=...` as a broad-net source
alongside the curated RSS feeds, using the same query terms already in
`categories.global_trend.keywords`.

**Why:** Automatically picks up new/unlisted outlets without maintaining a
feed list, at the cost of noisier raw input (needs the same relevance gate,
which is already fine since it works on title+snippet content regardless of
source).

**Pros:** Zero-maintenance breadth; catches outlets not yet on the curated
list.

**Cons:** Google News RSS snippets are often just the source name + a few
words, which may starve the `include_keywords` content-match gate of
signal (untested — needs the same manual spot-check as round 1 before
trusting it).

**Depends on / blocked by:** None, but do this after round 2 (curated feeds)
since curated feeds are higher-confidence-per-engineering-hour.

---

## RCR Wireless "roaming" tag feed is nearly dormant

**What:** `https://www.rcrwireless.com/tag/roaming/feed` — verified live on
2026-07-05: of 10 raw entries, only 1 falls inside the 30-day collection
window, and it's a generic "5G interoperability" piece that doesn't even
pass the relevance gate. The most recent genuinely on-topic article in this
feed ("Vodafone Germany, 1&1 launch national roaming partnership") is dated
2024-08-26 — essentially the tag page has gone quiet.

**Why:** This is one of the original 5 configured feeds (pre-dating this
change) contributing close to 0 articles/day currently. Worth deciding
whether to keep, replace with a different RCR Wireless feed (e.g. the
un-tagged general feed with a stricter content filter), or drop it.

**Pros:** Removing/replacing a dead-weight feed reduces noise and wasted
fetch calls without losing real coverage.

**Cons:** Tag pages can become active again if RCR's editorial focus shifts;
removing it isn't fully reversible-free (small chance of missing a future
relevant post).

**Context:** Confirmed via the same live-fetch verification harness used for
round 1 (`src/collectors/rss_collector.py`'s `RSSCollector.collect()` called
directly against the live feed URL).

**Depends on / blocked by:** None.
