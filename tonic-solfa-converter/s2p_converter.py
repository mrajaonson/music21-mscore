#!/usr/bin/env python3
"""
Tonic Solfa to PDF Renderer
============================
Parses tonic solfa notation and renders a traditional hymnal-style PDF
with aligned lyrics below each voice part.
"""

import sys
from s2p_solfa_pdf_renderer import TonicSolfaPDFRenderer
from s2p_solfa_parser import TonicSolfaParser

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def convert_tonic_solfa_to_pdf(input_path: str, output_path: str):
    """Main conversion function"""
    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Parse
    parser = TonicSolfaParser()
    song = parser.parse(text)

    # Render to PDF
    renderer = TonicSolfaPDFRenderer(song, output_path)
    renderer.render()

    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tonic_solfa_to_pdf.py <input.txt> [output.pdf]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + '.pdf'

    convert_tonic_solfa_to_pdf(input_file, output_file)
