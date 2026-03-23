#!/usr/bin/env python3
"""
Tonic Solfa .txt → MusicXML (.xml) converter
Output is compatible with MuseScore 4.

Usage:
    python3 solfa2xml.py <input.txt> [output.xml]
"""

import sys
from pathlib import Path

from solfa_parser import parse_file
from builder import build_score

OUTPUT_DIR = Path("outputs")

def convert(input_path: str, output_path: str | None = None):
    """Convert a tonic solfa .txt file to MusicXML."""
    input_p = Path(input_path)

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / input_p.with_suffix(".xml").name)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing: {input_p}")
    parsed = parse_file(str(input_p))

    props = parsed["properties"]
    print(f"  Title:    {props.get('TITLE')}")
    print(f"  Key:      {props.get('KEY')}")
    print(f"  Tempo:    {props.get('TEMPO')}")
    print(f"  TimeSig:  {props.get('TIMESIG')}")
    print(f"  Voices:   {list(parsed['voices'].keys())}")
    print(f"  Lyrics:   {list(parsed['lyrics'].keys())}")

    print("Building score …")
    score = build_score(parsed)

    print(f"Writing: {output_path}")
    score.write("musicxml", fp=output_path)
    print("Done.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 solfa2xml.py <input.txt> [output.xml]")
        print("  Converts tonic solfa notation to MusicXML for MuseScore 4.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert(input_file, output_file)


if __name__ == "__main__":
    main()
