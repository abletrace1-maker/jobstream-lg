import os
import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

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

def route_after_evaluate(state: ChildGraphState) -> str:
    if state.get("status") == "NEEDS_CLARIFICATION":
        return "clarification"
    return "strategy_generator"

# Define flow with conditional routing
child_builder.add_edge(START, "evaluate_fit")
child_builder.add_conditional_edges("evaluate_fit", route_after_evaluate)
child_builder.add_edge("clarification", "strategy_generator")
child_builder.add_edge("strategy_generator", "human_review")
child_builder.add_edge("human_review", "apply_changes")
child_builder.add_edge("apply_changes", "cover_letter")
child_builder.add_edge("cover_letter", "pdf_compiler")
child_builder.add_edge("pdf_compiler", END)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Initialize SqliteSaver checkpointer
# Since from_conn_string is a context manager, we need to manually create the connection
# if we want a global instance. Alternatively, we use context manager if we are inside a function.
# The task says: initialize SqliteSaver using from_conn_string('data/checkpoints.sqlite').
# Let's try to extract from context manager.
# Actually, let's just create connection manually to keep it global.
_conn = sqlite3.connect("data/checkpoints.sqlite", check_same_thread=False)
sqlite_saver = SqliteSaver(_conn)

# Compile child graph
child_graph = child_builder.compile(
    checkpointer=sqlite_saver,
    interrupt_before=["clarification", "human_review"]
)
