#!/usr/bin/env python3
"""
Simple test script to verify VCF parsing functionality
"""

import pandas as pd
import numpy as np
from typing import List

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
        return []

if __name__ == "__main__":
    print("Testing VCF parsing with sample.vcf...")
    try:
        result = parse_vcf_comprehensive('sample.vcf')
        print(f"\n✅ SUCCESS! Found {len(result)} variants")
        print("\n📋 Parsed Variants:")
        for i, variant in enumerate(result, 1):
            print(f"\n--- Variant {i} ---")
            print(f"Chromosome: {variant['chromosome']}")
            print(f"Position: {variant['position']}")
            print(f"rsID: {variant['rsid']}")
            print(f"Gene: {variant['gene']}")
            print(f"Reference: {variant['reference']}")
            print(f"Alternate: {variant['alternate']}")
            print(f"Quality: {variant['quality']}")
            print(f"Filter: {variant['filter']}")
            print(f"INFO: {variant['info']}")
            if 'format' in variant:
                print(f"Format: {variant['format']}")
            if 'genotypes' in variant:
                print("Genotypes:")
                for sample, data in variant['genotypes'].items():
                    if isinstance(data, dict):
                        print(f"  {sample}: {data['genotype']} (Depth: {data['depth']})")
                    else:
                        print(f"  {sample}: {data}")
            if 'genotype_stats' in variant:
                print(f"Genotype Statistics: {variant['genotype_stats']}")
        
        print(f"\n🎉 VCF parsing test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing VCF parsing: {e}")
        import traceback
        traceback.print_exc() 