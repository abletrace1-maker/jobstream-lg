from unittest import mock
from langgraph.checkpoint.memory import MemorySaver

from src.child_graph import child_builder, child_graph

def test_child_graph_compiles():
    """Verify that the child subgraph compiles and has the correct nodes/edges."""
    # This will fail if the graph isn't compiled or structured correctly
    assert child_graph is not None
    
    # Check that all our nodes are present in the compiled graph's nodes
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
        "user_profile": "Test Profile",
        "status": "EVALUATING"
    }
    
    # Run the graph
    with mock.patch("src.nodes.evaluate_fit_node.ChatOpenAI") as mock_chat:
        mock_instance = mock.MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = mock.MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput, ClarificationQuestion
        mock_response = EvaluateFitOutput(
            questions=[ClarificationQuestion(id="1", type="text", question="Q", options=[])]
        )
        
        # In Langchain, a MagicMock inside a chain is called via __call__ or invoke
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        for event in test_graph.stream(state, config=config):
            pass
        
    # Check if the graph is paused/interrupted
    state_snapshot = test_graph.get_state(config)
    assert state_snapshot.next == ("clarification",)
