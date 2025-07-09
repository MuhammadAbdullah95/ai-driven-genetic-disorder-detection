from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig
from tools.google_search_tool import google_search
from tools.tavily_search_tool import tavily_search
from typing import List, Optional
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

def parse_vcf_comprehensive(file_path: str) -> List[dict]:
    """
    Comprehensive VCF parser using pandas that handles both standard fields and sample genotype data.
    Updated to properly handle the sample VCF format with proper column names and genotype parsing.
    """
    try:
        print(f"Parsing VCF comprehensively with pandas: {file_path}")
        
        # Find the header line (starts with #CHROM)
        with open(file_path) as f:
            for i, line in enumerate(f):
                if line.startswith("#CHROM"):
                    header_line = i
                    break
            else:
                raise ValueError("No #CHROM header found in VCF file.")
        
        # Read the VCF into a DataFrame with all columns
        df = pd.read_csv(
            file_path,
            sep='\t',
            comment='#',
            header=None,
            skiprows=header_line
        )
        
        print(f"VCF DataFrame shape: {df.shape}")
        print(f"VCF DataFrame columns: {len(df.columns)}")
        
        # Determine column structure based on the sample VCF format
        if len(df.columns) >= 8:
            # Standard VCF columns
            standard_cols = ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            
            # If we have more columns, they are FORMAT + sample columns
            if len(df.columns) > 8:
                format_col = "FORMAT"
                # For the sample VCF, we have exactly one sample column named "SAMPLE1"
                sample_cols = ["SAMPLE1"] if len(df.columns) == 10 else [f"SAMPLE_{i}" for i in range(len(df.columns) - 9)]
                all_cols = standard_cols + [format_col] + sample_cols
                print(f"Detected {len(sample_cols)} sample columns: {sample_cols}")
            else:
                all_cols = standard_cols
                format_col = None
                sample_cols = []
            
            # Set column names
            df.columns = all_cols[:len(df.columns)]
            print(f"Column names: {list(df.columns)}")
            
            # Parse variants
            results = []
            for idx, row in df.iterrows():
                # Extract standard fields
                gene = "Unknown"
                info_str = str(row["INFO"])
                if not pd.isna(info_str) and info_str != 'nan':
                    # Try to extract gene from various INFO field formats
                    for entry in info_str.split(";"):
                        if entry.startswith("GENE="):
                            gene = entry.split("=", 1)[1]
                            break
                        # For the sample VCF, we don't have GENE field, so keep as "Unknown"
                
                # Handle NaN values
                pos = row["POS"]
                if pd.isna(pos):
                    print(f"Warning: Skipping variant with NaN position at row {idx}")
                    continue
                
                variant = {
                    "chromosome": str(row["CHROM"]),
                    "position": int(pos),
                    "rsid": str(row["ID"]) if not pd.isna(row["ID"]) else ".",
                    "gene": gene,
                    "reference": str(row["REF"]) if not pd.isna(row["REF"]) else ".",
                    "alternate": str(row["ALT"]) if not pd.isna(row["ALT"]) else ".",
                    "quality": str(row["QUAL"]) if not pd.isna(row["QUAL"]) else ".",
                    "filter": str(row["FILTER"]) if not pd.isna(row["FILTER"]) else ".",
                    "info": info_str,
                }
                
                # Extract genotype data if available
                if format_col and format_col in df.columns:
                    format_str = str(row[format_col]) if not pd.isna(row[format_col]) else ""
                    variant["format"] = format_str
                    
                    # Parse sample genotypes
                    genotypes = {}
                    for sample_col in sample_cols:
                        if sample_col in df.columns:
                            sample_data = str(row[sample_col]) if not pd.isna(row[sample_col]) else "./."
                            # Extract genotype (first part before ':') and depth
                            if ':' in sample_data:
                                parts = sample_data.split(':')
                                genotype = parts[0]  # GT part (e.g., "0/1")
                                depth = parts[1] if len(parts) > 1 else "0"  # DP part (e.g., "20")
                                genotypes[sample_col] = {
                                    "genotype": genotype,
                                    "depth": depth,
                                    "raw": sample_data
                                }
                            else:
                                genotypes[sample_col] = {
                                    "genotype": sample_data,
                                    "depth": "0",
                                    "raw": sample_data
                                }
                    
                    variant["genotypes"] = genotypes
                    
                    # Calculate genotype statistics
                    if genotypes:
                        genotype_counts = {}
                        for sample_data in genotypes.values():
                            gt = sample_data["genotype"]
                            genotype_counts[gt] = genotype_counts.get(gt, 0) + 1
                        variant["genotype_stats"] = genotype_counts
                
                results.append(variant)
                print(f"Parsed variant {idx+1}: {variant['chromosome']}:{variant['position']} {variant['gene']} - Genotypes: {variant.get('genotypes', {})}")
            
            print(f"Comprehensive parsing completed. Total variants found: {len(results)}")
            return results
        else:
            raise ValueError(f"VCF file has insufficient columns: {len(df.columns)} (need at least 8)")
            
    except Exception as e:
        print(f"Error in comprehensive VCF parsing: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Falling back to basic parsing...")
        return parse_vcf(file_path)

