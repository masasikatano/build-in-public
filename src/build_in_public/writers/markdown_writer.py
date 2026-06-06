from datetime import date
from pathlib import Path
from typing import Any, Dict, List


def format_seconds(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s:02d}s"


def format_change(value: float | None) -> str:
    if value is None:
        return ""
    sign = "+" if value >= 0 else ""
    return f" ({sign}{value:.1f}% from last week)"


def build_analytics_summary(
    ga4: Dict[str, Any],
    sc: Dict[str, Any],
    prev_ga4: Dict[str, Any] | None,
    prev_sc: Dict[str, Any] | None,
) -> str:
    lines: List[str] = []

    pv_change = _pct_change(prev_ga4, ga4, "pv") if prev_ga4 else None
    sessions_change = _pct_change(prev_ga4, ga4, "sessions") if prev_ga4 else None
    users_change = _pct_change(prev_ga4, ga4, "users") if prev_ga4 else None

    lines.append(f"- **PV**: {ga4.get('pv', 0):,}{format_change(pv_change)}")
    lines.append(f"- **Sessions**: {ga4.get('sessions', 0):,}{format_change(sessions_change)}")
    lines.append(f"- **Unique Users**: {ga4.get('users', 0):,}{format_change(users_change)}")
    lines.append(f"- **Avg. Engagement Time**: {format_seconds(ga4.get('avg_engagement_time', 0))}")

    lines.append("- **Top Pages**:")
    for i, page in enumerate(ga4.get("top_pages", []), 1):
        lines.append(f"  {i}. `{page['path']}` — {page['views']:,} views")

    clicks_change = _pct_change(prev_sc, sc, "clicks") if prev_sc else None
    impressions_change = _pct_change(prev_sc, sc, "impressions") if prev_sc else None

    lines.append("- **Search Console**:")
    lines.append(f"  - Clicks: {sc.get('clicks', 0):,}{format_change(clicks_change)}")
    lines.append(f"  - Impressions: {sc.get('impressions', 0):,}{format_change(impressions_change)}")
    lines.append(f"  - Avg Position: {sc.get('position', 0)}")
    top_query = sc.get("top_queries", [{}])[0]
    if top_query:
        lines.append(f"  - Top Query: \"{top_query.get('query', '')}\" ({top_query.get('clicks', 0)} clicks)")

    return "\n".join(lines)


def _pct_change(prev: Dict[str, Any], curr: Dict[str, Any], key: str) -> float | None:
    p = prev.get(key, 0)
    c = curr.get(key, 0)
    if p == 0:
        return None
    return round(((c - p) / p) * 100, 1)


def write_report(
    posts_dir: str,
    start: date,
    end: date,
    analytics_summary: str,
    patterns: List[str],
    notes: List[str],
) -> Path:
    dir_path = Path(posts_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{start.isoformat()}.md"

    lines: List[str] = [
        f"# Build in Public Report: {start.isoformat()} ~ {end.isoformat()}",
        "",
        "## 📊 This Week's Stats",
        analytics_summary,
        "",
        "## 📝 Post Drafts",
        "",
        "### Pattern A: Straight (levelsio風)",
        patterns[0] if len(patterns) > 0 else "",
        "",
        "### Pattern B: Self-deprecating",
        patterns[1] if len(patterns) > 1 else "",
        "",
        "### Pattern C: Future-oriented",
        patterns[2] if len(patterns) > 2 else "",
        "",
        "## 💡 Notes for Editor",
    ]

    if notes:
        for note in notes:
            lines.append(f"- {note}")
    else:
        lines.append("- 特になし")

    lines.append("")
    content = "\n".join(lines)
    file_path.write_text(content, encoding="utf-8")
    return file_path
