"""Parsing logic for tonic solfa .txt files."""

import re
from pathlib import Path

from models import NoteEvent

from config import (
    DEFAULTS, HEADER_STRING_PROPS, HEADER_INT_PROPS, HEADER_SPECIAL_PROPS,
    ALL_SOLFA_NOTES, SOLFA_TOKENS_SORTED, SOLFA_TO_SEMITONE,
    CHROMATIC_SHARP, CHROMATIC_FLAT,
    OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR,
    BEAT_SEPARATOR, SUBBEAT_SEPARATOR, HOLD, REST_STAR, REST_DOUBLE_STAR,
    NOTE_MELISMA_PREFIX, LYRICS_HYPHEN,
    VOICE_BASE_LABELS, DEFAULT_VOICE_ORDER,
    MODULATION_SEPARATOR, REPEAT_START, REPEAT_END, VOLTA_1_START,
    FINE, DA_CAPO_SEGNO,
)


# ──────────────────────────────────────────────────────────────────────
#  HEADER PARSING
# ──────────────────────────────────────────────────────────────────────

HEADER_KEYWORDS = HEADER_STRING_PROPS | HEADER_INT_PROPS | HEADER_SPECIAL_PROPS


def parse_header(lines: list[str]) -> tuple[dict, list[str]]:
    """Extract property lines from the top of the file."""
    props = dict(DEFAULTS)
    remaining = []
    header_done = False

    for line in lines:
        stripped = line.strip()
        if not header_done and stripped:
            parts = stripped.split(None, 1)
            keyword = parts[0].upper()
            if keyword in HEADER_KEYWORDS:
                if len(parts) == 2:
                    value = parts[1].strip()
                    if keyword in HEADER_INT_PROPS:
                        try:
                            props[keyword] = int(value)
                        except ValueError:
                            pass
                    elif keyword == "TIMESIG":
                        props[keyword] = value
                    else:
                        props[keyword] = value
                continue
            else:
                header_done = True
        if header_done or not stripped:
            if stripped:
                header_done = True
            remaining.append(line)
    return props, remaining


# ──────────────────────────────────────────────────────────────────────
#  NOTE TOKEN PARSING
# ──────────────────────────────────────────────────────────────────────

_DYNAMIC_PREFIX_RE = re.compile(r'^\(([^)]+)\)')


def _parse_single_token(s: str) -> tuple[NoteEvent | None, str]:
    """Parse one note token from the beginning of *s*."""
    if not s:
        return None, s

    # --- dynamic prefix ---
    dyn = None
    dm = _DYNAMIC_PREFIX_RE.match(s)
    if dm:
        dyn = dm.group(1)
        s = s[dm.end():]
        if not s:
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn), s

    # --- melisma prefix ---
    is_melisma = False
    if s.startswith(NOTE_MELISMA_PREFIX):
        is_melisma = True
        s = s[1:]
        if not s:
            return None, s

    # --- hold ---
    if s[0] == HOLD:
        return NoteEvent(is_hold=True, raw="-", dynamic=dyn), s[1:]

    # --- rest (* or **) ---
    if s.startswith(REST_DOUBLE_STAR):
        return NoteEvent(is_rest=True, raw="**", dynamic=dyn), s[2:]
    if s.startswith(REST_STAR):
        return NoteEvent(is_rest=True, raw="*", dynamic=dyn), s[1:]

    # --- solfa note (longest match) ---
    matched_solfa = None
    for tok in SOLFA_TOKENS_SORTED:
        if s.startswith(tok):
            matched_solfa = tok
            break
    if matched_solfa is None:
        if dyn:
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn), s
        return None, s

    s = s[len(matched_solfa):]
    semitone = ALL_SOLFA_NOTES[matched_solfa]
    is_sharp = matched_solfa in CHROMATIC_SHARP
    is_flat = matched_solfa in CHROMATIC_FLAT

    # --- octave modifiers ---
    octave_shift = 0
    while s and s[0] == OCTAVE_UP_CHAR:
        octave_shift += 1
        s = s[1:]
    while s and s[0] == OCTAVE_DOWN_CHAR:
        octave_shift -= 1
        s = s[1:]

    evt = NoteEvent(
        solfa=matched_solfa, semitone=semitone, octave_shift=octave_shift,
        is_melisma=is_melisma,
        is_chromatic_sharp=is_sharp, is_chromatic_flat=is_flat,
        raw=matched_solfa + OCTAVE_UP_CHAR * max(0, octave_shift)
                         + OCTAVE_DOWN_CHAR * max(0, -octave_shift),
        dynamic=dyn,
    )
    return evt, s


