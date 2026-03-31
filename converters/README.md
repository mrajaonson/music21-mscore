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
brew install --cask font-freefont

# configure music21
python3 -m music21.configure
```

## Use

```shell
python3 music21-mscore/s2m_converter.py sample.txt
```
