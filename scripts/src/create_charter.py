"""The purpose of this script is to create a project charter from a company strategy and project inputs.

The Synthesis-First Architecture
The script will follow a two-stage pipeline to ensure the charter is strategically aligned with the company’s goals.

Stage 1: Contextual Harvesting: The script must ingest two documents:
* Company Strategy (The Source of Truth): A PDF or Word document containing the company’s high-level annual goals, KPIs, and mission.
* Project Input (The Specifics): The rough project scope, budget, and timeline notes.

Stage 2: Structured Synthesis: Use an LLM (like Gemini 2.0 Flash) to act as a "PM Consultant." The LLM doesn't just rewrite text; it performs semantic mapping, ensuring every objective in the project charter is explicitly linked to a goal in the company strategy.

Proposed Technical Design
A. Data Ingestion
python-docx / pypdf
Harvests raw text from both strategy and project files.

B. Orchestration
LangChain
Manages the flow and memory of the "Consultant" AI.

C. Data Structure
Pydantic
Defines the exact schema of a Charter (e.g., Objectives, Success Criteria, Risks).

Implementation Strategy
A. Define the Charter Schema (The Pydantic Model)
By defining the charter structure using Pydantic, you guarantee the output will always have the fields you need (e.g., "Alignment with Strategy," "Budget Constraints").

B. The "Strategic Context" Prompt
The prompt should force the AI to reason across the inputs. Instead of a generic prompt, use one that demands Holistic Synthesis:
You are a Senior PMO Director. Analyze the attached Company Strategy document and the Project Inputs. Create a Project Charter that explicitly maps each Project Objective to a specific Strategic Goal. Ensure the 'Alignment with Strategy' section explains why this project is a priority based on the provided company goals."""

""""STAGE 1: CONTEXUAL HARVESTING
A. The objective of this stage is to convert disparate file formats (PDF, Word, or text) into a single, clean Python string variable (often called a "context" or "prompt payload") that can be sent to an LLM.

B. The strategy docunment is a PDF file, and the project input is a Word document. The script will use the python-docx and pypdf libraries to extract the text from these files.

Workflow Best Practices:
* Standardize the Output: Ensure every harvesting function returns a plain Python string.
* Create a "Master Context" Variable: Once you have harvested the text from both the Company Strategy document and your Project Notes, combine them into a single variable
* Pre-Processing: Before sending this to the LLM, perform basic cleaning—such as stripping unnecessary whitespace—to keep the token count manageable and the data clean. """

import docx
import pypdf
import logging
from pathlib import Path
import requests
import os
import json
from datetime import date

# Define global variables
today = date.today()
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

# Define the API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

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
    logging.info(f"Extracting text from Word file: {filepath}")
    print(f"Extracting text from Word file: {filepath}")
    # Load the Word document
    doc = docx.Document(filepath)
    # We join with a newline to preserve logical document structure
    return "\n".join([p.text for p in doc.paragraphs])

# This function extracts text from a PDF document and returns it as a string.
def extract_from_pdf(filepath):
    logging.info(f"Extracting text from PDF file: {filepath}")
    print(f"Extracting text from PDF file: {filepath}")
    # Create a PDF reader object
    reader = pypdf.PdfReader(filepath)
    text = ""
    # Loop through each page and extract text
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# This function extracts text from a text file and returns it as a string.
def extract_from_txt(filepath):
    logging.info(f"Extracting text from TXT file: {filepath}")
    print(f"Extracting text from TXT file: {filepath}")
    # 'with' ensures the file is safely opened and closed
    with open(filepath, "r", encoding="utf-8") as f:
        # read() pulls the entire file content into a single string
        return f.read()

# This function combines the strategy and project inputs into a single context payload.
def build_master_context(strategy_filepath, project_filepath):
    """
    Harvests data from multiple sources and assembles a unified context payload.
    """
    logging.info("Building master context...")
    print("Building master context...")
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
        return master_context

    except Exception as e:
        print(f"Error building master context: {e}")
        return None

# This function will be used to clean the text data before saving it to a file and sending it to the LLM.
def clean_text(text):
    logging.info(f"Cleaning master content text...")
    print(f"Cleaning master context text...")
    # Remove extra whitespace and newlines
    text = " ".join(text.split())
    return text

# This function will be used to save the master context to a file.
def save_master_context(master_context, masterfile_path):
    logging.info(f"Saving master context to {masterfile_path}")
    print(f"Saving master context to {masterfile_path}")
    with open(masterfile_path, "w", encoding="utf-8") as f:
        f.write(master_context)

# This functions sends the payload to the OpenAI API 
def send_to_llm(master_context, api_key):
    logging.info("Sending master context to LLM...")
    print("Sending master context to LLM...")
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
        return clean_ai_output
    else:
        print(f"DEBUG: API Failed: {response.status_code}")
        raise Exception(f"API Failed: {response.status_code}")

# This function will be used to save the LLM response to a file.
def save_llm_response(llm_response, llm_response_path):
    logging.info(f"Saving LLM response to {llm_response_path}")
    print(f"Saving LLM response to {llm_response_path}")
    # Save json string to a file
    with open(llm_response_path, "w", encoding="utf-8") as f:
        f.write(llm_response)
            
# This function will be used to generate a narrative project charter utilizing LLM json response.
def generate_project_charter(llm_response, project_charter_path):
    logging.info("Generating project charter from LLM response...")
    print("Generating project charter from LLM response...")
    
    # Convert the JSON string to a Python dictionary
    llm_response_dict = json.loads(llm_response)
    
    # Extract the report values from the dictionary
    project_metadata=llm_response_dict.get("report_metadata","TBD")
    project_report=llm_response_dict.get("project_report","TBD")

    # Create the project charter text
    lines =[]
    
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
        logging.info(f"Saving project charter to {project_charter_path}")
        print(f"Saving project charter to {project_charter_path}")
        with open(project_charter_path, "w", encoding="utf-8") as f:
            f.write(project_charter)
               
# This function will be the entry point for the script.
def main():
    logging.info("Starting script...")
    print("Starting script...")

    # Define the file paths
    strategy_name = "strategy.pdf"
    strategy_filepath = Path("data") / strategy_name

    project_name = "project_notes.docx"
    project_filepath = Path("data") / project_name

    masterfile_name = "master_context.txt"
    masterfile_path = Path("data") / masterfile_name

    llm_response_name = "llm_response.json"
    llm_response_path = Path("data") / llm_response_name

    project_charter_name = "project_charter.txt"
    project_charter_path = Path("data") / project_charter_name
    
    # Build the master context
    master_context = build_master_context(strategy_filepath, project_filepath)

    if not master_context:
        logging.error("Failed to build master context. Exiting.")
        print("Failed to build master context. Exiting.")
        return
    logging.info("Master context built successfully.")
    print("Master context built successfully.")

    # Clean the master context
    master_context = clean_text(master_context)

    # Save the master context to a file
    save_master_context(master_context, masterfile_path)

    # Send the master context to the LLM
    llm_response = send_to_llm(master_context, api_key)

    # Save the LLM response to a json file
    save_llm_response(llm_response, llm_response_path)
    
    # Generate the project charter
    project_charter = generate_project_charter(llm_response, project_charter_path)

    # Save the project charter to a file
    save_project_charter(project_charter, project_charter_path)

    logging.info("Script completed successfully.")
    print("Script completed successfully.")

# Execute main() if this script is run directly
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        filename=log_folder / "app.log",
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    main()
