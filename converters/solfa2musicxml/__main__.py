import sys
from .converter import convert

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m converters.solfa2musicxml <input.txt>")
        sys.exit(1)

    convert(sys.argv[1])
