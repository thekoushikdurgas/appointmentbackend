"""Analyze Apollo URLs from CSV files and generate unmapped categories report."""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.apollo_analysis_service import ApolloAnalysisService


def find_apollo_url_column(header_row: List[str]) -> int:
    """Find the index of the apollo_url column in the CSV header."""
    for idx, col in enumerate(header_row):
        if col.strip().lower() == "apollo_url":
            return idx
    raise ValueError("apollo_url column not found in CSV header")


def analyze_unmapped_categories() -> Dict:
    """Analyze all Apollo URLs from CSV files and aggregate unmapped parameters."""
    service = ApolloAnalysisService()
    csv_dir = Path(__file__).parent / "lead360data"
    
    if not csv_dir.exists():
        print(f"Error: Directory not found: {csv_dir}")
        return {}
    
    # Track statistics
    total_urls = 0
    successful_analyses = 0
    failed_analyses = 0
    
    # Aggregate unmapped parameters
    unmapped_params_counter = Counter()  # param_name -> count
    unmapped_params_details = {}  # param_name -> {reason, sample_values, categories, urls}
    unmapped_categories_counter = Counter()  # category_name -> count
    category_to_params = defaultdict(set)  # category_name -> set of param names
    # MAX_URLS_PER_PARAM = 50  # Limit URLs stored per parameter to avoid huge JSON files
    
    # Track all parameters found
    all_params_counter = Counter()  # param_name -> count
    
    # Process each CSV file
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        print(f"Error: No CSV files found in {csv_dir}")
        return {}
    
    print(f"Found {len(csv_files)} CSV file(s) to process...")
    
    for csv_file in csv_files:
        print(f"\nProcessing: {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Read header
                
                try:
                    apollo_url_idx = find_apollo_url_column(header)
                except ValueError as e:
                    print(f"  Warning: {e} - Skipping file")
                    continue
                
                row_count = 0
                for row in reader:
                    if len(row) <= apollo_url_idx:
                        continue
                    
                    apollo_url = row[apollo_url_idx].strip()
                    if not apollo_url or not apollo_url.startswith("http"):
                        continue
                    
                    total_urls += 1
                    row_count += 1
                    
                    try:
                        # Analyze the URL
                        analysis = service.analyze_url(apollo_url)
                        
                        # Track all parameters
                        for param_name in analysis.raw_parameters.keys():
                            all_params_counter[param_name] += 1
                        
                        # Map to contact filters and get unmapped parameters
                        filter_dict, unmapped_dict = service.map_to_contact_filters(
                            analysis.raw_parameters, include_unmapped=True
                        )
                        
                        successful_analyses += 1
                        
                        # Aggregate unmapped parameters
                        for param_name, (values, reason) in unmapped_dict.items():
                            unmapped_params_counter[param_name] += 1
                            
                            # Store details if first time seeing this parameter
                            if param_name not in unmapped_params_details:
                                unmapped_params_details[param_name] = {
                                    "reason": reason,
                                    "sample_values": [],
                                    "categories": set(),
                                    "urls": []
                                }
                            
                            # Add URL (avoid duplicates)
                            url_list = unmapped_params_details[param_name]["urls"]
                            if apollo_url not in url_list:
                                url_list.append(apollo_url)
                            
                            # Add sample values (limit to 3 unique samples)
                            existing_samples = unmapped_params_details[param_name]["sample_values"]
                            for val in values[:3]:
                                if val not in existing_samples and len(existing_samples) < 3:
                                    existing_samples.append(val)
                            
                            # Find category for this parameter
                            for category in analysis.categories:
                                for param_detail in category.parameters:
                                    if param_detail.name == param_name:
                                        category_name = category.name
                                        unmapped_params_details[param_name]["categories"].add(category_name)
                                        category_to_params[category_name].add(param_name)
                                        unmapped_categories_counter[category_name] += 1
                                        break
                        
                    except Exception as e:
                        failed_analyses += 1
                        if failed_analyses <= 5:  # Only show first 5 errors
                            print(f"  Error analyzing URL (row {row_count}): {e}")
                
                print(f"  Processed {row_count} URLs from {csv_file.name}")
        
        except Exception as e:
            print(f"  Error reading {csv_file.name}: {e}")
            continue
    
    # Convert sets to lists for JSON serialization
    for param_name in unmapped_params_details:
        unmapped_params_details[param_name]["categories"] = list(
            unmapped_params_details[param_name]["categories"]
        )
    
    # Build report
    report = {
        "summary": {
            "total_urls": total_urls,
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "total_unique_parameters": len(all_params_counter),
            "total_unique_unmapped_parameters": len(unmapped_params_counter),
            "total_unmapped_occurrences": sum(unmapped_params_counter.values()),
        },
        "unmapped_parameters": [
            {
                "parameter_name": param_name,
                "frequency": count,
                "reason": unmapped_params_details[param_name]["reason"],
                "categories": unmapped_params_details[param_name]["categories"],
                "sample_values": unmapped_params_details[param_name]["sample_values"],
                "urls": unmapped_params_details[param_name]["urls"],
                "total_urls_found": count,  # Total URLs where this parameter appears
                "urls_in_report": len(unmapped_params_details[param_name]["urls"]),  # URLs stored in report
            }
            for param_name, count in unmapped_params_counter.most_common()
        ],
        "unmapped_categories": [
            {
                "category_name": category_name,
                "frequency": count,
                "parameters": sorted(list(category_to_params[category_name])),
            }
            for category_name, count in unmapped_categories_counter.most_common()
        ],
    }
    
    return report


def print_report(report: Dict):
    """Print a formatted report to console."""
    if not report:
        print("No data to report.")
        return
    
    summary = report["summary"]
    
    print("\n" + "=" * 80)
    print("APOLLO URL UNMAPPED CATEGORIES REPORT")
    print("=" * 80)
    
    print("\nSUMMARY STATISTICS:")
    print("-" * 80)
    print(f"Total URLs analyzed:           {summary['total_urls']}")
    print(f"Successful analyses:            {summary['successful_analyses']}")
    print(f"Failed analyses:               {summary['failed_analyses']}")
    print(f"Total unique parameters:       {summary['total_unique_parameters']}")
    print(f"Total unique unmapped params:  {summary['total_unique_unmapped_parameters']}")
    print(f"Total unmapped occurrences:     {summary['total_unmapped_occurrences']}")
    
    print("\n" + "=" * 80)
    print("UNMAPPED PARAMETERS (sorted by frequency)")
    print("=" * 80)
    
    unmapped_params = report["unmapped_parameters"]
    if not unmapped_params:
        print("\nNo unmapped parameters found!")
    else:
        for idx, param_info in enumerate(unmapped_params[:50], 1):  # Show top 50
            print(f"\n{idx}. {param_info['parameter_name']}")
            print(f"   Frequency: {param_info['frequency']} occurrences")
            print(f"   Reason: {param_info['reason']}")
            if param_info['categories']:
                print(f"   Categories: {', '.join(param_info['categories'])}")
            if param_info['sample_values']:
                samples = ', '.join(str(v) for v in param_info['sample_values'][:3])
                print(f"   Sample values: {samples}")
            
            # Show sample URLs (limit to 3 in console, all stored in JSON)
            urls = param_info.get('urls', [])
            if urls:
                total_urls = param_info.get('total_urls_found', len(urls))
                urls_in_report = param_info.get('urls_in_report', len(urls))
                print(f"   URLs found: {total_urls} total, {urls_in_report} in report")
                print(f"   Sample URLs (showing first 3):")
                for url_idx, url in enumerate(urls[:3], 1):
                    # Truncate long URLs for display
                    display_url = url if len(url) <= 100 else url[:97] + "..."
                    print(f"     {url_idx}. {display_url}")
                if len(urls) > 3:
                    print(f"     ... and {len(urls) - 3} more URLs (see JSON report for all)")
            else:
                print(f"   URLs: {param_info.get('total_urls_found', 0)} found")
    
    if len(unmapped_params) > 50:
        print(f"\n... and {len(unmapped_params) - 50} more unmapped parameters")
    
    print("\n" + "=" * 80)
    print("UNMAPPED CATEGORIES (sorted by frequency)")
    print("=" * 80)
    
    unmapped_categories = report["unmapped_categories"]
    if not unmapped_categories:
        print("\nNo unmapped categories found!")
    else:
        for idx, cat_info in enumerate(unmapped_categories, 1):
            print(f"\n{idx}. {cat_info['category_name']}")
            print(f"   Frequency: {cat_info['frequency']} occurrences")
            print(f"   Parameters ({len(cat_info['parameters'])}):")
            for param in cat_info['parameters'][:10]:  # Show first 10
                param_freq = next(
                    (p['frequency'] for p in unmapped_params if p['parameter_name'] == param),
                    0
                )
                print(f"     - {param} ({param_freq} occurrences)")
            if len(cat_info['parameters']) > 10:
                print(f"     ... and {len(cat_info['parameters']) - 10} more parameters")
    
    print("\n" + "=" * 80)
    print("REPORT COMPLETE")
    print("=" * 80)


def save_report_json(report: Dict, output_path: Path):
    """Save the report as JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to: {output_path}")
    except Exception as e:
        print(f"\nError saving report: {e}")


def main():
    """Main entry point."""
    print("Starting Apollo URL unmapped categories analysis...")
    
    # Analyze URLs
    report = analyze_unmapped_categories()
    
    if not report:
        print("No data collected. Exiting.")
        return
    
    # Print report to console
    print_report(report)
    
    # Save report to JSON file
    csv_dir = Path(__file__).parent / "lead360data"
    output_path = csv_dir / "unmapped_report.json"
    save_report_json(report, output_path)


if __name__ == "__main__":
    main()

