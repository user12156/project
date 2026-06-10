"""Visualization creator registry."""

from .graph_visual import create_graph_visual
from .image_visual import create_image_visual
from .mindmap_visual import create_mindmap_visual
from .table_visual import create_table_visual


VISUAL_CREATORS = {
    "table": create_table_visual,
    "graph": create_graph_visual,
    "image": create_image_visual,
    "mindmap": create_mindmap_visual,
}
