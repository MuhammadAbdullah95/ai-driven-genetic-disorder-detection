#!/usr/bin/env python3
"""
Simple VCF parser to test the sample VCF format without external dependencies
"""

def parse_vcf_simple(file_path: str):
    """Simple VCF parser that handles the sample VCF format"""
    try:
        print(f"Parsing VCF file: {file_path}")
        
        variants = []
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        print(f"Total lines in file: {len(lines)}")
        
        # Find the header line
        header_line = None
        for i, line in enumerate(lines):
            if line.startswith("#CHROM"):
                header_line = i
                break
        
        if header_line is None:
            raise ValueError("No #CHROM header found in VCF file")
        
        print(f"Header found at line {header_line + 1}")
        
        # Parse data lines
        for i, line in enumerate(lines[header_line + 1:], header_line + 2):
            line = line.strip()
            if not line:
                continue
                
            print(f"Processing line {i}: {line}")
            
            # Split by tab
            fields = line.split('\t')
            print(f"  Fields: {fields}")
            
            if len(fields) >= 8:
                # Standard VCF fields
                chrom, pos, rsid, ref, alt, qual, filt, info = fields[:8]
                
                # Additional fields (FORMAT and SAMPLE)
                format_field = fields[8] if len(fields) > 8 else ""
                sample_field = fields[9] if len(fields) > 9 else ""
                
                # Parse genotype data
                genotype_info = {}
                if sample_field and ':' in sample_field:
                    parts = sample_field.split(':')
                    genotype_info = {
                        "genotype": parts[0],  # GT part
                        "depth": parts[1] if len(parts) > 1 else "0",  # DP part
                        "raw": sample_field
                    }
                
                variant = {
                    "chromosome": chrom,
                    "position": int(pos),
                    "rsid": rsid if rsid != "." else ".",
                    "gene": "Unknown",  # No GENE field in sample VCF
                    "reference": ref,
                    "alternate": alt,
                    "quality": qual,
                    "filter": filt,
                    "info": info,
                    "format": format_field,
                    "genotypes": {"SAMPLE1": genotype_info} if genotype_info else {}
                }
                
                variants.append(variant)
                print(f"  ✅ Parsed variant: {chrom}:{pos} {ref}->{alt}")
                if genotype_info:
                    print(f"     Genotype: {genotype_info['genotype']} (Depth: {genotype_info['depth']})")
            else:
                print(f"  ⚠️  Skipping line with insufficient fields: {len(fields)}")
        
        print(f"\n🎉 Parsing completed! Found {len(variants)} variants")
        return variants
        
    except Exception as e:
        print(f"❌ Error parsing VCF: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("🧬 Testing VCF parsing with sample.vcf...")
    print("=" * 50)
    
    variants = parse_vcf_simple('sample.vcf')
    
    if variants:
        print(f"\n📋 Parsed Variants Summary:")
        print("=" * 50)
        for i, variant in enumerate(variants, 1):
            print(f"\n--- Variant {i} ---")
            print(f"📍 Location: {variant['chromosome']}:{variant['position']}")
            print(f"🆔 rsID: {variant['rsid']}")
            print(f"🧬 Change: {variant['reference']} → {variant['alternate']}")
            print(f"📊 Quality: {variant['quality']}")
            print(f"✅ Filter: {variant['filter']}")
            print(f"ℹ️  INFO: {variant['info']}")
            print(f"📝 Format: {variant['format']}")
            
            if variant['genotypes']:
                print("🧬 Genotypes:")
                for sample, data in variant['genotypes'].items():
                    print(f"  {sample}: {data['genotype']} (Depth: {data['depth']})")
        
        print(f"\n✅ VCF parsing test completed successfully!")
        print(f"📊 Total variants processed: {len(variants)}")
    else:
        print("❌ No variants were parsed successfully") 