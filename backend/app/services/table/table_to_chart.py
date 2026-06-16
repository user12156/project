"""Convert matched table rows into chart JSON."""

from typing import Any

from app.services.chart.chart_normalizer import normalize_value


METRIC_LABELS = {
    "birth_count": "출생아 수",
    "death_count": "사망자 수",
    "marriage_count": "혼인 건수",
    "divorce_count": "이혼 건수",
    "natural_increase": "자연증가",
    "crude_birth_rate": "조출생률",
}

REGIONS = {
    "전국",
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
    "경기도",
    "강원도",
    "충청북도",
    "충청남도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주도",
}

REGION_NORMALIZE = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
    "제주도": "제주",
}

REGION_ORDER = [
    "전국",
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]


def _chart_error(message: str) -> dict[str, Any]:
    return {
        "type": "chart_error",
        "message": message,
    }


def normalize_region(value: Any) -> str | None:
    region = str(value or "").strip()
    if not region:
        return None
    region = REGION_NORMALIZE.get(region, region)
    return region if region in REGION_ORDER else None


def validate_birth_region_chart(year: str | None, data: list[dict[str, Any]]) -> bool:
    if year not in {"2024", "2025"}:
        return True

    values = [row["value"] for row in data if isinstance(row.get("value"), (int, float))]
    if not values:
        return False
    if max(values) < 10000:
        return False

    return True


def build_chart_from_table(
    request: dict[str, Any],
    table: dict[str, Any],
    x_col: str,
    y_col: str,
) -> dict[str, Any] | None:
    metric = request.get("metric")
    chart_type = request.get("chart_type") or "bar"
    metric_label = METRIC_LABELS.get(metric, "값")

    data = []
    for row in table.get("rows", []):
        x_value = row.get(x_col)
        y_value = normalize_value(row.get(y_col))

        if x_value is None or y_value is None:
            continue
        if request.get("dimension") == "region":
            x_value = normalize_region(x_value)
            if not x_value:
                continue
        if not isinstance(y_value, (int, float)):
            continue

        data.append(
            {
                "category": str(x_value).strip(),
                "value": y_value,
            }
        )

    if request.get("dimension") == "region":
        order = {region: index for index, region in enumerate(REGION_ORDER)}
        data.sort(key=lambda row: order.get(row["category"], len(REGION_ORDER)))

    if len(data) < 2:
        return None

    if request.get("dimension") == "region" and request.get("metric") == "birth_count":
        if not validate_birth_region_chart(request.get("year"), data):
            return _chart_error("선택된 컬럼의 출생아 수 값이 연간 시도별 출생아 수 범위와 맞지 않습니다.")

    year = request.get("year")
    title_prefix = f"{year}년 " if year else ""

    return {
        "type": "chart",
        "chartType": chart_type,
        "template": "regional_bar" if request.get("dimension") == "region" else "default",
        "title": f"{title_prefix}{metric_label} 비교",
        "xAxisKey": "category",
        "series": [
            {
                "dataKey": "value",
                "name": metric_label,
                "yAxisId": "left",
            }
        ],
        "data": data,
    }
