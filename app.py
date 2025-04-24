import streamlit as st
import groq
import tempfile
import os
from fpdf import FPDF
import textwrap
from dotenv import load_dotenv

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

def create_pdf(content, output_path):
    """Create a PDF file from the content"""
    pdf = FPDF()
    pdf.add_page()
    
    # Set font for title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Customized Resume", ln=True, align="C")
    pdf.ln(10)
    
    # Set font for content
    pdf.set_font("Arial", "", 12)
    
    # Split content into lines and add to PDF
    for line in content.split('\n'):
        # Check if line is a heading (assuming headings are in all caps or end with a colon)
        if line.isupper() or line.endswith(':') or not line.strip():
            pdf.ln(5)  # Add some space before headings
            if line.strip():  # Only print if line is not empty
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, line, ln=True)
                pdf.set_font("Arial", "", 12)
        else:
            # Wrap text to fit in PDF
            wrapped_lines = textwrap.wrap(line, width=90)
            for wrapped_line in wrapped_lines:
                pdf.cell(0, 10, wrapped_line, ln=True)
    
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
                # Get customized resume content
                customized_content = get_customized_resume(job_role, job_description, original_cv)
                
                # Create temporary file for PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_path = tmp_file.name
                
                # Create PDF
                create_pdf(customized_content, tmp_path)
                
                # Display customized content
                st.subheader("Customized Resume:")
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
