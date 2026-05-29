import pytest
from src.child_graph import child_graph

def test_child_graph_compiles():
    """Verify that the child subgraph compiles and has the correct nodes/edges."""
    # This will fail if the graph isn't compiled or structured correctly
    assert child_graph is not None
    
    # Check that all our nodes are present in the compiled graph's nodes
    # We can inspect the graph's nodes attribute (or similar depending on langgraph version)
    # The simplest check is simply that it compiled and we can invoke it.
    
    # Let's ensure we can get a visualization or just check nodes to ensure it works
    nodes = child_graph.nodes.keys()
    
    expected_nodes = {
        "evaluate_fit",
        "clarification",
        "strategy_generator",
        "human_review",
        "apply_changes",
        "cover_letter",
        "pdf_compiler"
    }
    
    for node in expected_nodes:
        assert node in nodes
