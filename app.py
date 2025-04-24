import streamlit as st
import groq
import tempfile
import os
import json
from fpdf import FPDF
import textwrap
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_customized_resume_json(job_role, job_description, original_cv):
    """Get a customized resume in JSON format using the Llama model via Groq API"""
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
    
    Return the resume in the following JSON format:
    {{
        "name": "Full Name",
        "contact_info": {{
            "location": "City, Country",
            "phone": "Phone number",
            "email": "Email address",
            "linkedin": "LinkedIn URL",
            "github": "GitHub URL",
            "portfolio": "Any other relevant URL",
            "additional": "Any other contact information"
        }},
        "professional_summary": "A tailored summary for the role...",
        "skills": [
            "Skill 1",
            "Skill 2",
            "etc..."
        ],
        "work_experience": [
            {{
                "title": "Job Title",
                "company": "Company Name",
                "location": "City, Country",
                "duration": "MM/YYYY to MM/YYYY",
                "achievements": [
                    "Achievement 1",
                    "Achievement 2"
                ]
            }}
        ],
        "education": [
            {{
                "degree": "Degree Name",
                "institution": "Institution Name",
                "location": "City, Country",
                "duration": "MM/YYYY to MM/YYYY",
                "details": [
                    "Detail 1",
                    "Detail 2"
                ]
            }}
        ],
        "projects": [
            {{
                "name": "Project Name",
                "details": [
                    "Detail 1",
                    "Detail 2"
                ]
            }}
        ]
    }}
    
    Return ONLY the JSON object without any other text, explanation, or formatting.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        content = response.choices[0].message.content
        
        # Try to parse the JSON
        try:
            # Clean up the content to handle potential extra characters or formatting
            json_content = content
            # If content starts with ```json and ends with ```, strip those
            if content.strip().startswith("```json") and content.strip().endswith("```"):
                json_content = content.strip()[7:-3].strip()
            elif content.strip().startswith("```") and content.strip().endswith("```"):
                json_content = content.strip()[3:-3].strip()
                
            resume_data = json.loads(json_content)
            return {"success": True, "data": resume_data, "raw": content}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parsing error: {str(e)}", "raw": content}
            
    except Exception as e:
        return {"success": False, "error": f"API error: {str(e)}", "raw": ""}

def create_text_resume(resume_data):
    """Create a text version of the resume from JSON data"""
    text_resume = []
    
    # Name
    text_resume.append(f"**{resume_data.get('name', 'Name')}**")
    text_resume.append("")
    
    # Contact Information
    text_resume.append("**Contact Information:**")
    contact_info = resume_data.get('contact_info', {})
    contact_parts = []
    
    if contact_info.get('location'):
        contact_parts.append(contact_info['location'])
    if contact_info.get('phone'):
        contact_parts.append(contact_info['phone'])
    if contact_info.get('email'):
        contact_parts.append(contact_info['email'])
    if contact_info.get('linkedin'):
        contact_parts.append(contact_info['linkedin'])
    if contact_info.get('github'):
        contact_parts.append(contact_info['github'])
    if contact_info.get('portfolio'):
        contact_parts.append(contact_info['portfolio'])
    if contact_info.get('additional'):
        contact_parts.append(contact_info['additional'])
    
    text_resume.append(" | ".join(contact_parts))
    text_resume.append("")
    
    # Professional Summary
    text_resume.append("**Professional Summary:**")
    text_resume.append(resume_data.get('professional_summary', ''))
    text_resume.append("")
    
    # Skills
    text_resume.append("**Skills:**")
    for skill in resume_data.get('skills', []):
        text_resume.append(f"* {skill}")
    text_resume.append("")
    
    # Work Experience
    text_resume.append("**Work Experience:**")
    for job in resume_data.get('work_experience', []):
        job_header = f"* {job.get('title', '')}, {job.get('company', '')}"
        if job.get('location'):
            job_header += f" ({job.get('location', '')})"
        if job.get('duration'):
            job_header += f" - {job.get('duration', '')}"
        text_resume.append(job_header)
        
        for achievement in job.get('achievements', []):
            text_resume.append(f"  + {achievement}")
        text_resume.append("")
    
    # Education
    text_resume.append("**Education:**")
    for edu in resume_data.get('education', []):
        edu_header = f"* {edu.get('degree', '')}, {edu.get('institution', '')}"
        if edu.get('location'):
            edu_header += f" ({edu.get('location', '')})"
        if edu.get('duration'):
            edu_header += f" - {edu.get('duration', '')}"
        text_resume.append(edu_header)
        
        for detail in edu.get('details', []):
            text_resume.append(f"  + {detail}")
        text_resume.append("")
    
    # Projects
    if resume_data.get('projects'):
        text_resume.append("**Personal Projects:**")
        for project in resume_data.get('projects', []):
            text_resume.append(f"* {project.get('name', '')}")
            
            for detail in project.get('details', []):
                text_resume.append(f"  + {detail}")
            text_resume.append("")
    
    return "\n".join(text_resume)

