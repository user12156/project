"""Visualization creator registry."""

from app.services.chart.chart_asset import create_graph_visual
from .image_visual import create_image_visual
from .mindmap_visual import create_mindmap_visual
from .table_visual import create_table_visual


VISUAL_CREATORS = {
    "table": create_table_visual,
    "graph": create_graph_visual,
    "image": create_image_visual,
    "mindmap": create_mindmap_visual,
}
