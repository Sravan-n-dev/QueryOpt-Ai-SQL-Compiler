"""
QueryOpt AI — Relational Algebra Visualizer
===========================================
Generates Graphviz DOT graphs, formatted text trees, and serialisable
hierarchical dictionaries for any Relational Algebra plan.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from relational_algebra.nodes import (
    Distinct,
    Join,
    Limit,
    Projection,
    RANode,
    Scan,
    Selection,
    Sort,
)


def ra_to_text_tree(node: RANode, indent: int = 0, is_last: bool = True, prefix: str = "") -> str:
    """Render a clean Unicode ascii/text tree diagram."""
    connector = "└── " if is_last else "├── "
    line = f"{prefix}{connector if indent > 0 else ''}{node}"

    child_prefix = prefix + ("    " if is_last else "│   ") if indent > 0 else ""
    children = node.children()

    res = [line]
    for i, child in enumerate(children):
        last = (i == len(children) - 1)
        res.append(ra_to_text_tree(child, indent + 1, last, child_prefix))

    return "\n".join(res)


def ra_to_dict(node: RANode) -> Dict[str, Any]:
    """Serialize an RA tree into a JSON-compatible dictionary."""
    return node.to_dict()


def ra_to_dot(node: RANode) -> str:
    """Generate a clean Graphviz DOT language string representing the plan tree."""
    nodes_dot: List[str] = []
    edges_dot: List[str] = []
    counter = [0]

    def _traverse(curr: RANode) -> int:
        counter[0] += 1
        node_id = counter[0]

        # Colors & styling per operator
        if isinstance(curr, Scan):
            color = "#D0E8FF"  # light blue
            border = "#1E88E5"
            shape = "box"
            label = f"<b>Scan({curr.table_name})</b>"
            if curr.alias:
                label += f"<br/><i>as {curr.alias}</i>"
            if curr.pushed_predicate:
                safe_pred = html.escape(str(curr.pushed_predicate))
                label += f"<br/><font color='#D32F2F'>σ[{safe_pred}]</font>"
        elif isinstance(curr, Selection):
            color = "#FFF9C4"  # light yellow
            border = "#FBC02D"
            shape = "box"
            safe_cond = html.escape(str(curr.condition))
            label = f"<b>σ (Selection)</b><br/>{safe_cond}"
        elif isinstance(curr, Projection):
            color = "#C8E6C9"  # light green
            border = "#388E3C"
            shape = "box"
            safe_cols = html.escape(", ".join(curr.columns))
            label = f"<b>π (Projection)</b><br/>{safe_cols}"
        elif isinstance(curr, Join):
            color = "#FFE0B2"  # light orange
            border = "#F57C00"
            shape = "box"
            safe_cond = html.escape(str(curr.condition))
            label = f"<b>⋈ ({curr.join_type} JOIN)</b><br/>{safe_cond}"
        elif isinstance(curr, Sort):
            color = "#E1BEE7"  # light purple
            border = "#8E24AA"
            shape = "box"
            items = ", ".join(f"{c} {d}" for c, d in curr.order_items)
            label = f"<b>τ (Sort)</b><br/>{html.escape(items)}"
        elif isinstance(curr, Limit):
            color = "#F8BBD0"  # light pink
            border = "#C2185B"
            shape = "box"
            label = f"<b>LIMIT</b><br/>count={curr.count}"
        elif isinstance(curr, Distinct):
            color = "#B2DFDB"  # teal
            border = "#00897B"
            shape = "box"
            label = "<b>δ (Distinct)</b>"
        else:
            color = "#EEEEEE"
            border = "#616161"
            shape = "box"
            label = f"<b>{type(curr).__name__}</b>"

        nodes_dot.append(
            f'  node{node_id} [shape="{shape}", style="filled,rounded", '
            f'fillcolor="{color}", color="{border}", penwidth=2, '
            f'label=<{label}>];'
        )

        for child in curr.children():
            child_id = _traverse(child)
            edges_dot.append(f"  node{node_id} -> node{child_id};")

        return node_id

    _traverse(node)

    dot = [
        "digraph RelationalAlgebra {",
        '  graph [rankdir=TB, bgcolor="transparent", fontname="Helvetica"];',
        '  node [fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=10, color="#555555"];',
    ]
    dot.extend(nodes_dot)
    dot.extend(edges_dot)
    dot.append("}")
    return "\n".join(dot)


def ra_to_graphviz(node: RANode) -> Any:
    """Return a Graphviz Digraph object if graphviz package is installed, or DOT string."""
    try:
        import graphviz
        dot_str = ra_to_dot(node)
        return graphviz.Source(dot_str)
    except Exception:
        return ra_to_dot(node)
