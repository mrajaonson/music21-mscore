#!/usr/bin/env python3
"""
Digital PDF → Solfa Text Converter
===================================
Extracts text from digital PDFs, detects musical structure,
and adds solfa metadata headers.

Features:
- Text extraction using pdftotext -raw
- Automatic key detection: "Do dia KEY" pattern (e.g., "Do dia Eb" → KEY: Eb)
- Automatic time signature detection: "N/N" pattern (e.g., "4/4" → TIMESIG: 4/4)
- Barline normalization (| → !)
- Beat separator detection and normalization (:)
- Normalized spacing: one space before/after separators (: and !)

Notes processing:
- Lines with both : and | are identified as notes lines
- Barlines (|) are replaced with ! for better visibility
- Spacing is normalized: "d:r:m" → "d : r : m" and "f|s" → "f ! s"

Requirements:
    sudo apt install poppler-utils

Usage:
    python3 -m converters.pdf2solfa.converter <input.pdf> [output.txt]

Generates .txt with solfa metadata headers in the same directory as the input file.

Example output:
    :title: Amazing Grace
    :composer: John Newton
    :key: G
    :tempo: 80

    S d : r : m ! f : m : f
    A m : d : d ! d : d : d
"""

import sys
import subprocess
import re
from pathlib import Path
from ..shared import spec


def _build_default_headers() -> str:
    """Build default solfa metadata headers from spec defaults."""
    prefix = spec["header"]["prop_prefix"]
    suffix = spec["header"]["prop_suffix"]

    headers = []
    for prop_key, default_val in spec["defaults"].items():
        header_line = f"{prefix}{prop_key}{suffix} {default_val}"
        headers.append(header_line)

    return "\n".join(headers) + "\n"


DEFAULT_HEADERS_TEXT = _build_default_headers()


