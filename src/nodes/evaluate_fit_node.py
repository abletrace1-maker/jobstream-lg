from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.state import ChildGraphState
from src.schemas import ClarificationQuestion, EvaluateFitOutput

# Define the prompt (T-1)
EVALUATE_FIT_PROMPT = """You are an expert technical recruiter and career coach.
Your task is to evaluate the fit between the candidate's base resume and the job description.
Identify any missing context or clarification needed to tailor the resume effectively.
If there are missing details that could strengthen the application, formulate clarification questions.

Base Resume:
{base_resume}

Job Details:
{job_details}
"""

def evaluate_fit(state: ChildGraphState) -> Dict[str, Any]:
    """
    Evaluate fit between base resume and job description, and generate structured clarification questions.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(EvaluateFitOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", EVALUATE_FIT_PROMPT),
        ("human", "Evaluate the fit and provide clarification questions if necessary.")
    ])
    
    chain = prompt | structured_llm
    
    response = chain.invoke({
        "base_resume": state.get("base_resume", {}),
        "job_details": state.get("job_details", {})
    })
    
    # For US-003, we return the parsed questions and update status
    questions = response.questions if response else []
    status = "NEEDS_CLARIFICATION" if questions else "EVALUATING"
    
    return {"status": status, "clarification_questions": questions}
