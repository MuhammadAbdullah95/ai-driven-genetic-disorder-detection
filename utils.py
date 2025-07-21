from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig
from tools.google_search_tool import google_search
from tools.tavily_search_tool import tavily_search
from typing import List, Optional, Dict, Any
from json_convert import extract_json_from_markdown
import shutil
from dotenv import load_dotenv
import os
from fastapi import HTTPException
import allel  # For proper VCF parsing
import numpy as np
import pandas as pd
from fastapi import status
import datetime
import asyncio
import re
from tqdm.asyncio import tqdm_asyncio
import requests
import mimetypes
import json
from google import genai
from google.genai import types
import os
import shutil
import pathlib
from fastapi import HTTPException, status
# from google.generativeai import types
from PIL import Image # Import Pillow for image handling
import io # For handling image bytes



CONCURRENCY_LIMIT = 1  # Adjust based on your LLM/search rate limits
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


# Load environment variables
load_dotenv()

# For type hints
from sqlalchemy.orm import Session

# Import models
import app.models as models
from app.models import Message
from custom_types import VariantInfo

# Initialize the client and model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# openrouter_external_client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

external_client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=external_client)
# title_renamer_model = OpenAIChatCompletionsModel(model="mistralai/mistral-small-3.2-24b-instruct:free", openai_client=openrouter_external_client)
run_config = RunConfig(model=model, model_provider=external_client, tracing_disabled=True)
# chat_title_run_config = RunConfig(model=title_renamer_model, model_provider=openrouter_external_client, tracing_disabled=True)

client = genai.Client(api_key=GEMINI_API_KEY)


def extract_gene_from_ann(ann):
    """Extract gene name from annotation field."""
    if not ann:
        return "Unknown"
    # This is a simplified extraction - VCF annotation fields can be complex
    return str(ann).split("|")[3] if "|" in str(ann) else "Unknown"

def extract_genes_from_info(info, num_variants):
    """Extract gene information from INFO field."""
    genes = []
    for i in range(num_variants):
        gene = "Unknown"
        # Try to extract gene from various INFO field formats
        if 'GENE' in info:
            gene_val = info['GENE']
            if isinstance(gene_val, (list, np.ndarray)) and i < len(gene_val):
                gene = str(gene_val[i])
            else:
                gene = str(gene_val)
        genes.append(gene)
    return genes

def get_agent():
    """Get the configured agent for genetic disorder detection."""
    return Agent(
        name="Genetic Disorder Detector",
        instructions=(
            "You are a clinical geneticist assistant AI focused on genetic disorders and variant analysis. "
            "You have access to two search tools:\n"
            "1. 'tavily_search' — for scientific, gene-specific, mutation-level medical information from databases like ClinVar, OMIM, PubMed.\n"
            "2. 'google_search' — for broader context such as symptoms, patient-facing content, and public information.\n\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "- ALWAYS use the search tools to find information about the genetic variant provided.\n"
            "- Search for the specific gene name, variant position, and mutation details.\n"
            "- Look for disease associations, clinical significance, and reported risks.\n"
            "- Provide detailed, accurate information about the genetic variant's medical implications.\n"
            "- Use scientific terminology appropriately but explain in accessible language.\n"
            "- If no specific information is found, search for general information about the gene and its function.\n"
            "- Do not make up information - only report what you find through searches.\n\n"
            "When analyzing a variants, provide:\n"
            "1. Gene function and normal role in the body\n"
            "2. Disease associations and clinical significance\n"
            "3. Inheritance patterns if known\n"
            "4. Available treatments or management strategies\n"
            "5. Risk assessment and recommendations"
        ),
        tools=[google_search, tavily_search]
    )

