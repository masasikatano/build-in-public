import sys
from datetime import date
from typing import Any, Dict, List

from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_service(credentials_path: str):
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        return build("webmasters", "v3", credentials=credentials)
    except Exception as e:
        print(f"Search Console API Error: 認証情報を確認してください\n{e}", file=sys.stderr)
        sys.exit(1)


def fetch_search_console_data(
    service,
    site_url: str,
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 5,
        "startRow": 0,
    }

    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as e:
        print(f"Search Console API Error: {e}", file=sys.stderr)
        sys.exit(1)

    result: Dict[str, Any] = {
        "clicks": 0,
        "impressions": 0,
        "position": 0.0,
        "top_queries": [],
    }

    rows = response.get("rows", [])
    if rows:
        # 全体サマリー（queryディメンションなしで再取得）
        summary_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }
        try:
            summary_response = (
                service.searchanalytics().query(siteUrl=site_url, body=summary_body).execute()
            )
        except Exception as e:
            print(f"Search Console API Error (summary): {e}", file=sys.stderr)
            sys.exit(1)

        summary_rows = summary_response.get("rows", [])
        if summary_rows:
            srow = summary_rows[0]
            result["clicks"] = int(srow.get("clicks", 0))
            result["impressions"] = int(srow.get("impressions", 0))
            result["position"] = round(float(srow.get("position", 0)), 2)

        queries: List[Dict[str, Any]] = []
        for row in rows:
            queries.append({
                "query": row["keys"][0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "position": round(float(row.get("position", 0)), 2),
            })
        result["top_queries"] = queries

    return result
