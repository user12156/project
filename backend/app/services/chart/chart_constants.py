"""Chart defaults, options, and templates."""

ALLOWED_CHART_TYPES = {"line", "bar"}

NULL_VALUES = {
    "",
    "-",
    "없음",
    "해당없음",
    "미상",
    "...",
    "N/A",
    "NA",
    "null",
    "None",
}

MONTH_LABELS = [f"{index}월" for index in range(1, 13)]

DEFAULT_SERIES_COLORS = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#9333ea",
    "#f97316",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#65a30d",
    "#c2410c",
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
