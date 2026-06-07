import argparse
import sys
from datetime import datetime as dt, timedelta
from pathlib import Path
from typing import List

from build_in_public.analytics.ga4 import fetch_ga4_data, get_client as get_ga4_client
from build_in_public.config import load_config, load_env, validate_config, validate_github_config
from build_in_public.github.client import fetch_commits
from build_in_public.github.formatter import build_activity_summary, format_commit_log, format_commit_summary
from build_in_public.llm.client import call_llm
from build_in_public.llm.prompt_builder import build_user_prompt, load_system_prompt, parse_post_patterns
from build_in_public.utils.archive_manager import load_week_data, save_github_data, save_week_data
from build_in_public.utils.date_helpers import (
    JST,
    format_date_range,
    format_utc_iso,
    get_jst_day_bounds,
    get_week_bounds,
    iso_week_str,
)
from build_in_public.writers.markdown_writer import build_analytics_summary, write_daily_report, write_report


def generate_command(args: argparse.Namespace) -> None:
    print("Loading config...")
    config = load_config()
    env = load_env()
    settings = validate_config(config, env)

    start, end = get_week_bounds(args.week, args.date)
    print(f"Target week: {format_date_range(start, end)}")

    # Check existing file
    posts_dir = Path(settings["posts_dir"])
    report_path = posts_dir / f"{start.isoformat()}.md"
    if report_path.exists() and not args.force:
        print(f"File already exists: {report_path}. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    # Google Auth
    creds_path = settings["GOOGLE_CREDENTIALS_PATH"]
    print("Fetching GA4 data...")
    ga4_client = get_ga4_client(creds_path)
    ga4_data = fetch_ga4_data(ga4_client, settings["ga4_property_id"], start, end)

    # Load previous week data
    print("Loading previous week data...")
    prev_start = start - timedelta(days=7)
    prev_ga4 = load_week_data(settings["archive_dir"], prev_start)

    # Analytics summary markdown
    analytics_summary = build_analytics_summary(ga4_data, prev_ga4)

    # Few-shot & prompt
    print("Building prompt...")
    system_prompt = load_system_prompt(settings["prompts_dir"])
    user_prompt = build_user_prompt(
        settings["prompts_dir"],
        settings["examples_file"],
        analytics_summary=analytics_summary,
        site_name=settings.get("site_name", ""),
        site_url=settings.get("site_url", ""),
        site_description=settings.get("site_description", ""),
        data_type="ga_weekly",
    )

    # Call LLM
    print("Generating post drafts via LLM...")
    raw_response, model_used = call_llm(
        api_key=settings["OPENROUTER_API_KEY"],
        model=settings["LLM_MODEL"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    patterns = parse_post_patterns(raw_response)
    if not all(patterns):
        print("Warning: Some post patterns could not be parsed. Using raw response fallback.", file=sys.stderr)
        # 最低限フォールバック
        fallback = raw_response or ""
        if not patterns[0]:
            patterns[0] = fallback[:280]
        if not patterns[1]:
            patterns[1] = fallback[280:560] if len(fallback) > 280 else ""
        if not patterns[2]:
            patterns[2] = fallback[560:840] if len(fallback) > 560 else ""

    # Notes
    notes: List[str] = []
    if ga4_data.get("pv", 0) < 100:
        notes.append("今週はデータ少なめなので控えめに")

    # Write report
    report_path = write_report(
        settings["posts_dir"],
        start,
        end,
        analytics_summary,
        patterns,
        notes,
        model_used=model_used,
    )
    print(f"Report written: {report_path}")

    # Archive
    archive_data = {
        "week": iso_week_str(start),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "ga4": ga4_data,
        "model_used": model_used,
    }
    save_week_data(settings["archive_dir"], start, archive_data)
    print("Archive saved.")
    print("Done!")


def github_command(args: argparse.Namespace) -> None:
    # Validate date format first
    date_str = args.date
    if date_str:
        try:
            dt.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    else:
        date_str = dt.now(JST).date().isoformat()

    print("Loading config...")
    config = load_config()
    env = load_env()
    settings = validate_github_config(config, env)

    posts_dir = Path(settings["posts_dir"])
    report_path = posts_dir / "daily" / f"{date_str}.md"
    if report_path.exists() and not args.force:
        print(
            f"File already exists: {report_path}. Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    repo = settings["github_repo"]
    token = env.get("GITHUB_TOKEN") or None
    since_dt, until_dt = get_jst_day_bounds(date_str)
    since = format_utc_iso(since_dt)
    until = format_utc_iso(until_dt)

    print(f"Fetching commits for {repo} ({date_str} JST)...")
    commits = fetch_commits(repo, token, since=since, until=until)

    if not commits:
        print("Warning: No commits found for the specified date.")

    commit_summary = format_commit_summary(commits, date_str)
    activity_summary = build_activity_summary(commits)
    commit_log = format_commit_log(commits)

    system_prompt = load_system_prompt(settings["prompts_dir"])
    user_prompt = build_user_prompt(
        settings["prompts_dir"],
        settings["examples_file"],
        site_name=settings.get("site_name", ""),
        site_url=settings.get("site_url", ""),
        site_description=settings.get("site_description", ""),
        data_type="github_daily",
        commit_summary=commit_summary,
    )

    print("Generating post drafts via LLM...")
    raw_response, model_used = call_llm(
        api_key=settings["OPENROUTER_API_KEY"],
        model=settings["LLM_MODEL"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    # Archive raw data
    archive_data = {
        "date": date_str,
        "repo": repo,
        "branch": "main",
        "total_commits": len(commits),
        "commits": commits,
        "model_used": model_used,
    }
    print("Archiving raw data...")
    save_github_data(settings["archive_dir"], date_str, archive_data)

    patterns = parse_post_patterns(raw_response)
    if not all(patterns):
        print("Warning: Some post patterns could not be parsed. Using raw response fallback.", file=sys.stderr)
        fallback = raw_response or ""
        if not patterns[0]:
            patterns[0] = fallback[:280]
        if not patterns[1]:
            patterns[1] = fallback[280:560] if len(fallback) > 280 else ""
        if not patterns[2]:
            patterns[2] = fallback[560:840] if len(fallback) > 560 else ""

    repo_url = f"https://github.com/{repo}"
    report_path = write_daily_report(
        settings["posts_dir"],
        date_str,
        activity_summary,
        patterns,
        commit_log,
        repo_url=repo_url,
        model_used=model_used,
    )
    print(f"Report written: {report_path}")
    print("Done!")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="build-in-public",
        description="Build in Public weekly report generator",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate weekly report")
    gen_parser.add_argument("--week", type=str, default=None, help="Week in YYYY-Www format")
    gen_parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD format (uses that week)")
    gen_parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    gen_parser.set_defaults(func=generate_command)

    gh_parser = subparsers.add_parser("github", help="Generate daily GitHub commit report")
    gh_parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD format (default: today JST)")
    gh_parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    gh_parser.set_defaults(func=github_command)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
