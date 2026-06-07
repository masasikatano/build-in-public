from typing import Any, Dict, List


def format_commit_summary(commits: List[Dict[str, Any]], date_str: str) -> str:
    lines = [f"## Today's Commits ({date_str})", "", f"Total: {len(commits)} commits", ""]
    for i, commit in enumerate(commits, 1):
        author = commit.get("author") or "unknown"
        message = commit.get("message") or ""
        sha = commit.get("sha") or ""
        lines.append(f"{i}. `{sha}` by @{author} — {message}")
    return "\n".join(lines)


def format_commit_log(commits: List[Dict[str, Any]]) -> str:
    if not commits:
        return "- 本日はコミットがありませんでした"
    lines = []
    for commit in commits:
        author = commit.get("author") or "unknown"
        message = commit.get("message") or ""
        sha = commit.get("sha") or ""
        lines.append(f"- `{sha}` — {message} by @{author}")
    return "\n".join(lines)


def build_activity_summary(commits: List[Dict[str, Any]]) -> str:
    if not commits:
        return "本日はコミットがありませんでした。"
    lines = [f"- Commits: {len(commits)}件"]
    # List top 3 commit messages as "main changes"
    messages = [c.get("message", "") for c in commits if c.get("message")]
    if messages:
        top = messages[:3]
        others = len(messages) - len(top)
        desc = "、".join(top)
        if others > 0:
            desc += f" など"
        lines.append(f"- 主な変更: {desc}")
    return "\n".join(lines)
