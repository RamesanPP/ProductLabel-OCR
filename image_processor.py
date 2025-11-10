import cv2

def preprocess_image(image_path, resize_factor=2):
    # Read image
    img = cv2.imread(image_path)

    # Resize (upscale to make text clearer)
    img = cv2.resize(img, None, fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_CUBIC)
    print("Resized image to enhance text clarity.")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print("Converted image to grayscale.")

    # Apply bilateral filter to reduce noise while keeping edges sharp
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    print("Applied bilateral filter to reduce noise.")

    # Thresholding (Otsu) - separate pixels into two classes (foreground and background) based on their intensity values
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    print("Applied Otsu's thresholding to binarize the image.")

    # # Deskew
    # coords = cv2.findNonZero(thresh)
    # if coords is not None:
    #     angle = cv2.minAreaRect(coords)[-1]
    #     if angle < -45:
    #         angle = -(90 + angle)
    #     else:
    #         angle = -angle
    #     (h, w) = thresh.shape
    #     M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    #     # flags=cv2.INTER_CUBIC → smoother resampling || borderMode=cv2.BORDER_REPLICATE → extends edge pixels instead of filling with black
    #     thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    #     print(f"Deskewed image by {angle} degrees.")

    # # Morphological operations (close gaps in text)
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    # print("Created a rectangular structuring element for morphological operations.")
    # processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    # print("Morphological closing applied to close gaps in text.")

    # Convert grayscale processed image back to BGR before returning for compatibility with PPOCR
    processed_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    print("Converted processed image back to BGR format for compatibility with OCR.")

    return processed_bgr

