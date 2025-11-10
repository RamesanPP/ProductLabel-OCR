# ProductLabel-OCR
Intelligent OCR parsing for Product labels.

PREFACE

This is a documentation of the research done to implement an intelligent-label-parser solution as part of the product cataloguing pipeline at Is Going Online.

The research and documentation was done by Ajay Dev as of 15th August 2025.


Objective:
Build a pipeline that processes product label images and extracts key textual data fields into a well-structured JSON output, incorporating AI-based image segmentation, OCR, and LLM-based data refinement.

Input:
1. Image/images of a product label.
2. A CSV file with basic client-provided data (e.g., brand name, description, SKU ID, etc.).

Expected Output:
A fully structured JSON with 43 labeled fields such as:
1. Title
2. Description
3. Brand
4. Bullet Point Heading 1
5. Bullet Point Short Text 1
6. Bullet Point Long Text A 1
7. Bullet Point Long Text B 1
8. Bullet Point Long Text C 1
9. Bullet Point Heading 2
10. Bullet Point Short Text 2
11. Bullet Point Long Text A 2
12. Bullet Point Long Text B 2
13. Bullet Point Long Text C 2
14. Icon - 1
15. Icon - 2
16. Icon - 3
17. Icon - 4
18. Weight
19. Height
20. Width
21. Size/Volume
22. Included Count
23. Content Type/Sub-packages
24. Ingredients
25. Instructions
26. Manufacturing Details
27. Country of Origin (COO)
28. Product Nature
29. Package Type
30. Category - 1
31. Sub-category 1
32. Category - 2
33. Sub-category 2
34. Nutritional Facts
35. Barcode
36. GSI EAN
37. Color
38. Industry
39. Warnings
40. Lifestyle Prompt
41. UNSPSC
42. Date of Manufacturing
43. Expiry Date



WORKFLOW

Stage 1:

Before doing any operations on the image, preprocess it using OpenCV to enhance the accuracy of the text extracted.

Step 1: OpenCV Pipeline

    • Resizing – Upscaling image to make text clearer (uses interpolation)
    • Grayscale conversion
    • Bilateral Filtering
    • Thresholding (Otsu binarization)

PS: Deskewing and Morphological operations can be optionally applied after bounding box recognition is implemented. That way it will be applied only to text that requires it and not the whole image.


Results

While only converting to grayscale improves accuracy, applying all the filters enhances accuracy which is visible.

Also note: The OCR model used above was PaddleOCR

Step 2: OCR Extraction

In this step we have to choose which model we will be using for text extraction. While there are many models out there which can be used, we will look at the most popular ones and choose from among them that suits our use-case.

There is already a OCR comparator online which we can use:
https://huggingface.co/spaces/Loren/Streamlit_OCR_comparator

The comparator also draws bounding boxes for the texts it detects. This will be an added advantage for our use-case for labelling later on.

The most accurate results were from PPOCR and the bounding boxes were most accurate, while Tesseract failed to identify most boxes with accuracy.

Nonetheless, the results did not vary drastically between these models.

Conclusion:

We can either go with PaddleOCR (PPOCRv5) or TesseractOCR

So I went with both (for comparison).
My findings were that PaddleOCR takes a bit long to generate answers(approx. 2-5 mins to run depending on the hardware specs) and is compute intensive.
Meanwhile Tesseract is quick and provides somewhat similar accuracy(after processing the images).  


Step 3: Text Processing after OCR Extraction

Now from this raw ocr text we will try to match it with the 43 fields.
Before we do this, we need to preprocess the text (removing unwanted spaces and characters,etc)

Text Processing Pipeline:

    • Basic Cleaning: Removing non-printable chars, non-ASCII chars, and collapsing spaces.
    • Spell Correction: For this I used Spellchecker library and a Custom Dictionary (with known fields from a product label).  

CUSTOM_DICTIONARY = [
    "Title", "Description", "Brand", "Ingredients", "Instructions", "Nutritional",
    "Facts", "Barcode", "GS1", "EAN", "Weight", "Height", "Width", "Volume",
    "COO", "UNSPSC", "Expiry", "Manufacturing", "Category", "Sub-category",
    "MRP", "Price", "MFD", "Best Before", "Use By"]

    • Field-specific regex extraction for some known product label fields.   
      {Weight, Size/Volume, Manufacturing Date (incl. MFD & USE BY), Expiry Date, Price, Barcode	}
    • Multi-line field extraction: for Nutrional Facts and Ingredients
        {"Ingredients": ["ingredients", "contents"],
        "Nutritional Facts": ["nutrition", "nutritional facts", "per serving"]}

    • Rule-based keyword mapping: I used Rapidfuzz library for fuzzy matching. Only if match score more than 80, then match. Else I leave the field empty/Nill.


Results

We get a Primary_staging.json file with the 43 fields.
Still accuracy is not upto par. 


Both models and results are not satisfactory. Hence we will have to depend on an LLM on the next stage.


Before we move on to Stage 2, we can also work on Bounding box detection for specific labels which can come in handy. For this I’ve tried out both PaddleOCR and TesseractOCR. We will have to go with PaddleOCR as Tesseract’s boxes are not uniform and there are breaks in between straight lines.


So in this solution, I can see very good results using PaddleOCR.
We can maybe label this info by provided more training and maybe by running some algorithms(like iterating each box/nearby boxes for similarity in data so that we can club them together for labelling). 
This needs more R&D.

I also tried out the YOLOv8 model(more resource intensive).
It was able to pick up objects in the images but other than that, no labels or text was extracted. The model needs to be fine-tuned for label detection using a custom dataset. 


My final opinion is to train/modify the PaddleOCR to detect blocks of text for the product labels. 



Stage 2:

LLM Refinement Pipeline


Choosing a model:

 
Local LLM 
  - Resource intensive
  - Free
  - High compute time (anywhere from 2-10 mins)
    
Cloud API 
  - No local hardware needed
  - Paid API calls
  - Quick responses (<1 min)


So in the local LLM approach, we can go with any good models. I didn’t try out any model locally since my PC specs are a bit on the downside. But I did see a  Llama model running locally and getting responses inside 5 mins. There are also many lightweight HuggingFace models like LayoutLM that can do the job fairly fast without needing high compute times.


I went with Google’s Gemini API call which was fast and got good results.
When combining with PPOCR or Tesseract, the results were pretty much the same and now we get more than 80% accuracy.



Conclusion

LLM refinement is an unavoidable step in the Label parsing pipeline. 
Only debate is whether to use an LLM locally or through API calls, and that is where the question of Performance vs Cost arises.


Also we can skip the text processing step (Step 3 in Stage 1) and directly go for the LLM. There is an upside to this as well, we can skip the SpellCheck which also takes up a bit of time(from few seconds to 1 min). This can improve performance since we anyway have to go for LLM usage.



Stage 3:


In this stage, we implement the use-case where we cross-check the results with the CSV file data. This can be done in the end as that is not our priority. This can be done through code easily and I have implemented it already. It all ultimately depends if the CSV file has all the proper accurate data. In that case all our fields will be filled with correct information, thus ensuring 100% accuracy.
