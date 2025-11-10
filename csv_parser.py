import pandas as pd
import json
import os

def load_csv_data(csv_path):
    """
    Load and convert CSV data into a dictionary.
    Assumes only one product per row.
    """
    df = pd.read_csv(csv_path)
    if df.shape[0] > 1:
        print("Warning: More than one row detected. Only processing the first row.")
    
    data = df.iloc[0].dropna().to_dict()
    cleaned = {k.strip(): str(v).strip() for k, v in data.items()}
    print('CSV file loaded and cleaned:', cleaned)
    return cleaned


def merge_with_ocr(primary_staging_json, csv_data, original_filename):
    """
    Merge CSV data with OCR data (csv takes priority).
    """

    # Load primary staging JSON if path is given
    if not isinstance(primary_staging_json, dict):
        with open(primary_staging_json, 'r', encoding='utf-8') as f:
            primary_staging = json.load(f)
    else:
        primary_staging = primary_staging_json.copy()

    # Start with primary staging data
    merged_data = primary_staging.copy()

    # Override fields from CSV (CSV has priority)
    merged_data.update(csv_data)

    # OCR blocks: keep existing or add new ones if needed
    if "ocr_blocks" not in merged_data:
        merged_data["ocr_blocks"] = []
    else:
        merged_data["ocr_blocks"] = merged_data.get("ocr_blocks", [])
        
    # Create output filename
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    output_filename = f"{base_name}_secondary_staging.json"

    # Create output directory (../data/outputs relative to this file)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.abspath(os.path.join(output_dir, output_filename))

    # Save full JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=4)

    print(f"Secondary JSON saved to: {output_path}")

    return merged_data