def parse_beat_tokens(beat_str: str) -> list[NoteEvent]:
    """Parse a beat string (between : separators) into NoteEvents."""
    beat_str = beat_str.strip()

    if not beat_str:
        return [NoteEvent(is_rest=True, raw=" ")]

    groups = beat_str.split(SUBBEAT_SEPARATOR)
    events: list[NoteEvent] = []

    for group in groups:
        g = group.strip()
        if not g:
            continue
        while g:
            evt, g = _parse_single_token(g)
            if evt is None:
                g = g[1:] if g else ""
            else:
                events.append(evt)

    if not events:
        return [NoteEvent(is_rest=True, raw=" ")]
    return events


# ──────────────────────────────────────────────────────────────────────
#  MEASURE / VOICE LINE PARSING
# ──────────────────────────────────────────────────────────────────────

_STRUCT_CHARS = {REPEAT_START, REPEAT_END, VOLTA_1_START, FINE, DA_CAPO_SEGNO}
_VOICE_LABEL_RE = re.compile(r'^([SATB]\d*)(?=\s|\t|\|)')


def _extract_voice_label(line: str) -> tuple[str | None, str]:
    """Strip a leading voice label from a note line."""
    stripped = line.strip()
    m = _VOICE_LABEL_RE.match(stripped)
    if m:
        return m.group(1), stripped[m.end():].strip()
    return None, stripped


def _split_measures(raw: str) -> list[str]:
    """Split a voice's bar content into measure strings."""
    raw = raw.strip().strip("|")
    raw = raw.replace("||", "|")
    return [m for m in raw.split("|")]


def _detect_structural_markers(measure_str: str) -> tuple[list[str], str]:
    """Pull out structural markers from a measure string."""
    markers = []
    cleaned = []
    for ch in measure_str:
        if ch in _STRUCT_CHARS:
            markers.append(ch)
        else:
            cleaned.append(ch)
    return markers, "".join(cleaned)


def _detect_modulation(beat_str: str) -> tuple[str | None, str]:
    """Check for a modulation marker like s/d inside a beat."""
    if MODULATION_SEPARATOR in beat_str:
        parts = beat_str.split(MODULATION_SEPARATOR, 1)
        left = parts[0].strip()
        right = parts[1].strip()
        left_valid = any(left.startswith(t) for t in SOLFA_TOKENS_SORTED)
        right_valid = any(right.startswith(t) for t in SOLFA_TOKENS_SORTED)
        if left_valid and right_valid:
            return f"{left}/{right}", ""
    return None, beat_str


def parse_voice_line(line: str) -> tuple[str | None, list]:
    """Parse one note line into (voice_label, list_of_measures)."""
    label, content = _extract_voice_label(line)
    raw_measures = _split_measures(content)

    measures = []
    for mstr in raw_measures:
        mstr = mstr.strip()
        if not mstr:
            continue
        markers, mstr_clean = _detect_structural_markers(mstr)

        beats_raw = mstr_clean.split(BEAT_SEPARATOR)
        beats = []
        modulations = []
        for b in beats_raw:
            mod, b_clean = _detect_modulation(b)
            if mod:
                modulations.append(mod)
            else:
                tokens = parse_beat_tokens(b_clean)
                beats.append(tokens)

        measures.append({
            "markers": markers,
            "beats": beats,
            "modulations": modulations,
        })

    return label, measures