def get_diet_planner_agent():
    """Get the configured agent for diet planning."""
    return Agent(
        name="Diet Planner Assistant",
        instructions=(
            "You are a professional nutritionist and diet planner AI assistant. "
            "You have access to two search tools:\n"
            "1. 'tavily_search' — for scientific nutrition research, dietary guidelines, and medical nutrition information.\n"
            "2. 'google_search' — for current dietary trends, recipes, and practical nutrition advice.\n\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "- ALWAYS use the search tools to find current, evidence-based nutrition information.\n"
            "- Consider individual health conditions, preferences, and dietary restrictions.\n"
            "- Provide personalized meal plans and dietary recommendations.\n"
            "- Include nutritional analysis and health benefits of recommended foods.\n"
            "- Consider cultural preferences and accessibility of ingredients.\n"
            "- Provide practical cooking tips and meal preparation advice.\n"
            "- Do not make up information - only report what you find through searches.\n\n"
            "When creating diet plans, provide:\n"
            "1. Personalized meal recommendations based on user needs\n"
            "2. Nutritional breakdown and health benefits\n"
            "3. Shopping lists and ingredient suggestions\n"
            "4. Meal preparation tips and cooking instructions\n"
            "5. Dietary considerations for specific health conditions\n"
            "6. Alternative options for dietary restrictions\n"
            "7. Weekly meal planning strategies"
        ),
        tools=[google_search, tavily_search]
    )

