import pytest
from unittest.mock import patch
from src.nodes.cover_letter_generator_node import cover_letter_generator
from src.schemas import BaseResumeSchema, ContactInfo, JobDetailsSchema

@pytest.fixture
def sample_resume():
    return BaseResumeSchema(
        name="Jane Doe",
        contact_info=ContactInfo(
            email="jane@example.com",
            phone="123-456-7890",
            linkedin="linkedin.com/in/jane",
            location="San Francisco, CA"
        ),
        professional_summary="Experienced developer.",
        skills={"languages": ["Python"]},
        professional_experience=[],
        educational_experience=[],
        other_points=[]
    )

@pytest.fixture
def sample_job_details():
    return JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job123",
        category="Engineering",
        requirements=["Python"],
        responsibilities=["Write code"],
        raw_text="Job Description"
    )

def test_cover_letter_generator(sample_resume, sample_job_details):
    # We patch invoke on the ChatGoogleGenerativeAI class itself
    from langchain_core.messages import AIMessage
    with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-api-key"}):
        with patch("langchain_google_genai.ChatGoogleGenerativeAI.invoke", return_value=AIMessage(content="# Cover Letter\n\nDear Hiring Manager,\n\nI am applying for the Software Engineer role at Tech Corp.\n\nSincerely,\nJane Doe")):
            state = {
                "tailored_resume": sample_resume,
                "job_details": sample_job_details,
                "strategy_markdown": "Focus on Python."
            }
            
            result = cover_letter_generator(state)
            
            assert "cover_letter_markdown" in result
            assert result["cover_letter_markdown"] == "# Cover Letter\n\nDear Hiring Manager,\n\nI am applying for the Software Engineer role at Tech Corp.\n\nSincerely,\nJane Doe"
