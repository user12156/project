MONTH_LABELS = [f"{i}월" for i in range(1, 13)]


DEFAULT_SERIES_COLORS = [
    "#2563eb",  # 파랑
    "#16a34a",  # 초록
    "#dc2626",  # 빨강
    "#9333ea",  # 보라
    "#f97316",  # 주황
    "#0891b2",  # 청록
    "#be123c",  # 진분홍
    "#4f46e5",  # 남색
    "#65a30d",  # 올리브
    "#c2410c",  # 진주황
]


COMMON_OPTIONS = {
    "showLegend": True,
    "showTooltip": True,
    "showDataLabels": False,
    "connectNulls": False,
    "grid": {
        "top": 48,
        "right": 48,
        "bottom": 56,
        "left": 64,
    },
}


CHART_TEMPLATES = {
    "monthly_trend": {
        **COMMON_OPTIONS,
        "xAxisMode": "month_12",
        "xCategories": MONTH_LABELS,
        "missingValue": None,
        "connectNulls": False,
    },
    "yearly_trend": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "missingValue": None,
        "connectNulls": False,
    },
    "regional_bar": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "sort": "desc",
        "limit": 20,
    },
    "category_bar": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
        "sort": None,
    },
    "dual_axis": {
        **COMMON_OPTIONS,
        "useDualAxis": True,
    },
    "default": {
        **COMMON_OPTIONS,
        "xAxisMode": "category",
    },
}


def guess_template(chart_json: dict) -> str:
    title = str(chart_json.get("title", ""))
    x_key = str(chart_json.get("xAxisKey", chart_json.get("xKey", "")))
    data = chart_json.get("data") or []

    sample_labels = " ".join(str(row.get(x_key, "")) for row in data[:12])

    if "월" in title or "월별" in title or "월" in sample_labels or x_key.lower() == "month":
        return "monthly_trend"

    if "지역" in title or x_key.lower() in {"region", "area"}:
        return "regional_bar"

    if "연도" in title or x_key.lower() == "year":
        return "yearly_trend"

    series = chart_json.get("series") or []
    y_axis_ids = {s.get("yAxisId") for s in series if s.get("yAxisId")}
    if len(y_axis_ids) >= 2:
        return "dual_axis"

    return "default"


def apply_template(chart_json: dict) -> dict:
    template_name = chart_json.get("template") or guess_template(chart_json)
    template = CHART_TEMPLATES.get(template_name, CHART_TEMPLATES["default"])

    chart_json["template"] = template_name
    chart_json["options"] = {
        **template,
        **chart_json.get("options", {}),
    }

    return chart_json