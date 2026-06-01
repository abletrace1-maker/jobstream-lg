import pytest
from unittest.mock import patch, MagicMock

from src.nodes.evaluate_fit_node import evaluate_fit
from src.state import ChildGraphState, JobStatus
from src.schemas import BaseResumeSchema, JobDetailsSchema

def test_evaluate_fit_node_calls_llm():
    # Setup dummy state
    dummy_resume = BaseResumeSchema(
        name="Jane Doe",
        contact_info={"email": "jane@example.com", "phone": "123", "linkedin": "", "location": ""},
        professional_summary="Great dev",
        skills={"tech": ["Python"]},
        professional_experience=[],
        educational_experience=[],
        other_points=[]
    )
    
    dummy_job = JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-1",
        category="engineering",
        requirements=["Python"],
        responsibilities=["Write code"],
        raw_text="Job posting text"
    )
    
    state = ChildGraphState(
        base_resume=dummy_resume,
        job_details=dummy_job,
        status=JobStatus.EVALUATING,
        clarification_questions=[],
        user_clarification_answers={},
        strategy_markdown="",
        resume_diffs=None,
        user_feedback="",
        tailored_resume=None,
        cover_letter_markdown="",
        resume_pdf_path="",
        cover_letter_pdf_path=""
    )
    
    with patch("src.nodes.evaluate_fit_node.ChatOpenAI") as mock_chat:
        # Configure mock
        mock_llm_instance = MagicMock()
        mock_chat.return_value = mock_llm_instance
        
        mock_structured_llm = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        
        # When chain.invoke is called, it calls the LLM
        mock_response = MagicMock()
        mock_response.questions = []
        mock_structured_llm.invoke.return_value = mock_response
        
        # Execute the node
        updates = evaluate_fit(state)
        
        # Assertions
        mock_chat.assert_called_once_with(model="gpt-4o", temperature=0)
        assert mock_structured_llm.called or mock_structured_llm.invoke.called or mock_structured_llm.mock_calls
        assert "status" in updates
        
