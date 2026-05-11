"""Unit tests for converters.pdfimg2solfa.converter."""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# Ensure optional imports don't block collection
import converters.pdfimg2solfa.converter as mod


# --- _build_default_headers ---

def test_build_default_headers_returns_string():
    result = mod._build_default_headers()
    assert isinstance(result, str)


def test_build_default_headers_ends_with_newline():
    result = mod._build_default_headers()
    assert result.endswith("\n")


def test_build_default_headers_contains_prop_prefix():
    from converters.shared import spec
    prefix = spec["header"]["prop_prefix"]
    result = mod._build_default_headers()
    assert prefix in result


def test_build_default_headers_contains_all_defaults():
    from converters.shared import spec
    result = mod._build_default_headers()
    for key in spec["defaults"]:
        assert key in result


# --- convert: unsupported file type ---

def test_convert_unsupported_extension_exits(tmp_path):
    fake = tmp_path / "score.xyz"
    fake.write_text("dummy")
    with pytest.raises(SystemExit):
        mod.convert(str(fake))


# --- convert: missing pytesseract exits ---

def test_convert_exits_when_pytesseract_unavailable(tmp_path):
    fake_pdf = tmp_path / "score.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    with patch.object(mod, "PYTESSERACT_AVAILABLE", False):
        with pytest.raises(SystemExit):
            mod.convert(str(fake_pdf))


# --- convert: PDF path (mocked OCR) ---

def test_convert_pdf_writes_output(tmp_path):
    fake_pdf = tmp_path / "score.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    output_txt = tmp_path / "score.txt"

    fake_image = MagicMock()

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.pdf2image", create=True) as mock_pdf2image, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pdf2image.convert_from_path.return_value = [fake_image]
        mock_tess.image_to_string.return_value = "d:r:m:f | s:l:t:d'"

        result = mod.convert(str(fake_pdf), str(output_txt))

    assert output_txt.exists()
    content = output_txt.read_text(encoding="utf-8")
    assert "d:r:m:f" in content
    assert result == str(output_txt)


def test_convert_pdf_default_output_path(tmp_path):
    fake_pdf = tmp_path / "score.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")

    fake_image = MagicMock()

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.pdf2image", create=True) as mock_pdf2image, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pdf2image.convert_from_path.return_value = [fake_image]
        mock_tess.image_to_string.return_value = "ocr text"

        result = mod.convert(str(fake_pdf))

    assert result == str(tmp_path / "score.txt")


def test_convert_pdf_output_contains_headers(tmp_path):
    fake_pdf = tmp_path / "score.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    output_txt = tmp_path / "score.txt"

    from converters.shared import spec
    prefix = spec["header"]["prop_prefix"]

    fake_image = MagicMock()

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.pdf2image", create=True) as mock_pdf2image, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pdf2image.convert_from_path.return_value = [fake_image]
        mock_tess.image_to_string.return_value = ""

        mod.convert(str(fake_pdf), str(output_txt))

    content = output_txt.read_text(encoding="utf-8")
    assert prefix in content


# --- convert: image path (mocked OCR) ---

def test_convert_image_png_writes_output(tmp_path):
    fake_png = tmp_path / "score.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n")
    output_txt = tmp_path / "score.txt"

    fake_image = MagicMock()

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.Image", create=True) as mock_pil, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pil.open.return_value = fake_image
        mock_tess.image_to_string.return_value = "d:r:m"

        result = mod.convert(str(fake_png), str(output_txt))

    assert output_txt.exists()
    assert result == str(output_txt)


def test_convert_image_jpg_extension_accepted(tmp_path):
    fake_jpg = tmp_path / "score.jpg"
    fake_jpg.write_bytes(b"\xff\xd8\xff")
    output_txt = tmp_path / "out.txt"

    fake_image = MagicMock()

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.Image", create=True) as mock_pil, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pil.open.return_value = fake_image
        mock_tess.image_to_string.return_value = ""

        result = mod.convert(str(fake_jpg), str(output_txt))

    assert result == str(output_txt)


# --- convert: multipage PDF concatenates pages ---

def test_convert_pdf_multipage_concatenates(tmp_path):
    fake_pdf = tmp_path / "score.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    output_txt = tmp_path / "score.txt"

    pages = [MagicMock(), MagicMock()]

    with patch.object(mod, "PYTESSERACT_AVAILABLE", True), \
         patch("converters.pdfimg2solfa.converter.pdf2image", create=True) as mock_pdf2image, \
         patch("converters.pdfimg2solfa.converter.pytesseract", create=True) as mock_tess:

        mock_pdf2image.convert_from_path.return_value = pages
        mock_tess.image_to_string.side_effect = ["page one text", "page two text"]

        mod.convert(str(fake_pdf), str(output_txt))

    content = output_txt.read_text(encoding="utf-8")
    assert "page one text" in content
    assert "page two text" in content
