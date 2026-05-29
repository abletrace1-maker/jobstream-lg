from langgraph.graph import StateGraph, START, END

from src.state import ChildGraphState
from src.nodes.child_nodes import (
    evaluate_fit,
    clarification,
    strategy_generator,
    human_review,
    apply_changes,
    cover_letter,
    pdf_compiler,
)

# Build the Child Graph
child_builder = StateGraph(ChildGraphState)

# Add nodes
child_builder.add_node("evaluate_fit", evaluate_fit)
child_builder.add_node("clarification", clarification)
child_builder.add_node("strategy_generator", strategy_generator)
child_builder.add_node("human_review", human_review)
child_builder.add_node("apply_changes", apply_changes)
child_builder.add_node("cover_letter", cover_letter)
child_builder.add_node("pdf_compiler", pdf_compiler)

# Define a linear sequential edge flow
child_builder.add_edge(START, "evaluate_fit")
child_builder.add_edge("evaluate_fit", "clarification")
child_builder.add_edge("clarification", "strategy_generator")
child_builder.add_edge("strategy_generator", "human_review")
child_builder.add_edge("human_review", "apply_changes")
child_builder.add_edge("apply_changes", "cover_letter")
child_builder.add_edge("cover_letter", "pdf_compiler")
child_builder.add_edge("pdf_compiler", END)

# Compile child graph
child_graph = child_builder.compile()
