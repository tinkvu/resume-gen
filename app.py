import streamlit as st
import groq
import tempfile
import os
import json
from fpdf import FPDF  # Keep original import, but install fpdf version 2+
import textwrap
from dotenv import load_dotenv
from io import StringIO
from pdfminer.high_level import extract_text as extract_pdf_text
import docx2txt

def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == 'pdf':
        text = extract_pdf_text(uploaded_file)
    elif file_type in ['docx', 'doc']:
        text = docx2txt.process(uploaded_file)
    elif file_type == 'txt':
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        text = stringio.read()
    else:
        st.error('Unsupported file type. Please upload a PDF, DOCX, or TXT file.')
        return None
    return text


# Load environment variables
load_dotenv()

# Get API key from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = groq.Groq(api_key=GROQ_API_KEY)

def get_default_prompt(job_role, job_description, original_cv):
    """Get the default prompt template with fields filled in"""
    return f"""
    As an AI resume expert, your task is to customize the provided CV to better match the specified job role and description.
    
    Job Role: {job_role}
    
    Job Description: {job_description}
    
    Original CV: {original_cv}
    
    Create a tailored resume that:
    1. Highlights relevant skills and experiences that match the job requirements
    2. Uses appropriate keywords from the job description
    3. Reorganizes content to emphasize the most relevant qualifications
    4. Maintains the candidate's genuine experience and skills (no fabrication)
    5. Remove any special characters (like –) in the CV and use the common ones.
    
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

def get_customized_resume_json(prompt, model="llama3-8b-8192"):
    """Get a customized resume in JSON format using the specified model via Groq API"""
    try:
        response = client.chat.completions.create(
            model=model,
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
    
    # Check if API key is available
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY is not set in environment variables. Please set it and restart the application.")
        st.stop()
    
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
        st.write("Upload or Paste Your Resume/CV")

        option = st.radio(
            "Choose how you want to provide your Resume/CV:",
            ("Upload File", "Paste Text")
        )
    
        col1, col2 = st.columns(2)

        with col2:
            if option == "Upload File":
                uploaded_file = st.file_uploader(
                    "Upload your resume/CV (PDF, DOCX, TXT)", 
                    type=["pdf", "docx", "doc", "txt"]
                )
                if uploaded_file is not None:
                    with st.spinner('Extracting text...'):
                        original_cv = extract_text_from_file(uploaded_file)
                        if original_cv:
                            st.success("Text extracted successfully!")
                        else:
                            original_cv = ""
            else:
                original_cv = st.text_area(
                    "Paste your current Resume/CV:", 
                    height=300,
                    placeholder="Paste your current resume/CV content here..."
                )
        
    # Add model selection
    model = st.selectbox(
        "Language Model:",
        ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"]
    )
    
    # Add option to edit the prompt
    edit_prompt = st.checkbox("Edit AI Prompt", value=False, help="Enable to edit the prompt sent to the AI model")
    
    # Initialize or retrieve custom_prompt from session state
    if 'custom_prompt' not in st.session_state:
        st.session_state.custom_prompt = ""
    
    # If edit_prompt is checked, show the prompt editor
    custom_prompt = ""
    if edit_prompt:
        # Generate the default prompt with current input values
        default_prompt = get_default_prompt(job_role, job_description, original_cv)
        
        # If custom_prompt is empty or inputs have changed, update it
        if not st.session_state.custom_prompt or st.session_state.get('prev_inputs') != (job_role, job_description):
            st.session_state.custom_prompt = default_prompt
        
        # Store current inputs for comparison on next render
        st.session_state.prev_inputs = (job_role, job_description)
        
        # Show the prompt editor
        custom_prompt = st.text_area(
            "Edit AI Prompt:",
            value=st.session_state.custom_prompt,
            height=400
        )
        
        # Update session state with edited prompt
        st.session_state.custom_prompt = custom_prompt
        
        # Show reset button
        if st.button("Reset to Default Prompt"):
            st.session_state.custom_prompt = get_default_prompt(job_role, job_description, original_cv)
            st.experimental_rerun()
    
    # Create a session state to store the generated resume data
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = None
        st.session_state.generated = False
    
    # Process button
    if st.button("Generate Customized Resume") or st.session_state.generated:
        if not job_role or not job_description or not original_cv:
            st.error("Please fill in all fields")
        else:
            # Only call the API if we haven't generated yet
            if not st.session_state.generated:
                with st.spinner(f"Customizing your resume using {model}... This may take a minute"):
                    # Determine which prompt to use
                    prompt_to_use = custom_prompt if edit_prompt and custom_prompt else get_default_prompt(job_role, job_description, original_cv)
                    
                    # Get customized resume content as JSON
                    result = get_customized_resume_json(prompt_to_use, model)
                    
                    if not result["success"]:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
                        st.text_area("Raw API response:", value=result.get('raw', ''), height=200)
                        st.stop()
                    else:
                        st.session_state.resume_data = result["data"]
                        st.session_state.generated = True
            
            # Now handle the editing and display
            resume_data = st.session_state.resume_data
            
            # Create editing interface with tabs
            st.subheader("Edit Your Resume:")
            tabs = st.tabs(["Personal Info", "Summary", "Skills", "Work Experience", "Education", "Projects"])
            
            # Personal Info Tab
            with tabs[0]:
                col1, col2 = st.columns(2)
                with col1:
                    resume_data["name"] = st.text_input("Name:", value=resume_data.get("name", ""))
                    resume_data["contact_info"]["location"] = st.text_input("Location:", value=resume_data.get("contact_info", {}).get("location", ""))
                    resume_data["contact_info"]["phone"] = st.text_input("Phone:", value=resume_data.get("contact_info", {}).get("phone", ""))
                    resume_data["contact_info"]["email"] = st.text_input("Email:", value=resume_data.get("contact_info", {}).get("email", ""))
                
                with col2:
                    resume_data["contact_info"]["linkedin"] = st.text_input("LinkedIn URL:", value=resume_data.get("contact_info", {}).get("linkedin", ""))
                    resume_data["contact_info"]["github"] = st.text_input("GitHub URL:", value=resume_data.get("contact_info", {}).get("github", ""))
                    resume_data["contact_info"]["portfolio"] = st.text_input("Portfolio URL:", value=resume_data.get("contact_info", {}).get("portfolio", ""))
                    resume_data["contact_info"]["additional"] = st.text_input("Additional Contact Info:", value=resume_data.get("contact_info", {}).get("additional", ""))
            
            # Summary Tab
            with tabs[1]:
                resume_data["professional_summary"] = st.text_area("Professional Summary:", value=resume_data.get("professional_summary", ""), height=200)
            
            # Skills Tab
            with tabs[2]:
                skills = resume_data.get("skills", [])
                skills_text = "\n".join(skills)
                skills_text = st.text_area("Skills (One per line):", value=skills_text, height=200)
                resume_data["skills"] = [s.strip() for s in skills_text.split("\n") if s.strip()]
            
            # Work Experience Tab
            with tabs[3]:
                work_experiences = resume_data.get("work_experience", [])
                work_experiences_count = len(work_experiences)
                
                work_experiences_count = st.number_input("Number of work experiences:", min_value=0, value=work_experiences_count)
                
                new_work_experiences = []
                for i in range(work_experiences_count):
                    st.subheader(f"Work Experience #{i+1}")
                    
                    job = {} if i >= len(work_experiences) else work_experiences[i]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        job["title"] = st.text_input(f"Job Title #{i+1}:", value=job.get("title", ""))
                        job["company"] = st.text_input(f"Company #{i+1}:", value=job.get("company", ""))
                    
                    with col2:
                        job["location"] = st.text_input(f"Location #{i+1}:", value=job.get("location", ""))
                        job["duration"] = st.text_input(f"Duration #{i+1}:", value=job.get("duration", ""))
                    
                    achievements = job.get("achievements", [])
                    achievements_text = "\n".join(achievements)
                    achievements_text = st.text_area(f"Achievements #{i+1} (One per line):", value=achievements_text)
                    job["achievements"] = [a.strip() for a in achievements_text.split("\n") if a.strip()]
                    
                    new_work_experiences.append(job)
                    st.markdown("---")
                
                resume_data["work_experience"] = new_work_experiences
            
            # Education Tab
            with tabs[4]:
                educations = resume_data.get("education", [])
                educations_count = len(educations)
                
                educations_count = st.number_input("Number of education entries:", min_value=0, value=educations_count)
                
                new_educations = []
                for i in range(educations_count):
                    st.subheader(f"Education #{i+1}")
                    
                    edu = {} if i >= len(educations) else educations[i]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edu["degree"] = st.text_input(f"Degree #{i+1}:", value=edu.get("degree", ""))
                        edu["institution"] = st.text_input(f"Institution #{i+1}:", value=edu.get("institution", ""))
                    
                    with col2:
                        edu["location"] = st.text_input(f"Education Location #{i+1}:", value=edu.get("location", ""))
                        edu["duration"] = st.text_input(f"Education Duration #{i+1}:", value=edu.get("duration", ""))
                    
                    details = edu.get("details", [])
                    details_text = "\n".join(details)
                    details_text = st.text_area(f"Details #{i+1} (One per line):", value=details_text)
                    edu["details"] = [d.strip() for d in details_text.split("\n") if d.strip()]
                    
                    new_educations.append(edu)
                    st.markdown("---")
                
                resume_data["education"] = new_educations
            
            # Projects Tab
            with tabs[5]:
                projects = resume_data.get("projects", [])
                if not projects:
                    projects = []
                
                projects_count = len(projects)
                projects_count = st.number_input("Number of projects:", min_value=0, value=projects_count)
                
                new_projects = []
                for i in range(projects_count):
                    st.subheader(f"Project #{i+1}")
                    
                    project = {} if i >= len(projects) else projects[i]
                    
                    project["name"] = st.text_input(f"Project Name #{i+1}:", value=project.get("name", ""))
                    
                    details = project.get("details", [])
                    details_text = "\n".join(details)
                    details_text = st.text_area(f"Project Details #{i+1} (One per line):", value=details_text)
                    project["details"] = [d.strip() for d in details_text.split("\n") if d.strip()]
                    
                    new_projects.append(project)
                    st.markdown("---")
                
                resume_data["projects"] = new_projects
            
            # Preview and download section
            st.subheader("Resume Preview")
            text_resume = create_text_resume(resume_data)
            st.text_area("Text Preview:", value=text_resume, height=300)
            
            # Create PDF button
            if st.button("Generate Final PDF"):
                # Create temporary file for PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_path = tmp_file.name
                
                # Create PDF from edited JSON data
                create_professional_pdf(resume_data, tmp_path)
                
                # Provide download button for PDF
                with open(tmp_path, "rb") as pdf_file:
                    st.download_button(
                        label="Download Resume as PDF",
                        data=pdf_file,
                        file_name=f"{job_role.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                
                # Clean up the temporary file
                os.unlink(tmp_path)
            
            # Add button to reset and start over
            if st.button("Start Over"):
                st.session_state.resume_data = None
                st.session_state.generated = False
                st.session_state.custom_prompt = ""
                st.experimental_rerun()

if __name__ == "__main__":
    main()