async def analyze_blood_report_with_gemini(image_path: str) -> Dict[str, Any]:
    """
    Analyzes a blood report image using Gemini's vision capabilities.
    Extracts key parameters and provides an interpretation.
    """
    if not os.path.exists(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image file not found at '{image_path}'")
    
    prompt_parts = """Analyze this blood report image. Extract the following information in a structured JSON format:,
            - Patient Name (if visible, otherwise 'N/A'),
            - Date of Report (if visible, otherwise 'N/A'),
            - For each test result (e.g., Hemoglobin, WBC, Platelets, Glucose, Cholesterol, etc.):,
              - Test Name,
              - Value,
              - Units (if available),
              - Reference Range (if available, e.g., 'X - Y'),
              - Status (e.g., 'Normal', 'High', 'Low', 'Borderline' - infer if not explicitly stated by comparing value to reference range),
            After the JSON, provide a concise medical interpretation of any abnormal or borderline values, explaining their potential implications. If all values are normal, state that. Focus on common blood markers.""",
        
    try:

        my_file = client.files.upload(file=image_path)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[my_file, prompt_parts],
            )

        print(response.text)
        full_response_text = response.text
        json_part_match = re.search(r'```json\n(.*)\n```', full_response_text, re.DOTALL)
        
        extracted_json_data = {}
        if json_part_match:
            try:
                extracted_json_data = json.loads(json_part_match.group(1))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from Gemini response: {e}")
                print(f"Problematic JSON string:\n{json_part_match.group(1)}")
        
        interpretation_start_index = full_response_text.find("```json")
        interpretation = full_response_text
        if json_part_match:
            # If JSON was found, interpretation is everything after the JSON block
            interpretation = full_response_text[json_part_match.end():].strip()
        
        return {
            "structured_data": extracted_json_data,
            "interpretation": interpretation
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error analyzing blood report with Gemini: {str(e)}")


async def analyze_blood_pdf_report_with_gemini(file_path: str) -> Dict[str, Any]:
    """
    Analyzes a blood report image using Gemini's vision capabilities.
    Extracts key parameters and provides an interpretation.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"pdf file not found at '{file_path}'")
    
    prompt_parts = """Analyze this blood report pdf. Extract the following information in a structured JSON format:,
            - Patient Name (if visible, otherwise 'N/A'),
            - Date of Report (if visible, otherwise 'N/A'),
            - For each test result (e.g., Hemoglobin, WBC, Platelets, Glucose, Cholesterol, etc.):,
              - Test Name,
              - Value,
              - Units (if available),
              - Reference Range (if available, e.g., 'X - Y'),
              - Status (e.g., 'Normal', 'High', 'Low', 'Borderline' - infer if not explicitly stated by comparing value to reference range),
            After the JSON, provide a concise medical interpretation of any abnormal or borderline values, explaining their potential implications. If all values are normal, state that. Focus on common blood markers.""",
        
    try:

        filepath = pathlib.Path(file_path)

        prompt = "Summarize this document"
        response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                types.Part.from_bytes(
                data=filepath.read_bytes(),
             mime_type='application/pdf',
            ),
        prompt_parts])
        print(response.text)
        full_response_text = response.text
        json_part_match = re.search(r'```json\n(.*)\n```', full_response_text, re.DOTALL)
        
        extracted_json_data = {}
        if json_part_match:
            try:
                extracted_json_data = json.loads(json_part_match.group(1))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from Gemini response: {e}")
                print(f"Problematic JSON string:\n{json_part_match.group(1)}")
        
        interpretation_start_index = full_response_text.find("```json")
        interpretation = full_response_text
        if json_part_match:
            # If JSON was found, interpretation is everything after the JSON block
            interpretation = full_response_text[json_part_match.end():].strip()
        
        return {
            "structured_data": extracted_json_data,
            "interpretation": interpretation
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error analyzing blood report with Gemini: {str(e)}")



async def annotate_with_search(variants: List[dict], user_message: str = None) -> List[VariantInfo]:
    """Annotate variants safely under rate limits using concurrency control and backoff."""
    try:
        agent = get_agent()

        async def process_variant(i: int, var: dict) -> VariantInfo:
            async with semaphore:
                print(f"Processing variant {i+1}: {var}")
                rsid_str = f"- rsID: {var['rsid']}\n" if var.get('rsid') and var['rsid'] not in ('.', '') else ''

                genotype_str = ""
                if 'genotypes' in var and var['genotypes']:
                    genotype_str = "\nGENOTYPE DATA:\n"
                    for sample, genotype_data in var['genotypes'].items():
                        if isinstance(genotype_data, dict):
                            genotype_str += f"- {sample}: {genotype_data['genotype']} (Depth: {genotype_data['depth']})\n"
                        else:
                            genotype_str += f"- {sample}: {genotype_data}\n"
                    if 'genotype_stats' in var:
                        genotype_str += f"\nGenotype Statistics: {var['genotype_stats']}\n"

                user_note = f"\n\nUSER NOTE:\n{user_message}\n" if user_message else ""

                query = f"""
                Analyze this genetic variant and provide comprehensive medical information:

                VARIANT DETAILS:
                - Gene: {var['gene']}
                - Chromosome: {var['chromosome']}
                - Position: {var['position']}
                - Reference allele: {var['reference']}
                - Alternate allele: {var['alternate']}
                {rsid_str}{genotype_str}{user_note}
                REQUIRED ANALYSIS:
                1. Search for this specific gene and variant in medical databases
                2. Find disease associations and clinical significance
                3. Identify inheritance patterns and risk factors
                4. Look for treatment options and management strategies
                5. Provide evidence-based recommendations
                """

                messages = [
                    {"role": "system", "content": "You are a clinical geneticist assistant..."},
                    {"role": "user", "content": query}
                ]

                await asyncio.sleep(7)  # Respect Gemini 10 RPM free tier
                try:
                    result = await Runner.run(agent, input=messages, run_config=run_config)
                except Exception as e:
                    if "429" in str(e):
                        retry_delay = extract_retry_delay(str(e)) or 24
                        print(f"[429] Rate limit hit. Retrying after {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        result = await Runner.run(agent, input=messages, run_config=run_config)
                    else:
                        raise

                return VariantInfo(
                    chromosome=var["chromosome"],
                    position=var["position"],
                    rsid=var.get("rsid", ""),
                    gene=var["gene"],
                    reference=var["reference"],
                    alternate=var["alternate"],
                    search_summary=result.final_output
                )

        tasks = [process_variant(i, var) for i, var in enumerate(variants)]
        enriched = await tqdm_asyncio.gather(*tasks, desc="Annotating Variants", total=len(tasks))
        return enriched

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Annotation failed: {str(e)}")
def extract_retry_delay(error_msg: str) -> int:
    """Extract retry delay in seconds from Gemini 429 error message if available."""
    match = re.search(r"'retryDelay': '(\d+)s'", error_msg)
    if match:
        return int(match.group(1))
    return None
async def _handle_chat_logic(chat, message, file, db):
    """Handle chat logic for both text and file input."""
    try:
        response_text = None
        last_user_content = None

        # Handle file upload
        if file is not None:
            try:
                # Use unified VCF processing function
                result = await process_vcf_file(file, db, None, create_chat=False, user_message=message)
                
                # Save messages to database using the existing chat
                combined_content = f"Uploaded VCF: {file.filename}"
                if message and message.strip():
                    combined_content += f"\n\nUser note:\n{message.strip()}"

                user_msg = models.Message(chat_id=chat.id, role="user", content=combined_content)

                # user_msg = models.Message(chat_id=chat.id, role="user", content=f"Uploaded VCF: {file.filename}")
                assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=result["summary_text"])
                db.add_all([user_msg, assistant_msg])
                db.commit()
                
                response_text = result["summary_text"]
                last_user_content = f"Uploaded VCF: {file.filename}"
            except Exception as e:
                print(f"Error in file processing: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing VCF file: {str(e)}")

        # Handle text message
        if message is not None and message.strip():
            try:
                user_msg = models.Message(chat_id=chat.id, role="user", content=message.strip())
                db.add(user_msg)
                db.commit()
                db.refresh(user_msg)
                
                # Get chat history for context
                history = db.query(models.Message).filter_by(chat_id=chat.id).order_by(models.Message.created_at.asc()).all()
                chat_history = [{"role": m.role, "content": m.content} for m in history]
                
                print(f"Chat history for agent: {chat_history}")
                
                # Choose agent based on chat type
                if hasattr(chat, 'chat_type') and chat.chat_type == 'diet_planner':
                    agent = get_diet_planner_agent()
                    tips_section = (
                        "---\n"
                        "**Tips:**\n"
                        "- Share your dietary preferences and restrictions.\n"
                        "- Ask for meal plans, recipes, or nutrition advice! 🥗\n"
                    )
                else:
                    agent = get_agent()
                    tips_section = (
                        "---\n"
                        "**Tips:**\n"
                        "- You can upload a VCF file for detailed analysis.\n"
                        "- Ask follow-up questions for more insights! 🧬\n"
                    )
                
                result = await Runner.run(
                    starting_agent=agent,
                    input=chat_history,
                    run_config=run_config
                )
                bot_reply = result.final_output or "🤖 (no reply generated)"
                
                # Enhance formatting for beautiful output
                if not bot_reply.strip().startswith("### 🤖 Assistant Response"):
                    bot_reply = f"### 🤖 Assistant Response\n\n" + bot_reply
                bot_reply = f"{bot_reply}\n\n{tips_section}"
                
                print(f"Agent response: {bot_reply}")
                
                assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=bot_reply)
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)
                
                response_text = bot_reply
                last_user_content = message.strip()
            except Exception as e:
                print(f"Error in text processing: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

        if not message and not file:
            raise HTTPException(status_code=400, detail="You must provide either a message or a VCF file.")

        # Auto-generate chat title if needed, but skip for greetings
        greetings = {"hi", "hello", "greetings", "hey", "good morning", "good evening", "good afternoon", "yo", "sup", "hola"}
        if chat.title == "New Chat" or chat.title == "Diet Planner Chat" and last_user_content:
            msg_lower = last_user_content.strip().lower()
            if msg_lower not in greetings and response_text:
                try:
                    title_input = []
                    if last_user_content:
                        title_input.append({"role": "user", "content": last_user_content})
                    if response_text:
                        title_input.append({"role": "assistant", "content": response_text})
                    print(f"[ChatTitle] Sending to LLM for title: {title_input}")
                    title_input_text = "\n".join(
                        f"{msg['role'].capitalize()}: {msg['content']}" for msg in title_input
                    )
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction="Based on the entire conversation content, generate a short, clear, and context-aware title that summarizes the main purpose or topic of the discussion. The title should be concise (3–8 words), informative, and user-friendly."),
                        contents=title_input_text
                    )
                    print("Tilte response from gemini.... ", response.text)
                    title_result = response.text
                    print(f"[ChatTitle] LLM raw output: {repr(title_result)}")
                    new_title = title_result.strip().replace('"', '')
                    if not new_title:
                        print("[ChatTitle] LLM returned empty title, using fallback 'Untitled Chat'")
                        new_title = "Untitled Chat"
                    chat.title = new_title
                    db.commit()
                    print(f"[ChatTitle] Final chat title set: {chat.title}")
                except Exception as e:
                    print(f"[ChatTitle][Error] Failed to auto-generate title: {e}")

        # Return the chat history and title
        messages = db.query(models.Message).filter_by(chat_id=chat.id).order_by(models.Message.created_at.asc()).all()
        chat_history = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "formatted_time": m.created_at.strftime('%b %d, %Y %H:%M') if isinstance(m.created_at, datetime.datetime) else str(m.created_at)
            }
            for m in messages
        ]
        # Log the formatted assistant response (text)
        if response_text:
            print(f"[LOG] Assistant response (text):\n{response_text}\n---")
        # Log the formatted VCF summary text
        if file is not None and response_text:
            print(f"[LOG] VCF summary text:\n{response_text}\n---")
        # Log the chat history output
        print(f"[LOG] Chat history output: {chat_history}")
        return {
            "session_id": str(chat.id),
            "response": response_text,
            "chat_history": chat_history,
            "chat_title": chat.title
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in _handle_chat_logic: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

async def process_vcf_file(file, db, user, create_chat=True, chat_title_prefix="Analysis", user_message=None):
    """
    Unified file processing function using Gemini for analysis. All DB/chat logic remains, but VCF parsing/annotation is commented out.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A file must be provided."
            )
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved: {file_path}")

        # --- Gemini-based file analysis ---

        
        analysis_result = analyze_file_with_gemini(file_path)
        # print("Analysis Result from gemini:  ", analysis_result)
        print(f"Gemini analysis result: {analysis_result}")
        if analysis_result:
            try:
                # Now, parse the cleaned JSON string into a Python list of dictionaries
                python_data = json.loads(analysis_result)

                print("Successfully extracted and converted JSON string to Python list of dictionaries:")
                print(python_data)

                # Example: Accessing data
                print(f"\nFirst variant ID: {python_data[0]['ID']}")
                print(f"Second variant Gene: {python_data[1]['Gene']}")

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON after cleaning: {e}")
                print(f"Problematic JSON string:\n{analysis_result}")
            except Exception as e:
                print(f"An unexpected error occurred during conversion: {e}")
        else:
            print("Could not extract valid JSON from the Markdown string.")
        # Always annotate with Gemini result before branching
        summaries = await annotate_with_search(python_data, user_message=user_message)

        # Create or get chat for storage
        chat = None
        if create_chat:
            chat = db.query(models.Chat).filter_by(user_id=user.id).order_by(models.Chat.created_at.desc()).first()
            if not chat:
                chat = models.Chat(user_id=user.id, title=f"{chat_title_prefix}: {file.filename}")
                db.add(chat)
                db.commit()
                db.refresh(chat)
        # Store analysis if chat exists
        if chat:
            user_msg = models.Message(chat_id=chat.id, role="user", content=f"Analyze file: {file.filename}")
            db.add(user_msg)
            summary_text = (
               "## 🧬 Variant Analysis Summary\n\n"
                "| Chromosome | Position | Gene | Change | Insight |\n"
                "|---|---|---|---|---|\n" +
                "\n".join([
                    f"| `{v.chromosome}` | `{v.position}` | **{v.gene}** | `{v.reference}`→`{v.alternate}` | {v.search_summary} |"
                    for v in summaries
                ]) +
                "\n\n---\n"
                "For more details, upload another file or ask a question! 😊"
            )
            assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=summary_text)
            db.add(assistant_msg)
            db.commit()
        else:
            summary_text = (
                "## 📄 File Analysis Summary\n\n"
                "| Chromosome | Position | Gene | Change | Insight |\n"
                "|---|---|---|---|---|\n" +
                "\n".join([
                    f"| `{getattr(v, 'chromosome', getattr(v, 'CHROM', ''))}` "
                    f"| `{getattr(v, 'position', getattr(v, 'POS', ''))}` "
                    f"| **{getattr(v, 'gene', getattr(v, 'GENE', ''))}** "
                    f"| `{getattr(v, 'reference', getattr(v, 'REF', ''))}`→`{getattr(v, 'alternate', getattr(v, 'ALT', ''))}` "
                    f"| {getattr(v, 'search_summary', '')} |"
                    for v in summaries
                ]) +
                "\n\n---\n"
                "For more details, upload another file or ask a question! 😊"
            )
        return {
            "chat_id": str(chat.id) if chat else None,
            "variants_analyzed": None,  # Not applicable
            "results": None,            # Not applicable
            "summary_text": summary_text
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in process_vcf_file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )

