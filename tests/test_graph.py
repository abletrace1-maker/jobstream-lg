import pytest
from langgraph.types import Send

from src.graph import map_to_job_processor, parent_graph
from src.state import ParentGraphState, JobStatus
from src.schemas import JobDetailsSchema, BaseResumeSchema, ContactInfo

@pytest.fixture
def dummy_base_resume():
    return BaseResumeSchema(
        name="John Doe",
        contact_info=ContactInfo(
            email="johndoe@example.com",
            phone="123-456-7890",
            linkedin="linkedin.com/in/johndoe",
            location="New York, NY"
        ),
        professional_summary="A summary",
        skills={"languages": ["Python"]},
        professional_experience=[],
        educational_experience=[]
    )

def test_map_to_job_processor_with_matching_category(dummy_base_resume):
    job1 = JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-1",
        category="software_engineering",
        requirements=["Python"],
        responsibilities=["Code"],
        raw_text="Job posting text"
    )
    job2 = JobDetailsSchema(
        job_title="Product Manager",
        company="Business Inc",
        location="NY",
        job_id="job-2",
        category="product_management",
        requirements=["Agile"],
        responsibilities=["Manage"],
        raw_text="Job posting text 2"
    )

    state = ParentGraphState(
        base_resumes={
            "software_engineering": dummy_base_resume,
            "product_management": dummy_base_resume
        },
        config={},
        prompts={},
        pending_jobs=[],
        scraped_jobs=[job1, job2],
        failed_jobs=[]
    )

    sends = map_to_job_processor(state)

    assert len(sends) == 2
    assert all(isinstance(send, Send) for send in sends)
    assert sends[0].node == "process_job"
    assert sends[0].arg["job_details"].job_id == "job-1"
    assert sends[0].arg["base_resume"] == dummy_base_resume
    assert sends[0].arg["status"] == JobStatus.EVALUATING

    assert sends[1].node == "process_job"
    assert sends[1].arg["job_details"].job_id == "job-2"
    assert sends[1].arg["base_resume"] == dummy_base_resume

def test_map_to_job_processor_fallback(dummy_base_resume):
    job1 = JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-1",
        category="unknown_category",
        requirements=["Python"],
        responsibilities=["Code"],
        raw_text="Job posting text"
    )

    state = ParentGraphState(
        base_resumes={
            "default": dummy_base_resume
        },
        config={},
        prompts={},
        pending_jobs=[],
        scraped_jobs=[job1],
        failed_jobs=[]
    )

    sends = map_to_job_processor(state)

    assert len(sends) == 1
    assert sends[0].node == "process_job"
    assert sends[0].arg["base_resume"] == dummy_base_resume

def test_map_to_job_processor_no_resumes():
    job1 = JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-1",
        category="software_engineering",
        requirements=["Python"],
        responsibilities=["Code"],
        raw_text="Job posting text"
    )

    state = ParentGraphState(
        base_resumes={},
        config={},
        prompts={},
        pending_jobs=[],
        scraped_jobs=[job1],
        failed_jobs=[]
    )

    sends = map_to_job_processor(state)

    assert len(sends) == 0

def test_parent_graph_compiles_and_has_correct_nodes():
    nodes = parent_graph.nodes
    
    # LangGraph has START and END nodes automatically
    # Check if our custom nodes are registered
    assert "load_config_and_resume" in nodes
    assert "job_ingestion" in nodes
    assert "process_job" in nodes

def test_parent_graph_run(dummy_base_resume):
    # Quick execution test of the parent graph structure
    job1 = JobDetailsSchema(
        job_title="Software Engineer",
        company="Tech Corp",
        location="Remote",
        job_id="job-1",
        category="software_engineering",
        requirements=["Python"],
        responsibilities=["Code"],
        raw_text="Job posting text"
    )
    
    # We initialize state with some scraped jobs
    initial_state = {
        "base_resumes": {"software_engineering": dummy_base_resume},
        "config": {},
        "prompts": {},
        "pending_jobs": [],
        "scraped_jobs": [job1],
        "failed_jobs": []
    }
    
    # Invoke the graph
    # process_job will be hit due to the map_to_job_processor
    result = parent_graph.invoke(initial_state)
    
    # Because process_job is a dummy, it doesn't change anything in parent state directly,
    # but let's just make sure it runs without error.
    assert "scraped_jobs" in result
