import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# 43 required fields
REQUIRED_FIELDS = [
    "Title", "Description", "Brand", "Bullet Point Heading 1", "Bullet Point Short Text 1",
    "Bullet Point Long Text A 1", "Bullet Point Long Text B 1", "Bullet Point Long Text C 1",
    "Bullet Point Heading 2", "Bullet Point Short Text 2", "Bullet Point Long Text A 2",
    "Bullet Point Long Text B 2", "Bullet Point Long Text C 2", "Icon - 1", "Icon - 2", "Icon - 3", "Icon-4",
    "Weight", "Height", "Width", "Size/Volume", "Included Count", "Content Type/Sub-packages",
    "Ingredients", "Instructions", "Manufacturing Details", "Country of Origin (COO)",
    "Product Nature", "Package Type", "Category - 1", "Sub-category 1", "Category - 2",
    "Sub-category 2", "Nutritional Facts", "Barcode", "GSI EAN", "Color", "Industry", "Warnings",
    "Lifestyle Prompt", "UNSPSC", "Date of Manufacturing", "Expiry Date"
]

def construct_prompt(ocr_data, primary_staging, secondary_staging):
    base_prompt = f"""
    You are an intelligent product label parser.

    Given the following OCR data from a product label, first correct the text yourself because ocr data may be gibberish, and afterward return ONLY a valid JSON object that contains exactly the following 43 fields:

    {', '.join(REQUIRED_FIELDS)}.

    Rules:
    - Output ONLY valid JSON — no markdown, no commentary, no extra text.
    - Use empty string ("") or "N/A" for any missing fields.
    - Do not use markdown fences (like ```json).

    Here is the ocr data:
    {ocr_data}

    Try to correct text errors if present.
    I have already refined the data with primary and secondary processing steps. 
    So give most priority to secondary data, and then primary data. (meaning, if a field is present in both primary and secondary data, use the value from secondary data).
    Update the JSON with the corrected values.
    Once again, the secondary data has priority over primary data and may not be changed. If only you feel 100% sure there is error in secondary data, then you can change it. Otherwise leave it unchanged.

    Primary data is:
    {primary_staging}


    Secondary data is:
    {secondary_staging}

    """

    return base_prompt

def run_gemini_refinement(ocr_data, primary_staging, secondary_staging, original_filename):
    prompt = construct_prompt(ocr_data, primary_staging, secondary_staging)
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    raw_text = response.text.strip()
    # Remove markdown code fences if they exist
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")  # Remove all backticks
        # Remove 'json' label if present
        raw_text = raw_text.replace("json\n", "", 1).replace("json\r\n", "", 1)

    # Create output filename
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    output_filename = f"{base_name}_tertiary_staging.json"

    # Create output directory (../data/outputs relative to this file)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.abspath(os.path.join(output_dir, output_filename))

    try:
        final_json = json.loads(raw_text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Gemini output as JSON. Saving raw text.")
        final_json = {"raw_response": response.text}

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2)

    return final_json
