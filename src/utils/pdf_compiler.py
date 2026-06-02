from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import markdown

def compile_resume_pdf(resume_data: dict, output_path: str) -> str:
    """
    Compiles a JSON/dict resume into a PDF using Jinja2 and WeasyPrint.
    
    Args:
        resume_data (dict): The resume data matching BaseResumeSchema.
        output_path (str): The path where the PDF should be saved.
        
    Returns:
        str: The absolute path to the generated PDF.
    """
    # Setup Jinja2 environment
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("resume_template.html")
    
    # Render HTML
    rendered_html = template.render(**resume_data)
    
    # Ensure output directory exists
    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Compile to PDF
    HTML(string=rendered_html).write_pdf(output_file)
    
    return str(output_file)

def compile_cover_letter_pdf(markdown_text: str, output_path: str) -> str:
    """
    Compiles a markdown cover letter into a PDF using Jinja2 and WeasyPrint.
    
    Args:
        markdown_text (str): The markdown content of the cover letter.
        output_path (str): The path where the PDF should be saved.
        
    Returns:
        str: The absolute path to the generated PDF.
    """
    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_text)
    
    # Setup Jinja2 environment
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("cover_letter_template.html")
    
    # Render full HTML document
    rendered_html = template.render(content=html_content)
    
    # Ensure output directory exists
    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Compile to PDF
    HTML(string=rendered_html).write_pdf(output_file)
    
    return str(output_file)
