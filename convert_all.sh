#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <directory> [--solfa2pdf] [--solfa2musicxml] [--solfareformat] [--pdfimg2solfa] [--pdf2solfa]"
  exit 1
}

[ $# -lt 1 ] && usage

DIR="$1"; shift

[ -d "$DIR" ] || { echo "Error: '$DIR' is not a directory"; exit 1; }

RUN_SOLFA2PDF=0
RUN_SOLFA2MUSICXML=0
RUN_SOLFAREFORMAT=0
RUN_PDFIMG2SOLFA=0
RUN_PDF2SOLFA=0

for arg in "$@"; do
  case "$arg" in
    --solfa2pdf)      RUN_SOLFA2PDF=1 ;;
    --solfa2musicxml) RUN_SOLFA2MUSICXML=1 ;;
    --solfareformat)  RUN_SOLFAREFORMAT=1 ;;
    --pdfimg2solfa)   RUN_PDFIMG2SOLFA=1 ;;
    --pdf2solfa)      RUN_PDF2SOLFA=1 ;;
    *) echo "Unknown flag: $arg"; usage ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

run() {
  local label="$1"; shift
  echo "[$label] $*"
  (cd "$SCRIPT_DIR" && python3 "$@")
}

for f in "$DIR"/*.txt; do
  [ -e "$f" ] || continue
  [ $RUN_SOLFA2PDF -eq 1 ]      && run solfa2pdf      -m converters.solfa2pdf      "$f"
  [ $RUN_SOLFA2MUSICXML -eq 1 ] && run solfa2musicxml -m converters.solfa2musicxml "$f"
  [ $RUN_SOLFAREFORMAT -eq 1 ]  && run solfareformat  -m converters.solfareformat  "$f"
done

for f in "$DIR"/*.pdf; do
  [ -e "$f" ] || continue
  [ $RUN_PDFIMG2SOLFA -eq 1 ] && run pdfimg2solfa -m converters.pdfimg2solfa "$f"
  [ $RUN_PDF2SOLFA -eq 1 ]    && run pdf2solfa    -m converters.pdf2solfa    "$f"
done