# ──────────────────────────────────────────────────────────────────────
#  LYRICS PARSING
# ──────────────────────────────────────────────────────────────────────

_LYRICS_PREFIX_RE = re.compile(
    r'^(?:(?P<refrain>R)(?P<rvoice>[SATB]\d*)?|(?P<vnum>\d+)(?P<voice>[SATB]\d*)?)\s+'
)


def parse_lyrics_line(line: str) -> tuple[str | None, str | int, list[str]]:
    """Parse a lyrics line into (voice, verse_id, syllables)."""
    stripped = line.strip()
    voice = None
    verse_id: str | int = 1

    m = _LYRICS_PREFIX_RE.match(stripped)
    if m:
        if m.group("refrain"):
            verse_id = "R"
            if m.group("rvoice"):
                voice = m.group("rvoice")
        elif m.group("vnum"):
            verse_id = int(m.group("vnum"))
            if m.group("voice"):
                voice = m.group("voice")
        stripped = stripped[m.end():]

    syllables = []
    words = stripped.split()
    for word in words:
        parts = word.split(LYRICS_HYPHEN)
        for part in parts:
            syllables.append(part)

    return voice, verse_id, syllables


# ──────────────────────────────────────────────────────────────────────
#  FILE PARSING  (top-level)
# ──────────────────────────────────────────────────────────────────────

_BLOCK_DYNAMIC_RE = re.compile(r'^\(([^)]+)\)$')


def _is_note_line(line: str) -> bool:
    """Heuristic: a note line contains barlines |."""
    return "|" in line


def _is_block_dynamic(line: str) -> str | None:
    """Check if a line is a standalone block dynamic."""
    m = _BLOCK_DYNAMIC_RE.match(line.strip())
    return m.group(1) if m else None


def parse_file(filepath: str) -> dict:
    """
    Parse a tonic solfa .txt file.
    Returns dict with keys: properties, voices, lyrics.
    """
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.splitlines()

    props, remaining = parse_header(lines)

    voice_data: dict[str, list] = {}
    lyrics_data: dict[str, dict] = {}

    default_voice_order = list(DEFAULT_VOICE_ORDER)
    voice_index = 0
    prev_was_note_line = False
    last_voice_label = "S"
    pending_block_dynamic = None

    for line in remaining:
        stripped = line.strip()

        if not stripped:
            if prev_was_note_line:
                prev_was_note_line = False
            continue

        block_dyn = _is_block_dynamic(stripped)
        if block_dyn:
            pending_block_dynamic = block_dyn
            continue

        if _is_note_line(stripped):
            if not prev_was_note_line:
                voice_index = 0
            prev_was_note_line = True

            label, measures = parse_voice_line(stripped)
            if label is None:
                if voice_index < len(default_voice_order):
                    label = default_voice_order[voice_index]
                else:
                    label = f"V{voice_index + 1}"
                voice_index += 1
            else:
                voice_index += 1

            if pending_block_dynamic and measures:
                first_beat = measures[0].get("beats", [])
                if first_beat and first_beat[0]:
                    first_beat[0][0].dynamic = pending_block_dynamic
                pending_block_dynamic = None

            last_voice_label = label

            if label not in voice_data:
                voice_data[label] = []
            voice_data[label].extend(measures)

        else:
            prev_was_note_line = False

            voice, verse_id, syllables = parse_lyrics_line(stripped)
            if voice is None:
                voice = last_voice_label
            if voice not in lyrics_data:
                lyrics_data[voice] = {}
            if verse_id not in lyrics_data[voice]:
                lyrics_data[voice][verse_id] = []
            lyrics_data[voice][verse_id].extend(syllables)

    return {
        "properties": props,
        "voices": voice_data,
        "lyrics": lyrics_data,
    }
