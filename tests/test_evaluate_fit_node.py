from unittest.mock import patch, MagicMock

from src.nodes.evaluate_fit_node import evaluate_fit
from src.state import ChildGraphState, JobStatus
from src.schemas import BaseResumeSchema, JobDetailsSchema

def test_evaluate_fit_node_no_questions():
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
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        # Return no questions
        from src.schemas import EvaluateFitOutput
        mock_response = EvaluateFitOutput(questions=[])
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        updates = evaluate_fit(state)
        
        assert updates["status"] == "EVALUATING"
        assert len(updates["clarification_questions"]) == 0

def test_evaluate_fit_node_with_questions():
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
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput, ClarificationQuestion
        mock_response = EvaluateFitOutput(
            questions=[ClarificationQuestion(id="1", type="text", question="Q", options=[])]
        )
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        updates = evaluate_fit(state)
        
        assert updates["status"] == "NEEDS_CLARIFICATION"
        assert len(updates["clarification_questions"]) == 1
        assert "status" in updates
        
