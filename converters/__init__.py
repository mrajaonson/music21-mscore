"""Tonic Solfa Converter Suite

Four main converters:
- solfa2musicxml: Tonic Solfa → MusicXML (for MuseScore)
- solfa2pdf: Tonic Solfa → PDF (direct hymnal rendering)
- pdf2solfa: Digital PDF → Tonic Solfa text (text extraction + headers)
- pdfimg2solfa: Scanned PDF/Images → Tonic Solfa text (OCR + headers)

Usage:
    python3 -m converters.solfa2musicxml.converter input.txt
    python3 -m converters.solfa2pdf.converter input.txt
    python3 -m converters.pdf2solfa.converter input.pdf
    python3 -m converters.pdfimg2solfa.converter input.pdf
"""

__all__ = [
    "solfa2musicxml",
    "solfa2pdf",
    "pdf2solfa",
    "pdfimg2solfa",
]
