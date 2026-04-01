# Tonic Solfa Converter

A suite of converters for working with Tonic Solfa notation.

## Converters

- **solfa2musicxml** - Tonic Solfa text to MusicXML (for MuseScore, Finale, etc.)
- **solfa2pdf** - Tonic Solfa text to PDF (direct hymnal rendering)
- **pdf2solfa** - Digital PDF to Tonic Solfa text (text extraction + metadata headers)
- **pdfimg2solfa** - Scanned PDF/Images to Tonic Solfa text (OCR + metadata headers)

## Usage

```bash
python3 -m converters.solfa2musicxml.converter input.txt
python3 -m converters.solfa2pdf.converter input.txt
python3 -m converters.pdf2solfa.converter input.pdf
python3 -m converters.pdfimg2solfa.converter input.pdf
```

## Input Format

Solfa text files use a simple header + notation format:

```
:title: Amazing Grace
:composer: John Newton
:key: G
:tempo: 80
:timesig: 3/4

S d : r : m ! f : m : f
A m : d : d ! d : d : d
```

## Requirements

- Python 3.10+
- `pdftotext` (for pdf2solfa): `sudo apt install poppler-utils`

## License

See [LICENSE](LICENSE).
