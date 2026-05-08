#!/usr/bin/env python3
"""
Tonic Solfa .txt → MusicXML (.xml) → PDF converter
Output is compatible with MuseScore 4.

Usage:
    python3 -m converters.solfa2musicxml.converter <input.txt>

Generates .xml and .pdf in the same directory as the input file.
"""

import sys
import subprocess
from pathlib import Path
from .solfa_parser import parse_file
from .builder import build_score


def convert(input_path: str):
    """Convert a tonic solfa .txt file to MusicXML, then to PDF."""
    input_p = Path(input_path)
    xml_path = input_p.with_suffix(".xml")

    print(f"Parsing: {input_p}")
    parsed = parse_file(str(input_p))

    props = parsed["properties"]
    print(f"  Title:    {props.get('title')}")
    print(f"  Key:      {props.get('key')}")
    print(f"  Tempo:    {props.get('tempo')}")
    print(f"  TimeSig:  {props.get('timesig')}")
    print(f"  Voices:   {list(parsed['voices'].keys())}")
    print(f"  Lyrics:   {list(parsed['lyrics'].keys())}")

    print("Building score …")
    score = build_score(parsed)

    print(f"Writing XML: {xml_path}")
    score.write("musicxml", fp=str(xml_path))

    if not xml_path.exists():
        print("Error: XML was not created.")
        sys.exit(1)
    print("XML done.")

    # Step 2: .xml → .pdf via MuseScore
    pdf_path = input_p.with_suffix(".pdf")
    print(f"Generating PDF: {pdf_path}")
    try:
        result = subprocess.run(
            ["mscore", "-o", str(pdf_path), str(xml_path)],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print("PDF done.")
        else:
            print("Warning: PDF generation failed.")
    except FileNotFoundError:
        print("Warning: mscore not found in PATH. Skipping PDF.")

    print("All done.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.solfa2musicxml.converter <input.txt>")
        sys.exit(1)

    convert(sys.argv[1])


if __name__ == "__main__":
    main()
