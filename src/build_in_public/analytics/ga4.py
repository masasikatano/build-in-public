import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account


def get_client(credentials_path: str) -> BetaAnalyticsDataClient:
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        return BetaAnalyticsDataClient(credentials=credentials)
    except Exception as e:
        print(f"GA4 API Error: 認証情報を確認してください\n{e}", file=sys.stderr)
        sys.exit(1)


def fetch_ga4_data(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    property_str = f"properties/{property_id}"
    date_range = DateRange(start_date=start_date.isoformat(), end_date=end_date.isoformat())

    # 基本指標
    request = RunReportRequest(
        property=property_str,
        date_ranges=[date_range],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="averageEngagementTimePerSession"),
        ],
    )

    try:
        response = client.run_report(request)
    except Exception as e:
        print(f"GA4 API Error: {e}", file=sys.stderr)
        sys.exit(1)

    result: Dict[str, Any] = {
        "pv": 0,
        "sessions": 0,
        "users": 0,
        "avg_engagement_time": 0.0,
        "top_pages": [],
    }

    if response.rows:
        row = response.rows[0]
        result["pv"] = int(row.metric_values[0].value)
        result["sessions"] = int(row.metric_values[1].value)
        result["users"] = int(row.metric_values[2].value)
        result["avg_engagement_time"] = float(row.metric_values[3].value)

    # Top pages
    top_request = RunReportRequest(
        property=property_str,
        date_ranges=[date_range],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        order_bys=[{"metric": {"metric_name": "screenPageViews"}, "desc": True}],
        limit=5,
    )

    try:
        top_response = client.run_report(top_request)
    except Exception as e:
        print(f"GA4 API Error (top pages): {e}", file=sys.stderr)
        sys.exit(1)

    pages: List[Dict[str, Any]] = []
    for row in top_response.rows:
        path = row.dimension_values[0].value
        views = int(row.metric_values[0].value)
        pages.append({"path": path, "views": views})
    result["top_pages"] = pages

    return result
