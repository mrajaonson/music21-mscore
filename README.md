# music21-mscore
music21 + musescore

## References

* https://music21.org/music21docs/
* https://musescore.org/fr
* https://www.musicxml.com/

## Requirements

* python 3.13

## Installation

```shell
# venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install system dependencies
brew install libb2 tesseract poppler

# configure music21
python3 -m music21.configure
```

## Use

```shell
python3 solfa2musicxml/main.py sample.txt
mscore -o sample.pdf sample.xml 2>/dev/null
```
