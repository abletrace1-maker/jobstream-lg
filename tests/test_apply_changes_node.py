import pytest
from src.nodes.child_nodes import apply_changes
from src.schemas import BaseResumeSchema, ResumeDiffSchema, ResumeChange

@pytest.fixture
def sample_base_resume():
    return BaseResumeSchema(
        name="John Doe",
        contact_info={
            "email": "john@example.com",
            "phone": "123",
            "linkedin": "url",
            "location": "NY"
        },
        professional_summary="A software engineer.",
        skills={"Languages": ["Python", "JavaScript"]},
        professional_experience=[
            {
                "job_title": "Engineer",
                "company": "Tech Corp",
                "location": "NY",
                "start_date": "2020",
                "end_date": "2023",
                "highlights": ["Built backend."]
            }
        ],
        educational_experience=[
            {
                "degree": "B.S.",
                "school": "University",
                "start_date": "2016",
                "end_date": "2020",
                "awards": []
            }
        ],
        other_points=[]
    )

def test_apply_changes_node_updates_tailored_resume(sample_base_resume):
    diffs = ResumeDiffSchema(
        changes=[
            ResumeChange(
                action="replace",
                section='professional_summary',
                old_value="A software engineer.",
                new_value="An expert software engineer.",
                reason="Tailor for senior role"
            )
        ]
    )
    
    state = {
        "base_resume": sample_base_resume,
        "resume_diffs": diffs
    }
    
    output = apply_changes(state)
    
    assert "tailored_resume" in output
    tailored = output["tailored_resume"]
    assert tailored.professional_summary == "An expert software engineer."
    # The rest should be unchanged
    assert tailored.name == "John Doe"

def test_apply_changes_node_empty_diffs(sample_base_resume):
    diffs = ResumeDiffSchema(changes=[])
    state = {
        "base_resume": sample_base_resume,
        "resume_diffs": diffs
    }
    
    output = apply_changes(state)
    assert "tailored_resume" in output
    tailored = output["tailored_resume"]
    assert tailored.professional_summary == "A software engineer."

def test_apply_changes_node_missing_base_resume():
    state = {
        "resume_diffs": ResumeDiffSchema(changes=[])
    }
    
    output = apply_changes(state)
    assert output == {}
