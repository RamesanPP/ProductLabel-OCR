import re
import unicodedata
from rapidfuzz import process, fuzz
from spellchecker import SpellChecker
import json
import os

# Custom dictionary
CUSTOM_DICTIONARY = [
    "Title", "Description", "Brand", "Ingredients", "Instructions", "Nutritional",
    "Facts", "Barcode", "GS1", "EAN", "Weight", "Height", "Width", "Volume",
    "COO", "UNSPSC", "Expiry", "Manufacturing", "Category", "Sub-category",
    "MRP", "Price", "MFD", "Best Before", "Use By"
]

# 43 fields list
FIELDS = [
    "Title", "Description", "Brand",
    "Bullet Point Heading 1", "Bullet Point Short Text 1", "Bullet Point Long Text A 1", "Bullet Point Long Text B 1", "Bullet Point Long Text C 1",
    "Bullet Point Heading 2", "Bullet Point Short Text 2", "Bullet Point Long Text A 2", "Bullet Point Long Text B 2", "Bullet Point Long Text C 2",
    "Icon - 1", "Icon - 2", "Icon - 3", "Icon - 4",
    "Weight", "Height", "Width", "Size/Volume", "Included Count", "Content Type/Sub-packages",
    "Ingredients", "Instructions", "Manufacturing Details", "Country of Origin (COO)",
    "Product Nature", "Package Type", "Category - 1", "Sub-category 1",
    "Category - 2", "Sub-category 2", "Nutritional Facts", "Barcode",
    "GSI EAN", "Color", "Industry", "Warnings", "Lifestyle Prompt",
    "UNSPSC", "Date of Manufacturing", "Expiry Date"
]

