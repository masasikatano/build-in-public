import random
import re
from pathlib import Path
from typing import List

from jinja2 import Template


def load_system_prompt(prompts_dir: str) -> str:
    path = Path(prompts_dir) / "system_prompt.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_generate_template(prompts_dir: str) -> Template:
    path = Path(prompts_dir) / "generate_post.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return Template(path.read_text(encoding="utf-8"))


def load_few_shot_examples(examples_file: str, max_examples: int = 5) -> str:
    path = Path(examples_file)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n---\s*\n", text)
    examples: List[str] = []
    for block in blocks:
        block = block.strip()
        if block:
            examples.append(block)
    # ランダムに選択
    if len(examples) > max_examples:
        examples = random.sample(examples, max_examples)
    return "\n---\n".join(examples)


def build_user_prompt(
    prompts_dir: str,
    examples_file: str,
    analytics_summary: str = "",
    site_name: str = "",
    site_url: str = "",
    site_description: str = "",
    data_type: str = "ga_weekly",
    commit_summary: str = "",
) -> str:
    template = load_generate_template(prompts_dir)
    few_shot = load_few_shot_examples(examples_file)
    return template.render(
        analytics_summary=analytics_summary,
        commit_summary=commit_summary,
        few_shot_examples=few_shot,
        site_name=site_name,
        site_url=site_url,
        site_description=site_description,
        data_type=data_type,
    )


def parse_post_patterns(content: str | None) -> List[str]:
    """
    LLMのレスポンスから3パターンを抽出する。
    Pattern A / Pattern B / Pattern C の見出しに続く本文を取得。
    """
    if not content:
        return ["", "", ""]
    patterns = []
    for label in ["Pattern A", "Pattern B", "Pattern C"]:
        regex = rf"####?\s*{re.escape(label)}.*?\n+(.+?)(?=####?\s*Pattern|$)"
        match = re.search(regex, content, re.DOTALL)
        if match:
            text = match.group(1).strip()
            patterns.append(text)
        else:
            # fallback: より緩い検索
            regex2 = rf"{re.escape(label)}.*?\n+(.+?)(?=Pattern [A-C]|$)"
            match2 = re.search(regex2, content, re.DOTALL)
            if match2:
                patterns.append(match2.group(1).strip())
            else:
                patterns.append("")
    return patterns
