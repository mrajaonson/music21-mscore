import sys
from .converter import convert_tonic_solfa_to_pdf

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m converters.solfa2pdf <input.txt> [output.pdf]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + '.pdf'

    convert_tonic_solfa_to_pdf(input_file, output_file)