def create_professional_pdf(resume_data, output_path):
    """Create a professionally formatted PDF resume from JSON data"""
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
    
    # Name at the top - centered and bold
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, resume_data.get('name', 'Name'), 0, 1, 'C')
    pdf.ln(2)
    
    # Contact Information - formatted in a clean way
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)  # Light gray background
    pdf.cell(0, 8, "Contact Information", 1, 1, 'L', True)
    pdf.ln(1)
    
    pdf.set_font('Arial', '', 10)
    contact_info = resume_data.get('contact_info', {})
    contact_text = []
    
    if contact_info.get('location'):
        contact_text.append(contact_info['location'])
    if contact_info.get('phone'):
        contact_text.append(contact_info['phone'])
    if contact_info.get('email'):
        contact_text.append(contact_info['email'])
    
    # First line of contact info
    pdf.cell(0, 6, " | ".join(contact_text), 0, 1)
    
    online_links = []
    if contact_info.get('linkedin'):
        online_links.append(f"LinkedIn: {contact_info['linkedin']}")
    if contact_info.get('github'):
        online_links.append(f"GitHub: {contact_info['github']}")
    if contact_info.get('portfolio'):
        online_links.append(f"Portfolio: {contact_info['portfolio']}")
    if contact_info.get('additional'):
        online_links.append(contact_info['additional'])
    
    # Second line for online profiles
    if online_links:
        pdf.cell(0, 6, " | ".join(online_links), 0, 1)
    
    pdf.ln(5)
    
    # Professional Summary
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "Professional Summary", 1, 1, 'L', True)
    pdf.ln(1)
    
    pdf.set_font('Arial', '', 10)
    summary = resume_data.get('professional_summary', '')
    wrapped_lines = textwrap.wrap(summary, width=100)
    for line in wrapped_lines:
        pdf.cell(0, 6, line, 0, 1)
    
    pdf.ln(5)
    
    # Skills
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "Skills", 1, 1, 'L', True)
    pdf.ln(1)
    
    pdf.set_font('Arial', '', 10)
    skills = resume_data.get('skills', [])
    
    # Format skills as either bullet points or in categories
    for skill in skills:
        pdf.cell(5, 6, chr(149), 0, 0)  # Bullet point
        pdf.cell(0, 6, skill, 0, 1)
    
    pdf.ln(5)
    
    # Work Experience
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "Work Experience", 1, 1, 'L', True)
    pdf.ln(1)
    
    for job in resume_data.get('work_experience', []):
        # Job title
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, job.get('title', ''), 0, 1)
        
        # Company and duration
        company_text = job.get('company', '')
        if job.get('location'):
            company_text += f", {job.get('location', '')}"
        
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, company_text, 0, 1)
        
        if job.get('duration'):
            pdf.cell(0, 6, job.get('duration', ''), 0, 1)
        
        # Achievements
        pdf.set_font('Arial', '', 10)
        for achievement in job.get('achievements', []):
            pdf.cell(10, 6, '', 0, 0)  # Indentation
            pdf.cell(3, 6, chr(149), 0, 0)  # Bullet point
            
            # Wrap text for bullet points
            wrapped_lines = textwrap.wrap(achievement, width=85)
            if wrapped_lines:
                pdf.cell(0, 6, wrapped_lines[0], 0, 1)
                for wrapped_line in wrapped_lines[1:]:
                    pdf.cell(13, 6, '', 0, 0)  # Indentation
                    pdf.cell(0, 6, wrapped_line, 0, 1)
        
        pdf.ln(3)  # Space between jobs
    
    pdf.ln(5)
    
    # Education
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "Education", 1, 1, 'L', True)
    pdf.ln(1)
    
    for edu in resume_data.get('education', []):
        # Degree
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, edu.get('degree', ''), 0, 1)
        
        # Institution and location
        institution_text = edu.get('institution', '')
        if edu.get('location'):
            institution_text += f", {edu.get('location', '')}"
        
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, institution_text, 0, 1)
        
        if edu.get('duration'):
            pdf.cell(0, 6, edu.get('duration', ''), 0, 1)
        
        # Details
        pdf.set_font('Arial', '', 10)
        for detail in edu.get('details', []):
            pdf.cell(10, 6, '', 0, 0)  # Indentation
            pdf.cell(3, 6, chr(149), 0, 0)  # Bullet point
            
            # Wrap text for bullet points
            wrapped_lines = textwrap.wrap(detail, width=85)
            if wrapped_lines:
                pdf.cell(0, 6, wrapped_lines[0], 0, 1)
                for wrapped_line in wrapped_lines[1:]:
                    pdf.cell(13, 6, '', 0, 0)  # Indentation
                    pdf.cell(0, 6, wrapped_line, 0, 1)
        
        pdf.ln(3)  # Space between education items
    
    # Projects (if any)
    if resume_data.get('projects'):
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "Personal Projects", 1, 1, 'L', True)
        pdf.ln(1)
        
        for project in resume_data.get('projects', []):
            # Project name
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, project.get('name', ''), 0, 1)
            
            # Details
            pdf.set_font('Arial', '', 10)
            for detail in project.get('details', []):
                pdf.cell(10, 6, '', 0, 0)  # Indentation
                pdf.cell(3, 6, chr(149), 0, 0)  # Bullet point
                
                # Wrap text for bullet points
                wrapped_lines = textwrap.wrap(detail, width=85)
                if wrapped_lines:
                    pdf.cell(0, 6, wrapped_lines[0], 0, 1)
                    for wrapped_line in wrapped_lines[1:]:
                        pdf.cell(13, 6, '', 0, 0)  # Indentation
                        pdf.cell(0, 6, wrapped_line, 0, 1)
            
            pdf.ln(3)  # Space between projects
    
    # Save the PDF
    pdf.output(output_path)

def main():
    st.set_page_config(page_title="AI Resume Customizer", layout="wide")
    
    st.title("AI Resume Customizer")
    st.write("Tailor your resume to match specific job descriptions using AI")
    
    # API key input
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
                # Get customized resume content as JSON
                result = get_customized_resume_json(job_role, job_description, original_cv)
                
                if not result["success"]:
                    st.error(f"Error: {result.get('error', 'Unknown error')}")
                    st.text_area("Raw API response:", value=result.get('raw', ''), height=200)
                else:
                    resume_data = result["data"]
                    
                    # Convert JSON to text resume for preview
                    text_resume = create_text_resume(resume_data)
                    
                    # Create temporary file for PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_path = tmp_file.name
                    
                    # Create PDF from JSON data
                    create_professional_pdf(resume_data, tmp_path)
                    
                    # Display tabs for different views
                    tab1, tab2 = st.tabs(["Resume Preview", "JSON Data"])
                    
                    with tab1:
                        st.subheader("Customized Resume Preview:")
                        st.text_area("Text Preview:", value=text_resume, height=400)
                    
                    with tab2:
                        st.subheader("JSON Data:")
                        st.json(resume_data)
                    
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
