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


#Define global variables
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

# This function will route the file to the appropriate extraction function based on the file type.
def ingest_file(filepath):
    # Determine the file type
    if filepath.suffix == '.docx':
        return extract_from_docx(filepath)
    elif filepath.suffix == '.pdf':
        return extract_from_pdf(filepath)
    elif filepath.suffix == '.txt':
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
    """
    Harvests data from multiple sources and assembles a unified context payload.
    """
    try:
        # Harvest the raw data
        strategy_text = ingest_file(strategy_filepath)
        project_text = ingest_file(project_filepath)
        
        # Assemble the master context with clear structural markers
        # These markers help the LLM distinguish between the two sources
        master_context = f"""
        ### ROLE
        You are an expert Project Management Consultant with a deep understanding of corporate strategy alignment.

        ### CONTEXT
        Below is the Company Strategy and the specific Project Inputs.
        --- COMPANY STRATEGY ---
        {strategy_text}
        --- PROJECT INPUTS ---
        {project_text}

        ### TASK
        Create a professional Project Charter. Your output must meet the following criteria:

        1. STRATEGIC ALIGNMENT: For every Project Objective, create a section called "Strategic Rationale" that cites the specific company goal from the Strategy document that this objective supports.
        2. STRUCTURE: Use the following headings: Project Title, Executive Summary, Strategic Rationale, Project Purpose, Strategic Objectives, Key Deliverables, High-Level Requirements, Project Constraints, Project Assumptions, Schedule - Milestones, Success Criteria, High-Level Risks, Budget, and Stakeholders List.
        3. CONSTRAINTS: 
           - Keep all descriptions professional and concise.
           - If a specific input is missing (e.g., Budget), state "To be defined" rather than hallucinating a number.
           - Return the result in clean Markdown format.
        """
        
        return master_context
        
    except Exception as e:
        print(f"Error building master context: {e}")
        return None

# This function will be used to clean the text data before saving it to a file and sending it to the LLM.
def clean_text(text):
    # Remove extra whitespace and newlines
    text = " ".join(text.split())
    return text

# This function will be used to save the master context to a file.
def save_master_context(master_context, masterfile_path):
    with open(masterfile_path, "w", encoding="utf-8") as f:
        f.write(master_context)
        logging.info(f"Master context saved to {masterfile_path}")
        print(f"Master context saved to {masterfile_path}")
            
# This function will ne used to send the master context to the Gemini LLM
def send_to_llm(master_context):
    # Placeholder for the LLM integration code
    print("Sending to LLM...")
    print(master_context)
    return "LLM response"
    
# This function will be the entry point for the script.
def main():

    print ("Starting script...")
    
    # Define the file paths
    strategy_name = "strategy.pdf"
    strategy_filepath = Path("data")/strategy_name
    
    project_name = "project_notes.docx"
    project_filepath = Path("data")/project_name
    
    masterfile_name = "master_context.txt"
    masterfile_path = Path("data")/masterfile_name
    
    # Build the master context
    logging.info ("Building master context...")
    print(f"Building master context from {strategy_filepath} and {project_filepath}...")
    master_context = build_master_context(strategy_filepath, project_filepath)

    if master_context:
        logging.info("Master context built successfully.")
        print("Master context built successfully.")

    # Clean the master context
    logging.info("Cleaning master context...")
    print("Cleaning master context...")
    master_context = clean_text(master_context)

    # Save the master context to a file
    logging.info("Saving master context to file...")
    print("Saving master context to file...")
    save_master_context(master_context, masterfile_path)


    print ("Script completed successfully.")
    
        

# Execute main() if this script is run directly
if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, filename=log_folder/"app.log",
     format="%(asctime)s - %(levelname)s - %(message)s")
  main()



