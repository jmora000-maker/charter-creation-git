import os
import json
import logging
import requests
import contextlib              # <--- This fixes the contextlib NameError
from datetime import date
from pathlib import Path

import streamlit as st
import docx                  # For python-docx
import pypdf

# Define paths and global variables
today = date.today()

current_script_dir=Path(__file__).resolve().parent
project_root=current_script_dir

input_folder = project_root / "inputs"
log_folder = project_root / "logs"
output_folder = project_root / "outputs"

# --- UTILITY TO CAPTURE STDOUT ---
# This class redirects standard output to a Streamlit text component in real-time.
class StreamlitStdoutRedirector:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.output_str = ""

    def write(self, text):
        self.output_str += text
        self.placeholder.code(self.output_str, language="text")

    def flush(self):
        pass

# --- ADD SCRIPT FUNCTIONS HERE ---

# This function will route the file to the appropriate extraction function based on the file type.
def ingest_file(filepath):
    # Determine the file type
    if filepath.suffix == ".docx":
        return extract_from_docx(filepath)
    elif filepath.suffix == ".pdf":
        return extract_from_pdf(filepath)
    elif filepath.suffix == ".txt":
        return extract_from_txt(filepath)
    else:
        return "Unsupported file type."

# This function extracts text from a Word document and returns it as a string.
def extract_from_docx(filepath):
    # Load the Word document
    doc = docx.Document(filepath)
    # We join with a newline to preserve logical document structure
    return "\n".join([p.text for p in doc.paragraphs])

# This function extracts text from a PDF document and returns it as a string.
def extract_from_pdf(filepath):
    # Create a PDF reader object
    reader = pypdf.PdfReader(filepath)
    text = ""
    # Loop through each page and extract text
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# This function extracts text from a text file and returns it as a string.
def extract_from_txt(filepath):
    # 'with' ensures the file is safely opened and closed
    with open(filepath, "r", encoding="utf-8") as f:
        # read() pulls the entire file content into a single string
        return f.read()


# This function combines the strategy and project inputs into a single context payload.
def build_master_context(strategy_filepath, project_filepath):
    try:
        # Harvest the raw data
        strategy_text = ingest_file(strategy_filepath)
        project_text = ingest_file(project_filepath)

        # Assemble the master context with clear structural markers
        # These markers help the LLM distinguish between the two sources
        master_context = f"""
        ### ROLE
        You are an expert Project Management Consultant with a deep understanding of corporate strategy alignment.

        ### TASK
        Today's date is: {today}. Create a professional Project Charter from the COMPANY STRATEGY {strategy_text} and PROJECT INPUTS {project_text}. The Project Charter should synthesize the contextual unity of the strategy. Your output must meet the strict JSON schema below:
        {{
          "report_metadata": {{
            "project_title": "string",
            "report_date": "string"
          }},
          "project_report": {{
            "executive_summary": "string",
            "strategic_objective": "string",
            "project_purpose": "string",
            "key_deliverables": ["string"],
            "high_level_requirements": ["string"],
            "project_constraints": ["string"],
            "project_assumptions": ["string"],
            "schedule_milestones": ["string"],
            "success_criteria": ["string"],
            "high_level_risks": ["string"],
            "budget": "string",
            "stakeholders_list": ["string"]
          }}   
        }}
        ### FIELD DEFINITIONS
        * project_title: The name of the strategic objective.
        * report_date: Today's date.
        * executive_summary: A 3 - 4 sentence summary of the project.
        * strategic_objective: The strategic objective the project supports.
        * project_purpose: A 3 - 4 project purpose of the project.
        * key_deliverables: Synthesize a list of the key deliverables of the project.
        * high_level_requirements: Synthesize a list of high-level requirements of the project from the contextual unity of the strategy.
        * project_constraints: Synthesize a list of project constraints from the contextual unity of the strategy. 
        * project_assumptions: Synthesize a list of project assumptions from the contextual unity of the strategy.
        * schedule_milestones: Synthesize a list of schedule milestones and dates from the contextual unity of the strategy. The dates should be in the format Month Day.
        * success_criteria: Synthesize a list of success criteria from the contextual unity of the strategy. 
        * high_level_risks: Synthesize a list of high level risks from the contextual unity of the strategy. 
        * budget: The budget. If one is not provided, state "To be defined."
        * stakeholders_list: Synthesize a list of the top 5 stakeholders.

        ### RULES
        1. Output must be valid JSON.
        2. Do not include markdown fences.
        3. Do not include any text before or after the JSON.
        4. Use exactly the schema and field names provided below.
        5. If a value is unknown, use an empty string for text fields.

         """
        print(" -> Master Context built")
        return master_context

    except Exception as e:
        print(f"Error building master context: {e}")
        return None


# This function will be used to clean the text data before saving it to a file and sending it to the LLM.
def clean_text(text):
    # Remove extra whitespace and newlines
    text = " ".join(text.split())
    print(f" -> Master context cleaned")
    return text


