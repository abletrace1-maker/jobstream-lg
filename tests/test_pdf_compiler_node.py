import os
from unittest.mock import patch
from src.nodes.child_nodes import pdf_compiler
from src.schemas import JobDetailsSchema, BaseResumeSchema, ContactInfo

def test_pdf_compiler_node_success():
    """Test that the pdf_compiler node correctly processes state and calls PDF utilities."""
    # Setup test state
    job_details = JobDetailsSchema(
        job_id="test_job_123",
        job_title="Software Engineer",
        company="Tech Corp",
        location="NY",
        category="Tech",
        requirements=[],
        responsibilities=[],
        raw_text="A great job"
    )
    
    tailored_resume = BaseResumeSchema(
        name="John Doe",
        contact_info=ContactInfo(
            email="john@example.com",
            phone="123-456-7890",
            location="NY",
            linkedin="linkedin.com/in/john"
        ),
        professional_summary="Test Summary",
        professional_experience=[],
        educational_experience=[],
        skills={}
    )
    
    state = {
        "job_details": job_details,
        "tailored_resume": tailored_resume,
        "cover_letter_markdown": "# Cover Letter\n\nHello World."
    }
    
    with patch('src.nodes.child_nodes.compile_resume_pdf') as mock_compile_resume, \
         patch('src.nodes.child_nodes.compile_cover_letter_pdf') as mock_compile_cl:
         
        mock_compile_resume.return_value = os.path.join("data", "output", "test_job_123_resume.pdf")
        mock_compile_cl.return_value = os.path.join("data", "output", "test_job_123_cover_letter.pdf")
        
        result = pdf_compiler(state)
        
        # Verify calls
        assert mock_compile_resume.called
        assert mock_compile_cl.called
        
        # Verify that filenames include job_id
        resume_call_args = mock_compile_resume.call_args[0]
        cl_call_args = mock_compile_cl.call_args[0]
        
        assert "test_job_123_resume.pdf" in resume_call_args[1]
        assert "test_job_123_cover_letter.pdf" in cl_call_args[1]
        
        # Verify return state
        assert "resume_pdf_path" in result
        assert "cover_letter_pdf_path" in result
        assert result["resume_pdf_path"] == os.path.join("data", "output", "test_job_123_resume.pdf")
        assert result["cover_letter_pdf_path"] == os.path.join("data", "output", "test_job_123_cover_letter.pdf")

def test_pdf_compiler_node_missing_data():
    """Test the node when optional state elements are missing."""
    # Test without tailored_resume and cover_letter
    state = {
        "job_details": JobDetailsSchema(
            job_id="test_job_456",
            job_title="DevOps",
            company="Cloud Inc",
            location="SF",
            category="Ops",
            requirements=[],
            responsibilities=[],
            raw_text="Ops"
        )
    }
    
    with patch('src.nodes.child_nodes.compile_resume_pdf') as mock_compile_resume, \
         patch('src.nodes.child_nodes.compile_cover_letter_pdf') as mock_compile_cl:
         
        result = pdf_compiler(state)
        
        # Utilities should not be called
        assert not mock_compile_resume.called
        assert not mock_compile_cl.called
        
        # State update should be empty
        assert result == {}

def test_pdf_compiler_node_no_job_id():
    """Test node handles missing job_id gracefully."""
    # State with missing job_id but valid resume
    state = {
        "tailored_resume": BaseResumeSchema(
            name="Jane Doe",
            contact_info=ContactInfo(email="jane@example.com", phone="123", location="NY", linkedin="linkedin.com/in/jane"),
            professional_summary="Testing", professional_experience=[], educational_experience=[], skills={}
        )
    }
    
    with patch('src.nodes.child_nodes.compile_resume_pdf') as mock_compile_resume:
        mock_compile_resume.return_value = os.path.join("data", "output", "unknown_job_resume.pdf")
        
        result = pdf_compiler(state)
        
        assert mock_compile_resume.called
        resume_call_args = mock_compile_resume.call_args[0]
        
        # Should fallback to "unknown_job"
        assert "unknown_job_resume.pdf" in resume_call_args[1]
        assert result["resume_pdf_path"] == os.path.join("data", "output", "unknown_job_resume.pdf")
