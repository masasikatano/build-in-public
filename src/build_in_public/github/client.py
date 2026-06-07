import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

GITHUB_API_BASE = "https://api.github.com"


def _parse_link_header(link_header: str | None) -> Optional[str]:
    if not link_header:
        return None
    parts = link_header.split(",")
    for part in parts:
        match = re.match(r'<([^>]+)>;\s*rel="next"', part.strip())
        if match:
            return match.group(1)
    return None


def fetch_commits(
    repo: str,
    token: str | None,
    since: str,
    until: str,
    branch: str = "main",
    per_page: int = 100,
) -> List[Dict[str, Any]]:
    url = f"{GITHUB_API_BASE}/repos/{repo}/commits"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "sha": branch,
        "since": since,
        "until": until,
        "per_page": per_page,
    }

    all_commits: List[Dict[str, Any]] = []
    next_url: str | None = url

    while next_url:
        try:
            response = requests.get(
                next_url,
                headers=headers,
                params=params if next_url == url else None,
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            print(f"GitHub Error: {e}", file=sys.stderr)
            sys.exit(1)

        if response.status_code == 404:
            print(f"GitHub Error: Repository not found: {repo}", file=sys.stderr)
            sys.exit(1)
        elif response.status_code == 403:
            try:
                msg = response.json().get("message", "")
            except Exception:
                msg = ""
            if "rate limit" in msg.lower() or response.headers.get("X-RateLimit-Remaining") == "0":
                print(
                    "GitHub API rate limit exceeded. GITHUB_TOKENを設定してください",
                    file=sys.stderr,
                )
            else:
                print(f"GitHub Error: {msg or 'Forbidden'}", file=sys.stderr)
            sys.exit(1)
        elif response.status_code == 401:
            print("GitHub Error: Bad credentials. GITHUB_TOKENを確認してください", file=sys.stderr)
            sys.exit(1)
        elif not response.ok:
            print(f"GitHub Error: {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)

        try:
            data = response.json()
        except Exception as e:
            print(f"GitHub Error: Failed to parse response: {e}", file=sys.stderr)
            sys.exit(1)

        if not isinstance(data, list):
            print("GitHub Error: Unexpected response format", file=sys.stderr)
            sys.exit(1)

        for item in data:
            commit_info = item.get("commit", {})
            author_info = commit_info.get("author", {})
            # Prefer GitHub login; fall back to commit author name
            author = ""
            if item.get("author") and item["author"].get("login"):
                author = item["author"]["login"]
            elif commit_info.get("author") and commit_info["author"].get("name"):
                author = commit_info["author"]["name"]

            date_raw = author_info.get("date", "")
            date_jst = ""
            if date_raw:
                try:
                    dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                    date_jst = dt.astimezone(timezone(timedelta(hours=9))).isoformat()
                except Exception:
                    date_jst = date_raw

            sha = item.get("sha", "")[:7]
            message = commit_info.get("message", "").split("\n")[0].strip()
            html_url = item.get("html_url", "")

            all_commits.append({
                "sha": sha,
                "message": message,
                "author": author,
                "date": date_jst,
                "url": html_url,
            })

        next_url = _parse_link_header(response.headers.get("Link"))

    return all_commits


def fetch_commit_detail(
    repo: str,
    sha: str,
    token: str | None,
) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{repo}/commits/{sha}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = requests.get(url, headers=headers, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"GitHub Error: {e}", file=sys.stderr)
        return {}

    if not response.ok:
        print(f"GitHub Error: {response.status_code} - {response.text}", file=sys.stderr)
        return {}

    try:
        data = response.json()
    except Exception as e:
        print(f"GitHub Error: Failed to parse response: {e}", file=sys.stderr)
        return {}

    stats = data.get("stats", {})
    files = [
        {
            "filename": f.get("filename", ""),
            "status": f.get("status", ""),
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
        }
        for f in data.get("files", [])
    ]
    return {"stats": stats, "files": files}


def enrich_commits_with_details(
    commits: List[Dict[str, Any]],
    repo: str,
    token: str | None,
) -> List[Dict[str, Any]]:
    import time

    total = len(commits)
    if total > 50:
        print(f"Warning: {total} commits found. Fetching details for each may take a while.")

    enriched = []
    for i, commit in enumerate(commits, 1):
        detail = fetch_commit_detail(repo, commit["sha"], token)
        commit["stats"] = detail.get("stats", {})
        commit["files"] = detail.get("files", [])
        enriched.append(commit)
        if i < total:
            time.sleep(0.3)
    return enriched
