"""Auto-charter: Converts pure Table JSON into Recharts visual configs based on data heuristics."""

import re

def auto_chart_config(table_config: dict) -> dict:
    if table_config.get("type") != "table":
        return table_config

    data = table_config.get("data") or []
    if not data:
        return table_config

    columns = table_config.get("columns") or []
    if not columns:
        # Auto-generate columns from data keys if AI forgot them
        keys = []
        for row in data:
            if isinstance(row, dict):
                for k in row.keys():
                    if k not in keys:
                        keys.append(k)
        if len(keys) < 2:
            return table_config
        columns = [{"key": k, "label": k} for k in keys]
        table_config["columns"] = columns

    recommended = table_config.get("recommended_chart") or "table"
    
    # 1. Analyze columns
    category_key = columns[0]["key"]
    numeric_keys = [col["key"] for col in columns[1:]]

    # If there are no numeric keys, we can't chart it.
    if not numeric_keys:
        return table_config

    # 2. Check data length
    data_length = len(data)

    # Rule 1: Very small data sets (<= 2) should always be Bar Chart or Pie Chart, NEVER Line Chart.
    # Because lines require a trend across multiple points.
    if data_length <= 2:
        chart_type = "bar" if recommended not in ("bar", "pie") else recommended
    else:
        # AI 스스로의 지능적 판단을 전적으로 신뢰합니다.
        if recommended in ("line", "bar", "pie"):
            chart_type = recommended
        else:
            chart_type = "bar"

    # Remove the early return for recommended == "table" so we force charts for visual requests.
    if data_length > 30:
        return table_config

    # 3. Clean numeric data (parse "25,200" -> 25200)
    for row in data:
        for key in numeric_keys:
            val = row.get(key)
            if isinstance(val, str):
                cleaned = re.sub(r"[^\d.-]", "", val)
                if cleaned:
                    try:
                        row[key] = float(cleaned) if "." in cleaned else int(cleaned)
                    except ValueError:
                        pass

    # 4. Build series configuration
    series = []
    for key in numeric_keys:
        label = next((col["label"] for col in columns if col["key"] == key), key)
        series.append({
            "dataKey": key,
            "name": label,
            "yAxisId": "left"
        })

    # 4. Assemble final chart config
    table_config["type"] = "chart"
    table_config["chartType"] = chart_type
    table_config["xAxisKey"] = category_key
    table_config["series"] = series

    return table_config
