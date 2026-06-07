import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        print(f"Config Error: {config_path} not found.", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        print("Config Error: config.yaml is invalid.", file=sys.stderr)
        sys.exit(1)
    return config


def load_env() -> dict:
    load_dotenv()
    env = {
        "GOOGLE_CREDENTIALS_PATH": os.getenv("GOOGLE_CREDENTIALS_PATH", ""),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", "openrouter"),
        "LLM_MODEL": os.getenv("LLM_MODEL", "anthropic/claude-3.5-sonnet"),
        "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL", ""),
    }
    return env


def validate_github_config(config: dict, env: dict) -> dict:
    if not config.get("github_repo"):
        print("Config Error: github_repo is required in config.yaml", file=sys.stderr)
        sys.exit(1)

    if not env.get("OPENROUTER_API_KEY"):
        print("Config Error: OPENROUTER_API_KEY is required in .env", file=sys.stderr)
        sys.exit(1)

    return {**config, **env}


def validate_config(config: dict, env: dict) -> dict:
    required = ["site_name", "ga4_property_id"]
    for field in required:
        if not config.get(field):
            print(f"Config Error: {field} is required in config.yaml", file=sys.stderr)
            sys.exit(1)

    if not env.get("GOOGLE_CREDENTIALS_PATH"):
        print("Config Error: GOOGLE_CREDENTIALS_PATH is required in .env", file=sys.stderr)
        sys.exit(1)

    creds_path = Path(env["GOOGLE_CREDENTIALS_PATH"])
    if not creds_path.exists():
        print(f"Config Error: Credentials file not found: {creds_path}", file=sys.stderr)
        sys.exit(1)

    if not env.get("OPENROUTER_API_KEY"):
        print("Config Error: OPENROUTER_API_KEY is required in .env", file=sys.stderr)
        sys.exit(1)

    return {**config, **env}
