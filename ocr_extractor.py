from paddleocr import PaddleOCR
import os
import json

ocr = PaddleOCR(
    ocr_version="PP-OCRv5",
    lang="en",
    use_textline_orientation=True,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False
)

def extract_text(image, original_filename):
    """
    Runs OCR on the given image and saves the full JSON result
    to ../data/outputs/<filename>_primary_staging.json
    """
    results = ocr.predict(image)
    print("OCR processing completed.")

    for res in results:
        # res.print()  # Visual debug: prints text + scores + boxes
        data = res.json  # Structured dict output

        # Create output filename
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        output_filename = f"{base_name}_ocr_raw.json"

        # Create output directory (../data/outputs relative to this file)
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
        os.makedirs(output_dir, exist_ok=True)

        # Full output path
        output_path = os.path.abspath(os.path.join(output_dir, output_filename))

        # Save full JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"OCR JSON saved to: {output_path}")

        # print(rec_texts)
        # Optionally, you can also get scores:
        # rec_scores = data.get("rec_scores", None)

    return data
