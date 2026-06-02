import os
from pathlib import Path
from src.utils.pdf_compiler import compile_resume_pdf, compile_cover_letter_pdf

def test_compile_resume_pdf(tmp_path):
    dummy_data = {
        "name": "John Doe",
        "contact_info": {
            "email": "john@example.com",
            "phone": "555-1234",
            "linkedin": "linkedin.com/in/johndoe",
            "location": "New York, NY"
        },
        "professional_summary": "Experienced software engineer.",
        "skills": {
            "Languages": ["Python", "JavaScript"]
        },
        "professional_experience": [
            {
                "job_title": "Software Engineer",
                "company": "Tech Corp",
                "location": "New York, NY",
                "start_date": "2020",
                "end_date": "Present",
                "highlights": ["Built things", "Fixed bugs"]
            }
        ],
        "educational_experience": [
            {
                "degree": "B.S. Computer Science",
                "school": "University of Tech",
                "start_date": "2016",
                "end_date": "2020",
                "awards": ["Dean's List"]
            }
        ],
        "other_points": ["Volunteer at local animal shelter"]
    }
    
    output_pdf = tmp_path / "test_resume.pdf"
    
    result_path = compile_resume_pdf(dummy_data, str(output_pdf))
    
    assert os.path.exists(result_path)
    assert Path(result_path).is_file()
    assert result_path == str(output_pdf.resolve())
    
    # Check if it's a valid PDF (basic check: starts with %PDF)
    with open(result_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"

def test_compile_cover_letter_pdf(tmp_path):
    markdown_text = """
# Cover Letter
Dear Hiring Manager,

I am writing to apply for the position.
Here is a bold **statement**.

Sincerely,
John Doe
"""
    output_pdf = tmp_path / "test_cover_letter.pdf"
    
    result_path = compile_cover_letter_pdf(markdown_text, str(output_pdf))
    
    assert os.path.exists(result_path)
    assert Path(result_path).is_file()
    assert result_path == str(output_pdf.resolve())
    
    # Check if it's a valid PDF (basic check: starts with %PDF)
    with open(result_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"
