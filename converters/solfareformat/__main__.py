import sys
from .converter import convert

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.solfareformat <input.txt> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert(input_file, output_file)
