import docx
import pypdf
import logging
from pathlib import Path
import requests
import os
import json
from datetime import date
import streamlit as st
import sys
import io
import contextlib

# Set up Streamlit page layout to wide
st.set_page_config(layout="wide", page_title="AI Project Charter Generator")

today = date.today()
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

api_key = os.getenv("OPENAI_API_KEY")

# --- DATA INGESTION UTILITIES (Updated to receive Path objects) ---

def ingest_file(filepath: Path):
    """Routes local path parameters to the matching string harvester."""
    if filepath.suffix == ".docx":
        return extract_from_docx(filepath)
    elif filepath.suffix == ".pdf":
        return extract_from_pdf(filepath)
    elif filepath.suffix == ".txt":
        return extract_from_txt(filepath)
    else:
        return "Unsupported file type."

def extract_from_docx(filepath: Path):
    print(f"Extracting text from Word file: {filepath.name}...")
    doc = docx.Document(filepath)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_from_pdf(filepath: Path):
    print(f"Extracting text from PDF file: {filepath.name}...")
    reader = pypdf.PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_from_txt(filepath: Path):
    print(f"Extracting text from plain text file: {filepath.name}...")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def build_master_context(strategy_text, project_text):
    print("Building master context payload...")
    try:
        master_context = f"""
        ### ROLE
        You are an expert Project Management Consultant with a deep understanding of corporate strategy alignment.

        ### CONTEXT
        Below is the Company Strategy data and the specific Project Inputs.
        --- COMPANY STRATEGY ---
        {strategy_text}
        --- PROJECT INPUTS ---
        {project_text}

        ### TASK
        Today's date is: {today}. Your primary task is to establish **Contextual Unity** between these documents. 
        Analyze the macro company milestones alongside the micro project constraints, and synthesize a single, unified, and tightly integrated Project Charter. 

        Your response must enforce semantic harmony, ensuring that individual project variables are explicitly mapped back to the strategic truth of the enterprise layout.

        ### STRUCTURE
        Use the following headings exactly: Project Title, Executive Summary, Strategic Rationale, Project Purpose, Key Deliverables, High-Level Requirements, Project Constraints, Project Assumptions, Schedule - Milestones, Success Criteria, High-Level Risks, Budget, and Stakeholders List.

        ### CONSTRAINTS
        - Keep descriptions professional, concise, and focused on maintaining contextual unity.
        - If a specific input is missing (e.g., Budget), state "To be defined" rather than hallucinating text.
        - Return your final result in clean, direct Markdown text.
         """
        return master_context
    except Exception as e:
        print(f"Error building master context: {e}")
        return None

def clean_text(text):
    print("Cleaning master context string variables...")
    return " ".join(text.split())

def send_to_llm(master_context, api_key):
    print("Sending master context out to OpenAI REST endpoint...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional PMO Director. Return your response using Markdown headings."},
            {"role": "user", "content": master_context},
        ],
        "temperature": 0.3,
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"DEBUG: API Failed: {response.status_code}")
        raise Exception(f"API Failed: {response.status_code}")


# --- STREAMLIT STDOUT CONSOLE CAPTURE REDIRECTOR ---

class StreamlitStdoutRedirector:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.output_str = ""

    def write(self, text):
        self.output_str += text
        self.placeholder.code(self.output_str, language="text")

    def flush(self):
        pass


# --- STREAMLIT INTERFACE ---

st.title("Automated Project Charter Dashboard")
st.caption("Synchronizing target workspace documents from the local directory parameters.")

if not api_key:
    st.error("🔑 Environment variable `OPENAI_API_KEY` missing. Please configure it to run.")
    st.stop()

# --- STEP 1: DEFINE LOCAL TARGET WORKSPACE DIRECTORIES ---

# Replace your previous path declarations with this resilient look-up:
current_working_dir = Path(__file__).resolve().parent
data_directory = current_working_dir / "data"

strategy_filepath = data_directory / "strategy.pdf"
project_filepath = data_directory / "project_notes.docx"

st.subheader("1. System Configuration & Workspace Audit")

# Provide an informative file validation status display on the interface
files_exist = strategy_filepath.exists() and project_filepath.exists()

status_col1, status_col2 = st.columns(2)
with status_col1:
    if strategy_filepath.exists():
        st.success(f"✅ Found Strategy Document: `strategy.pdf`")
    else:
        st.error(f"❌ Missing Target Path: `strategy.pdf`")

with status_col2:
    if project_filepath.exists():
        st.success(f"✅ Found Project Notes: `project_notes.docx`")
    else:
        st.error(f"❌ Missing Target Path: `project_notes.docx`")

st.markdown("---")

# --- STEP 2: SPLIT WORKSPACE INTERFACE COLUMNS ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("2. Control Center")

    # Execution Button locks/unlocks based on whether both directory paths exist on the server filesystem
    run_btn = st.button(
        "Trigger Charter Synthesis Pipeline", 
        disabled=not files_exist, 
        use_container_width=True,
        type="primary"
    )

    if not files_exist:
        st.warning("The execution button is locked. Please ensure files are saved in the `data/` path.")

    st.markdown("**Live Operational Console Logs:**")
    log_placeholder = st.empty()
    log_placeholder.code("System Engine Idle. Awaiting execution pipeline launch...", language="text")


with col_right:
    st.subheader("3. Executive Synthesis Workspace")
    charter_placeholder = st.empty()

    # Pre-execution placeholder info state
    if "final_charter_text" not in st.session_state:
        charter_placeholder.info("The parsed project charter narrative text will populate here upon synthesis.")
# --- STEP 3: RUNTIME HANDSHAKE WRAPPER ---
if run_btn and files_exist:
    redirector = StreamlitStdoutRedirector(log_placeholder)

    # Intercept print statements and mirror them directly to the Streamlit layout box
    with contextlib.redirect_stdout(redirector):
        print("Initializing synthesis lifecycle orchestration...")

        # Start the visual spinner context wrapper block
        with st.spinner("Synthesizing corporate strategy documents and mapping variables via LLM pipeline..."):

            # Parse local filesystem text blocks
            strategy_raw_text = ingest_file(strategy_filepath)
            project_raw_text = ingest_file(project_filepath)

            # Package and clean text payloads
            master_payload = build_master_context(strategy_raw_text, project_raw_text)
            cleaned_payload = clean_text(master_payload)

            try:
                # Execute API call transaction (This is what takes time)
                final_markdown_charter = send_to_llm(cleaned_payload, api_key)
                print("\nPipeline complete! Mirroring content structures onto interface...")

                # Update the right column layout with data outputs after spinner completes
                with col_right:
                    # Wipe previous layout message info state
                    charter_placeholder.empty()

                    # Wiping out markdown formatting to enforce raw plain-text look as configured
                    charter_placeholder.code(final_markdown_charter, language="text")

                    # Dynamic Download button 
                    st.download_button(
                        label="📥 Download Final Charter Text",
                        data=final_markdown_charter,
                        file_name=f"Project_Charter_{today}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    st.success("Project Charter processed successfully!")

            except Exception as error_msg:
                print(f"\nCRITICAL ENGINE ERROR: {error_msg}")
                st.error(f"Pipeline crashed: {error_msg}")