from langgraph.checkpoint.memory import MemorySaver

from src.child_graph import child_builder, child_graph

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

def test_child_graph_interrupt():
    """Verify that the child graph pauses at the interrupt node."""
    memory = MemorySaver()
    test_graph = child_builder.compile(
        checkpointer=memory,
        interrupt_before=["clarification", "human_review"]
    )
    
    config = {"configurable": {"thread_id": "test_thread_1"}}
    state = {
        "job_id": "test_job_123",
        "job_url": "http://test.com",
        "job_description": "Test Engineer",
        "company_name": "Test Co",
        "user_profile": "Test Profile"
    }
    
    # Run the graph
    for event in test_graph.stream(state, config=config):
        pass
        
    # Check if the graph is paused/interrupted
    state_snapshot = test_graph.get_state(config)
    assert state_snapshot.next == ("clarification",)
