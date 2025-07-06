from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig
from tools.google_search_tool import google_search
from tools.tavily_search_tool import tavily_search
from typing import List, Optional
import shutil
from dotenv import load_dotenv
import os
from fastapi import HTTPException
import allel  # For proper VCF parsing
import numpy as np
import pandas as pd

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

external_client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
model = OpenAIChatCompletionsModel(model="gemini-2.5-flash", openai_client=external_client)
run_config = RunConfig(model=model, model_provider=external_client, tracing_disabled=True)

def parse_vcf_comprehensive(file_path: str) -> List[dict]:
    """
    Comprehensive VCF parser using pandas that handles both standard fields and sample genotype data.
    Similar to the user's approach for parsing VCF files with sample data.
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
        
        # Determine column structure
        if len(df.columns) >= 8:
            # Standard VCF columns
            standard_cols = ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            
            # If we have more columns, they are FORMAT + sample columns
            if len(df.columns) > 8:
                format_col = "FORMAT"
                sample_cols = [f"SAMPLE_{i}" for i in range(len(df.columns) - 9)]  # -9 because we have 8 standard + 1 FORMAT
                all_cols = standard_cols + [format_col] + sample_cols
                print(f"Detected {len(sample_cols)} sample columns")
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
                    for entry in info_str.split(";"):
                        if entry.startswith("GENE="):
                            gene = entry.split("=", 1)[1]
                            break
                
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
                            # Extract genotype (first part before ':')
                            if ':' in sample_data:
                                genotype = sample_data.split(':')[0]
                            else:
                                genotype = sample_data
                            genotypes[sample_col] = genotype
                    
                    variant["genotypes"] = genotypes
                    
                    # Calculate genotype statistics
                    if genotypes:
                        genotype_counts = {}
                        for gt in genotypes.values():
                            genotype_counts[gt] = genotype_counts.get(gt, 0) + 1
                        variant["genotype_stats"] = genotype_counts
                
                results.append(variant)
                print(f"Parsed variant {idx+1}: {variant['chromosome']}:{variant['position']} {variant['gene']}")
            
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
            "When analyzing a variant, provide:\n"
            "1. Gene function and normal role in the body\n"
            "2. Disease associations and clinical significance\n"
            "3. Inheritance patterns if known\n"
            "4. Available treatments or management strategies\n"
            "5. Risk assessment and recommendations"
        ),
        tools=[google_search, tavily_search]
    )

async def annotate_with_search(variants: List[dict]) -> List[VariantInfo]:
    """Annotate variants using the agent and search tools."""
    try:
        enriched = []
        agent = get_agent()
        for i, var in enumerate(variants):
            print(f"Processing variant {i+1}: {var}")
            rsid_str = f"- rsID: {var['rsid']}\n" if var.get('rsid') and var['rsid'] not in ('.', '') else ''
            
            # Add genotype information if available
            genotype_str = ""
            if 'genotypes' in var and var['genotypes']:
                genotype_str = "\nGENOTYPE DATA:\n"
                for sample, genotype in var['genotypes'].items():
                    genotype_str += f"- {sample}: {genotype}\n"
                if 'genotype_stats' in var:
                    genotype_str += f"\nGenotype Statistics: {var['genotype_stats']}\n"
            
            # Create a more detailed query for better agent response
            query = f"""
            Analyze this genetic variant and provide comprehensive medical information:
            
            VARIANT DETAILS:
            - Gene: {var['gene']}
            - Chromosome: {var['chromosome']}
            - Position: {var['position']}
            - Reference allele: {var['reference']}
            - Alternate allele: {var['alternate']}
            {rsid_str}{genotype_str}
            REQUIRED ANALYSIS:
            1. Search for this specific gene and variant in medical databases
            2. Find disease associations and clinical significance
            3. Identify inheritance patterns and risk factors
            4. Look for treatment options and management strategies
            5. Provide evidence-based recommendations
            
            Please use your search tools to find accurate, up-to-date information about this genetic variant's medical implications.
            """
            print(f"Query for variant {i+1}: {query}")
            messages = [
                {"role": "system", "content": "You are a clinical geneticist assistant with expertise in genetic variant analysis. Your role is to analyze genetic variants and provide comprehensive, evidence-based information about disease associations, clinical significance, inheritance patterns, and medical implications. Always use your search tools to find accurate, up-to-date information from medical databases and scientific literature."},
                {"role": "user", "content": query}
            ]
            result = await Runner.run(
                agent, 
                input=messages, 
                run_config=run_config
            )
            print(f"Agent response for variant {i+1}: {result.final_output}")
            enriched.append(VariantInfo(
                chromosome=var["chromosome"],
                position=var["position"],
                rsid=var["rsid"],
                gene=var["gene"],
                reference=var["reference"],
                alternate=var["alternate"],
                search_summary=result.final_output
            ))
        print(f"Annotated {len(enriched)} variants successfully")
        return enriched
    except Exception as e:
        print(f"Error in annotate_with_search: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error annotating variants: {str(e)}")

async def _handle_chat_logic(chat, message, file, db):
    """Handle chat logic for both text and file input."""
    try:
        response_text = None
        last_user_content = None

        # Handle file upload
        if file is not None:
            try:
                file_path = f"uploads/{file.filename}"
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                print(f"File saved to: {file_path}")
                # Try comprehensive parsing first, fallback to basic parsing
                try:
                    variants = parse_vcf_comprehensive(file_path)
                except Exception as e:
                    print(f"Comprehensive parsing failed: {e}")
                    variants = parse_vcf(file_path)
                print(f"Variants from parse_vcf: {variants}")
                print(f"Number of variants: {len(variants)}")
                
                if not variants:
                    print("No variants found - raising error")
                    raise HTTPException(status_code=400, detail="No valid variants found in VCF file")
                
                print("Calling annotate_with_search...")
                summaries = await annotate_with_search(variants)
                print(f"Summaries returned: {len(summaries)}")
                
                # Create a more detailed summary
                summary_parts = []
                for i, v in enumerate(summaries):
                    part = f"Variant {i+1}:\n"
                    part += f"  Location: {v.chromosome}:{v.position}\n"
                    part += f"  rsID: {v.rsid}\n"
                    part += f"  Gene: {v.gene}\n"
                    part += f"  Change: {v.reference} → {v.alternate}\n"
                    part += f"  Analysis: {v.search_summary}\n"
                    summary_parts.append(part)
                
                summary_text = "\n".join(summary_parts)
                print("Summary Text -------------------", summary_text)
                
                # Save messages to database
                user_msg = models.Message(chat_id=chat.id, role="user", content=f"Uploaded VCF: {file.filename}")
                assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=summary_text)
                db.add_all([user_msg, assistant_msg])
                db.commit()
                
                response_text = summary_text
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

        # Auto-generate chat title if needed
        if chat.title == "New Chat" and last_user_content:
            try:
                title_rename_agent = Agent(name="Title renamer", instructions="Generate a short, clear title for this conversation.")
                title_result = await Runner.run(
                    starting_agent=title_rename_agent,
                    input=[{"role": "user", "content": last_user_content}],
                    run_config=run_config
                )
                new_title = title_result.final_output.strip().replace('"', '')
                chat.title = new_title
                db.commit()
            except Exception as e:
                print(f"[Warning] Failed to auto-generate title: {e}")

        # Return the chat history and title
        messages = db.query(models.Message).filter_by(chat_id=chat.id).order_by(models.Message.created_at.asc()).all()
        chat_history = [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages
        ]
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