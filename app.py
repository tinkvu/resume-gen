import streamlit as st
import groq
import tempfile
import os
from fpdf import FPDF
import textwrap
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize Groq client
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_customized_resume(job_role, job_description, original_cv):
    """Get a customized resume using the Llama model via Groq API"""
    prompt = f"""
    As an AI resume expert, your task is to customize the provided CV to better match the specified job role and description.
    
    Job Role: {job_role}
    
    Job Description: {job_description}
    
    Original CV: {original_cv}
    
    Create a tailored resume that:
    1. Highlights relevant skills and experiences that match the job requirements
    2. Uses appropriate keywords from the job description
    3. Reorganizes content to emphasize the most relevant qualifications
    4. Maintains the candidate's genuine experience and skills (no fabrication)
    5. Has a professional format with clear sections for:
       - Contact Information (use original)
       - Professional Summary (tailored to the role)
       - Skills (prioritized based on job relevance)
       - Work Experience (emphasizing relevant achievements)
       - Education
    
    Return only the customized resume content in a clean format, ready to be converted to PDF.
    Format the output in a consistent way that can be parsed by section headers.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating customized resume: {str(e)}"

def create_professional_pdf(content, output_path):
    """Create a professionally formatted PDF resume"""
    # Create PDF instance
    class PDF(FPDF):
        def header(self):
            # No header
            pass
        
        def footer(self):
            # Footer with page number
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Extract name from content (assuming it's the first line)
    lines = content.split('\n')
    name = lines[0].strip('*')
    
    # Name at the top
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, name, 0, 1, 'C')
    pdf.ln(2)
    
    # Parse sections from content
    sections = {}
    current_section = None
    current_content = []
    
    # Regular expression to match section headers
    section_pattern = re.compile(r'\*\*(.*?):\*\*')
    
    for line in lines[1:]:  # Skip the name line
        # Check if this is a section header
        match = section_pattern.match(line)
        if match:
            # If we already have a section, save it
            if current_section:
                sections[current_section] = current_content
            
            # Start a new section
            current_section = match.group(1)
            current_content = []
        elif current_section:
            current_content.append(line.strip())
    
    # Add the last section
    if current_section and current_content:
        sections[current_section] = current_content
    
    # Process each section
    for section, content in sections.items():
        # Section header
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(240, 240, 240)  # Light gray background
        pdf.cell(0, 8, section, 1, 1, 'L', True)
        pdf.ln(1)
        
        # Section content
        pdf.set_font('Arial', '', 10)
        
        # Special formatting for different sections
        if section == "Contact Information":
            # Format contact info in a single line or multiple lines
            contact_text = ' | '.join([c for c in content if c])
            
            # Wrap long contact information
            wrapped_lines = textwrap.wrap(contact_text, width=100)
            for wrapped_line in wrapped_lines:
                pdf.cell(0, 6, wrapped_line, 0, 1)
        
        elif section == "Skills":
            # Format skills as bullet points
            for skill_line in content:
                if skill_line.startswith('*'):
                    skill_text = skill_line[1:].strip()
                    pdf.cell(5, 6, chr(149), 0, 0)  # Bullet point
                    pdf.cell(0, 6, skill_text, 0, 1)
                elif skill_line:
                    pdf.cell(0, 6, skill_line, 0, 1)
        
        elif section == "Work Experience" or section == "Education":
            # Format work experience with better indentation
            current_role = None
            
            for line in content:
                if line.startswith('*'):
                    # This is a job title or degree
                    current_role = line.strip('* ')
                    parts = current_role.split(',', 1)
                    
                    if len(parts) >= 2:
                        role, company_info = parts
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(0, 6, role, 0, 1)
                        pdf.set_font('Arial', 'I', 10)
                        pdf.cell(0, 6, company_info, 0, 1)
                    else:
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(0, 6, current_role, 0, 1)
                    
                    pdf.set_font('Arial', '', 10)
                
                elif line.startswith('+'):
                    # This is a bullet point under a role
                    bullet_text = line[1:].strip()
                    pdf.cell(10, 6, '', 0, 0)  # Indentation
                    pdf.cell(3, 6, chr(149), 0, 0)  # Bullet point
                    
                    # Wrap text for bullet points with proper indentation
                    wrapped_lines = textwrap.wrap(bullet_text, width=85)
                    if wrapped_lines:
                        pdf.cell(0, 6, wrapped_lines[0], 0, 1)
                        for wrapped_line in wrapped_lines[1:]:
                            pdf.cell(13, 6, '', 0, 0)  # Indentation
                            pdf.cell(0, 6, wrapped_line, 0, 1)
                
                elif line:
                    pdf.cell(0, 6, line, 0, 1)
        
        elif section == "Personal Projects":
            # Format projects similar to work experience
            current_project = None
            
            for line in content:
                if line.startswith('*'):
                    # This is a project title
                    current_project = line.strip('* ')
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, current_project, 0, 1)
                    pdf.set_font('Arial', '', 10)
                
                elif line.startswith('+'):
                    # This is a bullet point under a project
                    bullet_text = line[1:].strip()
                    pdf.cell(10, 6, '', 0, 0)  # Indentation
                    pdf.cell(3, 6, chr(149), 0, 0)  # Bullet point
                    
                    # Wrap text for bullet points
                    wrapped_lines = textwrap.wrap(bullet_text, width=85)
                    if wrapped_lines:
                        pdf.cell(0, 6, wrapped_lines[0], 0, 1)
                        for wrapped_line in wrapped_lines[1:]:
                            pdf.cell(13, 6, '', 0, 0)  # Indentation
                            pdf.cell(0, 6, wrapped_line, 0, 1)
                
                elif line:
                    pdf.cell(0, 6, line, 0, 1)
        
        else:
            # Default formatting for other sections
            for line in content:
                if line:
                    wrapped_lines = textwrap.wrap(line, width=100)
                    for wrapped_line in wrapped_lines:
                        pdf.cell(0, 6, wrapped_line, 0, 1)
        
        pdf.ln(5)  # Add space between sections
    
    # Save the PDF
    pdf.output(output_path)

def main():
    st.set_page_config(page_title="AI Resume Customizer", layout="wide")
    
    st.title("AI Resume Customizer")
    st.write("Tailor your resume to match specific job descriptions using AI")
    
    # # API key input
    api_key = st.text_input("Enter your Groq API Key:", type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
    
    # Create two columns for inputs
    col1, col2 = st.columns(2)
    
    with col1:
        job_role = st.text_input("Job Role:", placeholder="Software Engineer")
        
        job_description = st.text_area(
            "Job Description:", 
            height=300,
            placeholder="Paste the complete job description here..."
        )
    
    with col2:
        original_cv = st.text_area(
            "Your Current Resume/CV:", 
            height=300,
            placeholder="Paste your current resume/CV content here..."
        )
    
    # Process button
    if st.button("Generate Customized Resume"):
        if not api_key:
            st.error("Please enter your Groq API key")
        elif not job_role or not job_description or not original_cv:
            st.error("Please fill in all fields")
        else:
            with st.spinner("Customizing your resume... This may take a minute"):
                # Get customized resume content
                customized_content = get_customized_resume(job_role, job_description, original_cv)
                
                # Create temporary file for PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_path = tmp_file.name
                
                # Create PDF
                create_professional_pdf(customized_content, tmp_path)
                
                # Display customized content
                st.subheader("Customized Resume Preview:")
                st.text_area("Preview:", value=customized_content, height=400)
                
                # Provide download button for PDF
                with open(tmp_path, "rb") as pdf_file:
                    st.download_button(
                        label="Download Resume as PDF",
                        data=pdf_file,
                        file_name=f"Customized_Resume_{job_role.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                
                # Clean up the temporary file
                os.unlink(tmp_path)

if __name__ == "__main__":
    main()
