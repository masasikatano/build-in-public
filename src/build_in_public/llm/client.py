import sys
import time
from typing import Any, Dict, List

import requests


def call_llm(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = "https://openrouter.ai/api/v1",
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if content is None:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                print("LLM Error: API returned empty content.", file=sys.stderr)
                sys.exit(1)
            return content
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("API rate limit exceeded. しばらく待って再実行してください", file=sys.stderr)
                sys.exit(1)
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print(f"LLM Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print(f"LLM Error: {e}", file=sys.stderr)
            sys.exit(1)

    return ""
