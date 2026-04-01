#!/usr/bin/env python3
"""
Scanned PDF / Image → Solfa Text Converter (OCR)
==================================================
Extracts text from scanned PDFs or images using OCR (tesseract)
and adds solfa metadata headers.

Requirements:
    sudo apt install tesseract-ocr libtesseract-dev
    python3 -m pip install pytesseract

Supports:
    - PDF files (scanned or image-based)
    - PNG, JPG, TIFF images

Usage:
    python3 -m converters.pdfimg2solfa.converter <input.pdf|image> [output.txt]

Generates .txt with solfa metadata headers in the same directory as the input file.
"""

import sys
import subprocess
from pathlib import Path
from ..shared import spec

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


def _build_default_headers() -> str:
    """Build default solfa metadata headers from spec defaults."""
    prefix = spec["header"]["prop_prefix"]
    suffix = spec["header"]["prop_suffix"]

    headers = []
    for prop_key, default_val in spec["defaults"].items():
        header_line = f"{prefix}{prop_key}{suffix} {default_val}"
        headers.append(header_line)

    return "\n".join(headers) + "\n"


def convert(input_path: str, output_path: str = None):
    """Convert scanned PDF or image to solfa text via OCR."""
    if not PYTESSERACT_AVAILABLE:
        print("Error: Required packages not found.")
        print("Install with:")
        print("  pip install pytesseract pdf2image Pillow")
        print("  apt install tesseract-ocr libtesseract-dev")
        sys.exit(1)

    input_p = Path(input_path)

    if output_path is None:
        output_path = str(input_p.with_suffix(".txt"))

    output_p = Path(output_path)

    print(f"Processing: {input_p}")

    # Detect input type and convert to images
    images = []
    if input_p.suffix.lower() == ".pdf":
        print("Converting PDF to images...")
        try:
            images = pdf2image.convert_from_path(str(input_p), dpi=300)
        except Exception as e:
            print(f"Error converting PDF: {e}")
            sys.exit(1)
    elif input_p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        print("Loading image...")
        try:
            images = [Image.open(str(input_p))]
        except Exception as e:
            print(f"Error loading image: {e}")
            sys.exit(1)
    else:
        print(f"Error: Unsupported file type '{input_p.suffix}'")
        print("Supported: .pdf, .png, .jpg, .jpeg, .tiff, .bmp")
        sys.exit(1)

    # Run OCR on each image and concatenate
    print(f"Running OCR on {len(images)} page(s)...")
    extracted_text = ""
    for i, image in enumerate(images, 1):
        print(f"  Page {i}/{len(images)}...", end=" ", flush=True)
        try:
            text = pytesseract.image_to_string(image)
            extracted_text += text + "\n"
            print("done")
        except Exception as e:
            print(f"error: {e}")

    # Combine headers + extracted text
    full_text = _build_default_headers() + "\n" + extracted_text

    # Write output
    print(f"Writing solfa text: {output_p}")
    output_p.write_text(full_text, encoding="utf-8")

    print(f"✓ Conversion complete: {output_p}")
    print("Note: OCR results may contain errors. Please review and correct:")
    print("  - Metadata headers (:title:, :composer:, etc.)")
    print("  - Note symbols (d, r, m, f, s, l, t)")
    print("  - Measure separators (|) and beat separators (:)")
    return str(output_p)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.pdfimg2solfa.converter <input.pdf|image> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert(input_file, output_file)


if __name__ == "__main__":
    main()
