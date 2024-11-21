# app/services/ocr_service.py
import re
from datetime import datetime, timedelta
import easyocr
from pdf2image import convert_from_path
import cv2
import numpy as np
import os
import fitz
import torch

# Expected amount options to match different OCR formats
EXPECTED_AMOUNT_OPTIONS = ["4 99 ₸", "499 ₸", "4,99 ₸"]
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"

# Initialize EasyOCR reader for Russian language
reader = easyocr.Reader(['ru'], gpu=torch.cuda.is_available())

def extract_text_from_pdf(pdf_path):
    # Extracts text directly from a PDF if it's selectable text
    with fitz.open(pdf_path) as pdf_document:
        text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()  # Get all text from each page
    return text

def convert_pdf_to_images(pdf_path):
    # Convert each page of the PDF to an image
    images = convert_from_path(pdf_path)
    image_paths = []
    
    # Save each page as an image file
    for i, image in enumerate(images):
        image_path = f"page_{i}.png"
        image.save(image_path, "PNG")
        image_paths.append(image_path)
    
    return image_paths

def preprocess_image(image_path):
    # Load image with OpenCV
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not loaded correctly, possibly due to an empty or invalid file.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding to highlight text
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Denoise the image for clarity
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)

    # Save the preprocessed image for OCR
    preprocessed_image_path = "preprocessed_image.png"
    cv2.imwrite(preprocessed_image_path, gray)
    return preprocessed_image_path

def process_receipt(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    
    # Step 2: If no text is found, fall back to OCR
    if not text.strip():
        print("No selectable text found in PDF. Falling back to OCR.")
        image_paths = convert_pdf_to_images(pdf_path)
        full_text = ""
        for image_path in image_paths:
            # Perform OCR on each image page
            results = reader.readtext(image_path, detail=0)
            page_text = "\n".join(results)  # Combine text from OCR results
            full_text += page_text + "\n"
            os.remove(image_path)  # Clean up after processing
        return full_text
    
    return text  # Return directly extracted text if available

def validate_receipt(text):
    # First, check for exact matches in EXPECTED_AMOUNT_OPTIONS
    if not any(amount in text for amount in EXPECTED_AMOUNT_OPTIONS):
        # If not found, apply a strict regex for variations of 499 only
        if re.search(r"\b4[ ,]?99 ₸\b", text):  # Strictly matching "499" with allowed spaces or commas
            return True, "Valid amount", None
        else:
            return False, "Чек не прошел проверку суммы", None

    # Step 2: Match and Extract the Date
    date_match = re.search(
        r"Дата\s*\S*\s*время\s*[\S\s]*?(\d{2}\.\d{2}\.\d{4}\s*\d{2}[:\.]\d{2}[:\.]\d{2})", text, re.IGNORECASE
    )
    if not date_match:
        print("Date label not matched. Text OCR read:", text)
        return False, "Чек не прошел проверку даты", None
    
    # Extract the matched date string for debugging
    date_str = date_match.group(1)
    print("Extracted date string:", date_str)

    # Parse the extracted date using DATE_FORMAT
    try:
        transaction_date = datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        print("Date parsing failed for string:", date_str)
        return False, "Чек не прошел проверку даты", None

    # Check if the transaction date is within ±30 days of the current date
    current_date = datetime.now()
    if not (current_date - timedelta(days=2) <= transaction_date <= current_date + timedelta(days=2)):
        return False, "Чек не прошел проверку даты", None

    # Step 3: Extract Receipt Number
    receipt_number_match = re.search(r"№\s?чека\s?(QR\d+)", text, re.IGNORECASE)  # Adjusted to match QR prefix
    receipt_number = receipt_number_match.group(1) if receipt_number_match else None
    print("Extracted receipt number:", receipt_number)

    # Return three values consistently
    return True, "Receipt validated successfully", receipt_number