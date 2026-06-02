from unittest.mock import patch, MagicMock

from src.nodes.evaluate_fit_node import evaluate_fit
from src.state import ChildGraphState, JobStatus
from src.schemas import BaseResumeSchema, JobDetailsSchema

def test_evaluate_fit_node_no_questions():
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
    
    with patch("src.nodes.evaluate_fit_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput
        mock_response = EvaluateFitOutput(questions=[], fit_score=8, should_apply=True, missing_requirements=[])
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
    
    with patch("src.nodes.evaluate_fit_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput, ClarificationQuestion
        mock_response = EvaluateFitOutput(
            questions=[ClarificationQuestion(id="1", type="text", question="Q", options=[])],
            fit_score=7,
            should_apply=True,
            missing_requirements=["Experience with Python"]
        )
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        updates = evaluate_fit(state)
        
        assert updates["status"] == "NEEDS_CLARIFICATION"
        assert len(updates["clarification_questions"]) == 1
        assert "status" in updates
        

def test_evaluate_fit_node_rejected():
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
    
    with patch("src.nodes.evaluate_fit_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput
        mock_response = EvaluateFitOutput(
            questions=[],
            fit_score=2,
            should_apply=False,
            missing_requirements=["Missing everything"]
        )
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        updates = evaluate_fit(state)
        
        assert updates["status"] == "REJECTED"
        assert len(updates["clarification_questions"]) == 0
        assert "status" in updates

def test_evaluate_fit_missing_context():
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
        job_title="Backend Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-2",
        category="engineering",
        requirements=["Python", "AWS Cloud"],
        responsibilities=["Write code", "Deploy to AWS"],
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
    
    with patch("src.nodes.evaluate_fit_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        
        mock_structured = MagicMock()
        mock_instance.with_structured_output.return_value = mock_structured
        
        from src.schemas import EvaluateFitOutput, ClarificationQuestion
        mock_response = EvaluateFitOutput(
            questions=[ClarificationQuestion(
                id="q_aws", 
                type="multiple_choice", 
                question="Do you have any AWS experience?", 
                options=["Yes, 1-2 years", "Yes, 3+ years", "No"]
            )],
            fit_score=6,
            should_apply=True,
            missing_requirements=["AWS Cloud"]
        )
        mock_structured.return_value = mock_response
        mock_structured.invoke.return_value = mock_response
        
        updates = evaluate_fit(state)
        
        assert updates["status"] == "NEEDS_CLARIFICATION"
        assert len(updates["clarification_questions"]) == 1
        assert updates["clarification_questions"][0].id == "q_aws"
        assert "Let LLM decide" in updates["clarification_questions"][0].options

def test_clarification_question_schema_appends_option():
    from src.schemas import ClarificationQuestion
    q = ClarificationQuestion(
        id="q1",
        type="multiple_choice",
        question="Which project?",
        options=["Project A", "Project B"]
    )
    assert "Let LLM decide" in q.options
    
    q_text = ClarificationQuestion(
        id="q2",
        type="text",
        question="Tell me more?",
        options=[]
    )
    assert "Let LLM decide" not in q_text.options
