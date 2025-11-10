import re
import os
import json

# --- Section definitions ---
SECTION_KEYWORDS = {
    "nutrition": ["NUTRITION", "NUTRITIONAL INFORMATION", "NUTRITION FACTS", "NUTRITIONAL INFO", "NUTRITIONAL FACTS"],
    "ingredients": ["INGREDIENTS", "CONTAINS"],
    "allergen": ["ALLERGEN"],
    "mrp": ["MRP", "MAX RETAIL PRICE", "UNIT SALE PRICE", "UNIT PRICE", "PRICE", "COST", "COST PRICE"],
    "mfd": ["MFD", "USE BY", "BEST BEFORE", "EXPIRY", "EXPIRY DATE", "MANUFACTURED", "MANUFACTURING DATE"],
    "qty": ["QTY", "NET WEIGHT", "NET QTY", "WEIGHT", "VOLUME"],
}

# --- Nutrition heuristics (for filtering valid rows) ---
NUTRITION_NAME_HINTS = ["ENER", "CALOR", "PROT", "CARB", "SUG", "FIB", "FAT", "SAT", "TRANS", "SOD", "SALT"]
NUTRITION_KEEP_PREFIXES = ["NUTRITION", "NUTRITIONAL", "SERVE", "SERVING", "PER 100", "PER100", "%RDA"]
NUTRITION_EXCLUDE_HINTS = [
    "LIC.", "M.LIC", "FSSAI", "WWW", "HTTP", "BATCH", "BARCODE", "ADDRESS",
    "FIND US", "FACEBOOK", "SCAN", "APP:", "MKT.", "MANUFACTURER", "LICENSE"
]

def looks_like_nutrition_value(text: str) -> bool:
    return bool(re.search(r"\d+(\.\d+)?\s*(kcal|kj|g|mg|mcg|%)(?![A-Za-z])", text, re.IGNORECASE))

def is_nutrition_fact(text: str) -> bool:
    """Heuristic filter for valid nutrition table lines."""
    t = text.strip()
    up = t.upper()

    if any(up.startswith(pfx) for pfx in NUTRITION_KEEP_PREFIXES):
        return True
    if any(h in up for h in NUTRITION_EXCLUDE_HINTS):
        return False
    if looks_like_nutrition_value(t):
        return True

    letters = re.sub(r"[^A-Za-z]", "", t).upper()
    return any(h in letters for h in NUTRITION_NAME_HINTS)

# # --- Merge all boxes in each section into a single bbox ---
# def merge_sections_to_bbox(sectioned_groups, pad=0):
#     """
#     Given sectioned_groups from group_boxes_into_columns, return one bbox per section.
#     pad: optional pixel padding to expand each bbox on all sides.
#     """
#     section_bboxes = {}

#     for section, columns in sectioned_groups.items():
#         # columns is a dict: {x_anchor: [(box, text), ...], ...}
#         if not columns:
#             continue

#         all_boxes = []
#         for items in columns.values():
#             for box, _ in items:
#                 all_boxes.append(box)

#         if not all_boxes:
#             continue

#         x1 = min(b[0] for b in all_boxes) - pad
#         y1 = min(b[1] for b in all_boxes) - pad
#         x2 = max(b[2] for b in all_boxes) + pad
#         y2 = max(b[3] for b in all_boxes) + pad

#         # Clamp to >= 0 just in case
#         section_bboxes[section] = (max(0, int(x1)), max(0, int(y1)), int(x2), int(y2))

#     return section_bboxes

# --- Main grouping function ---
def group_boxes_into_columns(rec_boxes, texts, img_filename, tolerance=5, anchor_tolerance=500):
    """
    Group OCR boxes that start at approximately the same x_min.
    
    rec_boxes: list of [x_min, y_min, x_max, y_max]
    texts: list of OCR recognized strings
    tolerance: allowed difference in x_min
    """

    sectioned_groups = {section: {} for section in SECTION_KEYWORDS}  # each section will have column groups
    active_section = None  # Track which section we are inside
    section_x_anchor = None
    section_y_anchor = None   # track vertical start

    for box, text in zip(rec_boxes, texts):
        x_min, y_min, x_max, y_max = box

        # 1. Check if text matches any section keyword
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                active_section = section
                section_x_anchor = x_min
                section_y_anchor = y_min  
                break  # once we find a match, switch section
        
        # 2. If inside a section, group into columns
        if active_section:
            x_min = box[0]

            # --- X-axis anchor validation ---
            if section_x_anchor is not None and abs(x_min - section_x_anchor) > anchor_tolerance:
                continue  

            # --- Optional Y cutoff (avoid trailing junk far below section) ---
            if section_y_anchor is not None:
                # Nutrition tables are tall, allow more vertical space
                if active_section == "nutrition":
                    y_cutoff = 2000
                else:
                    # For small sections like qty/mrp/etc., only allow 300px
                    y_cutoff = 200  

                if (y_min - section_y_anchor) > y_cutoff:
                    active_section = None   # reset section
                    continue
                
            groups = sectioned_groups[active_section]
            
            # Find if there's an existing group within tolerance
            found_group = None
            for gx in groups:
                if abs(gx - x_min) <= tolerance:
                    found_group = gx
                    break
            
            # Add to found group or create new one
            if found_group is not None:
                groups[found_group].append((box, text))
            else:
                groups[x_min] = [(box, text)]

    # 3. Nutrition-specific filtering
    if sectioned_groups["nutrition"]:
        validated = []
        for col, items in sectioned_groups["nutrition"].items():
            for box, text in items:
                if is_nutrition_fact(text):
                    validated.append((box, text))

        print("\nValidated Nutrition Facts:")
        for box, text in validated:
            print(f"  {text} @ {box}")

    print("\n[ Grouped Boxes by Columns]")
    print(sectioned_groups)
    # Create output filename
    base_name = os.path.splitext(os.path.basename(img_filename))[0]
    output_filename = f"{base_name}_bounding_boxes.json"

    # Create output directory (../data/outputs relative to this file)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.abspath(os.path.join(output_dir, output_filename))

    # Save full JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sectioned_groups, f, ensure_ascii=False, indent=4)

    print(f"Sectioned Bounding Boxes JSON saved to: {output_path}")
    return sectioned_groups