def process_ocr_text(raw_text, original_filename):
    extracted_data = {field: None for field in FIELDS}

    # ------------------ Step 1: Basic Cleaning ------------------
    text = unicodedata.normalize("NFKC", raw_text)
    text = re.sub(r'[^\x20-\x7E\n]', '', text)  # remove non-printable chars
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # remove non-ASCII chars
    text = re.sub(r'\s+', ' ', text)  # collapse spaces
    text = re.sub(r'[^A-Za-z0-9%/.,:\-\s]', '', text)  # allowed chars only
    text = text.strip()

    print("\n[Step 1 - Cleaned Text]")
    # print(text)

    # ------------------ Step 2: Spell Correction ------------------
    spell = SpellChecker()
    spell.word_frequency.load_words(CUSTOM_DICTIONARY)
    corrected_words = []
    for word in text.split():
        if word.lower() in spell:
            corrected_words.append(word)
        else:
            match = process.extractOne(word, CUSTOM_DICTIONARY, scorer=fuzz.ratio)
            if match and match[1] > 85:
                corrected_words.append(match[0])
            else:
                corrected_words.append(spell.correction(word) or word)
    text = " ".join(corrected_words)

    print("\n[Step 2 - Spell Corrected Text]")
    # print(text)

    # Create output filename
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    output_filename = f"{base_name}_primary_cleaned.json"

    # Create output directory (../data/outputs relative to this file)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.abspath(os.path.join(output_dir, output_filename))

    # Save full JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    print(f"Primary Cleaned JSON saved to: {output_path}")


    # ------------------ Step 3: Field-Specific Regex Extraction ------------------
    # Weight
    weight_match = re.search(r'(\d+\.?\d*)\s?(kg|g|mg|lb)', text, re.IGNORECASE)
    if weight_match:
        extracted_data["Weight"] = weight_match.group()

    # Size / Volume
    size_match = re.search(r'(\d+\.?\d*)\s?(ml|l|oz)', text, re.IGNORECASE)
    if size_match:
        extracted_data["Size/Volume"] = size_match.group()

    # Manufacturing Date (incl. MFD&USE BY)
    mfg_match = re.search(r'(MFD|Manufactured|Manufacturing|MFD&USE BY)[:\s-]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})?', text, re.IGNORECASE)
    if mfg_match:
        extracted_data["Date of Manufacturing"] = mfg_match.group(2) if mfg_match.group(2) else "unknown"

    # Expiry Date
    expiry_match = re.search(r'(EXP|Expiry|Best Before|Use By)[:\s-]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})?', text, re.IGNORECASE)
    if expiry_match:
        extracted_data["Expiry Date"] = expiry_match.group(2) if expiry_match.group(2) else "unknown"

    # Price detection
    price_match = re.search(r'(UNIT SALE PRICE|MRP RS\.?)[:\s-]*([0-9]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
    if price_match:
        extracted_data["Price"] = price_match.group(2)

    # Barcode
    barcode_match = re.search(r'\b\d{8,13}\b', text)
    if barcode_match:
        extracted_data["Barcode"] = barcode_match.group()

    print("\n[Step 3 - Regex Extraction]")
    print({k: v for k, v in extracted_data.items() if v is not None})

    # ------------------ Step 4: Multi-line Field Extraction ------------------
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    multiline_fields = {
        "Ingredients": ["ingredients", "contents"],
        "Nutritional Facts": ["nutrition", "nutritional facts", "per serving"]
    }

    def capture_multiline(idx):
        captured = []
        for j in range(idx + 1, len(lines)):
            if any(kw in lines[j].lower() for kws in multiline_fields.values() for kw in kws):
                break
            if not lines[j].strip():
                break
            captured.append(lines[j])
        return " ".join(captured).strip()

    for idx, line in enumerate(lines):
        for field, keywords in multiline_fields.items():
            if extracted_data[field] is None and any(k in line.lower() for k in keywords):
                val = capture_multiline(idx)
                if val:
                    extracted_data[field] = val

    print("\n[Step 4 - Multi-line Extraction]")
    print({k: v for k, v in extracted_data.items() if v is not None})

    # ------------------ Step 5: Keyword/Rule-Based Mapping ------------------
    # Only proceed for fields still None/empty
    fields_to_map = [f for f, v in extracted_data.items() if not v]

    # Tokenize into phrases (1- to 4-word ngrams)
    tokens = re.findall(r'\b\w+\b', text)
    ngrams = [
        ' '.join(tokens[i:i+n])
        for n in range(1, 5)  # up to 4-word phrases
        for i in range(len(tokens)-n+1)
    ]

    for field in fields_to_map:
        match = process.extractOne(
            field,
            ngrams,
            scorer=fuzz.partial_ratio
        )

        # Validate match before assigning
        if (
            match
            and match[1] > 85                # high similarity score
            and len(match[0]) > 2            # at least 3 characters
            and re.search(r'[A-Za-z]', match[0])  # has letters
        ):
            extracted_data[field] = match[0]
            
    print("\n[Step 5 - Keyword Mapping]")
    print({k: v for k, v in extracted_data.items() if v is not None})

    return extracted_data

def merge_with_boxes(ocr_data, box_data, original_filename):
    """
    Merge OCR data with CSV data based on the fields.
    - Keeps all fields from ocr_data (structured JSON).
    - If box_data has a corresponding field, it OVERRIDES ocr_data[field].
    """
    BOX_TO_FIELD = {
    "nutrition": "Nutritional Facts",
    "ingredients": "Ingredients",
    "allergen": "Warnings",   # or separate "Allergen" if you plan to add
    "mrp": "Price",
    "mfd": "Date of Manufacturing",
    "qty": "Weight"   # or "Size/Volume" depending on the use-case
    }

    merged_data = ocr_data.copy()
    print(merged_data)
    print(box_data)

    for section, field in BOX_TO_FIELD.items():
        if section in box_data and box_data[section]:
            collected_texts = []
            for col_items in box_data[section].values():
                for _, txt in col_items:
                    collected_texts.append(txt)

            merged_data[field] = " ".join(collected_texts).strip()

    # Create output filename
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    output_filename = f"{base_name}_primary_staging.json"

    # Create output directory (../data/outputs relative to this file)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.abspath(os.path.join(output_dir, output_filename))

    # Save merged JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=4)

    print(f"Primary Staging JSON saved to: {output_path}")

    return merged_data