def analyze_file_with_gemini(file_path):
    """
    Analyzes the content of a given file using the Gemini API.
    Args:
        file_path (str): The path to the file to be analyzed.
    Returns:
        str: The analysis result from Gemini or an error message.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'"
    mime_type, _ = mimetypes.guess_type(file_path)
    file_name = os.path.basename(file_path)
    extracted_content = None
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            extracted_content = f.read()
        is_text_file = True
    except UnicodeDecodeError:
        is_text_file = False
        print(f"Warning: '{file_name}' appears to be a binary file or has a non-UTF-8 encoding. Direct text extraction might be incomplete or fail.")
        with open(file_path, 'rb') as f:
            extracted_content = f.read()
            extracted_content = extracted_content.decode('latin-1', errors='ignore')
    prompt = ""
    content_to_send = extracted_content
    if (mime_type and 'vcf' in mime_type) or file_name.lower().endswith('.vcf'):
        prompt = "Analyze the following VCF file content and extract all variant information. For each variant, list the chromosome, position, rsid, reference, alternate, gene, and genotypes{'SAMPLE1': '0/1','SAMPLE2': '1/1'} . return the information in pure JSON format. only json no additional text or information like (Here is json file, Gemini analysis etc) only return JSON."
    elif (mime_type and 'csv' in mime_type) or file_name.lower().endswith('.csv'):
        prompt = "Parse the following CSV data. List each row and its corresponding columns. If headers are present, use them to label the data. Present as a list of key-value pairs or a table in plain text."
    elif (mime_type and 'json' in mime_type) or file_name.lower().endswith('.json'):
        prompt = "Extract all key-value pairs and nested structures from the following JSON data. Present the information as a flat list or a well-indented text representation, focusing on the human-readable content."
    elif (mime_type and 'xml' in mime_type) or file_name.lower().endswith('.xml'):
        prompt = "Extract all elements and their attributes/content from the following XML data. Present the information in a clear, readable text format."
    elif mime_type and mime_type.startswith('text/'):
        prompt = "Analyze the following text file content and provide a summary of its key information, or extract any structured data you find."
    else:
        if is_text_file:
            prompt = "Analyze the following file content and provide a summary of its key information, or extract any structured data you find."
        else:
            return f"File type '{mime_type or 'unknown'}' ({file_name}) is a binary file. For comprehensive analysis, text extraction from binary files (like PDFs, DOCX, XLSX, images for OCR) typically requires specialized Python libraries (e.g., PyPDF2, python-docx, Tesseract) for pre-processing before sending the text to an AI model."
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY is not set. Please set it as an environment variable or replace the placeholder.")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"text": content_to_send}
                ]
            }
        ] 
    }
    print(f"Analyzing '{file_name}' (MIME type: {mime_type})...")
    print(f"Prompting Gemini with: \n{prompt[:100]}...\nContent snippet: \n{content_to_send[:200]}...")
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result and 'candidates' in result and len(result['candidates']) > 0 and \
           'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content'] and \
           len(result['candidates'][0]['content']['parts']) > 0:
            data_to_json = result['candidates'][0]['content']['parts'][0]['text']
            print("Gemini data without parsing:::", data_to_json)
            extracted_json_data = extract_json_from_markdown(data_to_json)
            return extracted_json_data
        else:
            return f"Gemini API did not return expected content. Response structure: {json.dumps(result, indent=2)}"
    except requests.exceptions.RequestException as e:
        return f"Error communicating with Gemini API: {e}"
    except json.JSONDecodeError:
        return f"Error decoding JSON response from Gemini API: {response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {e}" 



async def process_blood_report_file(file, db, user, chat_title_prefix="Blood Report Analysis", user_message=None, chat_title=None):
    """
    Processes an uploaded blood report image file using Gemini for analysis.
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A file must be provided."
            )

        # Validate image file types
        allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'application/pdf']
        mime_type = file.content_type
        if mime_type not in allowed_image_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}. Only JPEG, PNG, GIF, BMP, TIFF images are allowed for blood reports."
            )

        # Save file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"Blood report file saved: {file_path}")

        # Analyze with Gemini Vision
        if mime_type == 'application/pdf':
            gemini_analysis_results = await analyze_blood_pdf_report_with_gemini(file_path)
            structured_data = gemini_analysis_results["structured_data"]
            interpretation = gemini_analysis_results["interpretation"]
        else:
            gemini_analysis_results = await analyze_blood_report_with_gemini(file_path)
            structured_data = gemini_analysis_results["structured_data"]
            interpretation = gemini_analysis_results["interpretation"]

        # Always create a new chat for each blood report upload
        chat_title_final = chat_title or f"{chat_title_prefix}: {file.filename}"
        chat = models.Chat(user_id=user.id, title=chat_title_final, chat_type="blood_report")
        db.add(chat)
        db.commit()
        db.refresh(chat)

        user_content = f"Uploaded blood report image: {file.filename}"
        if user_message:
            user_content += f"\n\nUser note: {user_message}"

        user_msg = models.Message(chat_id=chat.id, role="user", content=user_content)
        db.add(user_msg)

        # Format the structured data for display
        formatted_structured_data = "### 📋 Blood Test Results\n\n"
        if structured_data:
            for key, value in structured_data.items():
                if isinstance(value, list):
                    formatted_structured_data += f"**{key.replace('_', ' ').title()}:**\n"
                    for item in value:
                        if isinstance(item, dict):
                            formatted_structured_data += " - " + ", ".join([f"{k}: {v}" for k, v in item.items()]) + "\n"
                        else:
                            formatted_structured_data += f" - {item}\n"
                else:
                    formatted_structured_data += f"**{key.replace('_', ' ').title()}:** {value}\n"
        else:
            formatted_structured_data += "No structured data extracted.\n"
        
        # Combine structured data and interpretation for the assistant's response
        assistant_response_content = f"{formatted_structured_data}\n\n### 💡 Interpretation\n\n{interpretation}"
        
        # Add tips for the user specific to blood reports
        assistant_response_content += (
            "\n\n---\n"
            "**Tips:**\n"
            "- Remember, this is an AI interpretation and should not replace professional medical advice. Always consult a doctor for diagnosis and treatment.\n"
            "- You can ask follow-up questions about specific markers or general health advice! 🩺\n"
        )


        assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=assistant_response_content)
        db.add(assistant_msg)
        db.commit()

        return {
            "chat_id": str(chat.id),
            "summary_text": assistant_response_content,
            "structured_data": structured_data,
            "interpretation": interpretation
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in process_blood_report_file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing blood report file: {str(e)}"
        )