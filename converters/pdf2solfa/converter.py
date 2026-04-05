#!/usr/bin/env python3
"""
Digital PDF → Solfa Text Converter
===================================
Extracts text from digital PDFs using pdftotext -layout,
detects metadata (title, key, time signature),
prepends solfa property headers, and replaces | with !.

The original layout from pdftotext is preserved as-is.

Requirements:
    sudo apt install poppler-utils

Usage:
    python3 -m converters.pdf2solfa.converter <input.pdf> [output.txt]
"""

import sys
import subprocess
import re
from pathlib import Path
from ..shared import spec


def _build_default_headers() -> dict:
    """Build default solfa metadata headers dict from spec defaults."""
    return dict(spec["defaults"])


def _detect_title(text: str) -> str | None:
    """Detect title from the first non-empty line (stripped)."""
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _detect_key(text: str) -> str | None:
    """Detect key from 'Do dia KEY' or 'DodiaKEY' pattern."""
    match = re.search(r'Do\s*dia\s*([A-G][#b]?)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _detect_timesig(text: str) -> str | None:
    """Detect time signature from first 'N/N' pattern."""
    match = re.search(r'(\d+)/(\d+)', text)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def _format_headers(headers: dict) -> str:
    """Format headers dict as solfa property lines."""
    prefix = spec["header"]["prop_prefix"]
    suffix = spec["header"]["prop_suffix"]
    lines = []
    for key, val in headers.items():
        if val is not None:
            lines.append(f"{prefix}{key}{suffix} {val}")
        else:
            lines.append(f"{prefix}{key}{suffix}")
    return "\n".join(lines)


# Build note token regex from spec (solfa_to_semitone + chromatic_sharp + chromatic_flat)
def _build_note_token_re() -> str:
    all_tokens = set()
    all_tokens.update(spec["notes"]["solfa_to_semitone"].keys())
    all_tokens.update(spec["notes"]["chromatic_sharp"].keys())
    all_tokens.update(spec["notes"]["chromatic_flat"].keys())
    # Sort longest first for greedy matching
    sorted_tokens = sorted(all_tokens, key=len, reverse=True)
    tokens_alt = "|".join(re.escape(t) for t in sorted_tokens)
    # A note token: one of the solfa tokens, optionally followed by octave modifiers (' ,)
    up = re.escape(spec["octave"]["up_char"])
    down = re.escape(spec["octave"]["down_char"])
    return rf"(?:{tokens_alt})[{up}{down}]*"

_NOTE_TOKEN = _build_note_token_re()


def _is_note_line(line: str) -> bool:
    """A note line contains : separators and note tokens."""
    return ':' in line and re.search(_NOTE_TOKEN, line) is not None


def _insert_measure_barlines(line: str) -> str:
    """Insert | where two note tokens are separated by space(s) only (no : or !)."""
    # Match: note_token + spaces + note_token (no : or ! between)
    pattern = rf'({_NOTE_TOKEN})(\s+)({_NOTE_TOKEN})'
    # Need to loop since matches can overlap
    prev = None
    while prev != line:
        prev = line
        line = re.sub(pattern, r'\1 | \3', line)
    return line


def _add_edge_barlines(line: str, beats_per_measure: int) -> str:
    """Add | at start/end of a note line if the edge segment is a full measure."""
    if '|' not in line:
        return line

    segments = line.split('|')

    # Check first segment (before first |)
    first = segments[0]
    if first.strip():
        beat_count = first.count(':') + first.count('!') + 1
        if beat_count == beats_per_measure:
            line = '| ' + line.lstrip()

    # Re-split for end check
    segments = line.split('|')

    # Check last segment (after last |)
    last = segments[-1]
    if last.strip():
        beat_count = last.count(':') + last.count('!') + 1
        if beat_count == beats_per_measure:
            line = line.rstrip() + ' |'

    return line


def convert(input_path: str, output_path: str = None):
    """Convert digital PDF to solfa text with metadata headers."""
    input_p = Path(input_path)

    if output_path is None:
        output_path = str(input_p.with_suffix(".txt"))

    output_p = Path(output_path)

    # 1. Extract text with pdftotext -layout
    print(f"Extracting text from: {input_p}")
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(input_p), "-"],
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

    # 2. Build default headers
    headers = _build_default_headers()

    # 3. Detect title
    detected_title = _detect_title(extracted_text)
    if detected_title:
        headers["title"] = detected_title
        print(f"  Title detected: {detected_title}")

    # 4. Detect key
    detected_key = _detect_key(extracted_text)
    if detected_key:
        headers["key"] = detected_key
        print(f"  Key detected: {detected_key}")

    # 5. Detect time signature
    detected_timesig = _detect_timesig(extracted_text)
    if detected_timesig:
        headers["timesig"] = detected_timesig
        print(f"  Time signature detected: {detected_timesig}")

    # 6. Replace en-dash with standard hyphen
    extracted_text = extracted_text.replace('\u2013', '-')

    # 7. Replace all | with ! (soft barlines)
    extracted_text = extracted_text.replace('|', '!')

    # 8. Detect measure barlines from layout gaps
    lines = extracted_text.split('\n')
    for i, line in enumerate(lines):
        if _is_note_line(line):
            lines[i] = _insert_measure_barlines(line)
    extracted_text = '\n'.join(lines)

    # 9. Add barlines at start/end of note lines if timesig is known
    if detected_timesig:
        beats_per_measure = int(detected_timesig.split('/')[0])
        lines = extracted_text.split('\n')
        for i, line in enumerate(lines):
            if _is_note_line(line):
                lines[i] = _add_edge_barlines(line, beats_per_measure)
        extracted_text = '\n'.join(lines)

    # Combine headers + extracted text (layout preserved)
    full_text = _format_headers(headers) + "\n\n" + extracted_text

    # Write output
    output_p.write_text(full_text, encoding="utf-8")
    print(f"Done: {output_p}")

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
