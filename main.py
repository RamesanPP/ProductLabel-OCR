from flask import Flask, request, jsonify
import shutil
import os
from werkzeug.utils import secure_filename
import uuid

from csv_parser import load_csv_data, merge_with_ocr
from image_processor import preprocess_image
from ocr_extractor import extract_text
from text_processor import process_ocr_text, merge_with_boxes
from box_bounder import group_boxes_into_columns
from llm_refiner import run_gemini_refinement

app = Flask(__name__)

# Set upload folder to outputs directory in project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "../data/outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed extensions (optional but good practice)
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
ALLOWED_CSV_EXTENSIONS = {'csv'}

def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

@app.route('/ocr', methods=['POST'])
def ocr_api():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    img_file = request.files['image']
    filepath = os.path.join("temp", img_file.filename)
    os.makedirs("temp", exist_ok=True)
    img_file.save(filepath)
    csv_file = request.files.get('csv')

    # Validate CSV if provided
    csv_path = None
    if csv_file:
        if not allowed_file(csv_file.filename, ALLOWED_CSV_EXTENSIONS):
            return jsonify({"error": "Invalid CSV file format"}), 400
        csv_filename = secure_filename(f"{uuid.uuid4()}_data.csv")
        csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)
        csv_file.save(csv_path)
        csv_data = load_csv_data(csv_path)
    else:
        csv_data = {}

    if not allowed_file(img_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({"error": f"Invalid image file format: {img_file.filename}"}), 400

    # 1. Preprocess image
    processed_img = preprocess_image(filepath)

    # 2. Run OCR
    raw_ocr_data = extract_text(processed_img, img_file.filename)
    text = "\n".join(raw_ocr_data['res']['rec_texts'])

    # 3. Classify Section labels (Bounding Boxes)
    sectioned_groups = group_boxes_into_columns(raw_ocr_data['res']['rec_boxes'], raw_ocr_data['res']['rec_texts'], img_file.filename)
    
    # 4. Process OCR text
    processed_text = process_ocr_text(text, img_file.filename)
    primary_text = merge_with_boxes(processed_text, sectioned_groups, img_file.filename)

    # 5. Secondary cleanup using CSV data
    if csv_data:
        secondary_cleaned = merge_with_ocr(primary_text, csv_data, img_file.filename)

    # 6. LLM Refinement 
    final_json = run_gemini_refinement(processed_text, primary_text, secondary_cleaned, img_file.filename)

    # Cleanup temp directory
    if os.path.exists("temp"):
        shutil.rmtree("temp")

    return jsonify({"primary_staged_json": processed_text,
                    "secondary_staged_json": secondary_cleaned if csv_data else None,
                    "final_refined_json": final_json}), 200

if __name__ == "__main__":
    app.run(debug=False)