def _detect_key(text: str) -> str | None:
    """
    Detect the key signature from text.
    Looks for pattern: "Do dia KEY" where KEY is the key signature.

    Examples:
    - "Do dia Eb" → "Eb"
    - "Do dia C" → "C"
    - "DodiaG" → "G"
    - "DodiaEb" → "Eb"

    Returns: key string or None if not found
    """
    # Match "Do dia" (with or without spaces) followed by a key signature
    # Key signatures: C, D, E, F, G, A, B optionally followed by # or b
    match = re.search(r'Do\s*dia\s*([A-G][#b]?)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _detect_timesig(text: str) -> str | None:
    """
    Detect the time signature from text.
    Looks for the first occurrence of "N/N" pattern.

    Examples:
    - "4/4" → "4/4"
    - "3/4" → "3/4"
    - "6/8" → "6/8"

    Returns: timesig string or None if not found
    """
    match = re.search(r'(\d+)/(\d+)', text)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def _is_likely_solfa_line(line: str) -> bool:
    """Heuristic: does this line contain solfa notation?"""
    # Check for solfa note characters (d,r,m,f,s,l,t) with optional modifiers
    solfa_chars = set('drmslt')
    modifiers = set("',:*-|")

    # Count solfa-like characters
    solfa_count = sum(1 for c in line.lower() if c in solfa_chars)

    # Count barlines
    barline_count = line.count('|')

    # A solfa line should have:
    # - At least 2 solfa notes, AND
    # - At least 1 barline
    return solfa_count >= 2 and barline_count >= 1


def _normalize_barlines(text: str) -> str:
    """Normalize various barline representations to standard | and ||."""
    # Double barline variants
    text = re.sub(r'\|\|+', '||', text)  # || or more → ||
    text = re.sub(r'≠|║|║║', '||', text)  # Unicode/special chars → ||

    # Single barline
    text = re.sub(r'[¦‖]', '|', text)  # Unicode variants → |

    return text


def _normalize_beat_separators(text: str) -> str:
    """Normalize beat separators to : and sub-beat separators to .."""
    # Convert common separators: ; → : and ^ → .
    text = text.replace(';', ':')
    text = text.replace('^', '.')

    # Remove extra colons/dots
    text = re.sub(r':+', ':', text)
    text = re.sub(r'\.+', '.', text)

    return text


def _clean_text(text: str) -> str:
    """Clean extracted text for solfa processing."""
    lines = text.split('\n')
    cleaned = []

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()

        # Skip entirely blank lines
        if not line.strip():
            cleaned.append('')
            continue

        # For solfa lines, normalize notation
        if _is_likely_solfa_line(line):
            line = _normalize_barlines(line)
            line = _normalize_beat_separators(line)

            # Clean up spacing around barlines
            line = re.sub(r'\s*\|\s*', '|', line)
            line = re.sub(r'\s*:\s*', ':', line)
            line = re.sub(r'\s*\.\s*', '.', line)

        # Remove extra spaces
        line = re.sub(r' +', ' ', line)

        cleaned.append(line)

    return '\n'.join(cleaned)


def _is_notes_line(line: str) -> bool:
    """Check if line is a notes line (has both : and | separators)."""
    return ':' in line and '|' in line


def _process_notes_line(line: str) -> str:
    """
    Process a notes line:
    1. Replace | with !
    2. Normalize space: one space before and after separators (: and !)
    """
    # Replace | with !
    line = line.replace('|', '!')

    # Normalize spacing around : and !
    # Remove all spaces around these separators first
    line = re.sub(r'\s*:\s*', ':', line)
    line = re.sub(r'\s*!\s*', '!', line)

    # Add exactly one space before and after each separator
    line = re.sub(r':', ' : ', line)
    line = re.sub(r'!', ' ! ', line)

    # Clean up multiple spaces
    line = re.sub(r' +', ' ', line)

    # Remove leading/trailing spaces
    line = line.strip()

    return line


def _process_structure(text: str) -> str:
    """Process musical structure: normalize notes lines."""
    lines = text.split('\n')
    processed = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Keep blank lines as-is
            processed.append('')
            continue

        # Check if this is a solfa line (music notation with : and |)
        if _is_notes_line(line):
            # Process notes line (replace | with !, normalize spacing)
            line = _process_notes_line(line)

        processed.append(line)

    return '\n'.join(processed)


def convert(input_path: str, output_path: str = None, detect_structure: bool = True):
    """Convert digital PDF to solfa text with metadata headers."""
    input_p = Path(input_path)

    if output_path is None:
        output_path = str(input_p.with_suffix(".txt"))

    output_p = Path(output_path)

    print(f"Extracting text from: {input_p}")
    try:
        result = subprocess.run(
            ["pdftotext", "-raw", str(input_p), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        extracted_text = result.stdout
    except FileNotFoundError:
        print("Error: pdftotext not found. Install it with: sudo apt install poppler-utils")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting PDF: {e.stderr}")
        sys.exit(1)

    print("Processing extracted text...")

    # Clean and normalize text
    extracted_text = _clean_text(extracted_text)

    # Detect key and time signature from text
    detected_key = _detect_key(extracted_text)
    detected_timesig = _detect_timesig(extracted_text)

    print("  Detecting metadata...")
    if detected_key:
        print(f"    Key detected: {detected_key}")
    if detected_timesig:
        print(f"    Time signature detected: {detected_timesig}")

    # Build headers with detected values
    headers_lines = DEFAULT_HEADERS_TEXT.strip().split('\n')
    headers_dict = {}

    # Parse existing headers
    prefix = spec["header"]["prop_prefix"]
    suffix = spec["header"]["prop_suffix"]
    for header_line in headers_lines:
        if header_line.startswith(prefix):
            rest = header_line[len(prefix):]
            if suffix in rest:
                idx = rest.index(suffix)
                prop_key = rest[:idx].strip().lower()
                prop_val = rest[idx + len(suffix):].strip()
                headers_dict[prop_key] = prop_val

    # Update with detected values
    if detected_key:
        headers_dict["key"] = detected_key
    if detected_timesig:
        headers_dict["timesig"] = detected_timesig

    # Rebuild headers
    updated_headers = []
    for prop_key, prop_val in headers_dict.items():
        header_line = f"{prefix}{prop_key}{suffix} {prop_val}"
        updated_headers.append(header_line)
    updated_headers_text = "\n".join(updated_headers) + "\n"

    # Process musical structure (normalize notes lines)
    if detect_structure:
        print("  Normalizing notes lines...")
        extracted_text = _process_structure(extracted_text)

    # Combine headers + processed text
    full_text = updated_headers_text + "\n" + extracted_text

    # Write output
    print(f"Writing solfa text: {output_p}")
    output_p.write_text(full_text, encoding="utf-8")

    print(f"✓ Conversion complete: {output_p}")
    print("\nMetadata auto-detection:")
    if detected_key:
        print(f"  ✓ Key detected: {detected_key}")
    else:
        print("  ✗ Key not detected (add manually)")
    if detected_timesig:
        print(f"  ✓ Time signature detected: {detected_timesig}")
    else:
        print("  ✗ Time signature not detected (add manually)")
    print("\nNext steps:")
    print("  1. Review/edit metadata headers (:title:, :composer:, :author:, :key:, :tempo:, :timesig:, etc.)")
    print("  2. Add voice labels (S, A, T, B) at the start of each voice line")
    print("  3. Verify barline placement (!) and beat separators (:)")
    print("  4. Add lyrics lines below voice parts")
    return str(output_p)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.pdf2solfa.converter <input.pdf> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert(input_file, output_file)


if __name__ == "__main__":
    main()
