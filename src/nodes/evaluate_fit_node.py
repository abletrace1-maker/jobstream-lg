from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.state import ChildGraphState
from src.schemas import ClarificationQuestion

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
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", EVALUATE_FIT_PROMPT),
        ("human", "Evaluate the fit and provide clarification questions if necessary.")
    ])
    
    # We will just invoke the LLM here for US-001. 
    # Structured output binding is added in US-002.
    chain = prompt | llm
    
    response = chain.invoke({
        "base_resume": state.get("base_resume", {}),
        "job_details": state.get("job_details", {})
    })
    
    # For US-001, we just return empty or dummy for state updates.
    # US-003 will handle proper state updating and routing.
    return {"status": "EVALUATING", "clarification_questions": []}
