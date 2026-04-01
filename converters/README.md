# Tonic Solfa Converter Suite

Four specialized converters for tonic solfa notation:

## Converters

### 1. solfa2musicxml
**Solfa → MusicXML** (compatible with MuseScore 4)

Converts tonic solfa text notation to MusicXML, then optionally to PDF via MuseScore.

```bash
python3 -m converters.solfa2musicxml.converter sample.txt
```

**Requirements:**
- music21
- MuseScore 4 (optional, for PDF generation)

**Output:**
- `.xml` (MusicXML file for MuseScore)
- `.pdf` (if mscore is available)

---

### 2. solfa2pdf
**Solfa → PDF** (direct hymnal-style rendering)

Converts tonic solfa text directly to a traditional hymnal-style PDF with voice parts and aligned lyrics.

```bash
python3 -m converters.solfa2pdf.converter sample.txt [output.pdf]
```

**Requirements:**
- reportlab (PDF rendering)

**Output:**
- `.pdf` (hymnal-style PDF)

---

### 3. pdf2solfa
**Digital PDF → Solfa text** (text extraction)

Extracts text from digital (non-scanned) PDFs and wraps it with tonic solfa metadata headers.

```bash
python3 -m converters.pdf2solfa.converter input.pdf [output.txt]
```

Process:
1. `pdftotext -layout input.pdf output.txt` — extract text preserving layout
2. Add default solfa metadata headers (`:title:`, `:composer:`, etc.)

**Requirements:**
- `poppler-utils` (system package)

**Installation:**
```bash
sudo apt install poppler-utils
```

**Output:**
- `.txt` (solfa text with metadata headers to fill in)

---

### 4. pdfimg2solfa
**Scanned PDF / Images → Solfa text** (OCR-based)

Uses OCR (tesseract) to extract text from scanned PDFs or images and wraps it with tonic solfa metadata headers.

```bash
python3 -m converters.pdfimg2solfa.converter scanned.pdf [output.txt]
python3 -m converters.pdfimg2solfa.converter page.jpg [output.txt]
```

Process:
1. Convert PDF pages to high-resolution images (300 DPI)
2. Run tesseract OCR on each image
3. Add default solfa metadata headers

**Requirements:**
- `tesseract-ocr` (system package)
- Python packages: `pytesseract`, `pdf2image`, `Pillow`

**Installation:**
```bash
sudo apt install tesseract-ocr libtesseract-dev
pip install pytesseract pdf2image Pillow
```

**Output:**
- `.txt` (solfa text with metadata headers and OCR results)

**Note:** OCR results may contain errors. Review and correct:
- Metadata headers (`:title:`, `:composer:`, etc.)
- Note symbols (`d`, `r`, `m`, `f`, `s`, `l`, `t`)
- Measure separators (`|`) and beat separators (`:`)

---

## Shared Utilities

`shared/` contains common utilities:
- `solfa_spec.py` — Loads the tonic solfa notation spec from YAML
- `solfa_metadata.py` — Default metadata headers for converters

---

## Common Workflow

1. **Start with a scanned hymnal:**
   ```bash
   python3 -m converters.pdfimg2solfa.converter hymnal_page.pdf hymn.txt
   # Edit: hymn.txt (fix OCR errors, fill metadata headers)
   ```

2. **Convert to MusicXML + PDF:**
   ```bash
   python3 -m converters.solfa2musicxml.converter hymn.txt
   # Outputs: hymn.xml, hymn.pdf
   ```

   Or render directly to PDF without MuseScore:
   ```bash
   python3 -m converters.solfa2pdf.converter hymn.txt hymn_rendered.pdf
   ```

---

## Tonic Solfa Notation

The notation uses:
- **Notes:** `d` (do), `r` (re), `m` (mi), `f` (fa), `s` (sol), `l` (la), `t` (ti)
- **Octave modifiers:** `'` (up), `,` (down)
- **Barlines:** `|` (measure), `||` (double barline)
- **Beat separators:** `:` (beat separator), `.` (sub-beat)
- **Rest:** `*` (one beat), `**` (two beats)
- **Hold:** `-` (extend previous note)
- **Dynamics:** `(p)` (piano), `(f)` (forte), `(^)` (fermata)
- **Chords:** `<d.m.s>` (chord with notes separated by dots)

Example:
```
:title: Amazing Grace
:composer: John Newton
:key: G
:tempo: 80
:timesig: 4/4

S |d:d:d|r:.m:f|m:-:-:l|
A |m:m:m|d:.d:d|d:-:-:f|
T |l,:l,:l,|l,:l,:l,|l,:-:-:d|
B |g,:g,:g,|l,:.l,:l,|l,:-:-:-|

Amazing grace, how sweet the sound
```

---

## References

- **Music21:** https://music21.org/music21docs/
- **MuseScore:** https://musescore.org/
- **MusicXML:** https://www.musicxml.com/
- **Tesseract OCR:** https://github.com/UB-Mannheim/tesseract/wiki
