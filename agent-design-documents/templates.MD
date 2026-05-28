# Configuration and Input/Output Templates (templates.MD)

This document defines the strict data structures, schemas, and configurations required for the JobStream Agent workflow. The AI coding agent MUST use these schemas to ensure data consistency between nodes.

## 1. Job Tracker List (`job_tracker.json`)
This replaces the old Markdown tracker. It serves as the primary input queue for the agent. JSON is strictly required here because programmatic state updates to Markdown are brittle and prone to corruption.

```json
[
  {
    "job_id": "05-20_1_MHB-Group-Canada",
    "title": "Development Manager",
    "company": "MHB Group Canada",
    "source_type": "url",
    "source": "https://www.linkedin.com/jobs/view/...",
    "category": "project_management",
    "user_score": "8/10",
    "notes": "Development management job, pay unknown. I like the fact that my background plays a part but i am not doing technical drawings.",
    "status": "PENDING"
  },
  {
    "job_id": "05-20_2_Govan-Brown",
    "title": "Project Manager (Construction - Interiors)",
    "company": "Govan Brown",
    "source_type": "file",
    "source": "data/raw_jobs/govan_brown_details.txt",
    "category": "construction",
    "user_score": "8/10",
    "notes": "Project management role in construction, would be onsite...",
    "status": "PENDING"
  }
]
```

## 2. Global Configuration (`config.yaml`)
This file dictates the behavior of the agent, the models used for different tasks, and the strict constraints on resume modifications.

```yaml
models:
  cheap_parsing: "gpt-4o-mini" # Used for resume-to-JSON and job URL parsing
  heavy_reasoning: "gpt-4o"    # Used for fit evaluation and strategy drafting

resume_constraints:
  allowed_sections_to_alter:
    - "professional_summary"
    - "experience.highlights"  # Can rewrite bullet points
    - "skills"                 # Can reorder or highlight specific skills
  forbidden_sections:
    - "name"
    - "contact_info"
    - "experience.title"
    - "experience.company"
    - "experience.dates"
    - "education"
  rules:
    - "Never invent job experience or skills not present or implied in the base resume."
    - "Maintain the professional tone of the original resume."
    - "Match the stylistic structure of the starter resume (e.g., bullet point length)."
```

## 2. Base & Final Resume Structure (JSON)
The structure of both the ingested starter resume and the final tailored resume. This ensures consistent formatting.

```json
{
  "name": "John Doe",
  "contact_info": {
    "email": "john.doe@example.com",
    "phone": "555-0100",
    "linkedin": "linkedin.com/in/johndoe",
    "location": "New York, NY"
  },
  "professional_summary": "Experienced software engineer with a focus on scalable backend systems...",
  "skills": {
    "languages": ["Python", "JavaScript", "Go"],
    "frameworks": ["Django", "React", "LangChain"],
    "tools": ["Docker", "Kubernetes", "AWS"]
  },
  "professional_experience": [
    {
      "job_title": "Senior Backend Engineer",
      "company": "Tech Corp",
      "location": "Remote",
      "start_date": "2020-05",
      "end_date": "Present",
      "highlights": [
        "Designed and implemented microservices architecture reducing latency by 40%.",
        "Mentored a team of 4 junior developers."
      ]
    }
  ],
  "educational_experience": [
    {
      "degree": "B.S. Computer Science",
      "school": "State University",
      "start_date": "2015-09",
      "end_date": "2019-05",
      "awards": ["Dean's List 2018", "Cum Laude"]
    }
  ],
  "other_points": [
    "AWS Certified Solutions Architect"
  ]
}
```

## 3. Parsed Job Details (JSON)
The output from the URL scraping/parsing node. Note the `category` field—this MUST match one of the available `base_resume_[category].json` files so the correct resume is used for the application. The `job_id` will follow the `MM-DD_n_company_name` format.

```json
{
  "job_title": "Lead Python Developer",
  "company": "DataTech Solutions",
  "location": "New York, NY (Hybrid)",
  "job_id": "05-20_3_DataTech-Solutions",
  "category": "engineering", 
  "salary_range": "$140k - $180k",
  "requirements": [
    "5+ years of Python experience",
    "Experience with workflow orchestration (Airflow, LangGraph)"
  ],
  "nice_to_haves": [
    "Frontend experience with React"
  ],
  "responsibilities": [
    "Build and maintain agentic workflows",
    "Collaborate with data science team"
  ],
  "raw_text": "..." 
}
```

## 4. Clarification Questions (JSON)
Output from the `EvaluateFitNode` when the LLM needs more context to tailor the resume.

```json
{
  "questions": [
    {
      "id": "q1",
      "type": "multiple_choice",
      "question": "The job requires workflow orchestration. Which experience should we highlight most?",
      "options": [
        "Highlight the Airflow project from Tech Corp",
        "Highlight the LangChain project from previous startup",
        "Let the LLM decide the best approach based on job requirements"
      ]
    },
    {
      "id": "q2",
      "type": "text",
      "question": "The job mentions needing GCP experience, but your resume only lists AWS. Do you have any exposure to GCP you'd like me to add?",
      "options": ["Let the LLM handle framing the AWS experience as transferable"]
    }
  ]
}
```

## 5. Strategy Markdown Document
Generated by the `StrategyGeneratorNode` for human review in the frontend.

```markdown
# Resume Strategy: Lead Python Developer at DataTech Solutions

**Fit Assessment:** Strong Match (8/10). Your backend experience aligns well, though we need to emphasize your orchestration skills.

### Proposed Changes:

**1. Professional Summary**
*   *Current:* "Experienced software engineer..."
*   *Proposed:* "Backend engineer specializing in Python and workflow orchestration..."
*   *Reason:* Direct alignment with the first bullet of their requirements.

**2. Experience: Tech Corp**
*   *Change:* Reword the microservices bullet to explicitly mention DAGs and workflow orchestration principles.
```

## 6. Resume Diff Schema (JSON)
The strict programmatic representation of the Strategy Document. This is used by the `ApplyChangesNode` to safely update the JSON without hallucinations.

```json
{
  "changes": [
    {
      "action": "replace",
      "section": "professional_summary",
      "old_value": "Experienced software engineer with a focus on scalable backend systems...",
      "new_value": "Backend engineer specializing in Python and workflow orchestration...",
      "reason": "Aligns with core job requirement"
    },
    {
      "action": "replace",
      "section": "professional_experience[0].highlights[0]",
      "old_value": "Designed and implemented microservices architecture reducing latency by 40%.",
      "new_value": "Designed microservices and orchestrated workflow DAGs, reducing latency by 40%.",
      "reason": "Injecting orchestration keywords organically."
    }
  ]
}
```