def parse_vcf(file_path: str) -> List[dict]:
    """Parse a VCF file using pandas, extracting key fields and gene info. Fallback to manual parsing if pandas fails."""
    try:
        print(f"Parsing VCF file with pandas: {file_path}")
        # Find the header line (starts with #CHROM)
        with open(file_path) as f:
            for i, line in enumerate(f):
                if line.startswith("#CHROM"):
                    header_line = i
                    break
            else:
                raise ValueError("No #CHROM header found in VCF file.")
        
        # Try tab-separated first, then space-separated
        for separator in ['\t', ' ']:
            try:
                print(f"Trying separator: {repr(separator)}")
                df = pd.read_csv(
                    file_path,
                    sep=separator,
                    comment='#',
                    header=None,
                    skiprows=header_line,
                    names=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"],
                    skipinitialspace=True
                )
                
                # Check if we got the right number of columns
                if len(df.columns) >= 8:
                    print(f"Successfully parsed with separator: {repr(separator)}")
                    break
            except Exception as e:
                print(f"Failed with separator {repr(separator)}: {e}")
                continue
        else:
            raise ValueError("Could not parse VCF with any separator")
        
        results = []
        for _, row in df.iterrows():
            # Handle NaN values
            pos = row["POS"]
            if pd.isna(pos):
                print(f"Warning: Skipping variant with NaN position: {row}")
                continue
                
            gene = "Unknown"
            info_str = str(row["INFO"])
            if not pd.isna(info_str) and info_str != 'nan':
                for entry in info_str.split(";"):
                    if entry.startswith("GENE="):
                        gene = entry.split("=", 1)[1]
                        break
            
            results.append({
                "chromosome": str(row["CHROM"]),
                "position": int(pos),
                "rsid": str(row["ID"]) if not pd.isna(row["ID"]) else ".",
                "gene": gene,
                "reference": str(row["REF"]) if not pd.isna(row["REF"]) else ".",
                "alternate": str(row["ALT"]) if not pd.isna(row["ALT"]) else ".",
            })
        print(f"Parsed {len(results)} variants using pandas.")
        return results
    except Exception as e:
        print(f"Error parsing VCF with pandas: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Falling back to manual parsing...")
        return parse_vcf_manual(file_path)

