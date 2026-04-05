#!/usr/bin/env python3
"""
Solfa Text Reformatter
======================
Reformats .solfa/.txt tonic solfa files:
- Replaces multiple spaces with a single space
- Adds one space before and after : and ! separators (note lines only)

Note lines are identified by containing both : and ! separators.

Usage:
    python3 -m converters.solfafmt.converter <input.txt> [output.txt]
"""

import sys
import re
from pathlib import Path


def _is_note_line(line: str) -> bool:
    """A note line contains both : and ! separators."""
    return ':' in line and '!' in line


def _reformat_note_line(line: str) -> str:
    """Normalize spacing around : and ! separators in a note line."""
    # Collapse multiple spaces to one
    line = re.sub(r' +', ' ', line)

    # Normalize spacing: remove spaces around separators, then add exactly one
    line = re.sub(r'\s*:\s*', ' : ', line)
    line = re.sub(r'\s*!\s*', ' ! ', line)

    # Clean up any double spaces introduced
    line = re.sub(r' +', ' ', line)

    return line.strip()


def reformat(input_path: str, output_path: str = None):
    """Reformat a solfa text file."""
    input_p = Path(input_path)

    if output_path is None:
        output_path = str(input_p)

    output_p = Path(output_path)

    text = input_p.read_text(encoding="utf-8")
    lines = text.split('\n')
    result = []

    for line in lines:
        # Skip comment lines (optionally indented #)
        if line.lstrip().startswith('#'):
            pass
        elif _is_note_line(line):
            line = _reformat_note_line(line)
        else:
            # Non-note lines: only collapse multiple spaces
            line = re.sub(r' +', ' ', line)

        result.append(line)

    output_p.write_text('\n'.join(result), encoding="utf-8")
    print(f"Done: {output_p}")

    return str(output_p)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.solfafmt.converter <input.txt> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    reformat(input_file, output_file)


if __name__ == "__main__":
    main()