# This function will be used to save the master context to a file.
def save_master_context(master_context, masterfile_path):
    with open(masterfile_path, "w", encoding="utf-8") as f:
        f.write(master_context)


# This functions sends the payload to the OpenAI API
def send_to_llm(master_context, api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    prompt = f"""{master_context}"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a risk analyst. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        raw_ai_output = response.json()["choices"][0]["message"][
            "content"
        ]  # extract the response text
        clean_ai_output = (
            raw_ai_output.replace("```json", "").replace("```", "").strip()
        )
        print(" -> Report data extracted from LLM response.")
        return clean_ai_output
    else:
        print(f"DEBUG: API Failed: {response.status_code}")
        raise Exception(f"API Failed: {response.status_code}")


# This function will be used to save the LLM response to a file.
def save_llm_response(llm_response, llm_response_path):
    # Save json string to a file
    with open(llm_response_path, "w", encoding="utf-8") as f:
        f.write(llm_response)


# This function will be used to generate a narrative project charter utilizing LLM json response.
def generate_project_charter(llm_response):

    print(f" -> Performing automated report generation.")

    # Convert the JSON string to a Python dictionary
    llm_response_dict = json.loads(llm_response)

    # Extract the report values from the dictionary
    project_metadata = llm_response_dict.get("report_metadata", "TBD")
    project_report = llm_response_dict.get("project_report", "TBD")

    # Create the project charter text
    lines = []

    lines.append(f"PROJECT CHARTER")
    project_title = project_metadata.get("project_title", "TBD")
    lines.append(f"Project: {project_title}")
    lines.append(f"Report Date: {today}")
    lines.append("")


    # Executive Summary
    lines.append("EXECUTIVE SUMMARY")
    lines.append(project_report.get("executive_summary", "TBD"))
    lines.append("")

    # Strategic Objective
    lines.append("STRATEGIC OBJECTIVE")
    lines.append(project_report.get("strategic_objective", "TBD"))
    lines.append("")

    # Project Purpose
    lines.append("PROJECT PURPOSE")
    lines.append(project_report.get("project_purpose", "TBD"))
    lines.append("")

    # Key Deliverables
    key_deliverables = project_report.get("key_deliverables", [])
    lines.append("KEY DELIVERABLES")
    if key_deliverables:
        for d in key_deliverables:
            lines.append(f"- {d}")
    else:
        lines.append("No deliverables were identified.")
    lines.append("")

    # High Level Requirements
    high_level_requirements = project_report.get("high_level_requirements", [])
    lines.append("HIGH LEVEL REQUIREMENTS")
    if high_level_requirements:
        for r in high_level_requirements:
            lines.append(f"- {r}")
    else:
        lines.append("No requirements were identified.")
    lines.append("")

    # Project Constraints
    project_constraints = project_report.get("project_constraints", [])
    lines.append("PROJECT CONSTRAINTS")
    if project_constraints:
        for c in project_constraints:
            lines.append(f"- {c}")
    else:
        lines.append("No constraints were identified.")
    lines.append("")

    # Project Assumptions
    project_assumptions = project_report.get("project_assumptions", [])
    lines.append("PROJECT ASSUMPTIONS")
    if project_assumptions:
        for a in project_assumptions:
            lines.append(f"- {a}")
    else:
        lines.append("No assumptions were identified.")
    lines.append("")

    # Schedule Milestones
    schedule_milestones = project_report.get("schedule_milestones", [])
    lines.append("SCHEDULE MILESTONES")
    if schedule_milestones:
        for m in schedule_milestones:
            lines.append(f"- {m}")
    else:
        lines.append("No milestones were identified.")
    lines.append("")

    # Success Criteria
    success_criteria = project_report.get("success_criteria", [])
    lines.append("SUCCESS CRITERIA")
    if success_criteria:
        for c in success_criteria:
            lines.append(f"- {c}")
    else:
        lines.append("No success criteria were identified.")
    lines.append("")

    # High Level Risks
    high_level_risks = project_report.get("high_level_risks", [])
    lines.append("HIGH LEVEL RISKS")
    if high_level_risks:
        for r in high_level_risks:
            lines.append(f"- {r}")
    else:
        lines.append("No risks were identified.")
    lines.append("")

    # Budget
    lines.append("BUDGET")
    lines.append(project_report.get("budget", "TBD"))
    lines.append("")

    # Stakeholders List
    stakeholders_list = project_report.get("stakeholders_list", [])
    lines.append("STAKEHOLDERS LIST")
    if stakeholders_list:
        for s in stakeholders_list:
            lines.append(f"- {s}")
    else:
        lines.append("No stakeholders were identified.")
    lines.append("")

    # Join all lines with newline characters
    # Strip any leading or trailing whitespace
    # Return the final string
    # This ensures the output is clean and well-formatted
    # The strip() method removes any extra whitespace at the beginning or end of the string
    # This is important for consistency and readability

    return "\n".join(lines).strip()


# This function will be used to save the project charter to a file.
def save_project_charter(project_charter, project_charter_path):
    with open(project_charter_path, "w", encoding="utf-8") as f:
        f.write(project_charter)


# --- CORE PIPELINE EXECUTION WRAPPER ---
def run_automated_pipeline(log_placeholder):

    # Target export routing destinations
    api_key = os.environ.get("OPENAI_API_KEY")
    strategy_name = "strategy.pdf"
    project_name = "project_notes.docx"


    data_dir = project_root / "data"

    strategy_filepath = data_dir / strategy_name
    project_filepath = data_dir / project_name
    masterfile_path = data_dir / "master_context.txt"
    llm_response_path = data_dir / "llm_response.json"
    project_charter_path = data_dir / "project_charter.txt"

    # Pipeline Execution
    try:
        print("PIPELINE STARTED.")

        # Ingest files
        print("STEP #1: Ingesting project files.")
        strategy_raw_text = ingest_file(strategy_filepath)
        project_raw_text = ingest_file(project_filepath)


        # Package and clean text payloads
        # Change this inside run_automated_pipeline:
        print("STEP #2: Building master context.")
        master_payload = build_master_context(strategy_filepath, project_filepath)

        print("STEP #3: Cleaning master context.")
        cleaned_payload = clean_text(master_payload)


        # Send the master context to the LLM
        print("STEP #4: Sending master context to OpenAI.")
        print(" -> Please wait a few moments...")
        llm_response = send_to_llm(cleaned_payload, api_key)

        # FIX #1: Removed the extra path argument here
        print("STEP #5: Generating Project Charter.")
        project_charter = generate_project_charter(llm_response)

        # FIX #2: Pass BOTH variables to the saving function in the correct order
        save_project_charter(project_charter, project_charter_path)

        print("PIPELINE COMPLETED.")
        return project_charter

    except Exception as e:
        st.error(f"Pipeline crashed with an unhandled traceback exception: {e}")
        logging.error(f"Streamlit runtime pipeline execution failure: {e}", exc_info=True)
        return None


# --- STREAMLIT UI CONFIGURATION ---
st.set_page_config(
    page_title="AI Project Charter Generator",
    layout="wide"
)

# APPLICATION TITLE
st.title("Project Charter Dashboard")
st.caption("Deterministic contextual mapping to translate high-level corporate vision into aligned, execution-ready delivery frameworks.")
st.markdown("---")

# Split dashboard workspace view evenly into two layout control blocks
col1, col2 = st.columns(2)

with col1:
    st.subheader("System Configuration")
    strategy_name = "strategy.pdf"
    project_name = "project_notes.docx"

    # FIX: Use absolute paths here too
    data_dir = project_root / "data"

    strategy_filepath = data_dir / strategy_name
    project_filepath = data_dir / project_name

    # Provide an informative file validation status display on the interface
    files_exist = strategy_filepath.exists() and project_filepath.exists()
    if strategy_filepath.exists():
        st.text(f"Found Strategy Document: `strategy.pdf`")
    else:
        st.text(f"Missing Target Path: `strategy.pdf`")
    if project_filepath.exists():
        st.text(f"Found Project Notes: `project_notes.docx`")
    else:
        st.text(f"Missing Target Path: `project_notes.docx`")

    # Core system action trigger interface button
    start_pipeline = st.button("Generate Project Charter", use_container_width=True, type="primary")

    st.subheader("Pipeline Summary")
    # Interactive log tracing viewport block
    console_logs = st.empty()
    console_logs.info("Click 'Generate Project Charter' button to begin.")

# Persistent frame layout setup for Column 2 immediately on boot
with col2:
    st.subheader("Report Workspace")
    report_placeholder = st.empty()

    # Pre-execution placeholder info state setup
    report_placeholder.info("The Project Charter will populate here upon synthesis.")

# Active process handler evaluations
if start_pipeline:
    redirector = StreamlitStdoutRedirector(console_logs)

    with st.spinner("Processing contextual synthesis..."):
        # Wrap the stream interceptor strictly around the pipeline engine call
        with contextlib.redirect_stdout(redirector):
            final_narrative = run_automated_pipeline(console_logs)

    if final_narrative:
        with col2:
            # Overwrite the initial info alert box inside the locked workspace column element
            report_placeholder.markdown(
                f"""
                <div style="
                    background-color: #1e293b; 
                    color: #f8fafc; 
                    padding: 20px; 
                    border-radius: 8px; 
                    height: 550px; 
                    overflow-y: scroll; 
                    white-space: pre-wrap; 
                    font-family: monospace;
                    border: 1px solid #334155;
                    line-height: 1.5;
                ">{final_narrative}</div>
                """,
                unsafe_allow_html=True
            )

            # Native browser download button widget asset mapping final strings out of RAM memory
            st.download_button(
                label="Download Project Charter (.txt)",
                data=final_narrative,
                file_name="project_charter.txt",
                mime="text/plain",
                use_container_width=True
            )