def parse_vcf_manual(file_path: str) -> List[dict]:
    """Fallback manual VCF parsing (tab-separated, robust)."""
    try:
        results = []
        print(f"Manual parsing VCF file: {file_path}")
        with open(file_path, 'r') as f:
            lines = f.readlines()
            print(f"Total lines read from file: {len(lines)}")
            for i, line in enumerate(lines):
                print(f"Processing line {i+1}: '{line.strip()}'")
                if line.startswith("#"):
                    print(f"Line {i+1}: Skipping header line")
                    continue
                # Try tab-separated first, then space-separated
                fields = None
                for separator in ['\t', ' ']:
                    test_fields = line.rstrip().split(separator)
                    # Remove empty fields that might occur with multiple spaces
                    test_fields = [f for f in test_fields if f.strip()]
                    if len(test_fields) >= 8:
                        fields = test_fields
                        print(f"Line {i+1}: Successfully split with separator {repr(separator)} into {len(fields)} fields")
                        break
                
                if not fields or len(fields) < 8:
                    print(f"Line {i+1}: Skipping - only {len(fields) if fields else 0} fields (need 8)")
                    continue
                chrom, pos, rsid, ref, alt, qual, filt, info = fields[:8]
                print(f"Line {i+1}: Parsed fields - CHROM: '{chrom}', POS: '{pos}', RSID: '{rsid}', REF: '{ref}', ALT: '{alt}', INFO: '{info}'")
                gene = "Unknown"
                for entry in info.split(";"):
                    if entry.startswith("GENE="):
                        gene = entry.split("=", 1)[1]
                        print(f"Line {i+1}: Found gene: {gene}")
                variant = {
                    "chromosome": chrom,
                    "position": int(pos),
                    "rsid": rsid,
                    "gene": gene,
                    "reference": ref,
                    "alternate": alt,
                }
                results.append(variant)
                print(f"Line {i+1}: Added variant: {variant}")
        print(f"Manual parsing completed. Total variants found: {len(results)}")
        return results
    except Exception as e:
        print(f"Error in manual parse_vcf: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error parsing VCF file: {str(e)}")

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
                
                result = await Runner.run(
                    starting_agent=get_agent(),
                    input=chat_history,
                    run_config=run_config
                )
                bot_reply = result.final_output or "🤖 (no reply generated)"
                
                # Enhance formatting for beautiful output
                bot_reply = (
                    f"### 🤖 Assistant Response\n\n"
                    f"{bot_reply}\n\n"
                    "---\n"
                    "**Tips:**\n"
                    "- You can upload a VCF file for detailed analysis.\n"
                    "- Ask follow-up questions for more insights! 🧬\n"
                )
                
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
        if chat.title == "New Chat" and last_user_content:
            msg_lower = last_user_content.strip().lower()
            if msg_lower not in greetings and response_text:
                try:
                    # title_rename_agent = Agent(name="Title renamer", instructions="Based on the entire conversation content, generate a short, clear, and context-aware title that summarizes the main purpose or topic of the discussion. The title should be concise (3–8 words), informative, and user-friendly..")
                    # Pass both user message and assistant response for better context
                    title_input = []
                    if last_user_content:
                        title_input.append({"role": "user", "content": last_user_content})
                    if response_text:
                        title_input.append({"role": "assistant", "content": response_text})
                    print(f"[ChatTitle] Sending to LLM for title: {title_input}")
                    # response = requests.post(
                    #             url=f"https://openrouter.ai/api/v1/chat/completions",
                    #             headers={
                    #                 "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    #             },
                    #             data=json.dumps({
                    #                 "model": "mistralai/mistral-small-3.2-24b-instruct:free",
                    #                 "messages": [
                    #                 {
                    #                     "role": "system",
                    #                     "content": "Based on the entire conversation content, generate a short, clear, and context-aware title that summarizes the main purpose or topic of the discussion. The title should be concise (3–8 words), informative, and user-friendly.",
                    #                 }, 
                    #                 {    "role": "user",
                    #                     "content": title_input
                    #                 }
                    #                 ]
                    #             })
                    #             )
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
                    # data = response.json()
                    # data['choices'][0]['message']['content']
                    title_result = response.text
                    # title_result = await Runner.run(
                    #     starting_agent=title_rename_agent,
                    #     input=title_input,
                    #     run_config=chat_title_run_config
                    # )
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