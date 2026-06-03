from typing import Any, Dict
import os
import logging
from src.state import ChildGraphState
from src.nodes.evaluate_fit_node import evaluate_fit as evaluate_fit
from src.nodes.strategy_generator_node import strategy_generator as strategy_generator
from src.nodes.revise_strategy_node import revise_strategy as revise_strategy
from src.utils.diff_applier import apply_diffs
from src.utils.pdf_compiler import compile_resume_pdf, compile_cover_letter_pdf
from src.schemas import BaseResumeSchema

logger = logging.getLogger(__name__)

def clarification(state: ChildGraphState) -> Dict[str, Any]:
    """Stub for handling human-in-the-loop clarification."""
    return {}

def human_review(state: ChildGraphState) -> Dict[str, Any]:
    """Stub for human-in-the-loop review of the strategy."""
    return {}

def apply_changes(state: ChildGraphState) -> Dict[str, Any]:
    """Applies diffs to the base resume."""
    base_resume = state.get("base_resume")
    resume_diffs = state.get("resume_diffs")
    
    if not base_resume:
        logger.warning("No base_resume found in state.")
        return {}
        
    if not resume_diffs or not hasattr(resume_diffs, "changes") or not resume_diffs.changes:
        logger.info("No resume_diffs to apply. Keeping original resume.")
        return {"tailored_resume": base_resume, "status": "APPROVED"}
        
    # Convert models to dicts
    if hasattr(base_resume, "model_dump"):
        base_resume_dict = base_resume.model_dump()
    elif hasattr(base_resume, "dict"):
        base_resume_dict = base_resume.dict()
    else:
        base_resume_dict = base_resume
        
    diffs_list = []
    for change in resume_diffs.changes:
        if hasattr(change, "model_dump"):
            diffs_list.append(change.model_dump())
        elif hasattr(change, "dict"):
            diffs_list.append(change.dict())
        else:
            diffs_list.append(change)
            
    tailored_resume_dict = apply_diffs(base_resume_dict, diffs_list)
    
    # Parse back to BaseResumeSchema to match state type
    try:
        tailored_resume_obj = BaseResumeSchema.model_validate(tailored_resume_dict)
    except Exception as e:
        logger.error(f"Failed to validate tailored resume: {e}")
        # Fall back to base_resume if diffs corrupted the schema
        tailored_resume_obj = base_resume
        
    return {"tailored_resume": tailored_resume_obj, "status": "APPROVED"}


def pdf_compiler(state: ChildGraphState) -> Dict[str, Any]:
    """Compiles tailored resume and cover letter to PDF."""
    import json
    
    tailored_resume = state.get("tailored_resume")
    cover_letter_markdown = state.get("cover_letter_markdown")
    job_details = state.get("job_details")
    
    # Extract job_id to use in filenames
    if hasattr(job_details, "job_id"):
        job_id = job_details.job_id
    elif isinstance(job_details, dict):
        job_id = job_details.get("job_id", "unknown_job")
    else:
        job_id = "unknown_job"
        
    if not job_id:
        job_id = "unknown_job"
        
    # Ensure data/output/{job_id} directory exists
    output_dir = os.path.join("data", "output", str(job_id))
    os.makedirs(output_dir, exist_ok=True)
    
    # Save job_details.json
    job_details_path = os.path.join(output_dir, "job_details.json")
    try:
        job_details_dict = {}
        if hasattr(job_details, "model_dump"):
            job_details_dict = job_details.model_dump()
        elif hasattr(job_details, "dict"):
            job_details_dict = job_details.dict()
        elif isinstance(job_details, dict):
            job_details_dict = job_details
            
        with open(job_details_path, "w", encoding="utf-8") as f:
            json.dump(job_details_dict, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save job_details.json: {e}")
    
    result = {}
    
    if tailored_resume:
        # Convert models to dict
        if hasattr(tailored_resume, "model_dump"):
            resume_dict = tailored_resume.model_dump()
        elif hasattr(tailored_resume, "dict"):
            resume_dict = tailored_resume.dict()
        else:
            resume_dict = tailored_resume
            
        # Save tailored_resume.json
        resume_json_path = os.path.join(output_dir, "tailored_resume.json")
        try:
            with open(resume_json_path, "w", encoding="utf-8") as f:
                json.dump(resume_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tailored_resume.json: {e}")
            
        resume_path = os.path.join(output_dir, f"{job_id}_resume.pdf")
        compiled_resume_path = compile_resume_pdf(resume_dict, resume_path)
        result["resume_pdf_path"] = compiled_resume_path
        
    if cover_letter_markdown:
        cover_letter_path = os.path.join(output_dir, f"{job_id}_cover_letter.pdf")
        compiled_cover_letter_path = compile_cover_letter_pdf(cover_letter_markdown, cover_letter_path)
        result["cover_letter_pdf_path"] = compiled_cover_letter_path
        
    return {
        "resume_pdf_path": compiled_resume_path if tailored_resume else "",
        "cover_letter_pdf_path": compiled_cover_letter_path if cover_letter_markdown else "",
        "status": "APPROVED"
    }
